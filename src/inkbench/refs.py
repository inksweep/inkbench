"""Reference masks of one prepared segment on its native canvas, by two label-transfer routes:

* ``compat``: the published recipes' plain resize (cv2 INTER_AREA, or torch 'area' where the reference used it), to
  reproduce published numbers;
* ``exact``: the exact canvas map (:mod:`inkbench.canvasmap`), the primary route.
Results are cached next to the segment data (``teacher_<kind>_<route>_<resizer>.npy``, ``labels_<route>.npz``).
"""
from __future__ import annotations

import json
import logging
from functools import cached_property
from pathlib import Path
from typing import Optional

import numpy as np

from .canvasmap import naive_fine_to_coarse, read_geom, warp_fine_to_coarse
from .zio import atomic_save_npy, atomic_savez, open_array, read_2d, read_image, valid_max, valid_mid

LOG = logging.getLogger("inkbench.refs")


class SegmentRefs:
    """Lazy reference data of one prepared open-data segment folder."""

    def __init__(self, folder: str | Path) -> None:
        self.dir = Path(folder)
        self.meta = json.loads((self.dir / "segment.json").read_text())
        self.vol = open_array(self.dir / "sv")
        self.shape = tuple(int(v) for v in self.vol.shape[1:])

    # ------------------------------------------------------------------ validity
    @cached_property
    def valid_mid(self) -> np.ndarray:
        return valid_mid(self.vol)

    @cached_property
    def valid_max(self) -> np.ndarray:
        return valid_max(self.vol)

    # ------------------------------------------------------------------ geometry
    def mesh_geom(self, volume: Optional[str]):
        name = (self.meta.get("meshes") or {}).get(volume or "")
        return read_geom(self.dir / "mesh" / name) if name else None

    @cached_property
    def coarse_geom(self):
        return self.mesh_geom(self.meta["coarse_volume"])

    def canvas_check(self) -> dict:
        """The native SV must be the scale-1 render of the coarse mesh, or the exact map does not apply."""
        g = self.coarse_geom
        if g is None:
            return dict(ok=False, why="no coarse mesh")
        ok = tuple(g.canvas_shape) == self.shape
        return dict(ok=ok, mesh_canvas=list(g.canvas_shape), sv_canvas=list(self.shape))

    # ------------------------------------------------------------------ fine -> coarse transfer
    def _to_canvas(self, img: np.ndarray, volume: Optional[str], route: str, kind: str,
                   resizer: str = "cv2") -> np.ndarray:
        if volume == self.meta["coarse_volume"] or img.shape[:2] == self.shape:
            if img.shape[:2] != self.shape:
                return naive_fine_to_coarse(img, self.shape, kind)
            return (img > 0) if kind == "mask" else img.astype(np.float32)
        if route == "compat":
            if resizer == "torch" and kind == "map":
                from .inputs import area_resize_torch

                return area_resize_torch(img, self.shape)
            out = naive_fine_to_coarse(img, self.shape, kind)
            return out if kind == "mask" else out.astype(np.float32)
        fine = self.mesh_geom(volume)
        if fine is None or not self.canvas_check()["ok"]:
            raise LookupError(f"{self.dir.name}: exact map needs both meshes and a scale-1 render "
                              f"(fine mesh for {volume}: {fine is not None}; {self.canvas_check()})")
        return warp_fine_to_coarse(img, fine, self.coarse_geom, self.shape, kind=kind)

    def teacher(self, kind: str = "canon", route: str = "exact", resizer: str = "cv2") -> Optional[np.ndarray]:
        """Teacher map on the native canvas, 0..255 float32 (NaN outside the fine canvas on the exact route)."""
        t = (self.meta.get("teachers") or {}).get(kind)
        if t is None and kind == "canon":
            t = (self.meta.get("teachers") or {}).get("same")
        if t is None:
            return None
        cache = self.dir / f"teacher_{kind}_{route}_{resizer}.npy"
        if cache.is_file():
            return np.load(cache)
        img = read_image(self.dir / "teacher" / t["file"])
        if img.dtype == np.uint16:
            img = (img >> 8).astype(np.uint8)
        out = self._to_canvas(img, t.get("volume"), route, "map", resizer).astype(np.float32)
        atomic_save_npy(cache, out)
        return out

    def labels(self, route: str = "exact") -> Optional[dict[str, np.ndarray]]:
        """Human labels on the native canvas: ink, supervision, validation (bool) and ink_frac (float, area share)."""
        labs = self.meta.get("labels") or {}
        if not labs:
            return None
        vol_dir, rec = next(iter(labs.items()))
        base = self.dir / "labels" / vol_dir / rec["date"]
        cache = self.dir / f"labels_{route}.npz"
        if cache.is_file():
            z = np.load(cache)
            return {k: z[k] for k in z.files}
        out, fine = {}, {}
        for name in ("inklabels", "supervision", "validation"):
            p = base / f"{name}.zarr"
            if not p.exists():
                continue
            a = read_2d(p)
            fine[name] = a > 0
            out[name] = self._to_canvas(a, rec["volume"], route, "mask")
            if name == "inklabels":
                frac = self._to_canvas((a > 0).astype(np.float32), rec["volume"], route, "map")
                out["ink_frac"] = np.nan_to_num(frac).astype(np.float32)
        if "supervision" in fine and "validation" in fine:      # Reader v2's 0009B rule: union first, then resize
            out["union_fine"] = self._to_canvas(fine["supervision"] | fine["validation"], rec["volume"], route, "mask")
        atomic_savez(cache, **out)
        return out
