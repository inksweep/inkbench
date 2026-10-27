"""Where inkbench keeps its files. Every location is read from the environment when it is used, so a test or a
command line option (``inkbench --root DIR``) can move it:

  INKBENCH_ROOT     base folder                                                 (default ./inkbench-data)
  INKBENCH_DATA     benchmark inputs: surface volumes, labels, ink maps, meshes  (default $INKBENCH_ROOT/data)
  INKBENCH_RESULTS  scores, block statistics, tables                            (default $INKBENCH_ROOT/results)
  INKBENCH_PREDS    prediction maps                                             (default $INKBENCH_RESULTS/preds)
  INKBENCH_CKPT     reader checkpoints, sha256-verified                         (default $INKBENCH_ROOT/checkpoints)
  INKSWEEP_CKPT     optional: an existing inksweep checkpoint folder, used read-only before anything is downloaded
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


def root() -> Path:
    return Path(os.environ.get("INKBENCH_ROOT", "inkbench-data"))


def data() -> Path:
    """Benchmark inputs, one folder per open-data segment (``<sample>/<segment folder>/``)."""
    return Path(os.environ.get("INKBENCH_DATA", str(root() / "data")))


def results() -> Path:
    """Scores, block statistics, TABLE.md, REPRODUCTION.json, COMPARISONS.json, ensembles.json."""
    return Path(os.environ.get("INKBENCH_RESULTS", str(root() / "results")))


def preds() -> Path:
    """Prediction maps, one folder per benchmark input (``<sample>/<segment folder>[/crop_y_x]/ink/<reader>/``)."""
    return Path(os.environ.get("INKBENCH_PREDS", str(results() / "preds")))


def checkpoints() -> Path:
    """Reader weights downloaded by inkbench (inksweep's registry: pinned revisions, sha256-verified)."""
    return Path(os.environ.get("INKBENCH_CKPT", str(root() / "checkpoints")))


def shared_checkpoints() -> Optional[Path]:
    """An existing inksweep checkpoint folder, read only (its files are verified by sha256 before use)."""
    d = os.environ.get("INKSWEEP_CKPT")
    return Path(d) if d else None
