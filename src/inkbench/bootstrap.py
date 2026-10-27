"""Paired spatial block bootstrap for every comparison the harness prints.

Pixels are not independent (strokes, labels and render artefacts are spatially correlated), so the unit of
resampling is a 256 px block, the design of C. Hull's ChullMotors/ink-nullkit (MIT; its ``paired_auroc_diff``: blocks
of 256 px with at least 500 labelled pixels, the same draw for both readers, 2000 draws, MDE = 2.8 SD), implemented
anew here for several statistics and several segments. Each segment is a stratum: its blocks are resampled with
replacement, both readers get the same draw (paired), and the benchmark statistic is the mean over segments of the
per-segment statistic computed from the summed block statistics:

* ``auc``: positive / negative 256-bin histograms per block -> tie-aware AUC;
* ``fa``:  positive histograms of the ink segment and score histograms of the blank segment (two strata) -> the share
  of blank pixels at or above the 80 %-recall threshold;
* ``hp``:  (n, sum a, sum b, sum a^2, sum b^2, sum ab) per block -> Pearson r of the high-passed maps.

``minimum detectable effect`` = 2.8 x the bootstrap SD of the difference (80 % power at the 5 % level).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Sequence

import numpy as np

from .metrics import auc_hist, fa_from_hists

BLOCK = 256
MIN_PX = 500


@dataclass
class SegBlocks:
    """Block statistics of one segment (one stratum per named array; rows are blocks of that stratum)."""

    kind: str                                    # auc | fa | hp
    arrays: dict[str, np.ndarray] = field(default_factory=dict)
    block_ids: dict[str, np.ndarray] = field(default_factory=dict)

    def stat(self, weights: Optional[dict[str, np.ndarray]] = None) -> float:
        def tot(name: str) -> np.ndarray:
            a = self.arrays[name]
            return a.sum(0) if weights is None else weights[name] @ a

        if self.kind == "auc":
            return auc_hist(tot("pos"), tot("neg"))
        if self.kind == "fa":
            return fa_from_hists(tot("pos"), tot("blank"))
        if self.kind == "hp":
            n, sa, sb, saa, sbb, sab = tot("sums")
            if n < 1000:
                return float("nan")
            cov = sab / n - (sa / n) * (sb / n)
            va, vb = saa / n - (sa / n) ** 2, sbb / n - (sb / n) ** 2
            return float(cov / np.sqrt(max(va * vb, 1e-30)))
        raise ValueError(self.kind)

    def save_dict(self, prefix: str) -> dict[str, np.ndarray]:
        out = {f"{prefix}|kind": np.array(self.kind)}
        for k, v in self.arrays.items():
            out[f"{prefix}|a|{k}"] = v
            out[f"{prefix}|b|{k}"] = self.block_ids[k]
        return out

    @staticmethod
    def from_dict(d: dict, prefix: str) -> "SegBlocks":
        sb = SegBlocks(kind=str(d[f"{prefix}|kind"]))
        head = f"{prefix}|a|"
        for key in d:
            if key.startswith(head):
                name = key[len(head):]
                sb.arrays[name] = d[key]
                sb.block_ids[name] = d[f"{prefix}|b|{name}"]
        return sb

    def strata(self) -> list[tuple[str, ...]]:
        """Arrays resampled together: an AUC's positive and negative histograms come from the same blocks."""
        if self.kind == "auc":
            return [("pos", "neg")]
        return [(name,) for name in self.arrays]


def draw_weights(sb: SegBlocks, rng: np.random.Generator) -> dict[str, np.ndarray]:
    """One bootstrap draw: block multiplicities per stratum (shared by the arrays of a stratum)."""
    w: dict[str, np.ndarray] = {}
    for group in sb.strata():
        n = len(sb.arrays[group[0]])
        v = np.bincount(rng.integers(0, n, n), minlength=n).astype(np.float64) if n else np.zeros(0)
        for name in group:
            w[name] = v
    return w


