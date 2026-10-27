"""Fetch and lay out every benchmark input (resumable; nothing is guessed from file names alone).

Per open-data segment ``<data>/<sample>/<folder>/``:
  sv/                level 0 of the native surface volume (gated mirror; ``sv/0/GATED.json``)
  teacher/<file>     the organisers' fine-scan ink map(s) of the segment (ink-detection/)
  labels/<vol>/<date>/{inklabels,supervision,validation}.zarr   human labels, level 0 (zarr v3, fine canvas)
  mesh/<name>.tifxyz/{meta.json,x.tif}    the coarse and fine meshes (grid sizes for the exact canvas map)
  segment.json       what was chosen and why, with sizes and gate records
PHerc1447 (HF) under ``<data>/PHerc1447/<winding>/`` and the IR truth under ``<data>/ir_truth/``.
"""
from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path
from typing import Optional

from . import paths, remote
from .catalog import BENCHMARKS, HF_1447, IR_TRUTH, Seg
from .zio import atomic_write_text, voxel_um_from_zattrs

LOG = logging.getLogger("inkbench.data")
NATIVE_SV = re.compile(r"^(7\.91|8\.64|9\.3\d*)um-.*\.zarr$")
FINE_SV = re.compile(r"^(2\.\d+|1\.\d+)um-.*volume-(\d{14})(-L\d)?\.zarr$")
VOL_ID = re.compile(r"volume-(\d{14})")
LABEL_KEEP = re.compile(r"^(inklabels|supervision|validation)\.zarr/(zarr\.json|\.zgroup|\.zattrs|0/.*)$")


def seg_dir(sample: str, folder: str) -> Path:
    return paths.data() / sample / folder


def _listing(sample: str) -> list[str]:
    cache = paths.data() / "_listings" / f"{sample}.json"
    if cache.is_file():
        return json.loads(cache.read_text())
    names = remote.subdirs(f"{sample}/segments/")
    atomic_write_text(cache, json.dumps(names))
    return names


def resolve(seg: Seg, names: Optional[list[str]] = None) -> str:
    """The unique open-data segment folder starting with ``seg.prefix``."""
    hits = [n for n in (names if names is not None else _listing(seg.sample)) if n.startswith(seg.prefix)]
    if len(hits) != 1:
        raise LookupError(f"{seg.sample}/{seg.prefix}: {len(hits)} matching segment folders {hits[:5]}")
    return hits[0]


def choose_native_sv(names: list[str]) -> str:
    hits = sorted(n for n in names if NATIVE_SV.match(n))
    if not hits:
        raise LookupError(f"no native surface volume among {names}")
    hits.sort(key=lambda n: ("-1.2m-" not in n, n))       # the 1.2 m scans first (the prize-eligible protocol)
    return hits[0]


def choose_teacher(files: list[str], kind: str, fine_vol: Optional[str]) -> Optional[str]:
    """Teacher map file name in ink-detection/ (tifs only, never the downsampled previews)."""
    tifs = [f for f in files if f.endswith(".tif")]
    if kind == "78kev":
        hits = [f for f in tifs if "78keV" in f and "autoresearch" in f]
    elif kind == "59kev":
        hits = [f for f in tifs if "59keV" in f]
    elif kind in ("same", "same2"):                         # same-scan team maps (PHerc0172: two TimeSformers)
        hits = sorted(f for f in tifs if re.search(r"-(7\.91|8\.64|9\.3\d*)um-", f))
        hits = hits[:1] if kind == "same" else hits[1:2]
    else:
        hits = [f for f in tifs if re.search(r"-2\.\d+um-", f)]
        if fine_vol:
            hits = [f for f in hits if fine_vol in f] or hits
        hits.sort(key=lambda f: ("new_canon" not in f, f))
    return hits[0] if hits else None


