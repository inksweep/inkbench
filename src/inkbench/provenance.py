"""Leakage flags: whether a public reader's published training set includes a benchmark segment.

``trained_on(reader, sample, segment_folder)`` answers

* ``"yes"``: the segment is in the reader's published training configuration;
* ``"no"``: the configuration is published and does not include it;
* ``"unknown"``: the training data, or the segment lists, are not published (Hecate; v8-in on the scrolls its model
  card names);
* ``"n/a"``: no record (a plugin reader).

The segment lists are in ``resources/public_training_sets.json``, extracted from each reader's published configuration
(the sources are listed in that file under ``_sources``). An ensemble carries the flags of its members
(:func:`trained_on_any`).
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Iterable


@lru_cache(maxsize=1)
def training_sets() -> dict:
    return json.loads((Path(__file__).parent / "resources" / "public_training_sets.json").read_text())


def seg_id(segment_folder: str) -> str:
    """The 14-digit public id at the start of an open-data segment folder name."""
    m = re.match(r"(\d{14})", segment_folder)
    if not m:
        raise ValueError(f"not an open-data segment folder: {segment_folder!r}")
    return m.group(1)


def trained_on(reader: str, sample: str, segment_folder: str) -> str:
    """``"yes"`` | ``"no"`` | ``"unknown"`` for the public readers; ``"n/a"`` for a reader without a record."""
    sets = training_sets()
    if reader.startswith("hecate"):
        return "unknown"
    if reader.startswith("v8in"):
        return "unknown" if sample in sets["v8in_unknown_samples"] else "no"
    m = re.fullmatch(r"ink9_s(42|43)_\d{3}k", reader)
    if reader not in sets and m:                     # every released ink_9um step shares one training corpus
        reader = f"ink9_s{m.group(1)}"
    if reader not in sets:
        return "n/a"
    ids = set(sets[reader].get(sample, []))
    if ids and seg_id(segment_folder) in ids:
        return "yes"
    if reader == "dnative":
        for w in sets["dnative_windings"].get(sample, []):
            if f"-{w}_" in segment_folder:
                return "yes"
    return "no"


def trained_on_any(readers: Iterable[str], sample: str, segment_folder: str) -> str:
    """The flag of an ensemble: ``"yes"`` if any member trained on the segment, else ``"unknown"`` if any member's
    record is unknown or missing, else ``"no"``."""
    flags = [trained_on(r, sample, segment_folder) for r in readers]
    if "yes" in flags:
        return "yes"
    if "unknown" in flags or "n/a" in flags:
        return "unknown"
    return "no"
