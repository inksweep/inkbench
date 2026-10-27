"""Run readers on the benchmark inputs with inksweep's engine, one worker process per GPU.

Readers are inksweep built-ins by name (``readerv3``, ``readerv2``, ``d9v4c``, ``dnative``, ``hecate``, ``v8in``,
``v8in_released``, ``ink9_s42``, ``ink9_s43``, ``ink9_s43_060k`` ...) or plugins (``name=path/to/plugin.py:ckpt1[+ckpt2]``,
a module defining ``READER: inksweep.readers.ReaderSpec``). Every map is made in inksweep's ``exact`` mode (the
reference numerics of each reader) at depth 0, i.e. the window the published tools use by default (villa ``infer``
centre crop = ``L//2 - W//2`` = inksweep depth 0).

The map scored is the reference pipeline's own 8-bit value on the render grid (:func:`score_map`): ``trunc(255 p)``
for the villa family (the uint8 TIFF of ``vesuvius.ink_detection.inference.infer``), ``rint(255 p)`` resized with
INTER_LINEAR for readers that run at another voxel size (Hecate's PNG, as Reader v2's ``hecate_eval`` scores it).
"""
from __future__ import annotations

import json
import logging
import multiprocessing as mp
import os
import queue
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

import numpy as np

from . import paths
from .inputs import Input
from .metrics import to_reference_u8

LOG = logging.getLogger("inkbench.predict")
DEPTH = 0


@dataclass(frozen=True)
class ReaderRef:
    """A reader to run: an inksweep built-in (``plugin`` empty) or a plugin module with explicit checkpoints."""

    name: str
    plugin: str = ""
    checkpoints: tuple[str, ...] = ()

    @staticmethod
    def parse(text: str) -> "ReaderRef":
        if "=" not in text:
            return ReaderRef(text)
        name, rest = text.split("=", 1)
        plugin, _, ck = rest.partition(":")
        return ReaderRef(name, plugin, tuple(c for c in ck.replace(",", "+").split("+") if c))


def build_spec(ref: ReaderRef):
    """(ReaderSpec, checkpoint paths) for a ReaderRef; built-in weights come sha256-verified from the cache."""
    from inksweep.readers import get_reader, load_plugin

    if not ref.plugin:
        spec = get_reader(ref.name)
        files = [str(fetch_checkpoint(k)) for k in spec.checkpoints]
    else:
        spec = load_plugin(ref.plugin)
        if spec.name != ref.name:
            spec = spec.with_options(name=ref.name)
        files = list(ref.checkpoints)
    if spec.family in ("villa", "plugin") and spec.window_layers == 17 and spec.resample_tolerance < 0.2:
        # Reader v2's own suite ran the villa models unresampled on the 7.91 um PHerc0172 renders (|7.91/9.36 - 1|
        # = 0.155 > inksweep's 0.12): keep them native here too
        spec = spec.with_options(resample_tolerance=0.2)
    return spec, files


def fetch_checkpoint(key: str) -> Path:
    """A sha256-verified local copy of registry ``key``: an existing inksweep cache if it has it, else ours
    (downloading)."""
    from inksweep.readers import checkpoints as ck

    shared = paths.shared_checkpoints()
    if shared is not None:
        try:
            return ck.fetch(key, shared, download=False)
        except (FileNotFoundError, RuntimeError):
            pass
    return ck.fetch(key, paths.checkpoints(), download=True)


def _done(inp: Input, spec_name: str, side: str) -> Path:
    from inksweep.tiling import depth_tag

    return inp.pred_dir / "ink" / spec_name / "raw" / side / f"{depth_tag(DEPTH)}.tif"


def score_map(inp: Input, spec, orientation: str, render_shape: tuple[int, int]) -> np.ndarray:
    """The reference 8-bit map of ``spec`` on ``inp`` for ``orientation``, on the render grid."""
    import cv2
    import tifffile

    side = "reading" if orientation == inp.reading else "blind"
    raw = tifffile.imread(_done(inp, spec.name, side)).astype(np.float32)
    q = to_reference_u8(raw, spec.reference_storage or "u8_round")
    if q.shape != tuple(render_shape):
        q = cv2.resize(q, (int(render_shape[1]), int(render_shape[0])), interpolation=cv2.INTER_LINEAR)
    return q


def _cfg(inp: Input, mode: str):
    from inksweep.sweep import SweepConfig

    return SweepConfig(depths=[DEPTH], orientations=tuple(inp.orientations), reading=inp.reading, mode=mode,
                       keep_raw=True, reference_storage=True)


