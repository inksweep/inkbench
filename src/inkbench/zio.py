"""Small zarr and image helpers: reading surface volumes, labels and maps, and atomic writes."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

import numpy as np


def open_array(path: str | Path, level: str = "0") -> Any:
    """A zarr array (v2 or v3): the path itself if it is an array, else its ``level`` member."""
    import zarr

    node = zarr.open(str(path), mode="r")
    if hasattr(node, "shape"):
        return node
    return node[level]


def read_2d(path: str | Path, level: str = "0") -> np.ndarray:
    a = open_array(path, level)
    arr = np.asarray(a[...])
    if arr.ndim == 3:                         # label volumes keep their content on one plane (or the max over z)
        arr = arr.max(0)
    return arr


def voxel_um_from_zattrs(zarr_dir: str | Path) -> Optional[float]:
    """Level-0 in-plane voxel size from OME multiscales metadata (never from the file name)."""
    p = Path(zarr_dir) / ".zattrs"
    if not p.is_file():
        p = Path(zarr_dir) / "zarr.json"
        if not p.is_file():
            return None
        meta = json.loads(p.read_text()).get("attributes", {}).get("ome", {})
    else:
        meta = json.loads(p.read_text())
    try:
        ms = meta["multiscales"][0]
        ds = ms["datasets"][0]
        for t in ds["coordinateTransformations"]:
            if t.get("type") == "scale":
                return float(t["scale"][-1])
    except (KeyError, IndexError, TypeError):
        return None
    return None


def valid_mid(vol: Any) -> np.ndarray:
    """Reader v2 suite's valid rule: the middle layer has data."""
    return np.asarray(vol[vol.shape[0] // 2]) > 0


def valid_max(vol: Any, step: int = 1024) -> np.ndarray:
    """Nieuwlaar's rule: any layer has data."""
    d, h, w = vol.shape
    out = np.zeros((h, w), bool)
    for y in range(0, h, step):
        out[y:y + step] = np.asarray(vol[:, y:y + step, :]).max(0) > 0
    return out


def read_image(path: str | Path) -> np.ndarray:
    """Grey image from TIFF / PNG / NPY (RGB with equal channels -> first channel)."""
    p = str(path)
    if p.endswith(".npy"):
        return np.load(p)
    if p.endswith((".tif", ".tiff")):
        import tifffile

        a = tifffile.imread(p)
    else:
        import cv2

        a = cv2.imread(p, cv2.IMREAD_UNCHANGED)
        if a is None:
            raise FileNotFoundError(p)
    if a.ndim == 3:
        a = a[..., 0] if a.shape[-1] in (1, 3, 4) else a[0]
    return a


def atomic_write_text(path: str | Path, text: str) -> Path:
    """Write via a temporary file and ``os.replace`` (a kill mid-write never leaves a half file)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(text)
    os.replace(tmp, path)
    return path


def atomic_save_npy(path: str | Path, arr: np.ndarray) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.stem}.{os.getpid()}.tmp.npy")
    np.save(tmp, arr)
    os.replace(tmp, path)
    return path


def atomic_savez(path: str | Path, **arrays: np.ndarray) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.stem}.{os.getpid()}.tmp.npz")
    np.savez_compressed(tmp, **arrays)
    os.replace(tmp, path)
    return path