def _block_index(shape: tuple[int, int], block: int) -> tuple[np.ndarray, int]:
    h, w = shape
    nbx = (w + block - 1) // block
    by = (np.arange(h) // block)[:, None]
    bx = (np.arange(w) // block)[None, :]
    return (by * nbx + bx).astype(np.int64), ((h + block - 1) // block) * nbx


def hist_blocks(score_u8: np.ndarray, mask: np.ndarray, block: int = BLOCK) -> tuple[np.ndarray, np.ndarray]:
    """(block ids, histograms (n_blocks_present, 256)) of the uint8 scores inside ``mask``."""
    if score_u8.dtype != np.uint8:
        raise TypeError("block histograms need uint8 scores")
    bidx, nb = _block_index(mask.shape, block)
    key = bidx[mask] * 256 + score_u8[mask].astype(np.int64)
    h = np.bincount(key, minlength=nb * 256).reshape(nb, 256).astype(np.float64)
    return np.arange(nb), h


def auc_blocks(score_u8: np.ndarray, pos: np.ndarray, neg: np.ndarray, block: int = BLOCK,
               min_px: int = MIN_PX) -> SegBlocks:
    ids, hp = hist_blocks(score_u8, pos, block)
    _, hn = hist_blocks(score_u8, neg, block)
    keep = (hp.sum(1) + hn.sum(1)) >= min_px
    return SegBlocks("auc", {"pos": hp[keep], "neg": hn[keep]}, {"pos": ids[keep], "neg": ids[keep]})


def fa_blocks(ink_score_u8: np.ndarray, ink_pos: np.ndarray, blank_score_u8: np.ndarray, blank_valid: np.ndarray,
              block: int = BLOCK, min_px: int = MIN_PX) -> SegBlocks:
    ids_p, hp = hist_blocks(ink_score_u8, ink_pos, block)
    ids_b, hb = hist_blocks(blank_score_u8, blank_valid, block)
    kp, kb = hp.sum(1) >= min_px // 5, hb.sum(1) >= min_px
    return SegBlocks("fa", {"pos": hp[kp], "blank": hb[kb]}, {"pos": ids_p[kp], "blank": ids_b[kb]})


def hp_blocks(hp_pred: np.ndarray, hp_key: np.ndarray, mask: np.ndarray, block: int = BLOCK,
              grid_mask: Optional[np.ndarray] = None, min_px: int = MIN_PX) -> SegBlocks:
    """Per-block sums for the Pearson r of two high-passed maps; ``grid_mask`` (reader-independent) fixes the blocks."""
    bidx, nb = _block_index(mask.shape, block)
    b = bidx[mask]
    a, k = hp_pred[mask].astype(np.float64), hp_key[mask].astype(np.float64)
    sums = np.stack([np.bincount(b, weights=w, minlength=nb)
                     for w in (np.ones_like(a), a, k, a * a, k * k, a * k)], 1)
    gm = mask if grid_mask is None else grid_mask
    keep = np.bincount(bidx[gm], minlength=nb) >= min_px
    return SegBlocks("hp", {"sums": sums[keep]}, {"sums": np.arange(nb)[keep]})


def benchmark_stat(segs: Sequence[SegBlocks]) -> float:
    vals = [s.stat() for s in segs]
    vals = [v for v in vals if v == v]
    return float(np.mean(vals)) if vals else float("nan")


def _align(a: SegBlocks, b: SegBlocks) -> tuple[SegBlocks, SegBlocks]:
    """Restrict two readers' blocks to the common block ids, stratum by stratum (needed for pairing)."""
    oa, ob = SegBlocks(a.kind), SegBlocks(b.kind)
    for name in a.arrays:
        common = np.intersect1d(a.block_ids[name], b.block_ids[name])
        ia = np.searchsorted(a.block_ids[name], common)
        ib = np.searchsorted(b.block_ids[name], common)
        oa.arrays[name], oa.block_ids[name] = a.arrays[name][ia], common
        ob.arrays[name], ob.block_ids[name] = b.arrays[name][ib], common
    return oa, ob


def paired_bootstrap(segs_a: Sequence[SegBlocks], segs_b: Sequence[SegBlocks], n_boot: int = 2000,
                     seed: int = 0) -> dict:
    """stat(A) - stat(B) with a paired, segment-stratified block bootstrap. Returns a JSON-ready dict."""
    if len(segs_a) != len(segs_b):
        raise ValueError("both readers need the same segments")
    pairs = [_align(a, b) for a, b in zip(segs_a, segs_b)]
    sa = benchmark_stat([p[0] for p in pairs])
    sb = benchmark_stat([p[1] for p in pairs])
    rng = np.random.default_rng(seed)
    diffs = np.empty(n_boot)
    n_blocks = 0
    for name_counts in [{k: len(v) for k, v in p[0].arrays.items()} for p in pairs]:
        n_blocks += sum(name_counts.values())
    for i in range(n_boot):
        va, vb = [], []
        for a, b in pairs:
            w = draw_weights(a, rng)                      # the same blocks for both readers (paired)
            va.append(a.stat(w))
            vb.append(b.stat(w))
        da = np.nanmean(va) if np.isfinite(va).any() else np.nan
        db = np.nanmean(vb) if np.isfinite(vb).any() else np.nan
        diffs[i] = da - db
    d = diffs[np.isfinite(diffs)]
    sd = float(d.std()) if d.size else float("nan")
    return dict(stat_a=sa, stat_b=sb, diff=sa - sb,
                ci95=[float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))] if d.size else [np.nan, np.nan],
                p_diff_le_0=float((d <= 0).mean()) if d.size else float("nan"),
                sd=sd, mde_80pct=2.8 * sd, n_boot=int(d.size), n_blocks=int(n_blocks))


def bootstrap_ci(segs: Sequence[SegBlocks], n_boot: int = 2000, seed: int = 0) -> list[float]:
    """95 % interval of one reader's benchmark statistic."""
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(n_boot):
        per = [s.stat(draw_weights(s, rng)) for s in segs]
        vals.append(np.nanmean(per) if np.isfinite(per).any() else np.nan)
    v = np.array(vals)
    v = v[np.isfinite(v)]
    return [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))] if v.size else [np.nan, np.nan]
