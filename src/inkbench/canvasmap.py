"""Exact pixel map between the fine (~2.2-2.4 um) and coarse (~7.9-9.4 um) surface-volume canvases of one segment.

Moving labels or teacher maps between the two canvases by plain resizing ("index pairing") lands ~7.4 coarse px
(~70 um) off the same papyrus on the 9.4 um scrolls (villa#2243; TAUIL measured (-8, -7) px, Russo 6-8 px). The two
meshes come from one source through ``vc_transform_geom`` (half-pixel resample, grid size from the affine's measured
scale) and are rendered by ``vc_render_tifxyz`` (canvas pixel p -> grid s (p + 0.5)), so per axis the same mesh point
sits at

    p_coarse = (p_fine + 0.5 + 0.5 / s) * n_coarse / n_fine - 0.5 / s - 0.5       (= (p + 10.5) rho - 10.5 at s = 0.05)

with ``n`` the meshes' grid sizes on that axis and ``s`` the grid step. The rule, its derivation and its validation on
206 published pairs are by Chris Thomas and Sebastien Chicoineau (github.com/slchicoineau-creator/tifxyz-canvas-map,
MIT); this module is an independent implementation of the same conventions (canvas centred on the grid, render scale
R). It does not correct the residual of the scan-to-scan affine (0.5-1.5 coarse px after the map).

Pyramid levels: a level-l pixel i is centred on level-0 pixel ``2**l * i + (2**l - 1) / 2``.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np


def _lround(x: float) -> int:
    """Round half away from zero (C ``lround``)."""
    return int(math.floor(x + 0.5)) if x >= 0 else -int(math.floor(-x + 0.5))


@dataclass(frozen=True)
class MeshGeom:
    """Grid size and step of one tifxyz mesh, and the render scale its surface volume was made with."""

    rows: int
    cols: int
    scale_y: float = 0.05
    scale_x: float = 0.05
    render_scale: float = 1.0

    def n(self, axis: int) -> int:
        return self.rows if axis == 0 else self.cols

    def step(self, axis: int) -> float:
        return self.scale_y if axis == 0 else self.scale_x

    def canvas(self, axis: int) -> int:
        """Canvas size of the rendered surface volume on that axis."""
        return max(1, _lround(self.n(axis) * self.render_scale / self.step(axis)))

    @property
    def canvas_shape(self) -> tuple[int, int]:
        return self.canvas(0), self.canvas(1)

    def canvas_to_grid(self, p, axis: int):
        n, s, w, r = self.n(axis), self.step(axis), self.canvas(axis), self.render_scale
        return s * ((np.asarray(p, dtype=np.float64) - 0.5 * w) + 0.5) / r + n / 2.0

    def grid_to_canvas(self, g, axis: int):
        n, s, w, r = self.n(axis), self.step(axis), self.canvas(axis), self.render_scale
        return (np.asarray(g, dtype=np.float64) - n / 2.0) * r / s + 0.5 * w - 0.5


def read_geom(tifxyz_dir: str | Path, render_scale: float = 1.0) -> MeshGeom:
    """MeshGeom from a tifxyz folder: ``meta.json`` ("scale" = [x, y]) and the shape of ``x.tif``."""
    import tifffile

    d = Path(tifxyz_dir)
    meta = json.loads((d / "meta.json").read_text())
    sx, sy = meta.get("scale", [0.05, 0.05])
    with tifffile.TiffFile(d / "x.tif") as tf:
        rows, cols = (int(v) for v in tf.pages[0].shape[:2])
    return MeshGeom(rows=rows, cols=cols, scale_y=float(sy), scale_x=float(sx), render_scale=render_scale)


def fine_to_coarse(p_fine, fine: MeshGeom, coarse: MeshGeom, axis: int):
    """Level-0 fine canvas coordinate -> level-0 coarse canvas coordinate of the same mesh point."""
    g_f = fine.canvas_to_grid(p_fine, axis)
    g_c = (g_f + 0.5) * coarse.n(axis) / fine.n(axis) - 0.5          # half-pixel resample of the exporter
    return coarse.grid_to_canvas(g_c, axis)


def coarse_to_fine(p_coarse, fine: MeshGeom, coarse: MeshGeom, axis: int):
    g_c = coarse.canvas_to_grid(p_coarse, axis)
    g_f = (g_c + 0.5) * fine.n(axis) / coarse.n(axis) - 0.5
    return fine.grid_to_canvas(g_f, axis)


def coeffs(fine: MeshGeom, coarse: MeshGeom) -> dict[str, float]:
    """``p_coarse = a + b p_fine`` per axis (level 0): keys y_a, y_b, x_a, x_b."""
    out = {}
    for axis, k in ((0, "y"), (1, "x")):
        a = float(fine_to_coarse(0.0, fine, coarse, axis))
        out[f"{k}_a"], out[f"{k}_b"] = a, float(fine_to_coarse(1.0, fine, coarse, axis)) - a
    return out


def naive_offset_px(fine: MeshGeom, coarse: MeshGeom, p_fine: float, axis: int) -> float:
    """Exact minus plain-resize position (coarse px) of fine pixel ``p_fine``: what index pairing gets wrong."""
    r = coarse.canvas(axis) / fine.canvas(axis)
    naive = (p_fine + 0.5) * r - 0.5                                  # cv2.resize pixel-centre convention
    return float(fine_to_coarse(p_fine, fine, coarse, axis) - naive)


def level_of(shape_hw: tuple[int, int], fine: MeshGeom, tol: int = 2) -> int:
    """Pyramid level of a fine-canvas image from its shape; raises ValueError for an unknown frame."""
    for lev in range(6):
        f = 2 ** lev
        if all(abs(shape_hw[ax] - math.ceil(fine.canvas(ax) / f)) <= tol for ax in (0, 1)):
            return lev
    raise ValueError(f"image {shape_hw} is no pyramid level of the fine canvas {fine.canvas_shape}")


def _axis_resample(a: np.ndarray, src_coord: np.ndarray, axis: int, fill: float) -> np.ndarray:
    """Linear interpolation of ``a`` along ``axis`` at fractional source coordinates (one per output index)."""
    n = a.shape[axis]
    i0 = np.floor(src_coord).astype(np.int64)
    w = (src_coord - i0).astype(np.float32)
    ok = (src_coord >= -0.5) & (src_coord <= n - 0.5)
    i0c, i1c = np.clip(i0, 0, n - 1), np.clip(i0 + 1, 0, n - 1)
    lo, hi = np.take(a, i0c, axis=axis), np.take(a, i1c, axis=axis)
    shp = [1, 1]
    shp[axis] = -1
    out = lo * (1 - w.reshape(shp)) + hi * w.reshape(shp)
    if not ok.all():
        sl = [slice(None), slice(None)]
        sl[axis] = ~ok
        out[tuple(sl)] = fill
    return out


def warp_fine_to_coarse(img: np.ndarray, fine: MeshGeom, coarse: MeshGeom, out_shape: Optional[tuple[int, int]] = None,
                        kind: str = "map", fine_level: Optional[int] = None) -> np.ndarray:
    """Resample a fine-canvas image (label mask or teacher map) onto the coarse canvas with the exact map.

    Area-averages onto the coarse pixel size first (cv2 INTER_AREA, as the published label recipes do), then moves
    every coarse pixel to its exact source position (separable linear interpolation). ``kind="mask"`` returns bool
    (area fraction >= 0.5), ``kind="map"`` float32 with NaN outside the fine canvas."""
    import cv2

    out_shape = tuple(out_shape or coarse.canvas_shape)
    lev = level_of(img.shape[:2], fine) if fine_level is None else int(fine_level)
    src = (np.asarray(img) > 0).astype(np.float32) if kind == "mask" else np.asarray(img, dtype=np.float32)
    stretched = cv2.resize(src, (out_shape[1], out_shape[0]), interpolation=cv2.INTER_AREA)
    f = 2 ** lev
    out = stretched
    for axis in (0, 1):
        r = out_shape[axis] / img.shape[axis]                        # the resize ratio actually applied
        pc = np.arange(out_shape[axis], dtype=np.float64)
        pf0 = coarse_to_fine(pc, fine, coarse, axis)                 # level-0 fine coordinate
        pfl = (pf0 - (f - 1) / 2.0) / f                              # its coordinate on the image's level
        out = _axis_resample(out, (pfl + 0.5) * r - 0.5, axis, 0.0 if kind == "mask" else np.nan)
    return out >= 0.5 if kind == "mask" else out.astype(np.float32)


def naive_fine_to_coarse(img: np.ndarray, out_shape: tuple[int, int], kind: str = "map") -> np.ndarray:
    """The published recipes' index pairing: cv2 INTER_AREA onto the coarse canvas (masks: >= 128 of 255).

    Kept to reproduce published numbers (the ``compat`` protocols)."""
    import cv2

    if kind == "mask":
        a = (np.asarray(img) > 0).astype(np.uint8) * 255
        return cv2.resize(a, (out_shape[1], out_shape[0]), interpolation=cv2.INTER_AREA) >= 128
    a = np.asarray(img)
    if a.dtype not in (np.uint8, np.float32):
        a = a.astype(np.float32)
    return cv2.resize(a, (out_shape[1], out_shape[0]), interpolation=cv2.INTER_AREA)
