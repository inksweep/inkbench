"""Command line: ``inkbench [--root DIR] <command> [options]`` (or ``python -m inkbench``).

  benchmarks    list the benchmarks, their segments and protocols
  fetch         download every benchmark input (open-data S3, Hugging Face, GitHub; resumable, verified)
  predict       run readers on every benchmark input (inksweep exact mode, depth 0, one process per GPU)
  score         score readers on every protocol (CPU) and keep the block statistics for the bootstrap
  ensemble      build prediction-averaging ensembles (NAME=reader,reader,...) and score them like readers
  table         TABLE.md: results with 95 % intervals, the reproduction check, paired comparisons
  reproduction  the reproduction check alone (REPRODUCTION.json)
  compare       paired block bootstrap of one reader against another on every protocol
  all           fetch, predict, score, ensemble, table
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from typing import Optional

from . import __version__

#: The readers of the published tables (inksweep built-in names).
READERS = "readerv3,readerv2,d9v4c,dnative,hecate,v8in,v8in_released,ink9_s42,ink9_s43_060k"
#: The ensembles of the published tables. The PHerc. 343 recipe's four models include ink9_s43 (step 75k), which is
#: predicted for the ensemble only.
ENSEMBLES = ("ens_recipe343=dnative,hecate,ink9_s42,ink9_s43",
             "ens_v3_hecate_d9v4c=readerv3,hecate,d9v4c",
             "ens_v3_hecate=readerv3,hecate")
PREDICT_READERS = READERS + ",ink9_s43"
STRICT_EXIT = 3


def _readers(text: str) -> list[str]:
    return [t.strip() for t in text.split(",") if t.strip()]


def _plugins(items: list[str]) -> dict[str, str]:
    from .predict import ReaderRef

    refs = [ReaderRef.parse(t) for t in items]
    bad = [r.name for r in refs if not r.plugin]
    if bad:
        raise SystemExit(f"--plugin needs NAME=path/to/plugin.py[:checkpoint+...], got {bad}")
    return {r.name: r.plugin for r in refs}


def _benches(text: str) -> list[str]:
    from .catalog import bench_list

    try:
        return bench_list(text)
    except ValueError as e:
        raise SystemExit(str(e)) from None


# ----------------------------------------------------------------------------------------------- commands
def cmd_benchmarks(a: argparse.Namespace) -> int:
    from .catalog import BENCHMARKS

    if a.json:
        print(json.dumps({n: dict(kind=b.kind, primary=b.primary, protocols=list(b.protocols),
                                  segments=[dict(sample=s.sample, prefix=s.prefix, tag=s.tag) for s in b.segs],
                                  notes=b.notes) for n, b in BENCHMARKS.items()}, indent=1))
        return 0
    print("| benchmark | kind | segments | protocols (primary first) |")
    print("|---|---|---|---|")
    for n, b in BENCHMARKS.items():
        protos = [b.primary] + [p for p in b.protocols if p != b.primary]
        print(f"| {n} | {b.kind} | {', '.join(s.tag for s in b.segs)} | {', '.join(protos)} |")
    return 0


def cmd_fetch(a: argparse.Namespace) -> int:
    from .data import prepare

    print(json.dumps(prepare(_benches(a.bench), threads=a.threads), indent=1))
    return 0


def cmd_predict(a: argparse.Namespace) -> int:
    from . import inputs, predict

    refs = [predict.ReaderRef(t) for t in _readers(a.readers)] + [predict.ReaderRef.parse(t) for t in a.plugin]
    inp = inputs.inputs_for(_benches(a.bench))
    print(f"{len(inp)} inputs x {len(refs)} readers")
    predict.run(inp, refs, predict.devices(a.gpus), mode="exact")       # the reference numerics only
    return 0


def cmd_score(a: argparse.Namespace) -> int:
    from .score import score_benchmark

    plugins = _plugins(a.plugin)
    names = _readers(a.readers) + [n for n in plugins if n not in _readers(a.readers)]
    for b in _benches(a.bench):
        print(b, json.dumps(score_benchmark(b, names, plugins), default=float))
    return 0


def cmd_ensemble(a: argparse.Namespace) -> int:
    from .ensemble import parse, run

    specs = a.specs or list(ENSEMBLES)
    for s in specs:
        try:
            parse(s)
        except ValueError as e:
            raise SystemExit(str(e)) from None
    print(json.dumps(run(specs, _benches(a.bench)), indent=1, default=float))
    return 0


def cmd_table(a: argparse.Namespace) -> int:
    from .table import render, reproduction, verdict_counts

    print(render(a.reference, a.n_boot), end="")
    if a.strict and verdict_counts(reproduction())["FAIL"]:
        return STRICT_EXIT
    return 0


def cmd_reproduction(a: argparse.Namespace) -> int:
    from .table import render_reproduction, reproduction, verdict_counts

    print(render_reproduction(), end="")
    if a.strict and verdict_counts(reproduction())["FAIL"]:
        return STRICT_EXIT
    return 0


def cmd_compare(a: argparse.Namespace) -> int:
    from .table import compare

    print(compare(a.reader, a.reference, a.n_boot, _benches(a.bench)), end="")
    return 0


def cmd_all(a: argparse.Namespace) -> int:
    cmd_fetch(a)
    cmd_predict(argparse.Namespace(**{**vars(a), "readers": a.predict_readers}))
    cmd_score(a)
    cmd_ensemble(argparse.Namespace(**{**vars(a), "specs": []}))
    return cmd_table(a)


# ----------------------------------------------------------------------------------------------- parser
def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="inkbench",
                                 description="A benchmark of the public 9 um ink-detection readers for the "
                                             "Herculaneum scrolls.",
                                 epilog="Locations: --root or INKBENCH_ROOT (default ./inkbench-data); INKBENCH_DATA, "
                                        "INKBENCH_RESULTS, INKBENCH_PREDS, INKBENCH_CKPT override one part each.")
    ap.add_argument("--version", action="version", version=f"inkbench {__version__}")
    ap.add_argument("--root", help="base folder for data, results and checkpoints (sets INKBENCH_ROOT)")
    sub = ap.add_subparsers(dest="command", metavar="command", required=True)

    def add(name: str, func, help_: str) -> argparse.ArgumentParser:
        p = sub.add_parser(name, help=help_, description=help_)
        p.set_defaults(func=func)
        return p

    def bench(p: argparse.ArgumentParser) -> None:
        p.add_argument("--bench", default="all", help="comma list of benchmarks, or 'all' (see `inkbench benchmarks`)")

    def readers(p: argparse.ArgumentParser, default: str) -> None:
        p.add_argument("--readers", default=default, help=f"comma list of inksweep reader names (default {default})")
        p.add_argument("--plugin", action="append", default=[], metavar="NAME=PLUGIN.py[:CKPT+CKPT...]",
                       help="a reader of your own: an inksweep plugin module and its checkpoints (repeatable)")

    def table_opts(p: argparse.ArgumentParser) -> None:
        p.add_argument("--reference", default="readerv3", help="reader every other is compared against")
        p.add_argument("--n-boot", type=int, default=2000, help="bootstrap draws of the paired comparisons")
        p.add_argument("--strict", action="store_true", help=f"exit {STRICT_EXIT} when a reproduction row FAILs")

    p = add("benchmarks", cmd_benchmarks, "list the benchmarks, their segments and protocols")
    p.add_argument("--json", action="store_true")
    p = add("fetch", cmd_fetch, "download every benchmark input (resumable, verified)")
    bench(p)
    p.add_argument("--threads", type=int, default=32)
    p = add("predict", cmd_predict, "run readers on every benchmark input (inksweep exact mode, depth 0; needs a GPU)")
    bench(p)
    readers(p, PREDICT_READERS)
    p.add_argument("--gpus", help="CUDA devices to use, e.g. 0,1 (default: every visible device)")
    p = add("score", cmd_score, "score readers on every protocol (CPU)")
    bench(p)
    readers(p, READERS)
    p = add("ensemble", cmd_ensemble, "build and score prediction-averaging ensembles")
    p.add_argument("specs", nargs="*", metavar="NAME=READER,READER,...",
                   help="ensembles to build (default: " + " ".join(ENSEMBLES) + ")")
    bench(p)
    p = add("table", cmd_table, "TABLE.md, REPRODUCTION.json and COMPARISONS.json from the scores")
    table_opts(p)
    p = add("reproduction", cmd_reproduction, "the reproduction check of the published numbers")
    p.add_argument("--strict", action="store_true", help=f"exit {STRICT_EXIT} when a row FAILs")
    p = add("compare", cmd_compare, "paired block bootstrap of one reader against another")
    p.add_argument("reader")
    p.add_argument("reference")
    p.add_argument("--n-boot", type=int, default=2000)
    bench(p)
    p = add("all", cmd_all, "fetch, predict, score, ensemble and table, in order (resumable)")
    bench(p)
    readers(p, READERS)
    p.add_argument("--predict-readers", default=PREDICT_READERS, help="readers to predict (the score readers plus "
                   "the ensembles' members)")
    p.add_argument("--threads", type=int, default=32)
    p.add_argument("--gpus")
    table_opts(p)
    return ap


def main(argv: Optional[list[str]] = None) -> int:
    a = parser().parse_args(list(sys.argv[1:] if argv is None else argv))
    if a.root:
        os.environ["INKBENCH_ROOT"] = a.root
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    return int(a.func(a) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
