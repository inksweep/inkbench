import numpy as np
import pytest

from inkbench import metrics as M


def brute_auc(pos, neg):
    pos = np.asarray(pos, float)[:, None]
    neg = np.asarray(neg, float)[None, :]
    return float(((pos > neg) + 0.5 * (pos == neg)).mean())


def test_auc_u8_and_rank_match_brute_force_with_ties():
    rng = np.random.default_rng(1)
    pos = rng.integers(0, 40, 300).astype(np.uint8) + 10
    neg = rng.integers(0, 40, 400).astype(np.uint8)
    want = brute_auc(pos, neg)
    assert M.auc_u8(pos, neg) == pytest.approx(want, abs=1e-12)
    assert M.auc_rank(pos.astype(float), neg.astype(float)) == pytest.approx(want, abs=1e-12)


def test_auc_russo_is_deterministic_and_close_to_full():
    rng = np.random.default_rng(2)
    pos = rng.integers(60, 256, 500_000).astype(np.uint8)
    neg = rng.integers(0, 200, 600_000).astype(np.uint8)
    a, b = M.auc_russo(pos, neg), M.auc_russo(pos, neg)
    assert a == b
    assert abs(a - M.auc_u8(pos, neg)) < 0.003
    assert M.auc_russo(pos[:50], neg) is None


def test_percentile_and_fa_from_hists_match_numpy():
    rng = np.random.default_rng(3)
    pos = rng.integers(0, 256, 10_001).astype(np.uint8)
    blank = rng.integers(0, 256, 7_000).astype(np.uint8)
    for q in (0, 20, 37.5, 50, 99, 100):
        assert M.percentile_from_hist(M.hist256(pos), q) == pytest.approx(float(np.percentile(pos, q)))
    fa, _ = M.fa_at_recall(pos, blank)
    assert M.fa_from_hists(M.hist256(pos), M.hist256(blank)) == pytest.approx(fa)


def test_native78_thresholds_follow_the_frozen_rule():
    t = np.repeat(np.arange(256, dtype=np.uint8), 100).reshape(256, 100)
    valid = np.ones_like(t, bool)
    lo, hi = M.native78_thresholds(t, valid)
    dom = t[t > 0]
    assert (dom <= lo).mean() >= 0.25 and (dom <= lo - 1).mean() < 0.25
    assert hi == max(128, int(np.searchsorted(np.cumsum(np.bincount(dom, minlength=256)) / dom.size, 0.85)))


def test_hp_score_perfect_and_null():
    rng = np.random.default_rng(4)
    from scipy.ndimage import gaussian_filter

    key = gaussian_filter(rng.random((600, 600)).astype(np.float32), 3)
    key = (key - key.min()) / (key.max() - key.min())
    valid = np.ones_like(key, bool)
    r = M.hp_score(key, key + 0.01, valid)
    assert r["hp_r"] > 0.99
    assert r["null_max"] < 0.2
    other = gaussian_filter(rng.random((600, 600)).astype(np.float32), 3) + 0.01
    assert abs(M.hp_score(key, other, valid)["hp_r"]) < 0.1


def test_ir_truth_score_separates_planted_letters():
    rng = np.random.default_rng(5)
    H, W = 400, 300
    valid = np.zeros((H, W), bool)
    valid[20:380, 20:280] = True
    ink = np.zeros_like(valid)
    ink[150:170, 60:240] = True
    from scipy import ndimage

    noink = valid & (ndimage.distance_transform_edt(~ink) >= 12)
    p = rng.random((H, W)).astype(np.float32) + 2.0 * ink
    d = M.ir_draws(ink, valid, n_perm=50, min_shift=60)       # the 250 px default needs a fragment-sized canvas
    assert len(d) == 50 and d == M.ir_draws(ink, valid, n_perm=50, min_shift=60)   # fixed seed
    r = M.ir_truth_score(p, ink, noink, valid, draws=d)
    assert r["auc"] > 0.95 and r["random_max"] < r["auc"] and r["p"] == pytest.approx(1 / 51)


def test_reference_storage():
    p = np.array([0.0, 0.4999, 0.5, 1.0, 1.2], np.float32)
    assert M.to_reference_u8(p, "u8_floor").tolist() == [0, 127, 127, 255, 255]
    assert M.to_reference_u8(p, "u8_round").tolist() == [0, 127, 128, 255, 255]


def test_tauil_auc_counts_ties_as_zero():
    pos = np.array([5, 5, 9], np.uint8)
    neg = np.array([5, 1], np.uint8)
    want = float(((pos[:, None] > neg[None, :])).mean())           # ties count 0
    assert M.auc_tauil(np.repeat(pos, 20), np.repeat(neg, 30)) == pytest.approx(want)
    assert M.auc_tauil(np.repeat(pos, 20).astype(float), np.repeat(neg, 30).astype(float)) == pytest.approx(want)


def test_auc_nieuwlaar_matches_rank_auc_below_the_cap():
    rng = np.random.default_rng(7)
    s = rng.random((100, 100))
    ink = s > 0.8
    noink = s < 0.3
    assert M.auc_nieuwlaar(ink, noink, s + rng.normal(0, 0.1, s.shape)) > 0.9
