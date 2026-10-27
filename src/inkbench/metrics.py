"""Scores, each a transcription of the published rule it reproduces (so the numbers are comparable to the published
ones). The sources are MIT-licensed; NOTICE lists them with their copyright notices.

* ``auc_hist`` / ``auc_u8``: tie-aware Mann-Whitney AUC (P(pos > neg) + 0.5 P(tie)) from 256-bin histograms.
* ``auc_rank``: the same for float scores (average ranks of ties).
* ``auc_russo``: Reader v2's ``v2_run.auc`` (300 000 px per class drawn without replacement, rng seed 0, pos first).
* ``auc_tauil``: TAUIL's ``eval9v2.auc`` (ordinal ranks: a tied positive/negative pair counts 0).
* ``auc_nieuwlaar``: Nieuwlaar's ``native_bench.roc_auc`` selection (20 M-pixel subsample, seed 20260803).
* ``fa_at_recall``: Reader v2's ``bkill`` blank-segment rate: share of blank pixels >= the 20th percentile of the
  positives (80 % ink-pixel recall).
* ``native78_classes`` / ``nieuwlaar_fp_control``: Nieuwlaar ``native_bench.py`` (classes from the 78 keV map, and the
  component-recall operating point on w047 applied to blank w053).
* ``hp_score``: the letter-scale score (C. Scheirer, ShribyrLabs/vesuvius-reports report 02), Pearson r after a 48 um
  Gaussian high-pass, as TAUIL's ``hp_eval.score`` applies it.
* ``ir_truth_score``: DomRusso2/ir-truth-9um ``score_map.py`` (percentile quantisation, 2000 random placements).
All arrays are numpy; nothing here touches the GPU.
"""
from __future__ import annotations

from typing import Optional

import numpy as np


# ----------------------------------------------------------------------------------------------- AUC
def hist256(values: np.ndarray) -> np.ndarray:
    v = np.asarray(values)
    if v.dtype != np.uint8:
        raise TypeError(f"hist256 needs uint8, got {v.dtype}")
    return np.bincount(v.ravel(), minlength=256).astype(np.float64)


def auc_hist(hp: np.ndarray, hn: np.ndarray) -> float:
    """AUC from positive / negative histograms over the same ordered bins."""
    hp = np.asarray(hp, np.float64)
    hn = np.asarray(hn, np.float64)
    npos, nneg = hp.sum(), hn.sum()
    if npos <= 0 or nneg <= 0:
        return float("nan")
    below = np.cumsum(hn) - hn
    return float(((hp * below).sum() + 0.5 * (hp * hn).sum()) / (npos * nneg))


def auc_u8(pos: np.ndarray, neg: np.ndarray) -> float:
    return auc_hist(hist256(pos), hist256(neg))


def auc_rank(pos: np.ndarray, neg: np.ndarray) -> float:
    """Tie-aware AUC of float scores."""
    pos = np.asarray(pos, np.float64).ravel()
    neg = np.asarray(neg, np.float64).ravel()
    if pos.size == 0 or neg.size == 0:
        return float("nan")
    s = np.concatenate([pos, neg])
    order = np.argsort(s, kind="mergesort")
    srt = s[order]
    _, first, counts = np.unique(srt, return_index=True, return_counts=True)
    ranks = np.empty(s.size, np.float64)
    ranks[order] = np.repeat(first + (counts + 1) / 2.0, counts)
    return float((ranks[:pos.size].sum() - pos.size * (pos.size + 1) / 2.0) / (pos.size * neg.size))


def auc_any(pos: np.ndarray, neg: np.ndarray) -> float:
    if np.asarray(pos).dtype == np.uint8 and np.asarray(neg).dtype == np.uint8:
        return auc_u8(pos, neg)
    return auc_rank(pos, neg)


def auc_russo(pos: np.ndarray, neg: np.ndarray, n: int = 300_000, seed: int = 0,
              min_px: int = 100) -> Optional[float]:
    """Reader v2 ``v2_run.auc``: subsample each class (pos first, one generator), rank AUC, rounded to 4 places."""
    pos, neg = np.asarray(pos).ravel(), np.asarray(neg).ravel()
    if pos.size < min_px or neg.size < min_px:
        return None
    rng = np.random.default_rng(seed)
    sp = pos[rng.choice(pos.size, min(n, pos.size), replace=False)]
    sn = neg[rng.choice(neg.size, min(n, neg.size), replace=False)]
    return round(auc_any(sp, sn), 4)