def meshes_for(names: list[str], vol_ids: list[str]) -> dict[str, str]:
    """The tifxyz mesh folder of each volume id (``*-on-<volume>-*.tifxyz``)."""
    out = {}
    for v in vol_ids:
        hit = [n for n in names if f"-on-{v}-" in n and n.endswith(".tifxyz")]
        if hit:
            out[v] = hit[0]
    return out


def prepare_segment(seg: Seg, need: tuple[str, ...] = ("sv", "teacher", "labels", "mesh"),
                    teacher_kinds: tuple[str, ...] = ("canon",), threads: int = 32) -> Path:
    """Fetch what a benchmark needs for one segment; returns the local folder (with segment.json)."""
    folder = resolve(seg)
    base = f"{seg.sample}/segments/{folder}"
    d = seg_dir(seg.sample, folder)
    d.mkdir(parents=True, exist_ok=True)
    rec_path = d / "segment.json"
    rec = json.loads(rec_path.read_text()) if rec_path.is_file() else {}
    rec.update(sample=seg.sample, folder=folder, tag=seg.tag)
    sv_names = remote.subdirs(f"{base}/surface-volumes/")
    native = choose_native_sv(sv_names)
    coarse_vol = VOL_ID.search(native).group(1)
    fine_svs = [n for n in sv_names if FINE_SV.match(n)]
    rec.update(native_sv=native, coarse_volume=coarse_vol, fine_svs=fine_svs)
    if "sv" in need:
        gate = remote.mirror_zarr_level(f"{base}/surface-volumes/{native}", d / "sv", "0", threads=threads)
        rec["sv_gate"] = gate
        rec["sv_voxel_um"] = voxel_um_from_zattrs(d / "sv")
    listed = dict(remote.files_in(f"{base}/ink-detection/")) if "teacher" in need else {}
    files = sorted(listed)
    teachers = {}
    fine_vol = None
    for kind in teacher_kinds if "teacher" in need else ():
        name = choose_teacher(files, kind, None)
        if name is None:
            LOG.warning("%s: no %s teacher map", folder, kind)
            continue
        remote.download(remote.s3_url(f"{base}/ink-detection/{name}"), d / "teacher" / name, size=listed[name])
        m = VOL_ID.search(name)
        teachers[kind] = dict(file=name, volume=m.group(1) if m else None,
                              um=(re.search(r"-(\d+\.\d+)um-", name) or [None, None])[1])
        if kind == "canon" and m:
            fine_vol = m.group(1)
    rec["teachers"] = teachers
    if "labels" in need:
        vols = remote.subdirs(f"{base}/ink-labels/") if _has(base, "ink-labels") else []
        labels = {}
        for v in vols:
            dates = sorted(remote.subdirs(f"{base}/ink-labels/{v}/"))
            if not dates:
                continue
            date = dates[-1]
            remote.mirror_prefix(f"{base}/ink-labels/{v}/{date}", d / "labels" / v / date, threads=8, keep=LABEL_KEEP)
            labels[v] = dict(date=date, volume=(VOL_ID.search(v) or [None, None])[1])
        rec["labels"] = labels
        if fine_vol is None and labels:
            fine_vol = next(iter(labels.values()))["volume"]
    rec["fine_volume"] = fine_vol
    if "mesh" in need:
        names = remote.subdirs(f"{base}/mesh/")
        vols = [v for v in (coarse_vol, fine_vol) if v] + [t["volume"] for t in teachers.values() if t.get("volume")]
        vols += [lab["volume"] for lab in (rec.get("labels") or {}).values() if lab.get("volume")]
        meshes = meshes_for(names, sorted(set(vols)))
        for v, name in meshes.items():
            sizes = dict(remote.files_in(f"{base}/mesh/{name}/"))
            for f in ("meta.json", "x.tif"):
                remote.download(remote.s3_url(f"{base}/mesh/{name}/{f}"), d / "mesh" / name / f, size=sizes.get(f))
        rec["meshes"] = meshes
    rec["prepared_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    atomic_write_text(rec_path, json.dumps(rec, indent=1))
    return d


def _has(base: str, sub: str) -> bool:
    return sub in remote.subdirs(f"{base}/")


def prepare_hf1447(winding: str) -> Path:
    """w058 / w060 from the pinned HF dataset revision, every file checked against its SHA256SUMS."""
    d = paths.data() / "PHerc1447" / winding
    repo, rev = HF_1447["repo"], HF_1447["rev"]
    sums_path = remote.download(remote.hf_url(repo, "SHA256SUMS", rev), paths.data() / "PHerc1447" / "SHA256SUMS")
    sums = {}
    for line in sums_path.read_text().splitlines():
        if line.strip():
            h, name = line.split(None, 1)
            sums[name.strip()] = h
    wanted = [n for n in sums if n.startswith(f"{winding}/") and
              (n.startswith(f"{winding}/layers/") or n.startswith(f"{winding}/labels/") or
               n.startswith(f"{winding}/tifxyz/") or n.startswith(f"{winding}/predictions/"))]
    if not any(n.startswith(f"{winding}/layers/") for n in wanted):
        raise LookupError(f"{winding}: no layers in SHA256SUMS")
    for n in wanted:
        remote.download(remote.hf_url(repo, n, rev), paths.data() / "PHerc1447" / n, sha256=sums[n])
    atomic_write_text(d / "segment.json", json.dumps(dict(sample="PHerc1447", folder=winding, source=HF_1447,
                                                          files=sorted(wanted), voxel_um=8.64), indent=1))
    return d


def prepare_irtruth() -> Path:
    """The camera-truth masks and published maps (GitHub, pinned commit), sizes checked."""
    d = paths.data() / "ir_truth"
    for f in IR_TRUTH["files"]:
        remote.download(remote.gh_raw_url(IR_TRUTH["repo"], IR_TRUTH["rev"], f), d / f, size=IR_TRUTH["sizes"][f])
    sums = {f: remote.sha256_file(d / f) for f in IR_TRUTH["files"]}
    atomic_write_text(d / "source.json", json.dumps(dict(IR_TRUTH, sha256=sums), indent=1))
    return d


#: What each benchmark kind needs per segment.
NEEDS = {"human": (("sv", "teacher", "labels", "mesh"), ("canon",)),
         "map": (("sv", "teacher", "labels", "mesh"), ("canon", "same")),
         "native78": (("sv", "teacher", "mesh"), ("78kev",)),
         "blank": (("sv", "teacher", "mesh"), ("78kev",)),
         "ir": (("sv", "mesh"), ()),
         "hp": (("sv", "teacher", "labels", "mesh"), ("canon",))}


def prepare(bench_names: list[str], threads: int = 32) -> dict[str, list[str]]:
    """Prepare every input of the named benchmarks; returns {benchmark: [local dirs]}."""
    out: dict[str, list[str]] = {}
    for name in bench_names:
        b = BENCHMARKS[name]
        dirs = []
        if b.kind == "hf1447":
            dirs = [str(prepare_hf1447(s.prefix)) for s in b.segs]
        else:
            need, kinds = NEEDS[b.kind]
            for s in b.segs:
                dirs.append(str(prepare_segment(s, need, kinds, threads=threads)))
            if b.kind == "ir":
                dirs.append(str(prepare_irtruth()))
        out[name] = dirs
        LOG.info("prepared %s: %d inputs", name, len(dirs))
    return out


def local_segment(seg: Seg) -> Path:
    """Local folder of a prepared segment (no network)."""
    if seg.sample == "PHerc1447":
        return paths.data() / "PHerc1447" / seg.prefix
    root = paths.data() / seg.sample
    hits = [p for p in root.iterdir() if p.is_dir() and p.name.startswith(seg.prefix)] if root.is_dir() else []
    if len(hits) != 1:
        raise LookupError(f"{seg.sample}/{seg.prefix}: prepared folder not found (run `inkbench fetch`)")
    return hits[0]
