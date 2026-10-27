"""inkbench: a benchmark of the public 9 um ink-detection readers for the Herculaneum scrolls.

Eight benchmarks scored with each published rule, exact label transfer between scan resolutions, leakage flags from
the readers' published training configurations, a paired spatial block bootstrap for every comparison, and a check
that the published numbers are reproduced. Predictions run through inksweep (exact mode); scoring runs on the CPU.
See docs/benchmarks.md.
"""
__version__ = "0.1.0"

__all__ = ["__version__"]