def auc_tauil(pos: np.ndarray, neg: np.ndarray, n: int = 400_000, seed: int = 0) -> Optional[float]:
    """TAUIL ``eval9v2.auc``: one generator, each class subsampled only above 400 000 px, ordinal ranks of a stable
    sort with the positives first, so a tied positive/negative pair counts 0 (not 0.5): P(pos > neg)."""
    pos, neg = np.asarray(pos).ravel(), np.asarray(neg).ravel()
    if pos.size < 50 or neg.size < 50:
        return None
    rng = np.random.default_rng(seed)
    if pos.size > n:
        pos = rng.choice(pos, n, replace=False)
    if neg.size > n:
        neg = rng.choice(neg, n, replace=False)
    if pos.dtype == np.uint8 and neg.dtype == np.uint8:
        hp, hn = hist256(pos), hist256(neg)
        return float((hp * (np.cumsum(hn) - hn)).sum() / (hp.sum() * hn.sum()))
    allv = np.concatenate([pos, neg])
    rank = allv.argsort(kind="mergesort").argsort() + 1
    return float((rank[:pos.size].sum() - pos.size * (pos.size + 1) / 2) / (pos.size * neg.size))


def auc_nieuwlaar(ink: np.ndarray, noink: np.ndarray, score: np.ndarray, max_n: int = 20_000_000,
                  seed: int = 20260803) -> float:
    """``native_bench.roc_auc(ink[sel], p[sel])`` with ``sel = ink | noink``: tie-aware ranks, the selection (row-major
    order) subsampled to 20 M pixels with seed 20260803 when larger."""
    sel = ink | noink
    y = ink[sel].ravel()
    s = np.asarray(score)[sel].ravel().astype(np.float64)
    if y.size > max_n:
        idx = np.random.default_rng(seed).choice(y.size, size=max_n, replace=False)
        y, s = y[idx], s[idx]
    return auc_rank(s[y], s[~y])


# ----------------------------------------------------------------------------------------------- operating points
def percentile_from_hist(h: np.ndarray, q: float) -> float:
    """``np.percentile(values, q)`` (linear interpolation) of the uint8 values whose histogram is ``h``."""
    h = np.asarray(h, np.int64)
    n = int(h.sum())
    if n == 0:
        return float("nan")
    idx = q / 100.0 * (n - 1)
    lo, hi = int(np.floor(idx)), int(np.ceil(idx))
    c = np.cumsum(h)
    v_lo = int(np.searchsorted(c, lo + 1))
    v_hi = int(np.searchsorted(c, hi + 1))
    return float(v_lo + (v_hi - v_lo) * (idx - lo))


def fa_at_recall(pos: np.ndarray, blank: np.ndarray, recall: float = 0.8) -> tuple[float, float]:
    """(false-alarm share of ``blank`` at the threshold that keeps ``recall`` of ``pos``, the threshold)."""
    thr = float(np.percentile(np.asarray(pos).ravel(), 100.0 * (1.0 - recall)))
    return float((np.asarray(blank).ravel() >= thr).mean()), thr


def fa_from_hists(hpos: np.ndarray, hblank: np.ndarray, recall: float = 0.8) -> float:
    """``fa_at_recall`` for uint8 scores given as histograms (used inside the bootstrap)."""
    thr = percentile_from_hist(hpos, 100.0 * (1.0 - recall))
    hb = np.asarray(hblank, np.float64)
    if hb.sum() <= 0 or not np.isfinite(thr):
        return float("nan")
    return float(hb[int(np.ceil(thr - 1e-12)):].sum() / hb.sum())


# ----------------------------------------------------------------------------------------------- Nieuwlaar native bench
NATIVE_LO_FRAC, NATIVE_HI_PCT, NATIVE_HI_MIN = 0.25, 85, 128
NATIVE_FP_COMP_MIN_PX, NATIVE_FP_RECALL_FRAC, NATIVE_FP_TEACHER_RECALL = 1597, 0.10, 0.80


def native78_thresholds(teacher_u8: np.ndarray, valid: np.ndarray) -> tuple[int, int]:
    """lo = smallest uint8 value holding >= 25 % of the domain; hi = max(128, P85). Domain = valid & teacher > 0."""
    vals = teacher_u8[valid & (teacher_u8 > 0)]
    cdf = np.cumsum(np.bincount(vals, minlength=256).astype(np.float64)) / max(vals.size, 1)
    lo = int(np.searchsorted(cdf, NATIVE_LO_FRAC))
    hi = max(NATIVE_HI_MIN, int(np.searchsorted(cdf, NATIVE_HI_PCT / 100.0)))
    return lo, hi


def native78_classes(teacher_u8: np.ndarray, valid: np.ndarray) -> tuple[np.ndarray, np.ndarray, int, int]:
    lo, hi = native78_thresholds(teacher_u8, valid)
    dom = valid & (teacher_u8 > 0)
    return (teacher_u8 >= hi) & dom, (teacher_u8 <= lo) & dom, lo, hi


