"""File choices of the fetch stage (no network: the listings are given)."""
import pytest

from inkbench import data, paths
from inkbench.catalog import Seg


def test_native_sv_prefers_the_1_2m_scan():
    names = ["2.399um-0.22m-78keV-volume-20260102150214.zarr", "9.362um-0.22m-113keV-volume-20250101000000.zarr",
             "9.362um-1.2m-113keV-volume-20250728140407.zarr"]
    assert data.choose_native_sv(names) == "9.362um-1.2m-113keV-volume-20250728140407.zarr"
    with pytest.raises(LookupError):
        data.choose_native_sv(names[:1])


def test_teacher_choice():
    files = ["PHerc0139-x-2.399um-0.22m-78keV-volume-20260102150214-autoresearch.tif",
             "PHerc0139-x-2.399um-0.22m-78keV-volume-20260102150214-new_canon.tif",
             "PHerc0139-x-2.399um-0.22m-78keV-volume-20260102150214-new_canon.png",
             "PHerc0172-x-7.91um-volume-20250101000000-a.tif", "PHerc0172-x-7.91um-volume-20250101000000-b.tif"]
    assert data.choose_teacher(files, "canon", None).endswith("-new_canon.tif")
    assert data.choose_teacher(files, "78kev", None).endswith("-autoresearch.tif")
    assert data.choose_teacher(files, "same", None).endswith("-a.tif")
    assert data.choose_teacher(files, "same2", None).endswith("-b.tif")
    assert data.choose_teacher(files, "59kev", None) is None


def test_meshes_and_resolve():
    names = ["seg-on-20250728140407-x.tifxyz", "seg-on-20260102150214-y.tifxyz", "seg-on-20260102150214-y.obj"]
    assert data.meshes_for(names, ["20250728140407", "20260102150214", "20990101000000"]) == {
        "20250728140407": "seg-on-20250728140407-x.tifxyz", "20260102150214": "seg-on-20260102150214-y.tifxyz"}
    folders = ["20260220213127-w00", "20260220214732-auto_grown_20260220144552896"]
    assert data.resolve(Seg("PHerc0841", "20260220213127-w00", "w00"), folders) == "20260220213127-w00"
    with pytest.raises(LookupError):
        data.resolve(Seg("PHerc0841", "2026022", "x"), folders)


def test_local_segment_and_paths(tmp_path, monkeypatch):
    monkeypatch.setenv("INKBENCH_ROOT", str(tmp_path))
    for k in ("INKBENCH_DATA", "INKBENCH_RESULTS", "INKBENCH_PREDS", "INKBENCH_CKPT", "INKSWEEP_CKPT"):
        monkeypatch.delenv(k, raising=False)
    assert paths.data() == tmp_path / "data" and paths.preds() == tmp_path / "results" / "preds"
    assert paths.checkpoints() == tmp_path / "checkpoints" and paths.shared_checkpoints() is None
    monkeypatch.setenv("INKBENCH_PREDS", str(tmp_path / "elsewhere"))
    assert paths.preds() == tmp_path / "elsewhere" and paths.results() == tmp_path / "results"
    seg = Seg("PHerc0841", "20260220213127-w00", "w00")
    with pytest.raises(LookupError):
        data.local_segment(seg)
    (tmp_path / "data" / "PHerc0841" / "20260220213127-w00").mkdir(parents=True)
    assert data.local_segment(seg).name == "20260220213127-w00"
