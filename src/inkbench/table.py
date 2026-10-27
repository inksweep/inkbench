"""The result tables: benchmark means with 95 % block-bootstrap intervals and leakage flags, the reproduction check,
and paired comparisons against a reference reader.

``render`` writes ``TABLE.md``, ``REPRODUCTION.json`` and ``COMPARISONS.json`` to the results folder;
``render_reproduction`` writes only ``REPRODUCTION.json``; ``compare`` pairs two readers on every protocol.
"""
from __future__ import annotations

import json
from typing import Optional, Sequence

import numpy as np

from . import paths
from .bootstrap import bootstrap_ci, paired_bootstrap
from .catalog import BENCHMARKS
from .published import PUBLISHED, verdict
from .score import load_blocks

HIGHER_IS_BETTER = {"fa80_russo": False, "fa80_exact": False, "fa80_nieuwlaar": False}
VERDICTS = ("PASS", "WARN", "FAIL", "INFO", "missing", "n/a")


def _scores(bench: str) -> dict[str, dict]:
    d = paths.results() / "scores" / bench
    out = {}
    for f in sorted(d.glob("*.json")) if d.is_dir() else []:
        out[f.stem] = json.loads(f.read_text())
    return out


def _fmt(v: Optional[float], nd: int = 3) -> str:
    return "-" if v is None or v != v else f"{v:.{nd}f}"


def leak_cell(score: dict, protocols: Sequence[str]) -> str:
    """The leakage column: the test segments the reader's published training set includes (``tag``) or may include
    (``tag?``: training data not published); ``no`` when neither, ``n/a`` when the reader has no record."""
    flags: dict[str, str] = {}
    for p in protocols:
        flags.update(score.get(p, {}).get("trained_on", {}))
    marked = [f"{t}?" if v == "unknown" else t for t, v in sorted(flags.items()) if v in ("yes", "unknown")]
    if marked:
        return ",".join(marked)
    return "n/a" if flags and all(v == "n/a" for v in flags.values()) else "no"


def reproduction() -> list[dict]:
    """One row per published number: ours, the difference, the worst per-segment difference and the verdict."""
    rows = []
    for bench, proto, reader, want, source, *rest in PUBLISHED:
        kind = rest[0] if rest else "exact"
        b = BENCHMARKS[bench]
        sc = _scores(bench)
        tags = [s.tag for s in b.segs]
        external = reader.startswith("ext:")
        got_per = (sc.get("_external", {}).get(reader, {}) if external
                   else sc.get(reader, {}).get(proto, {}).get("per_segment", {}))
        if isinstance(want, list):
            pairs = [(t, w, got_per.get(t)) for t, w in zip(tags, want) if w is not None]
            have = [(t, w, g) for t, w, g in pairs if g is not None]
            got_mean = float(np.mean([g for _, _, g in have])) if have and len(have) == len(pairs) else None
            want_mean = float(np.mean([w for _, w, _ in pairs])) if pairs else None
            worst = max((abs(g - w) for _, w, g in have), default=None)
        else:
            vals = list(got_per.values())
            got_mean, want_mean, worst = (vals[0] if vals else None), float(want), None
        v = verdict(got_mean, want_mean, external, kind) if got_mean is not None else "missing"
        rows.append(dict(benchmark=bench, protocol=proto, reader=reader, published=want_mean, ours=got_mean,
                         delta=None if got_mean is None else got_mean - want_mean, worst_segment_delta=worst,
                         verdict=v, source=source))
    return rows


def verdict_counts(rows: Sequence[dict]) -> dict[str, int]:
    return {v: sum(r["verdict"] == v for r in rows) for v in VERDICTS}


def comparisons(reference: str, n_boot: int = 2000, readers: Optional[Sequence[str]] = None,
                benches: Optional[Sequence[str]] = None) -> list[dict]:
    """Paired block bootstrap of every reader (or ``readers``) against ``reference`` on every protocol."""
    rows = []
    for name, b in BENCHMARKS.items():
        if benches is not None and name not in benches:
            continue
        sc = _scores(name)
        candidates = [r for r in sc if not r.startswith("_") and r != reference]
        if readers is not None:
            candidates = [r for r in candidates if r in readers]
        if reference not in sc:
            continue
        for proto in b.protocols:
            ref_blocks = load_blocks(name, reference, proto)
            if not ref_blocks:
                continue
            for r in candidates:
                rb = load_blocks(name, r, proto)
                common = sorted(set(t for t, _ in rb) & set(t for t, _ in ref_blocks))
                if not common:
                    continue
                a = [s for t, s in rb if t in common]
                bb = [s for t, s in ref_blocks if t in common]
                res = paired_bootstrap(a, bb, n_boot=n_boot)
                hib = HIGHER_IS_BETTER.get(proto, True)
                better = (res["ci95"][0] > 0) if hib else (res["ci95"][1] < 0)
                rows.append(dict(benchmark=name, protocol=proto, reader=r, reference=reference, segments=common,
                                 primary=proto == b.primary, higher_is_better=hib,
                                 significant_better=bool(better), **res))
    return rows


