"""Read-only fetching from the public open-data S3 bucket, Hugging Face and GitHub, resumable and verified.

Rules:
* A zarr level is mirrored from an authoritative S3 listing: every listed chunk is downloaded and its size checked;
  chunks the listing does not contain are genuinely absent (fill value). A failed or short download is retried and,
  if it keeps failing, the level stays un-gated. Nothing is ever written as a zero chunk on failure.
* Every file goes through ``<name>.part`` and an atomic rename, so an interrupted run resumes cleanly.
* A level counts as complete only when ``GATED.json`` exists (count, bytes and the listing digest).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Iterable, Optional, Sequence

from . import __version__

S3 = os.environ.get("INKBENCH_S3", "https://vesuvius-challenge-open-data.s3.us-east-1.amazonaws.com")
HF = "https://huggingface.co"
GH_RAW = "https://raw.githubusercontent.com"
UA = {"User-Agent": f"inkbench/{__version__} (+read-only open-data client)"}


class FetchError(RuntimeError):
    """A file could not be fetched completely."""


def _open(url: str, timeout: float = 120.0):
    req = urllib.request.Request(url, headers=UA)
    return urllib.request.urlopen(req, timeout=timeout)


def http_bytes(url: str, retries: int = 8, timeout: float = 120.0) -> bytes:
    """GET a small object fully into memory (listings, metadata), with backoff and Retry-After."""
    delay = 2.0
    for attempt in range(retries):
        try:
            with _open(url, timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise FileNotFoundError(url) from e
            wait = float(e.headers.get("Retry-After") or delay) if e.code in (429, 503) else delay
            if attempt == retries - 1:
                raise FetchError(f"{url}: HTTP {e.code}") from e
            time.sleep(min(wait, 120.0))
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
            if attempt == retries - 1:
                raise FetchError(f"{url}: {e}") from e
            time.sleep(delay)
        delay = min(delay * 2, 120.0)
    raise FetchError(url)


def sha256_file(path: str | os.PathLike, block: int = 1 << 22) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(block), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url: str, dest: str | os.PathLike, size: Optional[int] = None, sha256: Optional[str] = None,
             retries: int = 8, timeout: float = 300.0) -> Path:
    """Download ``url`` to ``dest`` (atomic). Skips a present file of the right size / hash. Raises FetchError."""
    dest = Path(dest)
    if dest.is_file() and (size is None or dest.stat().st_size == size):
        if sha256 is None or sha256_file(dest) == sha256:
            return dest
        dest.unlink()
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    delay = 2.0
    for attempt in range(retries):
        try:
            with _open(url, timeout) as r, open(part, "wb") as f:
                want = size
                if want is None and r.headers.get("Content-Length") and "gzip" not in (r.headers.get(
                        "Content-Encoding") or ""):
                    want = int(r.headers["Content-Length"])      # an early close must not pass as a complete file
                while True:
                    buf = r.read(1 << 22)
                    if not buf:
                        break
                    f.write(buf)
            got = part.stat().st_size
            if want is not None and got != want:
                raise FetchError(f"{url}: got {got} bytes, expected {want}")
            if sha256 is not None and sha256_file(part) != sha256:
                raise FetchError(f"{url}: sha256 mismatch")
            os.replace(part, dest)
            return dest
        except urllib.error.HTTPError as e:
            if e.code == 404:
                part.unlink(missing_ok=True)
                raise FileNotFoundError(url) from e
            err: Exception = e
            if e.code in (429, 503):
                delay = max(delay, float(e.headers.get("Retry-After") or delay))
        except (FetchError, urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
            err = e
        part.unlink(missing_ok=True)
        if attempt == retries - 1:
            raise FetchError(f"{url}: {err}")
        time.sleep(min(delay, 120.0))
        delay = min(delay * 2, 120.0)
    raise FetchError(url)


# ----------------------------------------------------------------------------------------------- S3 listing
def s3_list(prefix: str, delimiter: Optional[str] = "/") -> tuple[list[str], list[tuple[str, int]]]:
    """ListObjectsV2 of the public bucket: (common prefixes, [(key, size)]), all pages."""
    prefixes: list[str] = []
    files: list[tuple[str, int]] = []
    token = None
    while True:
        q = {"list-type": "2", "prefix": prefix}
        if delimiter:
            q["delimiter"] = delimiter
        if token:
            q["continuation-token"] = token
        x = http_bytes(f"{S3}/?{urllib.parse.urlencode(q)}").decode()
        prefixes += re.findall(r"<CommonPrefixes><Prefix>([^<]+)</Prefix>", x)
        files += [(k, int(s)) for k, s in re.findall(r"<Key>([^<]+)</Key>.*?<Size>(\d+)</Size>", x, flags=re.S)]
        m = re.search(r"<NextContinuationToken>([^<]+)</NextContinuationToken>", x)
        if not m:
            if "<IsTruncated>true</IsTruncated>" in x:
                raise FetchError(f"s3://{prefix}: truncated listing without a continuation token")
            return prefixes, files
        token = m.group(1)


def s3_url(key: str) -> str:
    return f"{S3}/{urllib.parse.quote(key)}"


def subdirs(prefix: str) -> list[str]:
    """Names (without trailing '/') of the immediate sub-folders of an S3 prefix."""
    pre, _ = s3_list(prefix.rstrip("/") + "/")
    return [p.rstrip("/").split("/")[-1] for p in pre]


def files_in(prefix: str) -> list[tuple[str, int]]:
    """(name, size) of the files directly in an S3 prefix."""
    _, files = s3_list(prefix.rstrip("/") + "/")
    return [(k.rsplit("/", 1)[-1], s) for k, s in files]


# ----------------------------------------------------------------------------------------------- zarr mirrors
def _parallel(tasks: Sequence[tuple[str, Path, Optional[int]]], threads: int) -> list[str]:
    errors: list[str] = []
    lock = threading.Lock()

    def one(t: tuple[str, Path, Optional[int]]) -> None:
        url, dest, size = t
        try:
            download(url, dest, size=size)
        except Exception as e:  # recorded, never written as zeros
            with lock:
                errors.append(f"{url}: {e}")

    with ThreadPoolExecutor(max_workers=threads) as pool:
        list(pool.map(one, tasks))
    return errors


def mirror_prefix(prefix: str, dest: str | os.PathLike, threads: int = 32,
                  keep: Optional[re.Pattern] = None) -> dict:
    """Mirror every object under ``prefix`` (recursive) into ``dest``; returns the gate record. Raises FetchError."""
    dest = Path(dest)
    gate = dest / "GATED.json"
    if gate.is_file():
        return json.loads(gate.read_text())
    prefix = prefix.rstrip("/") + "/"
    _, files = s3_list(prefix, delimiter=None)
    if keep is not None:
        files = [(k, s) for k, s in files if keep.search(k[len(prefix):])]
    if not files:
        raise FileNotFoundError(f"s3://{prefix}: no objects")
    tasks = [(s3_url(k), dest / k[len(prefix):], s) for k, s in files]
    errors = _parallel(tasks, threads)
    missing = [str(d) for _, d, s in tasks if not (d.is_file() and d.stat().st_size == s)]
    if errors or missing:
        raise FetchError(f"s3://{prefix}: {len(errors)} errors, {len(missing)} incomplete; rerun to resume. "
                         f"First: {(errors or missing)[0]}")
    digest = hashlib.sha256("\n".join(f"{k} {s}" for k, s in sorted(files)).encode()).hexdigest()
    rec = dict(prefix=prefix, n_objects=len(files), bytes=sum(s for _, s in files), listing_sha256=digest,
               fetched_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    gate.write_text(json.dumps(rec, indent=1))
    return rec


def mirror_zarr_level(zarr_prefix: str, dest: str | os.PathLike, level: str = "0", threads: int = 32) -> dict:
    """Mirror one pyramid level of an OME-Zarr v2 group (plus the group metadata) into ``dest``.

    Keeps the remote key layout, so the copied ``.zarray`` (dimension_separator "/") reads unchanged."""
    dest = Path(dest)
    zarr_prefix = zarr_prefix.rstrip("/")
    for meta in (".zgroup", ".zattrs"):
        try:
            download(s3_url(f"{zarr_prefix}/{meta}"), dest / meta)
        except FileNotFoundError:
            pass
    return mirror_prefix(f"{zarr_prefix}/{level}", dest / level, threads=threads)


def hf_url(repo: str, path: str, rev: str = "main", repo_type: str = "dataset") -> str:
    base = f"{HF}/datasets/{repo}" if repo_type == "dataset" else f"{HF}/{repo}"
    return f"{base}/resolve/{rev}/{urllib.parse.quote(path)}"


def gh_raw_url(owner_repo: str, commit: str, path: str) -> str:
    return f"{GH_RAW}/{owner_repo}/{commit}/{path}"


def fetch_many(items: Iterable[tuple[str, str | os.PathLike]], threads: int = 8) -> list[Path]:
    """Download (url, dest) pairs in parallel; raises FetchError listing the failures."""
    tasks = [(u, Path(d), None) for u, d in items]
    errors = _parallel(tasks, threads)
    if errors:
        raise FetchError(f"{len(errors)} downloads failed; first: {errors[0]}")
    return [d for _, d, _ in tasks]
