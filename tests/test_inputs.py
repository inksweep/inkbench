import numpy as np

from inkbench.inputs import pick_crops
from inkbench.predict import ReaderRef, devices


def test_pick_crops_takes_the_best_two_without_overlap():
    valid = np.ones((6000, 6000), bool)
    score = np.zeros_like(valid)
    score[4000:5000, 4000:5000] = True                     # the best area
    score[0:600, 0:600] = True                             # second best
    crops = pick_crops(valid, score, crop=2048, step=256)
    assert len(crops) == 2
    (y0, x0), (y1, x1) = crops
    assert abs(y0 - y1) >= 2048 or abs(x0 - x1) >= 2048
    assert y0 <= 4000 and y0 + 2048 >= 5000 and x0 <= 4000 and x0 + 2048 >= 5000


def test_pick_crops_respects_the_valid_fraction():
    valid = np.zeros((3000, 3000), bool)
    valid[:, :1000] = True
    assert pick_crops(valid, valid, crop=2048, step=256) == []


def test_reader_ref_parse():
    assert ReaderRef.parse("readerv3") == ReaderRef("readerv3")
    r = ReaderRef.parse("mine=/x/plugin.py:/c/a.pt+/c/b.pt")
    assert r.name == "mine" and r.plugin == "/x/plugin.py" and r.checkpoints == ("/c/a.pt", "/c/b.pt")
    assert ReaderRef.parse("mine=/x/plugin.py").checkpoints == ()


def test_devices(monkeypatch):
    assert devices("0,2") == ["cuda:0", "cuda:2"]
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "5,6,7")
    assert devices() == ["cuda:0", "cuda:1", "cuda:2"]          # relative to the visible set