def _is_done(inp: Input, spec, mode: str) -> bool:
    """Every orientation's raw map exists and its inksweep marker carries the digest of these exact settings."""
    from inksweep.tiling import depth_tag

    cfg = _cfg(inp, mode)
    for o in inp.orientations:
        side = cfg.side(o)
        marker = inp.pred_dir / "ink" / spec.name / ".done" / f"{side}_{depth_tag(DEPTH)}.json"
        if not (_done(inp, spec.name, side).is_file() and marker.is_file()):
            return False
        if json.loads(marker.read_text()).get("digest") != cfg.digest(spec):
            raise RuntimeError(f"{marker}: made with other settings; delete {inp.pred_dir / 'ink' / spec.name}")
    return True


def _worker(rank: int, device: str, my_inputs: list, results, readers: Sequence[ReaderRef], mode: str) -> None:
    logging.basicConfig(level=logging.INFO, format=f"[gpu{rank}] %(asctime)s %(message)s")
    try:
        import torch
        from inksweep import io as iox
        from inksweep.sweep import Sweep

        specs = {r.name: build_spec(r) for r in readers}
    except Exception:
        results.put(("error", f"gpu{rank} setup: {traceback.format_exc()}"))
        results.put(("done", rank))
        return
    for inp in my_inputs:
        try:
            surface = iox.open_surface(inp.surface, voxel_size_um=inp.voxel_um)
            sweep = Sweep(surface, inp.pred_dir, _cfg(inp, mode), device=device)
        except Exception:
            results.put(("error", f"{inp.key}: {traceback.format_exc()}"))
            continue
        for name, (spec, files) in specs.items():
            t0 = time.time()
            try:
                recs = sweep.run_reader(spec, files)
                results.put(("ok", dict(input=inp.key, reader=name, maps=len(recs), seconds=round(time.time() - t0, 1),
                                        skipped=[r.skipped for r in recs if r.skipped])))
            except Exception:
                results.put(("error", f"{inp.key} {name}: {traceback.format_exc()}"))
        del sweep
        torch.cuda.empty_cache()
    results.put(("done", rank))


def run(inputs: Sequence[Input], readers: Sequence[ReaderRef], gpus: Sequence[str], mode: str = "exact") -> list[dict]:
    """Predict every (input, reader) not done yet on the CUDA devices ``gpus`` (see :func:`devices`); inputs are dealt
    to the devices largest first. One failing pair is recorded and the rest still run; the stage then raises so the
    run is visibly incomplete (rerun resumes)."""
    specs = [build_spec(r)[0] for r in readers]          # fetch / verify weights once, before the workers start
    todo = [i for i in inputs if not all(_is_done(i, sp, mode) for sp in specs)]
    if not todo:
        LOG.info("all predictions present")
        return []
    todo.sort(key=lambda i: -_surface_bytes(i))
    n = max(1, min(len(gpus), len(todo)))
    shares = [todo[k::n] for k in range(n)]
    ctx = mp.get_context("spawn")
    results = ctx.Queue()
    procs = [ctx.Process(target=_worker, args=(k, gpus[k], shares[k], results, list(readers), mode))
             for k in range(n)]
    for p in procs:
        p.start()
    out, errors, done = [], [], set()
    while len(done) < n:
        try:
            kind, payload = results.get(timeout=60)
        except queue.Empty:
            for k, p in enumerate(procs):
                if k not in done and not p.is_alive():
                    errors.append(f"gpu{k}: worker died (exit {p.exitcode}) without finishing")
                    done.add(k)
            continue
        if kind == "ok":
            LOG.info("%s %s: %s maps in %ss", payload["input"], payload["reader"], payload["maps"], payload["seconds"])
            out.append(payload)
        elif kind == "error":
            LOG.error("%s", payload)
            errors.append(payload)
        else:
            done.add(int(payload))
    for p in procs:
        p.join(timeout=120)
    log = paths.results() / "predict_log.jsonl"
    log.parent.mkdir(parents=True, exist_ok=True)
    with open(log, "a") as f:
        for rec in out:
            f.write(json.dumps(rec) + "\n")
        for e in errors:
            f.write(json.dumps(dict(error=e[:4000])) + "\n")
    if errors:
        raise RuntimeError(f"{len(errors)} prediction errors (see {log}); first:\n{errors[0]}")
    return out


def _surface_bytes(inp: Input) -> int:
    p = Path(inp.surface)
    try:
        return sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
    except OSError:
        return 0


def devices(gpus: Optional[str] = None) -> list[str]:
    """CUDA devices for the prediction workers, one worker each. ``gpus`` (``"0,1"``) names devices of the visible
    set; without it every visible device is used (as many as CUDA_VISIBLE_DEVICES lists, else all)."""
    if gpus:
        return [f"cuda:{int(g)}" for g in gpus.split(",") if g.strip()]
    visible = os.environ.get("CUDA_VISIBLE_DEVICES")
    if visible is not None:
        n = len([g for g in visible.split(",") if g.strip()])
    else:
        import torch

        n = torch.cuda.device_count()
    if n < 1:
        raise RuntimeError("no CUDA device visible: prediction needs a GPU (scoring does not)")
    return [f"cuda:{k}" for k in range(n)]
