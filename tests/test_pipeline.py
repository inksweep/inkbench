"""Score, ensemble, tables and the command line end to end on a synthetic PHerc1447 benchmark (CPU, no download).

Two readers' raw maps are laid out as ``inkbench predict`` writes them; the readers' map conventions come from
inksweep's registry (no weights are loaded).
"""
import json

import numpy as np
import pytest

pytest.importorskip("inksweep.readers")

import cv2  # noqa: E402
import tifffile  # noqa: E402

from inkbench import cli, ensemble, score, table  # noqa: E402

H, W = 800, 700
ENV = ("INKBENCH_DATA", "INKBENCH_RESULTS", "INKBENCH_PREDS", "INKBENCH_CKPT", "INKSWEEP_CKPT")


@pytest.fixture
def root(tmp_path, monkeypatch):
    monkeypatch.setenv("INKBENCH_ROOT", str(tmp_path))
    for k in ENV:
        monkeypatch.delenv(k, raising=False)
    rng = np.random.default_rng(0)
    for w in ("w058", "w060"):
        d = tmp_path / "data" / "PHerc1447" / w
        (d / "labels").mkdir(parents=True)
        (d / "layers").mkdir()
        lab = np.zeros((H, W), np.uint8)
        for y in range(240, 560, 80):
            lab[y:y + 30, 240:460] = 255                    # strokes, inside the >= 200 px edge rule too
        mask = np.zeros((H, W), np.uint8)
        mask[20:780, 20:680] = 255
        cv2.imwrite(str(d / "labels" / "inklabels.png"), lab)
        cv2.imwrite(str(d / "labels" / "mask.png"), mask)
        ct = np.zeros((H, W), np.uint8)
        ct[10:790, 10:690] = 120
        for k in range(3):
            tifffile.imwrite(d / "layers" / f"{k:02d}.tif", ct)
        (d / "segment.json").write_text(json.dumps({"sample": "PHerc1447", "folder": w, "voxel_um": 8.64}))
        for reader, gain in (("readerv3", 0.35), ("v8in", 0.2)):          # AUC about 0.95 and 0.82
            p = np.clip(rng.random((H, W)).astype(np.float32) * 0.5 + gain * (lab > 0), 0, 1)
            dst = tmp_path / "results" / "preds" / "PHerc1447" / w / "ink" / reader / "raw" / "reading" / "d+00.tif"
            dst.parent.mkdir(parents=True)
            tifffile.imwrite(dst, p)
    return tmp_path


def test_score_ensemble_and_tables(root):
    summary = score.score_benchmark("p1447", ["readerv3", "v8in"])
    assert summary["readerv3"]["hf_mask"] > summary["v8in"]["hf_mask"] > 0.5
    s = json.loads((root / "results" / "scores" / "p1447" / "readerv3.json").read_text())
    assert set(s["hf_mask"]["per_segment"]) == {"w058", "w060"}
    assert s["hf_mask"]["blind_orientation"] == {}                 # no blind-side maps were made
    assert set(s["hf_mask_edge200"]["per_segment"]) == {"w058", "w060"}

    rec = ensemble.run(["ens_test=readerv3,v8in"], ["p1447"])
    assert rec["ens_test"]["built"] == {"maps": 2, "skipped": 2}   # the blind sides are missing
    raw = tifffile.imread(root / "results" / "preds" / "PHerc1447" / "w058" / "ink" / "ens_test" / "raw" / "reading"
                          / "d+00.tif")
    assert raw.dtype == np.float32 and raw.min() == 0.0 and raw.max() == 1.0
    assert ensemble.registered() == {"ens_test": ["readerv3", "v8in"]}
    assert rec["ens_test"]["scores"]["p1447"]["hf_mask"] > summary["v8in"]["hf_mask"]
    with pytest.raises(ValueError):
        ensemble.run(["ens_test=readerv3,readerv2"], ["p1447"])   # the name is taken by other members

    text = table.render("readerv3", n_boot=50)
    assert "## p1447 (hf1447)" in text
    for r in ("ens_test", "readerv3", "v8in"):
        assert f"\n| {r} | 0." in text
    comp = json.loads((root / "results" / "COMPARISONS.json").read_text())
    assert {(c["reader"], c["protocol"]) for c in comp} == {
        (r, p) for r in ("ens_test", "v8in") for p in ("hf_mask", "hf_mask_edge200")}
    v8 = next(c for c in comp if c["reader"] == "v8in" and c["protocol"] == "hf_mask")
    assert v8["primary"] and v8["diff"] < 0 and v8["ci95"][1] < 0 and v8["n_boot"] == 50
    rep = json.loads((root / "results" / "REPRODUCTION.json").read_text())
    assert rep["counts"]["missing"] == 43                           # only readerv3's edge-200 row has scores
    row = next(r for r in rep["rows"] if r["protocol"] == "hf_mask_edge200" and r["reader"] == "readerv3")
    assert row["verdict"] == "FAIL"                                 # synthetic maps, not the published ones


def test_command_line(root, capsys):
    assert cli.main(["benchmarks"]) == 0
    out = capsys.readouterr().out
    assert "| p0841 | human | w00, ag896, ag405 |" in out and "| v2_heldout | map |" in out
    assert cli.main(["benchmarks", "--json"]) == 0
    assert len(json.loads(capsys.readouterr().out)) == 8
    assert cli.main(["--root", str(root), "score", "--bench", "p1447", "--readers", "readerv3,v8in"]) == 0
    assert cli.main(["--root", str(root), "reproduction"]) == 0
    assert cli.main(["--root", str(root), "reproduction", "--strict"]) == 3   # the synthetic row FAILs
    capsys.readouterr()
    assert cli.main(["--root", str(root), "compare", "v8in", "readerv3", "--n-boot", "20", "--bench", "p1447"]) == 0
    assert "| p1447 | hf_mask * | v8in |" in capsys.readouterr().out
    with pytest.raises(SystemExit):
        cli.main(["score", "--bench", "nope"])
