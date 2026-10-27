"""The gated mirror never caches a failed chunk and only gates a complete listing (no network: both calls faked)."""
import json

import pytest

from inkbench import remote


def _fake(monkeypatch, files, fail=()):
    monkeypatch.setattr(remote, "s3_list", lambda prefix, delimiter="/": ([], [(prefix + k, s) for k, s in files]))

    def dl(url, dest, size=None, sha256=None, **kw):
        if any(url.endswith(f) for f in fail):
            raise remote.FetchError("simulated 500")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"x" * size)
        return dest

    monkeypatch.setattr(remote, "download", dl)


def test_failed_chunk_is_not_gated_and_not_zero_filled(tmp_path, monkeypatch):
    _fake(monkeypatch, [("0/0/0", 10), ("0/0/1", 10)], fail=("0/0/1",))
    with pytest.raises(remote.FetchError):
        remote.mirror_prefix("S/x.zarr/0", tmp_path / "m")
    assert not (tmp_path / "m" / "GATED.json").exists()
    assert not (tmp_path / "m" / "0" / "0" / "1").exists()


def test_complete_listing_is_gated(tmp_path, monkeypatch):
    _fake(monkeypatch, [("0/0/0", 10), ("0/1/0", 7)])
    rec = remote.mirror_prefix("S/x.zarr/0", tmp_path / "m")
    assert rec["n_objects"] == 2 and rec["bytes"] == 17
    assert json.loads((tmp_path / "m" / "GATED.json").read_text())["listing_sha256"] == rec["listing_sha256"]
