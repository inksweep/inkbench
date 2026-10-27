# Changelog

All notable changes to inkbench. Versions follow [semantic versioning](https://semver.org/).

## 0.1.0

First release.

- Eight benchmarks of the public 9 µm ink-detection readers: PHerc0841 human labels, PHerc0009B at 116 keV,
  Nieuwlaar's native 113 keV benchmark, blank papyrus (false alarms at 80 % ink recall), PHerc1447, the PHerc0343P
  infrared camera truth, the letter-scale high-pass score on TAUIL's eight segments, and Reader v2's other held-out
  segments; each scored with the rule of the published evaluation it reproduces.
- Exact label transfer between scan resolutions (the canvas map of villa#2243 / tifxyz-canvas-map) next to the
  published plain-resize transfer, so both routes are reported.
- Leakage flags from each reader's published training configuration (`yes`, `unknown`), also for ensembles.
- A paired spatial block bootstrap (256 px blocks, segment-stratified) for every value and every comparison.
- A reproduction check of 44 published numbers (PASS / WARN / FAIL / INFO).
- `inkbench fetch`, `predict` (through inksweep, exact mode), `score`, `ensemble`, `table`, `reproduction`,
  `compare`, `benchmarks` and `all`; node scripts for setup and the full evaluation.
- CI (CPU tests on Python 3.12 and 3.14) and a release workflow that publishes to PyPI with trusted publishing.
