import numpy as np
import pytest

from inkbench import ensemble as E


def test_parse():
    assert E.parse("ens=readerv3,hecate") == ("ens", ["readerv3", "hecate"])
    for bad in ("ens", "ens=readerv3", "=a,b", "ens=a,a", "a=a,b"):
        with pytest.raises(ValueError):
            E.parse(bad)


def test_stretch_z_is_standardised_over_the_valid_pixels():
    rng = np.random.default_rng(0)
    m = rng.integers(0, 256, (200, 300)).astype(np.uint8)
    valid = m > 20
    z = E.stretch_z(m, valid)
    assert z[valid].mean() == pytest.approx(0.0, abs=1e-12) and z[valid].std() == pytest.approx(1.0, abs=1e-9)
    lo, hi = np.percentile(m[valid].astype(np.float64), [1.0, 99.5])
    s = np.clip((m.astype(np.float64) - lo) / (hi - lo), 0, 1)
    assert np.allclose(z, (s - s[valid].mean()) / s[valid].std())


def test_combine_is_the_rescaled_mean_z_score():
    rng = np.random.default_rng(1)
    a = rng.integers(1, 256, (120, 100)).astype(np.uint8)
    b = rng.integers(1, 256, (120, 100)).astype(np.uint8)
    a[:10] = 0
    b[:10] = 0                                                       # invalid in both: stays 0
    out = E.combine([a, b])
    valid = (a > 0) | (b > 0)
    z = (E.stretch_z(a, valid) + E.stretch_z(b, valid)) / 2
    want = (z[valid] - z[valid].min()) / (z[valid].max() - z[valid].min())
    assert out.dtype == np.float32 and np.allclose(out[valid], want, atol=1e-6)
    assert out[valid].min() == 0.0 and out[valid].max() == 1.0 and not out[~valid].any()
    assert E.combine([a[:15], b[:15]]) is None                     # 500 valid pixels: fewer than 1000


def test_combine_of_identical_members_keeps_the_ranking():
    rng = np.random.default_rng(2)
    a = rng.integers(1, 256, (64, 64)).astype(np.uint8)
    out = E.combine([a, a, a])
    order = np.argsort(a.ravel(), kind="stable")
    assert np.all(np.diff(out.ravel()[order]) >= -1e-7)
