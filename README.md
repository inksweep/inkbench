# inkbench

**A benchmark of the public 9 µm ink-detection readers for the Herculaneum scrolls.**

inkbench scores nine public 9 µm ink readers, and ensembles of them, on eight benchmarks built from the Vesuvius
Challenge open data, each with the rule of the published evaluation it comes from. Labels move between scan
resolutions with the exact canvas map, every result carries leakage flags from the readers' published training
configurations, values come with spatial block-bootstrap intervals and comparisons with paired ones, and a
reproduction check of 44 published numbers comes first. Predictions run through
[inksweep](https://github.com/inksweep/inksweep) in exact mode (each reader's reference numerics); scoring runs on the
CPU.

## Findings

From one run of nine readers and three ensembles ([all tables](https://github.com/inksweep/inkbench/blob/main/docs/results.md)):

- **The harness reproduces the published numbers:** 42 of 44 PASS, 0 FAIL, 1 WARN, 1 INFO. The six published map
  files scored directly agree to the published decimals (largest difference 0.0003, on a value given to three).
- **Leakage flags, from the published configurations:** d9v4C's training list includes 3 of the 4 PHerc0009B
  segments, both segments of Nieuwlaar's native benchmark, both blank-papyrus segments, the IR-truth segment, 4 of the
  6 Reader v2 held-out segments and 3 of the 8 letter-shape (hp8) segments. Reader v2 and V3 include the same 3 hp8
  segments and the IR-truth segment. Hecate's training data are not published, so its rows are flagged unknown.
- **The PHerc. 343 recipe's four models do worse than Reader V3 alone on every benchmark** (combined with the
  recipe's z-score rule at one depth): PHerc0841 0.844 against 0.867; on the IR-truth fragment 0.772 against 0.774,
  within noise. At 80 % ink recall they mark 24.6 % of blank papyrus as ink, 4.5 times Reader V3's 5.4 %.
- **Adding Hecate to Reader V3 gives the best detector on PHerc0841:** Reader V3 + Hecate + d9v4C 0.888, +0.021
  [0.010, 0.033] over Reader V3; Reader V3 + Hecate 0.890, +0.023 [0.013, 0.035] (Hecate's flag is unknown). On
  PHerc0009B, PHerc1447 and Reader v2's held-out segments the three-model ensemble is +0.004 to +0.011 above Reader
  V3, but it nearly doubles the blank false alarms (10.3 % against 5.4 %). For letter shape single readers stay
  ahead: hp8 high-pass r 0.185 for d9v4C and 0.145 for Reader V3 against 0.135 for the ensemble.
- **v8-in's stitching fix** (J. Wallis, EconLearn; shipped in inksweep) raises its letter-shape score from 0.028
  [0.026, 0.030] to 0.037 [0.035, 0.039] (+33 %, higher on all eight segments) and raises every detection AUC by
  0.001 to 0.004 (each paired interval above 0).
- **Exact label transfer** removes the 7.4 px offset of a plain resize between the 2.4 µm and 9.4 µm canvases
  (villa#2243). On Nieuwlaar's native benchmark it raises every reader's AUC by 0.004 to 0.010 (Reader V3 0.968 to
  0.972); the plain-resize route is kept as `*_compat` to reproduce the published numbers.

## How it helps ink detection

The organisers ask analytic tools to show how they improve unwrapping or ink detection. inkbench did three things:

1. **Measured a fix.** The v8-in stitching fix gains a third in letter shape at no cost in detection; inksweep runs
   v8-in with it (`v8in`) and keeps the released stitching as `v8in_released`.
2. **Picked a screening ensemble.** Reader V3 + Hecate + d9v4C detects ink on PHerc0841 better than any single
   reader, with about half the blank false alarms of Reader V3 + Hecate (10.3 % against 18.5 %), while the PHerc. 343
   recipe's four models do worse than Reader V3 alone everywhere.
3. **Corrected the yardstick.** With the exact label transfer every reader scores higher than under a plain resize,
   and the leakage flags and the reproduction check show which comparisons can be trusted.

## Quick start

One Linux machine with an NVIDIA GPU and a final CPython 3.14 (the organisers' `vesuvius` package needs 3.14):

```bash
uv venv --seed --python 3.14 ~/venvs/inkbench && source ~/venvs/inkbench/bin/activate
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu129    # the build for your CUDA driver
pip install inkbench "inksweep[villa,v8in]"
pip install --no-deps "vesuvius @ git+https://github.com/ScrollPrize/villa.git@0fb38c45b488e192566ea83ae36369cb6db92652#subdirectory=vesuvius"

export INKBENCH_ROOT=/data/inkbench   # about 30 GB of inputs and caches, 55 GB of maps
inkbench fetch                        # every benchmark input: open-data S3, Hugging Face, GitHub (resumable, verified)
inkbench predict                      # the readers on every visible GPU (inksweep exact mode, depth 0)
inkbench score                        # CPU from here on
inkbench ensemble                     # the three ensembles of docs/results.md
inkbench table                        # TABLE.md, REPRODUCTION.json, COMPARISONS.json in $INKBENCH_ROOT/results
```

`inkbench all` runs the five steps; `node/run_inkbench_eval.sh` does the same on a GPU node after
`node/setup_inkbench.sh`. To benchmark a reader of your own, write an inksweep plugin and add
`--plugin mine=reader.py:weights.pt` to `predict` and `score`; `inkbench compare mine readerv3` pairs it with Reader V3.

## The benchmarks

| Benchmark | What it measures | Segments | Primary protocol |
|---|---|---|---|
| `p0841` | AUC against human labels on a scroll no published training list includes | PHerc0841 w00, ag896, ag405 | `human_strict_exact` |
| `p0009b` | AUC against the team's 2.4 µm ink map, 116 keV scan | PHerc0009B, 4 segments | `map_exact` |
| `p0139_native` | Nieuwlaar's native 113 keV benchmark (78 keV map classes) | PHerc0139 title, w024 | `native78_exact` |
| `p0139_blank` | False ink on blank papyrus at 80 % ink recall | PHerc0139 w047 (ink), w053 (blank) | `fa80_exact` |
| `p1447` | AUC against refined labels on a Grand Prize scroll | PHerc1447 w058, w060 | `hf_mask` |
| `p0343p_ir` | AUC against letters traced on an infrared photo | PHerc0343P 20250511003658 | `ir_camera` |
| `hp8` | Letter shape: high-pass r against the 2.4 µm map | TAUIL's 8 held-out segments | `hp_exact` |
| `v2_heldout` | AUC against the team's map on Reader v2's other held-out segments | PHerc0500P2, 0343P, 0172 | `map_exact` |

[docs/benchmarks.md](https://github.com/inksweep/inkbench/blob/main/docs/benchmarks.md) gives every protocol, the
label transfer, the region rules, the leakage flags, the statistics and the transcribed scoring rules;
[docs/results.md](https://github.com/inksweep/inkbench/blob/main/docs/results.md) gives every number.

## Development

```bash
pip install -e ".[test]" && pytest -q        # CPU only, synthetic data
```

CI runs these tests on Python 3.12 and 3.14; a `v*` tag equal to `__version__` publishes the release to PyPI.
Changes are listed in [CHANGELOG.md](https://github.com/inksweep/inkbench/blob/main/CHANGELOG.md).

## Credits and licence

inkbench is MIT-licensed (`LICENSE`); the scoring rules it transcribes are listed with their licences in `NOTICE`.

- Readers: D. Russo (Reader v2 and V3), TAUIL Abd Elilah (d9v4C), E. Nieuwlaar (dense_native), Y. Nader (v8-in), the
  Vesuvius Challenge team (`ink_9um`, Hecate); J. Wallis (EconLearn) for the v8-in stitching fix.
- Benchmarks and labels: the Vesuvius Challenge team (scans, surface volumes, 2.4 µm ink maps, the human labels of
  PHerc0841 and PHerc0009B, the infrared photography and letter tracing of PHerc0343P); E. Nieuwlaar (the native
  113 keV benchmark and its false-positive control); D. Russo (Reader v2's held-out suite and blank-papyrus test, the
  IR camera truth); TAUIL Abd Elilah (the hp8 segments and near-2 mm human AUC); C. Scheirer, Shribyr Labs (the
  letter-scale score); Y. Nader (the PHerc1447 surfaces and refined labels); J. S. Gill and N. N. Tran, Jashann (the
  PHerc1447 edge rule); ibarapascal (the validation masks cover unannotated surface).
- Methods: S. Chicoineau and C. Thomas (the canvas map, tifxyz-canvas-map), ScrollPrize/villa#2243 (the plain-resize
  offset), C. Hull (the paired block bootstrap, ink-nullkit), E. Nieuwlaar (the ensemble rule of the PHerc. 343
  First Letters recipe).

Scan data and everything derived from it (surface volumes, ink maps, labels, prediction maps) are under the Vesuvius
Challenge data licence (CC BY-NC 4.0) and are not included in this repository; `inkbench fetch` downloads them from
their sources. Model weights are downloaded from their authors' repositories under their own licences.
