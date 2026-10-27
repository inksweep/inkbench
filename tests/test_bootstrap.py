import numpy as np
import pytest

from inkbench import bootstrap as B
from inkbench import metrics as M


def _maps(seed=0, shift=0.0, h=1024, w=1024):
    rng = np.random.default_rng(seed)
    lab = np.zeros((h, w), bool)
    lab[::64, :] = True
    lab = np.roll(lab, 3, 0) | lab
    score = rng.normal(0, 1, (h, w)) + (1.0 + shift) * lab
    q = np.clip((score + 3) / 8 * 255, 0, 255).astype(np.uint8)
    return q, lab, ~lab


def test_block_auc_equals_full_auc():
    q, pos, neg = _maps()
    sb = B.auc_blocks(q, pos, neg)
    assert sb.stat() == pytest.approx(M.auc_u8(q[pos], q[neg]), abs=1e-12)


def test_paired_bootstrap_identical_and_better():
    q, pos, neg = _maps(0)
    a = [B.auc_blocks(q, pos, neg)]
    same = B.paired_bootstrap(a, a, n_boot=200)
    assert same["diff"] == 0 and same["ci95"] == [0.0, 0.0]
    q2, _, _ = _maps(1, shift=1.0)
    better = B.paired_bootstrap([B.auc_blocks(q2, pos, neg)], a, n_boot=200)
    assert better["diff"] > 0 and better["ci95"][0] > 0 and better["p_diff_le_0"] == 0.0


def test_fa_and_hp_block_stats():
    rng = np.random.default_rng(2)
    pos_s = rng.integers(80, 256, (512, 512)).astype(np.uint8)
    blank = rng.integers(0, 200, (512, 512)).astype(np.uint8)
    m = np.ones((512, 512), bool)
    sb = B.fa_blocks(pos_s, m, blank, m)
    fa, _ = M.fa_at_recall(pos_s[m], blank[m])
    assert sb.stat() == pytest.approx(fa, abs=1e-12)
    a = rng.normal(size=(512, 512))
    b = a + rng.normal(size=(512, 512))
    hb = B.hp_blocks(a, b, m)
    assert hb.stat() == pytest.approx(np.corrcoef(a.ravel(), b.ravel())[0, 1], abs=1e-9)


def test_save_roundtrip_and_alignment():
    q, pos, neg = _maps()
    sb = B.auc_blocks(q, pos, neg)
    d = sb.save_dict("p|t")
    back = B.SegBlocks.from_dict({k: np.asarray(v) for k, v in d.items()}, "p|t")
    assert back.kind == "auc" and back.stat() == pytest.approx(sb.stat())
    half = B.SegBlocks("auc", {k: v[::2] for k, v in sb.arrays.items()}, {k: v[::2] for k, v in sb.block_ids.items()})
    r = B.paired_bootstrap([sb], [half], n_boot=50)
    assert r["diff"] == pytest.approx(0.0, abs=1e-12)          # aligned to the common blocks before comparing
