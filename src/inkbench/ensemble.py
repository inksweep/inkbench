"""Prediction-averaging ensembles, scored exactly like single readers.

For every benchmark input, each member's depth-0 map is read as the scorer reads it (the reference 8-bit map on the
render grid, so Hecate's 9.6 um maps are resized the same way), stretched to its own p1/p99.5 over the input's valid
pixels (any member > 0), clipped to [0, 1] and z-scored there: the per-model stretch and mean of z-scores of the
PHerc. 343 First Letters recipe (E. Nieuwlaar), at one depth. The members' mean z-score, mapped to [0, 1] by its own
min and max over the valid pixels, is written as the raw map of a pseudo-reader named after the ensemble, which the
regular scorer, the block statistics and the tables then treat as one more reader.

* The pseudo-reader is scored with Reader V3's map conventions (``trunc(255 p)``; its calibration label, so the
  Nieuwlaar protocols apply their ``(v - 64) / 128`` rescale for label-smoothed maps to the ensemble map as well).
* Its leakage flags are those of its members (:func:`inkbench.provenance.trained_on_any`).
* Members and scores are recorded in ``<results>/ensembles.json``.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Optional, Sequence

import numpy as np

from . import paths
from .catalog import BENCHMARKS
from .inputs import inputs_for
from .zio import atomic_write_text

LOG = logging.getLogger("inkbench.ensemble")
BASE_READER = "readerv3"           # whose map conventions score an ensemble
MIN_VALID_PX = 1000


def registry_path() -> Path:
    return paths.results() / "ensembles.json"


def _registry() -> dict:
    p = registry_path()
    return json.loads(p.read_text()) if p.is_file() else {}


def registered() -> dict[str, list[str]]:
    """{ensemble name: member readers} of every ensemble built in this results folder."""
    return {name: list(rec["members"]) for name, rec in _registry().items()}


def _record(name: str, members: list[str], built: Optional[dict] = None, scores: Optional[dict] = None) -> None:
    """Add or update an ensemble's entry in ensembles.json (scores are merged per benchmark)."""
    reg = _registry()
    rec = reg.setdefault(name, {})
    if rec.get("members", members) != members:
        raise ValueError(f"{name} is already an ensemble of {rec['members']} in {registry_path()}; pick another name "
                         f"(or delete its entry and its maps, ink/{name}/, under {paths.preds()})")
    rec["members"] = members
    if built is not None:
        rec["built"] = built
    if scores is not None:
        rec.setdefault("scores", {}).update(scores)
    atomic_write_text(registry_path(), json.dumps(reg, indent=1, default=float))


def ensemble_spec(name: str):
    """The inksweep ReaderSpec an ensemble is scored with: Reader V3's, renamed."""
    from inksweep.readers import get_reader

    return get_reader(BASE_READER).with_options(name=name)


def parse(text: str) -> tuple[str, list[str]]:
    """``NAME=reader,reader,...`` -> (name, members)."""
    name, sep, rest = text.partition("=")
    members = [m.strip() for m in rest.split(",") if m.strip()]
    if not sep or not name or len(members) < 2 or name in members or len(set(members)) != len(members):
        raise ValueError(f"{text!r}: an ensemble is NAME=reader,reader[,...] with two or more distinct members")
    return name.strip(), members


def stretch_z(m: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """One member: p1/p99.5 stretch over the valid pixels, clipped to [0, 1], then z-scored over the valid pixels."""
    v = m[valid].astype(np.float64)
    lo, hi = np.percentile(v, [1.0, 99.5])
    s = np.clip((m.astype(np.float64) - lo) / max(hi - lo, 1e-9), 0.0, 1.0)
    sv = s[valid]
    return (s - sv.mean()) / max(sv.std(), 1e-9)


def combine(maps: Sequence[np.ndarray], min_valid: int = MIN_VALID_PX) -> Optional[np.ndarray]:
    """The ensemble map of the members' 8-bit maps (float32 in [0, 1], 0 outside the valid pixels), or None when
    fewer than ``min_valid`` pixels are valid. Members are summed in the order given."""
    valid = np.zeros(maps[0].shape, bool)
    for m in maps:
        valid |= m > 0
    if valid.sum() < min_valid:
        return None
    z = np.mean([stretch_z(m, valid) for m in maps], axis=0)
    zv = z[valid]
    out = np.zeros(z.shape, np.float32)
    out[valid] = ((zv - zv.min()) / max(zv.max() - zv.min(), 1e-9)).astype(np.float32)
    return out


def build(name: str, members: Sequence[str], bench_names: Optional[Sequence[str]] = None) -> dict[str, int]:
    """Write the ensemble's raw maps for every input (both orientations where the members have them)."""
    import tifffile
    from inksweep.tiling import depth_tag

    from .predict import DEPTH
    from .score import _map, reader_spec

    specs = [reader_spec(m) for m in members]
    made = skipped = 0
    for inp in inputs_for(list(bench_names or BENCHMARKS), both_orientations=True):
        for orientation in inp.orientations:
            maps = [_map(inp, sp, orientation) for sp in specs]
            if any(m is None for m in maps):
                skipped += 1
                continue
            out = combine(maps)
            if out is None:
                skipped += 1
                continue
            side = "reading" if orientation == inp.reading else "blind"
            dst = inp.pred_dir / "ink" / name / "raw" / side / f"{depth_tag(DEPTH)}.tif"
            dst.parent.mkdir(parents=True, exist_ok=True)
            tmp = dst.with_name(f".{dst.stem}.{os.getpid()}.tmp.tif")
            tifffile.imwrite(tmp, out)
            os.replace(tmp, dst)
            made += 1
    return {"maps": made, "skipped": skipped}


def run(texts: Sequence[str], bench_names: Optional[Sequence[str]] = None) -> dict:
    """Build, register and score each ensemble ``NAME=reader,reader,...``; returns the ensembles.json records."""
    from .score import score_benchmark

    benches = list(bench_names or BENCHMARKS)
    summary = {}
    for text in texts:
        name, members = parse(text)
        existing = registered().get(name)
        if existing is not None and existing != members:
            _record(name, members)                       # raises with the explanation
        built = build(name, members, benches)
        if built["maps"] == 0:
            raise RuntimeError(f"{name}: no input has maps of every member {members}; run "
                               f"`inkbench predict --readers {','.join(members)}` first")
        _record(name, members, built=built)              # registered before scoring: the scorer looks it up
        scores = {b: score_benchmark(b, [name]).get(name) for b in benches}
        _record(name, members, scores=scores)
        summary[name] = dict(members=members, built=built, scores=scores)
        LOG.info("%s %s", name, json.dumps(summary[name], default=float))
    return summary