def nieuwlaar_pred(u8: np.ndarray) -> np.ndarray:
    """``native_bench.load_pred`` for the villa uint8 tif: ``clip((v - 64) / 128, 0, 1)``."""
    return np.clip((np.asarray(u8, np.float32) - 64.0) / 128.0, 0.0, 1.0)


def nieuwlaar_fp_control(ink_teacher_u8: np.ndarray, ink_valid: np.ndarray, ink_pred: np.ndarray,
                         blank_valid: np.ndarray, blank_pred: np.ndarray) -> dict:
    """theta* recalls 80 % of the teacher's ink components (>= 1597 px; recalled when >= 10 % of px >= theta) on the
    ink segment; returns the share of the blank segment's valid area >= theta*."""
    import cv2

    ink, _, _, _ = native78_classes(ink_teacher_u8, ink_valid)
    n_lab, cc = cv2.connectedComponents(ink.astype(np.uint8), connectivity=8)
    sizes = np.bincount(cc.ravel())
    keep = [i for i in range(1, n_lab) if sizes[i] >= NATIVE_FP_COMP_MIN_PX]
    if not keep:
        return dict(theta_star=float("nan"), component_recall=float("nan"), n_components=0,
                    blank_flagged_valid_frac=float("nan"))
    order = np.argsort(cc.ravel(), kind="stable")
    starts = np.searchsorted(cc.ravel()[order], np.arange(n_lab + 1))
    flat = np.asarray(ink_pred, np.float32).ravel()
    comp = np.array([np.percentile(flat[order[starts[i]:starts[i + 1]]], 100 * (1 - NATIVE_FP_RECALL_FRAC))
                     for i in keep])
    theta = float(np.percentile(comp, 100 * (1 - NATIVE_FP_TEACHER_RECALL)))
    return dict(theta_star=theta, component_recall=float((comp >= theta).mean()), n_components=len(keep),
                blank_flagged_valid_frac=float((np.asarray(blank_pred)[blank_valid] >= theta).mean()))


def misregistration_auc(score: np.ndarray, ink: np.ndarray, noink: np.ndarray, valid: np.ndarray,
                        shift_px: int = 214) -> dict:
    """Nieuwlaar's control: classes shifted ~2 mm or rotated 90 degrees must collapse toward 0.5."""
    import cv2

    out = {}
    tfs = {"shift_y": lambda m: np.roll(m, shift_px, axis=0), "shift_x": lambda m: np.roll(m, shift_px, axis=1),
           "rot90": lambda m: cv2.resize(np.rot90(m).astype(np.uint8), (m.shape[1], m.shape[0]),
                                         interpolation=cv2.INTER_NEAREST).astype(bool)}
    for name, tf in tfs.items():
        it = tf(ink) & valid
        nt = tf(noink) & valid & ~it
        out[name] = auc_any(score[it], score[nt]) if it.sum() >= 1000 and nt.sum() >= 1000 else float("nan")
    vals = [v for v in out.values() if v == v]
    out["max"] = max(vals) if vals else float("nan")
    return out


# ----------------------------------------------------------------------------------------------- letter scale
HP_SIGMA_PX = 20 / 3.9                  # 48 um at 9.362 um (kept in px on other grids, as TAUIL does)
HP_INKED_SIGMA_PX = 40 / 3.9


def _gauss(a: np.ndarray, sigma: float) -> np.ndarray:
    from scipy.ndimage import gaussian_filter

    return gaussian_filter(a, sigma)


def highpass(img: np.ndarray, mask: np.ndarray, sigma: float = HP_SIGMA_PX) -> np.ndarray:
    """``img`` minus its mask-normalised Gaussian blur (Scheirer's hp)."""
    w = _gauss(mask.astype(np.float32), sigma)
    return img - _gauss(img * mask, sigma) / np.maximum(w, 1e-3)


def _r(a: np.ndarray, b: np.ndarray) -> float:
    if a.size < 1000:
        return float("nan")
    return float(np.corrcoef(a, b)[0, 1])


