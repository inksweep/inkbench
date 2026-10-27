# Benchmarks and protocols

How inkbench makes its predictions, what each benchmark scores, how labels reach the 9 µm canvas, how leakage is
flagged, how the intervals are computed, and which published rules are transcribed. The numbers are in
[results.md](results.md).

## Predictions

Every reader runs through inksweep (`inksweep.sweep.Sweep`) in **exact mode**, which reproduces each reader's
reference numerics (precision, batch composition, accumulation order, OpenCV resampling), at **depth 0**: the centred
window that the published tools use by default (villa `infer` starts it at layer `L//2 - W//2`). Each benchmark has a reading
orientation: forward on the published surface volumes, reverse on the PHerc1447 surfaces. On PHerc1447 and on the
IR-truth segment the other orientation is predicted as well and its score is recorded as a control
(`blind_orientation` in the score files).

The map that is scored is the reference pipeline's own 8-bit value: `trunc(255 p)` for the villa family (the uint8
TIFF of `vesuvius.ink_detection.inference.infer`), and `round(255 p)` resized onto the native canvas with
INTER_LINEAR for readers run at another voxel size (Hecate at 9.6 µm, as Reader v2's `hecate_eval.py` scores it).
The villa-family readers run unresampled on the 7.91 µm PHerc0172 renders, as Reader v2's suite ran them.

Readers (inksweep names): `readerv3`, `readerv2` (D. Russo), `d9v4c` (TAUIL Abd Elilah), `dnative` (E. Nieuwlaar's
dense_native, step 16000), `hecate` (Hecate 9.6 µm, Vesuvius Challenge), `v8in` (Y. Nader's v8-in with the stitching
fixed) and `v8in_released` (its released stitching), `ink9_s42` and `ink9_s43_060k` (the organisers' `ink_9um`
seeds 42 and 43 at steps 75k and 60k). `ink9_s43` (step 75k) is predicted for the PHerc. 343 recipe ensemble only.
Weights are pinned by revision and sha256 in inksweep's registry.

## The eight benchmarks

Valid pixels are those whose middle layer has data (Reader v2's rule), except where a protocol says otherwise.
AUCs are tie-aware (P(ink > no-ink) + ½ P(tie)) unless a transcribed rule says otherwise. `_compat` protocols move
labels by plain resize, `_exact` protocols by the exact canvas map (next section).

### `p0841`: PHerc0841, human labels

Segments `20260220213127-w00` (w00), `20260220214732-auto_grown_20260220144552…` (ag896) and
`20260221022814-auto_grown_20260220174252…` (ag405): one patch, three overlapping segments, a noise floor of about
±0.03 AUC. Reference: the organisers' human labels (ink, supervision and validation masks, drawn on the 2.403 µm
canvas) and their 2.4 µm ink map.

| Protocol | Region and classes | AUC |
|---|---|---|
| `human_strict_exact` (primary) | validation ∩ supervision; ink labels against the rest | full |
| `human_sup_compat` | supervision | Reader v2's |
| `human_union_compat` | supervision ∪ validation (Reader v2's suite) | Reader v2's |
| `human_near2mm_exact` | ink: ≥ 50 % of the pixel inked; no-ink: < 5 % inked and within 214 px (~2 mm) of ink | TAUIL's |
| `map_compat`, `map_exact` | the 2.4 µm map: ink ≥ 128, no-ink ≤ 40 (of 255) | Reader v2's / full |

The validation masks of these segments cover 66-74 % of the canvas, unannotated surface included (ibarapascal), so
the union counts unlabelled papyrus as background; the primary protocol keeps only pixels both masks cover. If that
intersection holds fewer than 1000 pixels the protocol falls back to supervision and says so in the score file.

### `p0009b`: PHerc0009B at 116 keV

Segments `20250919125754`, `20250510172639`, `20250919133208`, `20250919140325` (8.64 µm). Reference: the 2.401 µm
map, moved for `map_compat` with torch's area resize as Reader v2's suite does; human labels on 125754 only. Protocols
`map_exact` (primary), `map_compat`, and on 125754 `human_union_compat` (the union taken on the fine canvas before the
resize, as in Reader v2's suite), `human_strict_exact`, `human_near2mm_exact`. Reader v2 and V3 trained on other
0009B segments, not these.

### `p0139_native`: Nieuwlaar's native 113 keV benchmark

Segments PHerc0139 `20260422000000-title` and `20260215000000-w024` (9.362 µm, 113 keV). Reference: the 78 keV
2.399 µm map. Nieuwlaar's frozen rule: domain = pixels where any layer has data and the map is > 0; `lo` = the
smallest map value holding ≥ 25 % of the domain, `hi` = max(128, the 85th percentile); ink ≥ `hi`, no-ink ≤ `lo`.
AUC as `native_bench.py` computes it (tie-aware ranks; a 20 M-pixel subsample, seed 20260803, when larger); maps of
label-smoothed readers (the villa family) are read as `clip((v − 64) / 128, 0, 1)`, other maps as `v / 255`.
Protocols `native78_exact` (primary) and `native78_compat`. The score files also hold Nieuwlaar's misregistration
control (classes shifted about 2 mm or rotated must fall towards 0.5).

### `p0139_blank`: false ink on blank papyrus

PHerc0139 `20260206000001-w047` (ink) and `20260220000000-w053` (known blank), two 2048 px crops of each published
surface volume, chosen from the reference and never from a model (Reader v2's `bkill.pick_crops`): on w047 the two
non-overlapping crops, at least 60 % valid, with the most 78 keV-map ink (≥ 128); on w053 the two with the most
rendered surface. Valid pixels: layer 14 has data.

| Protocol | Rule |
|---|---|
| `fa80_exact` (primary) | share of w053's valid pixels at or above the threshold that keeps 80 % of w047's ink pixels (map ≥ 128, exact transfer) |
| `fa80_russo` | the same with the map moved by torch's area resize (Reader v2's `bkill`) |
| `fa80_nieuwlaar` | Nieuwlaar's operating point on the whole segments: θ* recalls 80 % of the map's ink components ≥ 1597 px on w047 (a component counts when ≥ 10 % of its pixels reach θ); share of w053's valid area ≥ θ* (no interval) |
| `auc78_w047` | AUC on the w047 crops, map ≥ 128 against ≤ 40 (map moved by torch's area resize; Reader v2's AUC) |

Lower is better for the three false-alarm protocols.

### `p1447`: PHerc1447

Windings w058 and w060 of the Hugging Face dataset `YoussefMoNader/ink-8um-pherc1447-surfaces` (revision
`7e4d9187`, every file checked against its SHA256SUMS), read in reverse. The labels were refined with v8-in in the
loop. `hf_mask` (primary): inside the dataset's mask, label > 127 is ink (the dataset card's rule). `hf_mask_edge200`:
the mask, CT present in the middle layer, at least 200 px from the edge of the render (Jashann's rule for the
published Reader V3 and v2 rows).

### `p0343p_ir`: infrared camera truth

PHerc0343P segment `20250511003658` (8.64 µm) and `DomRusso2/ir-truth-9um` (commit `7e96b969`): ink = letters
traced on the infrared photo, no-ink = papyrus the photo shows as clean, at least 12 px from any letter. The map is
quantised by its own 0.1 and 99.9 percentiles over the fragment, and the AUC is compared with 2000 random placements
of the same letter mask (at least 250 px away, at least 80 % on the fragment), as `score_map.py` does: one fragment,
two lines of text.

### `hp8`: letter shape

TAUIL's eight held-out segments: PHerc0009B 125754, PHerc0139 w030 (`20250108000005`) and w045 (`20260126000000`),
PHerc0500P2 `20250825181859--1`, PHerc0814 46527 (`20260226000000`) and the three PHerc0841 segments.
`hp_exact` (primary): Pearson r between the prediction and the 2.4 µm map (exact transfer), both high-passed by
subtracting a mask-normalised Gaussian blur of σ = 20/3.9 px (48 µm at 9.362 µm, kept in pixels on other grids),
on valid pixels with a prediction, away from the border (normalised support > 0.999 at 2σ); |r| at shifts of 150 and
±300 px is recorded as a null. `human_near2mm_exact`: TAUIL's human-label AUC where labels exist.

### `v2_heldout`: Reader v2's other held-out segments

PHerc0500P2 `20250716055229` and `20250716055230`, PHerc0343P `20250904233748-0_b2` and `20250905172054-1_b2`,
PHerc0172 `20250926122938-w082` and `20250926132117-w083`. Reference: the 2.4 µm map, or for PHerc0172 the team's
same-scan map. Protocols `map_exact` (primary) and `map_compat`. Other segments of these objects were trained on.

## Label transfer

Labels and maps are drawn on the fine canvas (2.2-2.4 µm) and scored on the native one (7.9-9.4 µm). The published
recipes move them by plain resize, which pairs pixel indices; but the two meshes come from one source through
`vc_transform_geom` (a half-pixel resample of the grid) and are rendered with the canvas centred on the grid, so the
same papyrus sits at

    p_coarse = (p_fine + 0.5 + 0.5 / s) · n_coarse / n_fine − 0.5 / s − 0.5     (= (p + 10.5) ρ − 10.5 at s = 0.05)

per axis, with `n` the meshes' grid sizes and `s` the grid step: a plain resize lands about 10 (1 − ρ) px off, 7.4 px
(70 µm) on the 9.4 µm scans (villa#2243). `canvasmap.py` implements this rule (by S. Chicoineau and C. Thomas,
tifxyz-canvas-map, independently re-implemented) and reproduces three of their published pair maps to 1e-4 px
(`tests/test_canvasmap.py`). Every exact transfer first checks that the native surface volume is the scale-1 render
of its mesh. The `_compat` protocols keep the plain resize (cv2 INTER_AREA, or torch's area resize where the
published suite used it) so that the published numbers reproduce.

## Leakage flags

`resources/public_training_sets.json` lists, per reader and scroll, the 14-digit ids of the segments in its published
training configuration:

| Reader | Source | Flagged benchmark segments |
|---|---|---|
| Reader v2, Reader V3 | `train_config.json` of DomRusso2/reader-v2 and reader-v3 | hp8: PHerc0139 w030, w045, PHerc0814 46527; the IR-truth segment |
| d9v4C | `src/train.txt` of TAUIL-Abd-Elilah/9um-reader-letter-shape (124 segments) and its initialisation, Reader v2 | PHerc0009B 172639, 133208, 140325; title, w024; w047, w053; the IR-truth segment; hp8 w030, w045, 46527; v2_heldout 0500P2 ×2 and 0343P ×2 |
| dense_native | Nieuwlaar/ink9um-dense-native README, section 4 (the `ink_9um` corpus, 7 dense segments and 10 native PHerc0139 windings) | hp8 w030, w045, 46527 |
| ink_9um s42, s43 | the `ink_9um` README of the organisers' dataset (24 aligned and 5 native segments) | hp8 w030, w045, 46527 |
| Hecate | training data not published (its trainer is villa#1819) | unknown on every segment |
| v8-in | the model card names the scrolls (Scroll 1, Scroll 5, PHerc1667, PHerc0139, PHerc0814, PHerc0500P2 and one fragment), not the segments | unknown on PHerc0139, 0814, 0500P2 and 0172 segments |

A flag is `yes` when the segment is listed, `unknown` when the reader's lists are not published, `no` otherwise
(`n/a` for a reader without a record, such as a plugin). An ensemble carries its members' flags. Tables print the
flagged segments, unknown ones with `?`. No reader lists PHerc0841 or PHerc1447.

## Statistics

`bootstrap.py` resamples 256 px blocks (spatially correlated pixels are not independent), the design of C. Hull's
ink-nullkit. A block counts when it holds at least 500 labelled pixels (100 for the ink side of a false-alarm rate;
for the high-pass r, 500 pixels of the reader-independent core mask, so every reader has the same blocks). Each
segment is a stratum; the benchmark statistic is the mean over segments of the statistic computed from the summed
block statistics (an AUC's ink and no-ink histograms are drawn from the same blocks). Intervals are the 2.5 and 97.5
percentiles: 500 draws for one reader's interval in the tables, 2000 for the paired comparisons, seed 0.

Paired comparisons give both readers the same draws on their common blocks: the difference with its interval, the
share of draws ≤ 0, and the minimum detectable effect (2.8 × the bootstrap SD: 80 % power at the 5 % level). A reader
is "significantly better" when the interval excludes 0 in the better direction. Comparison values are block
statistics and can differ in the third decimal from the table means, which use every pixel (or the published
subsample).

## Transcribed scoring rules

| Rule | Source | Function |
|---|---|---|
| Subsampled rank AUC: 300 000 pixels per class, seed 0, rounded to 4 places | Reader v2 `v2_run.auc` | `metrics.auc_russo` |
| Ordinal-rank AUC: a tied pair counts 0; classes subsampled above 400 000 | TAUIL `eval9v2.auc` | `metrics.auc_tauil` |
| Rank AUC with a 20 M-pixel subsample (seed 20260803); `(v − 64) / 128` for label-smoothed maps | Nieuwlaar `native_bench.py` | `metrics.auc_nieuwlaar`, `nieuwlaar_pred` |
| 78 keV classes and the component-recall false-positive control | Nieuwlaar `native_bench.py` | `metrics.native78_classes`, `nieuwlaar_fp_control` |
| False alarms at 80 % ink recall; crop choice | Reader v2 `bkill.py` | `metrics.fa_at_recall`, `inputs.pick_crops` |
| Letter-scale high-pass r | C. Scheirer (report 02), as TAUIL's `hp_eval.score` applies it | `metrics.hp_score` |
| Camera-truth AUC and 2000 random placements | D. Russo `score_map.py` | `metrics.ir_truth_score` |
| The 0009B union on the fine canvas; Hecate's 8-bit map | Reader v2 `v2_run.evaluate`, `hecate_eval.py` | `refs.SegmentRefs`, `predict.score_map` |

## Reproduction check

`published.py` holds 44 published numbers, each with its source. A row compares the benchmark mean of the harness with
the published mean (per-segment values where they were published, with the worst segment reported):

- a published map file scored directly (`ext:` rows: PHerc1447's `v8in.png`, the five IR-truth maps) must match to
  0.002: same pixels, same rule;
- a re-inferred row PASSes within 0.015, WARNs within 0.03 (the PHerc0841 noise floor), else FAILs;
- rows made by a pipeline other than the one re-run here (Reader v2's own Hecate resampling script) are marked
  `approx` and end at INFO beyond the WARN band; the published v8-in rows are compared with `v8in_released`.

`inkbench table --strict` (and `reproduction --strict`) exits 3 when a row FAILs.

## Ensembles

`inkbench ensemble NAME=reader,reader,...` combines readers' depth-0 maps per input with the rule of the PHerc. 343
First Letters recipe (E. Nieuwlaar), at one depth: each member's 8-bit map is stretched to its own 1st and 99.5th
percentiles over the pixels where any member has a value, clipped to [0, 1] and z-scored; the mean z-score is mapped
to [0, 1] by its minimum and maximum and written as the map of a pseudo-reader, scored like any other. Two caveats:

- The pseudo-reader is scored with Reader V3's map conventions, so on Nieuwlaar's protocols (`native78_*`,
  `fa80_nieuwlaar`) its map is read as a label-smoothed map, `clip((v − 64) / 128, 0, 1)`. Ensemble values on those
  protocols are not comparable with single readers; `fa80_nieuwlaar` reads 1.000 for two of the three ensembles.
- The recipe itself sweeps 31 depths and two tile phases; these ensembles use the benchmarks' single depth.

## Data

| Data | Source | Licence |
|---|---|---|
| Native surface volumes (level 0), ink maps, human labels (level 0), meshes (grid sizes) | `vesuvius-challenge-open-data` S3 bucket, `<scroll>/segments/<segment>/` | CC BY-NC 4.0 |
| PHerc1447 w058, w060 surfaces, labels, masks | HF `YoussefMoNader/ink-8um-pherc1447-surfaces` @ `7e4d9187` | CC BY-NC 4.0 |
| PHerc0343P camera truth and published maps | GitHub `DomRusso2/ir-truth-9um` @ `7e96b969` | code MIT, data CC BY-NC 4.0 |
| Reader weights | inksweep's registry (pinned revisions, sha256) | MIT, as published |

`inkbench fetch` mirrors each zarr level from the bucket's listing (every listed chunk downloaded and its size
checked; a level counts only with its `GATED.json`), downloads through `.part` files and atomic renames, and records
what it chose in each segment's `segment.json`: about 24 GB, plus about 5 GB of label-transfer caches written by
the scorer. The prediction maps of the nine readers, `ink9_s43` and the three ensembles take about 55 GB.

## Outputs

Under `$INKBENCH_ROOT` (or the folders set by `INKBENCH_DATA`, `INKBENCH_RESULTS`, `INKBENCH_PREDS`,
`INKBENCH_CKPT`):

| Path | Content |
|---|---|
| `data/<scroll>/<segment>/` | the fetched inputs, `segment.json`, and caches of the transferred labels and maps |
| `results/preds/<scroll>/<segment>[/crop_y_x]/ink/<reader>/` | inksweep's maps (`raw/reading/d+00.tif`) |
| `results/scores/<benchmark>/<reader>.json` | per protocol: per-segment values, the mean, notes, leakage flags |
| `results/blocks/<benchmark>/<reader>.npz` | block statistics for the bootstrap |
| `results/TABLE.md`, `REPRODUCTION.json`, `COMPARISONS.json` | `inkbench table` |
| `results/ensembles.json` | members and scores of each ensemble |