def _reproduction_lines(rep: Sequence[dict]) -> list[str]:
    out = ["## Reproduction of published numbers", "",
           "| benchmark | protocol | reader | published | ours | delta | verdict | source |",
           "|---|---|---|---|---|---|---|---|"]
    for row in rep:
        out.append(f"| {row['benchmark']} | {row['protocol']} | {row['reader']} | {_fmt(row['published'], 4)} | "
                   f"{_fmt(row['ours'], 4)} | {_fmt(row['delta'], 4)} | {row['verdict']} | {row['source']} |")
    out += ["", f"REPRODUCTION: {verdict_counts(rep)}", ""]
    return out


def _comparison_lines(comp: Sequence[dict], reference: str, n_boot: int) -> list[str]:
    out = [f"## Paired block bootstrap against {reference} ({n_boot} draws; difference = reader - {reference})", "",
           "| benchmark | protocol | reader | reader value | reference value | difference [95 % CI] | MDE | "
           "significantly better |", "|---|---|---|---|---|---|---|---|"]
    for c in comp:
        out.append(f"| {c['benchmark']} | {c['protocol']}{' *' if c['primary'] else ''} | {c['reader']} | "
                   f"{_fmt(c['stat_a'])} | {_fmt(c['stat_b'])} | {_fmt(c['diff'])} [{_fmt(c['ci95'][0])}, "
                   f"{_fmt(c['ci95'][1])}] | {_fmt(c['mde_80pct'])} | {'yes' if c['significant_better'] else 'no'} |")
    return out


def render(reference: str = "readerv3", n_boot: int = 2000) -> str:
    """TABLE.md (returned and written), REPRODUCTION.json and COMPARISONS.json."""
    out = ["# inkbench results", ""]
    for name, b in BENCHMARKS.items():
        sc = _scores(name)
        readers = [r for r in sc if not r.startswith("_")]
        if not readers:
            continue
        out += [f"## {name} ({b.kind}): {b.notes}", "",
                "| reader | " + " | ".join(f"{p}{' (primary)' if p == b.primary else ''}" for p in b.protocols)
                + " | trained on a test segment (? = unknown) |", "|---" * (len(b.protocols) + 2) + "|"]
        for r in readers:
            cells = []
            for p in b.protocols:
                m = sc[r].get(p, {}).get("mean")
                ci = bootstrap_ci([s for _, s in load_blocks(name, r, p)], n_boot=min(n_boot, 500)) \
                    if m is not None else [None, None]
                cells.append(f"{_fmt(m)} [{_fmt(ci[0])}, {_fmt(ci[1])}]" if m is not None else "-")
            out.append(f"| {r} | " + " | ".join(cells) + f" | {leak_cell(sc[r], b.protocols)} |")
        ext = sc.get("_external")
        if ext:
            out += ["", "Published map files scored directly: " +
                    "; ".join(f"{k}: " + ", ".join(f"{t} {_fmt(v)}" for t, v in d.items()) for k, d in ext.items())]
        out.append("")
    rep = reproduction()
    out += _reproduction_lines(rep)
    comp = comparisons(reference, n_boot)
    out += _comparison_lines(comp, reference, n_boot)
    text = "\n".join(out) + "\n"
    root = paths.results()
    root.mkdir(parents=True, exist_ok=True)
    (root / "TABLE.md").write_text(text)
    (root / "REPRODUCTION.json").write_text(json.dumps(dict(rows=rep, counts=verdict_counts(rep)), indent=1,
                                                       default=float))
    (root / "COMPARISONS.json").write_text(json.dumps(comp, indent=1, default=float))
    return text


def render_reproduction() -> str:
    """The reproduction table alone (fast: no bootstrap); writes REPRODUCTION.json."""
    rep = reproduction()
    root = paths.results()
    root.mkdir(parents=True, exist_ok=True)
    (root / "REPRODUCTION.json").write_text(json.dumps(dict(rows=rep, counts=verdict_counts(rep)), indent=1,
                                                       default=float))
    return "\n".join(_reproduction_lines(rep)) + "\n"


def compare(reader: str, reference: str, n_boot: int = 2000, benches: Optional[Sequence[str]] = None) -> str:
    """Paired block bootstrap of ``reader`` against ``reference`` on every protocol (printed, not written)."""
    comp = comparisons(reference, n_boot, readers=[reader], benches=benches)
    if not comp:
        return f"no protocol has block statistics of both {reader} and {reference} (run `inkbench score` first)\n"
    return "\n".join(_comparison_lines(comp, reference, n_boot)) + "\n"