def hp_score(key: np.ndarray, pred: np.ndarray, valid: np.ndarray, sigma: float = HP_SIGMA_PX) -> dict:
    """Letter-scale score of ``pred`` (probability in [0, 1]) against ``key`` (the 2.4 um map in [0, 1])."""
    key = np.where(valid, key, 0).astype(np.float32)
    pred = np.asarray(pred, np.float32)
    kh = highpass(key, valid, sigma)
    inked = _gauss(key, HP_INKED_SIGMA_PX) > 60 / 255
    core = valid & (_gauss(valid.astype(np.float32), 2 * sigma) > 0.999)
    m = core & (pred > 0)
    ph = highpass(pred, m, sigma)
    res = dict(hp_r=_r(ph[m], kh[m]), inked_hp_r=_r(ph[m & inked], kh[m & inked]), raw_r=_r(pred[m], key[m]),
               px=int(m.sum()))
    nulls = []
    for s in (150, 300, -300):
        mm = m & np.roll(m, s, 0)
        nulls.append(abs(_r(ph[mm], np.roll(kh, s, 0)[mm])))
    res["null_max"] = float(np.nanmax(nulls)) if np.isfinite(nulls).any() else float("nan")
    res["_hp_pred"], res["_hp_key"], res["_mask"] = ph, kh, m           # for the block bootstrap (dropped on save)
    return res


# ----------------------------------------------------------------------------------------------- IR truth (343P)
IR_N_PERM, IR_MIN_SHIFT, IR_SEED, IR_NOINK_DIST = 2000, 250, 0, 12


def ir_quantise(p: np.ndarray, valid: np.ndarray) -> np.ndarray:
    lo, hi = np.percentile(p[valid], [0.1, 99.9])
    return np.clip((p - lo) / (hi - lo + 1e-9) * 255, 0, 255).astype(np.uint8)


def ir_draws(ink: np.ndarray, valid: np.ndarray, n_perm: int = IR_N_PERM, min_shift: int = IR_MIN_SHIFT,
             seed: int = IR_SEED) -> list[tuple[int, int]]:
    """The 2000 random placements of the letter mask (>= 250 px away, >= 80 % inside the fragment)."""
    H, W = ink.shape
    ys, xs = np.nonzero(ink)
    n = len(ys)
    rng = np.random.default_rng(seed)
    out: list[tuple[int, int]] = []
    for _ in range(200_000):
        dy, dx = int(rng.integers(-H // 2, H // 2)), int(rng.integers(-W // 2, W // 2))
        if dy * dy + dx * dx < min_shift ** 2:
            continue
        y2, x2 = ys + dy, xs + dx
        ok = (y2 >= 0) & (y2 < H) & (x2 >= 0) & (x2 < W)
        ok[ok] = valid[y2[ok], x2[ok]]
        if ok.sum() >= 0.8 * n:
            out.append((dy, dx))
        if len(out) == n_perm:
            break
    return out


def ir_truth_score(p: np.ndarray, ink: np.ndarray, noink: np.ndarray, valid: np.ndarray,
                   draws: Optional[list[tuple[int, int]]] = None) -> dict:
    from scipy import ndimage

    q = ir_quantise(np.asarray(p, np.float32), valid)
    obs = auc_u8(q[ink], q[noink])
    draws = draws if draws is not None else ir_draws(ink, valid)
    edt = ndimage.distance_transform_edt(~ink)
    H, W = ink.shape
    ys, xs = np.nonzero(ink)
    yn, xn = np.nonzero(noink)
    qn = q[yn, xn]
    null = []
    for dy, dx in draws:
        y2, x2 = ys + dy, xs + dx
        ok = (y2 >= 0) & (y2 < H) & (x2 >= 0) & (x2 < W)
        ok[ok] = valid[y2[ok], x2[ok]]
        pos = q[y2[ok], x2[ok]]
        ya, xa = yn - dy, xn - dx
        inb = (ya >= 0) & (ya < H) & (xa >= 0) & (xa < W)
        far = np.ones(len(yn), bool)
        far[inb] = edt[ya[inb], xa[inb]] >= IR_NOINK_DIST
        null.append(auc_u8(pos, qn[far]))
    nl = np.array(null)
    if not np.isfinite(nl).any():
        return dict(auc=round(obs, 4), random_mean=float("nan"), random_max=float("nan"), p=float("nan"),
                    z=float("nan"), n_draws=len(draws))
    return dict(auc=round(obs, 4), random_mean=round(float(np.nanmean(nl)), 4),
                random_max=round(float(np.nanmax(nl)), 4), p=float((1 + np.sum(nl >= obs)) / (len(nl) + 1)),
                z=round(float((obs - np.nanmean(nl)) / (np.nanstd(nl) + 1e-9)), 2), n_draws=len(draws))


# ----------------------------------------------------------------------------------------------- storage helpers
def to_reference_u8(prob: np.ndarray, storage: str = "u8_floor") -> np.ndarray:
    """The 8-bit storage of the reference pipelines: villa ``trunc(255 p)``, Hecate ``rint(255 p)``."""
    m = np.clip(np.asarray(prob, np.float32), 0, 1) * np.float32(255)
    return (m if storage == "u8_floor" else np.rint(m)).astype(np.uint8)
