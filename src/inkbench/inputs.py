"""The surfaces every reader is run on, derived from the prepared benchmark data.

An :class:`Input` is one surface volume (a whole segment, a 1447 layer stack, or a 2048 px crop of PHerc0139 w047 /
w053 for the blank-papyrus test) with its voxel size and the orientations to read it in.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from . import paths
from .catalog import BENCHMARKS, W047, W053
from .data import local_segment
from .zio import atomic_save_npy, atomic_write_text, open_array, read_image

CROP = 2048


@dataclass(frozen=True)
class Input:
    key: str                     # unique, path-like (used as the prediction folder)
    surface: str                 # SV zarr folder or layer-TIFF folder
    voxel_um: float
    reading: str                 # orientation the benchmark scores
    orientations: tuple[str, ...]

    @property
    def pred_dir(self) -> Path:
        return paths.preds() / self.key


def _seg_input(seg, reading: str, both: bool) -> Input:
    d = local_segment(seg)
    rec = json.loads((d / "segment.json").read_text())
    if seg.sample == "PHerc1447":
        surface, vox = str(d / "layers"), float(rec["voxel_um"])
    else:
        surface, vox = str(d / "sv"), rec.get("sv_voxel_um")
        if not vox:
            raise ValueError(f"{d}: voxel size missing from the surface volume metadata")
    other = "forward" if reading == "reverse" else "reverse"
    return Input(f"{seg.sample}/{d.name}", surface, float(vox), reading, (reading, other) if both else (reading,))


def area_resize_torch(img: np.ndarray, shape: tuple[int, int]) -> np.ndarray:
    """``torch.nn.functional.interpolate(mode='area')`` (adaptive average pooling), as Reader v2's suite resizes."""
    import torch

    t = torch.from_numpy(np.ascontiguousarray(img, dtype=np.float32))[None, None]
    return torch.nn.functional.interpolate(t, size=tuple(shape), mode="area")[0, 0].numpy()


def _window_sums(a: np.ndarray, size: int, step: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    cs = np.pad(np.cumsum(np.cumsum(a.astype(np.int64), 0), 1), ((1, 0), (1, 0)))
    ys = np.arange(0, a.shape[0] - size + 1, step)
    xs = np.arange(0, a.shape[1] - size + 1, step)
    Y, X = np.meshgrid(ys, xs, indexing="ij")
    s = cs[Y + size, X + size] - cs[Y, X + size] - cs[Y + size, X] + cs[Y, X]
    return s, Y, X


def pick_crops(valid: np.ndarray, score: np.ndarray, crop: int = CROP, step: int = 256, n: int = 2) -> list[list[int]]:
    """Reader v2 ``bkill.pick_crops``: the ``n`` non-overlapping crops (>= 60 % valid) with the highest score sum."""
    vs, Y, X = _window_sums(valid, crop, step)
    ss, _, _ = _window_sums(score, crop, step)
    ok = vs / float(crop * crop) >= 0.6
    cand = sorted(zip(ss[ok].tolist(), Y[ok].tolist(), X[ok].tolist()), reverse=True)
    out: list[list[int]] = []
    for _, y, x in cand:
        if all(abs(y - a) >= crop or abs(x - b) >= crop for a, b in out):
            out.append([int(y), int(x)])
        if len(out) == n:
            break
    return out


def blank_crops() -> dict[str, dict]:
    """Make (once) the w047 / w053 crops of the published SVs and return their records."""
    out = {}
    for seg in (W047, W053):
        d = local_segment(seg)
        rec_path = d / "crops.json"
        if rec_path.is_file():
            out[seg.tag] = json.loads(rec_path.read_text())
            continue
        vol = open_array(d / "sv")
        H, W = vol.shape[1:]
        valid = np.asarray(vol[14]) > 0
        if seg is W047:
            meta = json.loads((d / "segment.json").read_text())
            t = read_image(d / "teacher" / meta["teachers"]["78kev"]["file"]).astype(np.float32)
            ref = area_resize_torch(t, (H, W))
            atomic_save_npy(d / "ref78_torch_area.npy", ref)
            score = (ref >= 128) & valid
        else:
            score = valid
        crops = pick_crops(valid, score)
        made = []
        for y0, x0 in crops:
            p = d / "crops" / f"{y0}_{x0}.zarr"
            if not (p / "DONE").is_file():
                import zarr

                arr = np.asarray(vol[:, y0:y0 + CROP, x0:x0 + CROP])
                z = zarr.open_array(str(p), mode="w", shape=arr.shape, chunks=(arr.shape[0], 128, 128),
                                    dtype="u1", zarr_format=2, fill_value=0)
                z[:] = arr
                (p / "DONE").write_text("ok")
            made.append(dict(y0=y0, x0=x0, path=str(p)))
        rec = dict(segment=d.name, crops=made, voxel_um=json.loads((d / "segment.json").read_text())["sv_voxel_um"])
        atomic_write_text(rec_path, json.dumps(rec, indent=1))
        out[seg.tag] = rec
    return out


def inputs_for(bench_names: list[str], both_orientations: bool = False) -> list[Input]:
    """Every surface the named benchmarks score, deduplicated."""
    seen: dict[str, Input] = {}
    for name in bench_names:
        b = BENCHMARKS[name]
        both = both_orientations or b.kind in ("hf1447", "ir")        # orientation sanity on non-official renders
        for s in b.segs:
            inp = _seg_input(s, b.orientation, both)
            seen.setdefault(inp.key, inp)
        if b.kind == "blank":
            for tag, rec in blank_crops().items():
                seg = W047 if tag == "w047" else W053
                for c in rec["crops"]:
                    key = f"{seg.sample}/{rec['segment']}/crop_{c['y0']}_{c['x0']}"
                    seen.setdefault(key, Input(key, c["path"], float(rec["voxel_um"]), b.orientation,
                                               (b.orientation,)))
    return list(seen.values())
