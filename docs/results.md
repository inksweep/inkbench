# Results

One run on 27 October 2026 over the Vesuvius Challenge open data as published that day: nine public readers and three
ensembles on the eight benchmarks of [benchmarks.md](benchmarks.md), predicted in inksweep's exact mode at depth 0
and scored by inkbench 0.1.0; re-scoring the same maps with the released package reproduces every number here
exactly. `inkbench table` prints these numbers under the readers' inksweep names (`TABLE.md`, `REPRODUCTION.json`,
`COMPARISONS.json`); here the names are spelled out.

Each value is the benchmark mean (the mean over segments of the per-segment score) with its 95 % interval from the
spatial block bootstrap (500 draws). AUCs are higher-is-better, false-alarm rates (`fa80_*`) lower-is-better.
"Trained on" lists the benchmark segments in the reader's published training set; `?` marks segments whose
status is unknown because the training data are not published (benchmarks.md, Leakage flags).

## Readers and ensembles

| Name | inksweep reader | Authors |
|---|---|---|
| Reader V3, Reader v2 | `readerv3`, `readerv2` | D. Russo |
| d9v4C | `d9v4c` | TAUIL Abd Elilah |
| dense_native | `dnative` (step 16000) | E. Nieuwlaar |
| Hecate 9.6 µm | `hecate` | Vesuvius Challenge |
| v8-in | `v8in` (tile stitching fixed by J. Wallis) | Y. Nader |
| v8-in, released stitching | `v8in_released` | Y. Nader |
| ink_9um s42, ink_9um s43 (60k) | `ink9_s42` (step 75k), `ink9_s43_060k` | Vesuvius Challenge |

| Ensemble | Members | `inkbench ensemble` default name |
|---|---|---|
| Ens. V3 + Hecate + d9v4C | `readerv3`, `hecate`, `d9v4c` | `ens_v3_hecate_d9v4c` |
| Ens. V3 + Hecate | `readerv3`, `hecate` | `ens_v3_hecate` |
| Ens. PHerc. 343 recipe | `dnative`, `hecate`, `ink9_s42`, `ink9_s43` (the four models of the PHerc. 343 First Letters recipe, at one depth) | `ens_recipe343` |

Ensembles combine the members' maps with the recipe's rule (per-model stretch, mean z-score) and are scored like a
reader. On Nieuwlaar's protocols (`native78_*`, `fa80_nieuwlaar`) their maps get the `(v − 64) / 128` rescale meant
for label-smoothed maps, so those ensemble values (marked †) are not comparable with the single readers'.

## PHerc0841, human labels (`p0841`)

A scroll in no published training list (one patch, three overlapping segments; ~+-0.03 AUC noise floor).

| Reader | `human_strict_exact` (primary) | `human_sup_compat` | `human_union_compat` | `human_near2mm_exact` | `map_compat` | `map_exact` | Trained on |
|---|---|---|---|---|---|---|---|
| Reader V3 | 0.867 [0.835, 0.896] | 0.868 [0.836, 0.895] | 0.852 [0.816, 0.879] | 0.862 [0.832, 0.892] | 0.869 [0.857, 0.879] | 0.874 [0.862, 0.884] | no |
| Reader v2 | 0.839 [0.806, 0.870] | 0.840 [0.804, 0.870] | 0.824 [0.788, 0.852] | 0.827 [0.796, 0.860] | 0.858 [0.847, 0.868] | 0.863 [0.851, 0.873] | no |
| d9v4C | 0.842 [0.813, 0.871] | 0.841 [0.809, 0.867] | 0.829 [0.799, 0.854] | 0.831 [0.803, 0.860] | 0.853 [0.842, 0.862] | 0.862 [0.852, 0.872] | no |
| dense_native | 0.802 [0.762, 0.839] | 0.802 [0.761, 0.835] | 0.800 [0.763, 0.829] | 0.794 [0.759, 0.830] | 0.802 [0.788, 0.814] | 0.808 [0.794, 0.820] | no |
| Hecate 9.6 µm | 0.871 [0.845, 0.894] | 0.863 [0.839, 0.886] | 0.856 [0.833, 0.876] | 0.860 [0.843, 0.886] | 0.846 [0.834, 0.856] | 0.855 [0.843, 0.865] | ag405?, ag896?, w00? |
| v8-in | 0.823 [0.790, 0.853] | 0.821 [0.788, 0.852] | 0.801 [0.763, 0.832] | 0.811 [0.779, 0.841] | 0.840 [0.828, 0.851] | 0.846 [0.833, 0.857] | no |
| v8-in, released stitching | 0.821 [0.788, 0.851] | 0.820 [0.786, 0.851] | 0.801 [0.763, 0.831] | 0.809 [0.778, 0.839] | 0.839 [0.827, 0.849] | 0.844 [0.831, 0.855] | no |
| ink_9um s42 | 0.739 [0.697, 0.779] | 0.740 [0.698, 0.781] | 0.729 [0.689, 0.764] | 0.737 [0.704, 0.776] | 0.716 [0.700, 0.729] | 0.720 [0.704, 0.734] | no |
| ink_9um s43 (60k) | 0.735 [0.700, 0.770] | 0.729 [0.696, 0.763] | 0.733 [0.700, 0.761] | 0.741 [0.711, 0.776] | 0.708 [0.694, 0.721] | 0.712 [0.698, 0.724] | no |
| Ens. V3 + Hecate + d9v4C | 0.888 [0.860, 0.912] | 0.885 [0.859, 0.907] | 0.874 [0.844, 0.895] | 0.882 [0.856, 0.906] | 0.896 [0.888, 0.904] | 0.904 [0.895, 0.911] | ag405?, ag896?, w00? |
| Ens. V3 + Hecate | 0.890 [0.862, 0.914] | 0.886 [0.861, 0.909] | 0.874 [0.843, 0.896] | 0.886 [0.860, 0.910] | 0.894 [0.885, 0.902] | 0.900 [0.891, 0.908] | ag405?, ag896?, w00? |
| Ens. PHerc. 343 recipe | 0.844 [0.812, 0.874] | 0.837 [0.803, 0.865] | 0.832 [0.801, 0.857] | 0.841 [0.811, 0.868] | 0.827 [0.814, 0.839] | 0.836 [0.823, 0.847] | ag405?, ag896?, w00? |

## PHerc0009B, 116 keV (`p0009b`)

116 keV; held out by Reader v2/V3 (other 0009B segments trained); d9v4C trained 3 of 4.

| Reader | `map_exact` (primary) | `map_compat` | `human_union_compat` | `human_strict_exact` | `human_near2mm_exact` | Trained on |
|---|---|---|---|---|---|---|
| Reader V3 | 0.856 [0.842, 0.869] | 0.854 [0.839, 0.867] | 0.949 [0.928, 0.967] | 0.952 [0.919, 0.975] | 0.937 [0.919, 0.957] | no |
| Reader v2 | 0.838 [0.824, 0.851] | 0.834 [0.821, 0.847] | 0.927 [0.902, 0.950] | 0.933 [0.895, 0.963] | 0.917 [0.896, 0.945] | no |
| d9v4C | 0.832 [0.819, 0.844] | 0.823 [0.811, 0.834] | 0.923 [0.894, 0.948] | 0.936 [0.897, 0.964] | 0.920 [0.899, 0.948] | 133208, 140325, 172639 |
| dense_native | 0.729 [0.712, 0.748] | 0.725 [0.709, 0.742] | 0.901 [0.867, 0.933] | 0.925 [0.859, 0.967] | 0.895 [0.861, 0.932] | no |
| Hecate 9.6 µm | 0.759 [0.746, 0.771] | 0.753 [0.740, 0.766] | 0.906 [0.878, 0.935] | 0.890 [0.834, 0.933] | 0.897 [0.879, 0.932] | 125754?, 133208?, 140325?, 172639? |
| v8-in | 0.771 [0.757, 0.785] | 0.765 [0.750, 0.777] | 0.871 [0.836, 0.903] | 0.901 [0.862, 0.934] | 0.859 [0.825, 0.891] | no |
| v8-in, released stitching | 0.769 [0.755, 0.783] | 0.763 [0.749, 0.775] | 0.870 [0.835, 0.902] | 0.899 [0.861, 0.932] | 0.856 [0.824, 0.890] | no |
| ink_9um s42 | 0.618 [0.604, 0.632] | 0.615 [0.602, 0.628] | 0.805 [0.760, 0.845] | 0.849 [0.771, 0.908] | 0.797 [0.760, 0.845] | no |
| ink_9um s43 (60k) | 0.630 [0.616, 0.645] | 0.626 [0.612, 0.640] | 0.813 [0.780, 0.844] | 0.835 [0.769, 0.883] | 0.793 [0.764, 0.833] | no |
| Ens. V3 + Hecate + d9v4C | 0.860 [0.846, 0.873] | 0.855 [0.842, 0.867] | 0.950 [0.927, 0.969] | 0.952 [0.916, 0.976] | 0.944 [0.926, 0.963] | 125754?, 133208, 140325, 172639 |
| Ens. V3 + Hecate | 0.854 [0.839, 0.868] | 0.850 [0.836, 0.863] | 0.953 [0.932, 0.970] | 0.951 [0.916, 0.975] | 0.945 [0.928, 0.962] | 125754?, 133208?, 140325?, 172639? |
| Ens. PHerc. 343 recipe | 0.737 [0.718, 0.754] | 0.731 [0.713, 0.748] | 0.915 [0.884, 0.943] | 0.928 [0.886, 0.960] | 0.910 [0.882, 0.939] | 125754?, 133208?, 140325?, 172639? |

## Nieuwlaar's native 113 keV benchmark (`p0139_native`)

Nieuwlaar's frozen native 113 keV benchmark (78 keV-map classes; teacher family = canonical).

| Reader | `native78_compat` | `native78_exact` (primary) | Trained on |
|---|---|---|---|
| Reader V3 | 0.968 [0.960, 0.976] | 0.972 [0.964, 0.979] | no |
| Reader v2 | 0.959 [0.950, 0.966] | 0.964 [0.956, 0.970] | no |
| d9v4C | 0.961 [0.954, 0.967] | 0.967 [0.961, 0.972] | title, w024 |
| dense_native | 0.962 [0.954, 0.968] | 0.965 [0.958, 0.971] | no |
| Hecate 9.6 µm | 0.898 [0.884, 0.910] | 0.905 [0.891, 0.916] | title?, w024? |
| v8-in | 0.917 [0.906, 0.928] | 0.922 [0.910, 0.932] | title?, w024? |
| v8-in, released stitching | 0.913 [0.902, 0.924] | 0.918 [0.906, 0.928] | title?, w024? |
| ink_9um s42 | 0.843 [0.824, 0.857] | 0.851 [0.832, 0.866] | no |
| ink_9um s43 (60k) | 0.854 [0.837, 0.868] | 0.863 [0.847, 0.877] | no |
| Ens. V3 + Hecate + d9v4C | 0.964 [0.956, 0.971] † | 0.970 [0.962, 0.976] † | title, w024 |
| Ens. V3 + Hecate | 0.924 [0.912, 0.935] † | 0.932 [0.920, 0.942] † | title?, w024? |
| Ens. PHerc. 343 recipe | 0.920 [0.909, 0.930] † | 0.929 [0.918, 0.938] † | title?, w024? |

## False ink on blank papyrus (`p0139_blank`)

False ink on known-blank w053 at 80 % ink recall on w047 (published SV crops).

| Reader | `fa80_exact` (primary) | `fa80_russo` | `fa80_nieuwlaar` | `auc78_w047` | Trained on |
|---|---|---|---|---|---|
| Reader V3 | 0.054 [0.034, 0.079] | 0.056 [0.035, 0.078] | 0.108 [-, -] | 0.933 [0.917, 0.945] | no |
| Reader v2 | 0.097 [0.068, 0.135] | 0.104 [0.074, 0.137] | 0.132 [-, -] | 0.896 [0.876, 0.913] | no |
| d9v4C | 0.120 [0.090, 0.158] | 0.137 [0.103, 0.167] | 0.106 [-, -] | 0.898 [0.878, 0.914] | w047, w053 |
| dense_native | 0.107 [0.077, 0.143] | 0.112 [0.078, 0.143] | 0.137 [-, -] | 0.895 [0.875, 0.912] | no |
| Hecate 9.6 µm | 0.526 [0.415, 0.611] | 0.526 [0.436, 0.624] | 0.309 [-, -] | 0.795 [0.765, 0.828] | w047?, w053? |
| v8-in | 0.436 [0.355, 0.521] | 0.461 [0.379, 0.530] | 0.246 [-, -] | 0.811 [0.785, 0.835] | w047?, w053? |
| v8-in, released stitching | 0.438 [0.358, 0.523] | 0.464 [0.384, 0.532] | 0.248 [-, -] | 0.808 [0.783, 0.832] | w047?, w053? |
| ink_9um s42 | 0.441 [0.380, 0.510] | 0.486 [0.394, 0.555] | 0.269 [-, -] | 0.748 [0.719, 0.776] | no |
| ink_9um s43 (60k) | 0.397 [0.340, 0.473] | 0.421 [0.361, 0.490] | 0.203 [-, -] | 0.770 [0.744, 0.793] | no |
| Ens. V3 + Hecate + d9v4C | 0.103 [0.073, 0.136] | 0.109 [0.078, 0.137] | 0.194 [-, -] † | 0.881 [0.860, 0.905] | w047, w053 |
| Ens. V3 + Hecate | 0.185 [0.135, 0.235] | 0.190 [0.142, 0.239] | 1.000 [-, -] † | 0.914 [0.898, 0.930] | w047?, w053? |
| Ens. PHerc. 343 recipe | 0.246 [0.189, 0.294] | 0.253 [0.205, 0.303] | 1.000 [-, -] † | 0.870 [0.847, 0.890] | w047?, w053? |

`fa80_nieuwlaar` is computed on the whole segments and has no interval.

## PHerc1447 (`p1447`)

Grand Prize-eligible scroll, in no reader's published training set; labels refined with v8-in in the loop.

| Reader | `hf_mask` (primary) | `hf_mask_edge200` | Trained on |
|---|---|---|---|
| Reader V3 | 0.811 [0.781, 0.838] | 0.810 [0.777, 0.841] | no |
| Reader v2 | 0.798 [0.769, 0.824] | 0.797 [0.765, 0.826] | no |
| d9v4C | 0.772 [0.743, 0.799] | 0.769 [0.736, 0.800] | no |
| dense_native | 0.767 [0.736, 0.793] | 0.767 [0.738, 0.798] | no |
| Hecate 9.6 µm | 0.759 [0.726, 0.789] | 0.751 [0.715, 0.785] | w058?, w060? |
| v8-in | 0.837 [0.816, 0.857] | 0.834 [0.810, 0.860] | no |
| v8-in, released stitching | 0.836 [0.814, 0.856] | 0.833 [0.809, 0.859] | no |
| ink_9um s42 | 0.697 [0.666, 0.725] | 0.696 [0.665, 0.725] | no |
| ink_9um s43 (60k) | 0.705 [0.674, 0.731] | 0.702 [0.672, 0.730] | no |
| Ens. V3 + Hecate + d9v4C | 0.816 [0.786, 0.844] | 0.810 [0.778, 0.841] | w058?, w060? |
| Ens. V3 + Hecate | 0.817 [0.787, 0.845] | 0.810 [0.778, 0.841] | w058?, w060? |
| Ens. PHerc. 343 recipe | 0.785 [0.758, 0.810] | 0.781 [0.754, 0.807] | w058?, w060? |

Published map files scored directly (the dataset's own prediction files): predictions/loo_w058.png: w058 0.846; predictions/v8in.png: w058 0.862, w060 0.810; predictions/loo_w060.png: w060 0.803.

## PHerc0343P, infrared camera truth (`p0343p_ir`)

Camera truth (one fragment, two lines); Reader v2/V3 and d9v4C trained on this segment.

| Reader | `ir_camera` (primary) | Trained on |
|---|---|---|
| Reader V3 | 0.774 [0.693, 0.856] | 343P_ir |
| Reader v2 | 0.834 [0.775, 0.902] | 343P_ir |
| d9v4C | 0.834 [0.775, 0.894] | 343P_ir |
| dense_native | 0.746 [0.663, 0.819] | no |
| Hecate 9.6 µm | 0.743 [0.677, 0.821] | 343P_ir? |
| v8-in | 0.747 [0.688, 0.812] | no |
| v8-in, released stitching | 0.744 [0.686, 0.807] | no |
| ink_9um s42 | 0.623 [0.536, 0.711] | no |
| ink_9um s43 (60k) | 0.709 [0.649, 0.771] | no |
| Ens. V3 + Hecate + d9v4C | 0.852 [0.792, 0.908] | 343P_ir |
| Ens. V3 + Hecate | 0.832 [0.767, 0.893] | 343P_ir |
| Ens. PHerc. 343 recipe | 0.772 [0.707, 0.841] | 343P_ir? |

Published map files scored directly (the maps published with the camera truth): maps/hecate-9.6um.png: 343P_ir 0.721; maps/reader-v2.png: 343P_ir 0.834; maps/reader-v3.png: 343P_ir 0.774; maps/team-2.2um-model-map.png: 343P_ir 0.909; maps/v8-in.png: 343P_ir 0.744.

## Letter shape (`hp8`)

TAUIL's 8 held-out segments; 0139 w030/w045 and 0814 46527 were trained on by Reader v2/V3.

| Reader | `hp_exact` (primary) | `human_near2mm_exact` | Trained on |
|---|---|---|---|
| Reader V3 | 0.145 [0.137, 0.153] | 0.887 [0.870, 0.906] | 0139_w030, 0139_w045, 0814_46527 |
| Reader v2 | 0.129 [0.122, 0.135] | 0.854 [0.835, 0.879] | 0139_w030, 0139_w045, 0814_46527 |
| d9v4C | 0.185 [0.178, 0.192] | 0.854 [0.837, 0.875] | 0139_w030, 0139_w045, 0814_46527 |
| dense_native | 0.069 [0.064, 0.074] | 0.840 [0.821, 0.861] | 0139_w030, 0139_w045, 0814_46527 |
| Hecate 9.6 µm | 0.056 [0.052, 0.059] | 0.868 [0.855, 0.891] | 0009B_125754?, 0139_w030?, 0139_w045?, 0500P2_1?, 0814_46527?, ag405?, ag896?, w00? |
| v8-in | 0.037 [0.035, 0.039] | 0.811 [0.791, 0.835] | 0139_w030?, 0139_w045?, 0500P2_1?, 0814_46527? |
| v8-in, released stitching | 0.028 [0.026, 0.030] | 0.808 [0.788, 0.832] | 0139_w030?, 0139_w045?, 0500P2_1?, 0814_46527? |
| ink_9um s42 | 0.035 [0.031, 0.038] | 0.794 [0.773, 0.820] | 0139_w030, 0139_w045, 0814_46527 |
| ink_9um s43 (60k) | 0.041 [0.037, 0.046] | 0.789 [0.767, 0.814] | 0139_w030, 0139_w045, 0814_46527 |
| Ens. V3 + Hecate + d9v4C | 0.135 [0.129, 0.141] | 0.900 [0.884, 0.918] | 0009B_125754?, 0139_w030, 0139_w045, 0500P2_1?, 0814_46527, ag405?, ag896?, w00? |
| Ens. V3 + Hecate | 0.102 [0.096, 0.107] | 0.903 [0.886, 0.920] | 0009B_125754?, 0139_w030, 0139_w045, 0500P2_1?, 0814_46527, ag405?, ag896?, w00? |
| Ens. PHerc. 343 recipe | 0.087 [0.082, 0.092] | 0.879 [0.858, 0.898] | 0009B_125754?, 0139_w030, 0139_w045, 0500P2_1?, 0814_46527, ag405?, ag896?, w00? |

## Reader v2's other held-out segments (`v2_heldout`)

Reader v2's other held-out segments (other segments of these objects were trained on).

| Reader | `map_exact` (primary) | `map_compat` | Trained on |
|---|---|---|---|
| Reader V3 | 0.866 [0.852, 0.878] | 0.865 [0.851, 0.876] | no |
| Reader v2 | 0.850 [0.838, 0.863] | 0.847 [0.834, 0.860] | no |
| d9v4C | 0.836 [0.825, 0.848] | 0.829 [0.818, 0.842] | 0343P_0b2, 0343P_1b2, 0500P2_371, 0500P2_377 |
| dense_native | 0.638 [0.622, 0.654] | 0.637 [0.620, 0.651] | no |
| Hecate 9.6 µm | 0.729 [0.716, 0.742] | 0.724 [0.710, 0.736] | 0172_w082?, 0172_w083?, 0343P_0b2?, 0343P_1b2?, 0500P2_371?, 0500P2_377? |
| v8-in | 0.810 [0.794, 0.823] | 0.806 [0.791, 0.819] | 0172_w082?, 0172_w083?, 0500P2_371?, 0500P2_377? |
| v8-in, released stitching | 0.808 [0.792, 0.821] | 0.804 [0.789, 0.817] | 0172_w082?, 0172_w083?, 0500P2_371?, 0500P2_377? |
| ink_9um s42 | 0.526 [0.511, 0.543] | 0.527 [0.511, 0.544] | no |
| ink_9um s43 (60k) | 0.563 [0.547, 0.578] | 0.562 [0.546, 0.576] | no |
| Ens. V3 + Hecate + d9v4C | 0.877 [0.865, 0.887] | 0.872 [0.860, 0.883] | 0172_w082?, 0172_w083?, 0343P_0b2, 0343P_1b2, 0500P2_371, 0500P2_377 |
| Ens. V3 + Hecate | 0.873 [0.861, 0.884] | 0.870 [0.858, 0.881] | 0172_w082?, 0172_w083?, 0343P_0b2?, 0343P_1b2?, 0500P2_371?, 0500P2_377? |
| Ens. PHerc. 343 recipe | 0.620 [0.607, 0.633] | 0.617 [0.603, 0.629] | 0172_w082?, 0172_w083?, 0343P_0b2?, 0343P_1b2?, 0500P2_371?, 0500P2_377? |

## Reproduction of published numbers

The harness against 44 published numbers (benchmarks.md, Reproduction check). Published and inkbench values are
benchmark means; "worst" is the largest per-segment difference where per-segment values were published.

| Benchmark | Protocol | Reader | Published | inkbench | Difference | Worst segment | Verdict | Source |
|---|---|---|---|---|---|---|---|---|
| `p0841` | `human_union_compat` | Reader v2 | 0.8237 | 0.8237 | 0.0000 | 0.0000 | PASS | DomRusso2/reader-v2 results/040000.json (v2_run.evaluate: union of supervision+validation, resized labels) |
| `p0841` | `human_union_compat` | Hecate 9.6 µm | 0.8551 | 0.8558 | 0.0008 | 0.0114 | PASS | DomRusso2/reader-v2 results/0841_regions.json |
| `p0841` | `human_union_compat` | dense_native | 0.7999 | 0.7999 | 0.0000 | 0.0000 | PASS | DomRusso2/reader-v2 results/0841_regions.json |
| `p0841` | `human_union_compat` | ink_9um s43 (60k) | 0.7325 | 0.7325 | 0.0000 | 0.0000 | PASS | DomRusso2/reader-v2 results/0841_regions.json (released_s43_60k) |
| `p0841` | `human_sup_compat` | Reader v2 | 0.8404 | 0.8403 | -0.0000 | 0.0001 | PASS | DomRusso2/reader-v2 results/0841_regions.json (in_supervision) |
| `p0841` | `human_sup_compat` | Hecate 9.6 µm | 0.8632 | 0.8631 | -0.0001 | 0.0125 | PASS | DomRusso2/reader-v2 results/0841_regions.json |
| `p0841` | `human_near2mm_exact` | Reader V3 | 0.8629 | 0.8624 | -0.0005 | 0.0021 | PASS | TAUIL-Abd-Elilah/9um-reader-letter-shape results/v3_row (labels aligned by NCC; we use the exact canvas map) |
| `p0841` | `human_near2mm_exact` | Reader v2 | 0.8279 | 0.8272 | -0.0007 | 0.0028 | PASS | TAUIL results/v3_row |
| `p0841` | `human_near2mm_exact` | d9v4C | 0.8317 | 0.8309 | -0.0008 | 0.0024 | PASS | TAUIL results/v3_row |
| `p0841` | `map_compat` | Reader v2 | 0.8578 | 0.8578 | 0.0000 | 0.0000 | PASS | DomRusso2/reader-v2 results/040000.json (auc_map) |
| `p0009b` | `map_compat` | Reader v2 | 0.8342 | 0.8342 | 0.0000 | 0.0000 | PASS | DomRusso2/reader-v2 results/040000.json |
| `p0009b` | `human_union_compat` | Reader v2 | 0.9266 | 0.9266 | 0.0000 | 0.0000 | PASS | DomRusso2/reader-v2 results/040000.json |
| `p0009b` | `human_union_compat` | Reader V3 | 0.9431 | 0.9487 | 0.0056 | 0.0056 | PASS | DomRusso2/reader-v3 results/suite_reader-v3.json (0009B_125754) |
| `p0009b` | `human_union_compat` | Hecate 9.6 µm | 0.8928 | 0.9063 | 0.0135 | 0.0135 | PASS | DomRusso2/reader-v3 results/suite_hecate.json |
| `p0009b` | `human_union_compat` | v8-in, released stitching | 0.8699 | 0.8697 | -0.0002 | 0.0002 | PASS | DomRusso2/reader-v3 results/suite_base21.json (v8-in stride 21, released code) |
| `p0009b` | `human_near2mm_exact` | Reader V3 | 0.9385 | 0.9374 | -0.0011 | 0.0011 | PASS | TAUIL results/v3_row |
| `p0009b` | `human_near2mm_exact` | Reader v2 | 0.9171 | 0.9169 | -0.0002 | 0.0002 | PASS | TAUIL results/v3_row |
| `p0139_native` | `native78_compat` | dense_native | 0.9617 | 0.9617 | 0.0000 | 0.0000 | PASS | Nieuwlaar/ink9um-dense-native training/BENCHMARK.csv (dense_native-016000) |
| `p0139_native` | `native78_compat` | ink_9um s42 | 0.8429 | 0.8430 | 0.0000 | 0.0001 | PASS | Nieuwlaar native-eval/RESULTS_full.csv (released-s42-075000) |
| `p0139_blank` | `fa80_russo` | Reader V3 | 0.0545 | 0.0563 | 0.0018 | - | PASS | DomRusso2/reader-v3 results/suite_reader-v3.json (FA80_w053) |
| `p0139_blank` | `fa80_russo` | Reader v2 | 0.0925 | 0.1044 | 0.0119 | - | PASS | DomRusso2/reader-v3 results/suite_v2.json |
| `p0139_blank` | `fa80_russo` | Hecate 9.6 µm | 0.5765 | 0.5260 | -0.0505 | - | INFO | DomRusso2/reader-v3 results/suite_hecate.json |
| `p0139_blank` | `fa80_russo` | v8-in, released stitching | 0.4608 | 0.4645 | 0.0037 | - | PASS | DomRusso2/reader-v3 results/suite_base21.json |
| `p0139_blank` | `auc78_w047` | Reader V3 | 0.9298 | 0.9327 | 0.0029 | - | PASS | DomRusso2/reader-v3 results/suite_reader-v3.json (w047) |
| `p0139_blank` | `auc78_w047` | Reader v2 | 0.8971 | 0.8960 | -0.0011 | - | PASS | DomRusso2/reader-v3 results/suite_v2.json |
| `p0139_blank` | `auc78_w047` | Hecate 9.6 µm | 0.7756 | 0.7952 | 0.0196 | - | WARN | DomRusso2/reader-v3 results/suite_hecate.json |
| `p0139_blank` | `fa80_nieuwlaar` | ink_9um s42 | 0.2690 | 0.2694 | 0.0004 | - | PASS | Nieuwlaar README section 5 (released checkpoint, 26.9 %) |
| `p1447` | `hf_mask` | published map `predictions/v8in.png` | 0.8360 | 0.8361 | 0.0001 | 0.0003 | PASS | HF YoussefMoNader/ink-8um-pherc1447-surfaces dataset card (base v8-in, reversed layers) |
| `p1447` | `hf_mask` | v8-in, released stitching | 0.8360 | 0.8361 | 0.0001 | 0.0003 | PASS | HF ink-8um-pherc1447-surfaces dataset card (base v8-in re-run with the released code, reversed layers) |
| `p1447` | `hf_mask_edge200` | Reader V3 | 0.8120 | 0.8098 | -0.0022 | 0.0054 | PASS | Jashann/vesuvius-sheet-chain score_vs_labels (mask, CT present, >= 200 px from the render edge) |
| `p1447` | `hf_mask_edge200` | Reader v2 | 0.7975 | 0.7966 | -0.0009 | 0.0030 | PASS | Jashann/vesuvius-sheet-chain |
| `p0343p_ir` | `ir_camera` | published map `maps/reader-v3.png` | 0.7739 | 0.7739 | 0.0000 | - | PASS | DomRusso2/ir-truth-9um results/scores.json |
| `p0343p_ir` | `ir_camera` | published map `maps/reader-v2.png` | 0.8339 | 0.8339 | 0.0000 | - | PASS | DomRusso2/ir-truth-9um results/scores.json |
| `p0343p_ir` | `ir_camera` | published map `maps/v8-in.png` | 0.7438 | 0.7438 | 0.0000 | - | PASS | DomRusso2/ir-truth-9um results/scores.json |
| `p0343p_ir` | `ir_camera` | published map `maps/hecate-9.6um.png` | 0.7213 | 0.7213 | 0.0000 | - | PASS | DomRusso2/ir-truth-9um results/scores.json |
| `p0343p_ir` | `ir_camera` | published map `maps/team-2.2um-model-map.png` | 0.9090 | 0.9090 | 0.0000 | - | PASS | DomRusso2/ir-truth-9um results/scores.json |
| `p0343p_ir` | `ir_camera` | Reader V3 | 0.7739 | 0.7739 | 0.0000 | - | PASS | DomRusso2/ir-truth-9um (re-inferred on the published SV) |
| `p0343p_ir` | `ir_camera` | v8-in, released stitching | 0.7438 | 0.7438 | 0.0000 | - | PASS | DomRusso2/ir-truth-9um (re-inferred on the published SV) |
| `hp8` | `hp_exact` | Reader V3 | 0.1477 | 0.1452 | -0.0026 | 0.0103 | PASS | TAUIL results/v3_row/results_v3_row.json (hp_r) |
| `hp8` | `hp_exact` | Reader v2 | 0.1294 | 0.1285 | -0.0009 | 0.0040 | PASS | TAUIL v3_row |
| `hp8` | `hp_exact` | d9v4C | 0.1824 | 0.1848 | 0.0024 | 0.0063 | PASS | TAUIL v3_row |
| `hp8` | `human_near2mm_exact` | Reader V3 | 0.8892 | 0.8874 | -0.0018 | 0.0072 | PASS | TAUIL v3_row (human_auc) |
| `hp8` | `human_near2mm_exact` | Reader v2 | 0.8564 | 0.8543 | -0.0021 | 0.0122 | PASS | TAUIL v3_row (human_auc) |
| `v2_heldout` | `map_compat` | Reader v2 | 0.8470 | 0.8470 | 0.0000 | 0.0001 | PASS | DomRusso2/reader-v2 results/040000.json |

Verdicts: 42 PASS, 1 WARN, 0 FAIL, 1 INFO (of 44).

## Paired comparisons with Reader V3

Difference = reader − Reader V3 on the same bootstrap draws (2000), with its 95 % interval; **bold** when the
interval excludes 0. For `fa80_*` a negative difference is better. MDE: the minimum detectable effect of the
primary protocol (2.8 × the SD of the difference). The differences are block statistics, so they can differ in the
third decimal from the differences of the table means.

### PHerc0841, human labels (`p0841`)

| Reader | `human_strict_exact` (primary) | `human_sup_compat` | `human_union_compat` | `human_near2mm_exact` | `map_compat` | `map_exact` | MDE (primary) |
|---|---|---|---|---|---|---|---|
| Reader v2 | **-0.028 [-0.045, -0.013]** | **-0.028 [-0.043, -0.012]** | **-0.029 [-0.048, -0.011]** | **-0.034 [-0.050, -0.019]** | **-0.011 [-0.018, -0.005]** | **-0.011 [-0.017, -0.004]** | 0.023 |
| d9v4C | **-0.026 [-0.042, -0.009]** | **-0.027 [-0.043, -0.010]** | **-0.023 [-0.041, -0.006]** | **-0.030 [-0.045, -0.015]** | **-0.017 [-0.023, -0.010]** | **-0.011 [-0.018, -0.004]** | 0.023 |
| dense_native | **-0.065 [-0.092, -0.042]** | **-0.066 [-0.091, -0.041]** | **-0.052 [-0.077, -0.028]** | **-0.068 [-0.092, -0.046]** | **-0.068 [-0.078, -0.057]** | **-0.066 [-0.076, -0.056]** | 0.035 |
| Hecate 9.6 µm | +0.003 [-0.019, +0.027] | -0.005 [-0.027, +0.017] | +0.003 [-0.018, +0.027] | +0.001 [-0.020, +0.023] | **-0.023 [-0.035, -0.012]** | **-0.019 [-0.030, -0.008]** | 0.032 |
| v8-in | **-0.045 [-0.066, -0.022]** | **-0.047 [-0.069, -0.025]** | **-0.051 [-0.076, -0.027]** | **-0.052 [-0.074, -0.031]** | **-0.029 [-0.039, -0.019]** | **-0.028 [-0.038, -0.018]** | 0.031 |
| v8-in, released stitching | **-0.047 [-0.067, -0.024]** | **-0.048 [-0.070, -0.027]** | **-0.052 [-0.076, -0.028]** | **-0.054 [-0.075, -0.032]** | **-0.031 [-0.040, -0.021]** | **-0.030 [-0.040, -0.020]** | 0.031 |
| ink_9um s42 | **-0.129 [-0.168, -0.092]** | **-0.128 [-0.167, -0.093]** | **-0.124 [-0.161, -0.089]** | **-0.123 [-0.157, -0.085]** | **-0.154 [-0.167, -0.141]** | **-0.154 [-0.168, -0.141]** | 0.054 |
| ink_9um s43 (60k) | **-0.132 [-0.168, -0.098]** | **-0.139 [-0.172, -0.107]** | **-0.120 [-0.151, -0.089]** | **-0.120 [-0.151, -0.091]** | **-0.161 [-0.174, -0.149]** | **-0.162 [-0.175, -0.149]** | 0.049 |
| Ens. V3 + Hecate + d9v4C | **+0.021 [+0.010, +0.033]** | **+0.017 [+0.007, +0.028]** | **+0.021 [+0.011, +0.034]** | **+0.019 [+0.010, +0.030]** | **+0.027 [+0.021, +0.032]** | **+0.030 [+0.024, +0.035]** | 0.016 |
| Ens. V3 + Hecate | **+0.023 [+0.013, +0.035]** | **+0.018 [+0.009, +0.029]** | **+0.022 [+0.013, +0.033]** | **+0.022 [+0.013, +0.033]** | **+0.025 [+0.019, +0.030]** | **+0.026 [+0.021, +0.031]** | 0.015 |
| Ens. PHerc. 343 recipe | **-0.024 [-0.046, -0.000]** | **-0.031 [-0.053, -0.009]** | -0.020 [-0.041, +0.002] | **-0.022 [-0.042, -0.001]** | **-0.042 [-0.051, -0.033]** | **-0.038 [-0.047, -0.029]** | 0.033 |

### PHerc0009B, 116 keV (`p0009b`)

| Reader | `map_exact` (primary) | `map_compat` | `human_union_compat` | `human_strict_exact` | `human_near2mm_exact` | MDE (primary) |
|---|---|---|---|---|---|---|
| Reader v2 | **-0.018 [-0.026, -0.009]** | **-0.019 [-0.028, -0.011]** | **-0.022 [-0.033, -0.013]** | **-0.020 [-0.038, -0.005]** | **-0.019 [-0.030, -0.009]** | 0.012 |
| d9v4C | **-0.024 [-0.031, -0.016]** | **-0.031 [-0.038, -0.023]** | **-0.026 [-0.042, -0.014]** | **-0.016 [-0.035, -0.001]** | **-0.016 [-0.030, -0.005]** | 0.011 |
| dense_native | **-0.127 [-0.137, -0.116]** | **-0.128 [-0.138, -0.118]** | **-0.048 [-0.072, -0.027]** | -0.028 [-0.088, +0.013] | **-0.042 [-0.070, -0.018]** | 0.015 |
| Hecate 9.6 µm | **-0.097 [-0.108, -0.086]** | **-0.100 [-0.111, -0.089]** | **-0.042 [-0.060, -0.024]** | **-0.062 [-0.104, -0.029]** | **-0.032 [-0.049, -0.017]** | 0.016 |
| v8-in | **-0.085 [-0.101, -0.070]** | **-0.089 [-0.104, -0.073]** | **-0.077 [-0.098, -0.058]** | **-0.052 [-0.084, -0.025]** | **-0.079 [-0.101, -0.057]** | 0.022 |
| v8-in, released stitching | **-0.087 [-0.103, -0.072]** | **-0.091 [-0.106, -0.075]** | **-0.079 [-0.099, -0.059]** | **-0.053 [-0.085, -0.026]** | **-0.080 [-0.102, -0.059]** | 0.022 |
| ink_9um s42 | **-0.238 [-0.250, -0.225]** | **-0.238 [-0.251, -0.226]** | **-0.144 [-0.178, -0.112]** | **-0.104 [-0.170, -0.052]** | **-0.135 [-0.172, -0.104]** | 0.018 |
| ink_9um s43 (60k) | **-0.226 [-0.239, -0.213]** | **-0.227 [-0.239, -0.213]** | **-0.136 [-0.160, -0.113]** | **-0.117 [-0.182, -0.074]** | **-0.140 [-0.168, -0.115]** | 0.019 |
| Ens. V3 + Hecate + d9v4C | **+0.004 [+0.000, +0.009]** | +0.001 [-0.003, +0.005] | +0.001 [-0.005, +0.006] | -0.000 [-0.006, +0.005] | **+0.006 [+0.001, +0.012]** | 0.006 |
| Ens. V3 + Hecate | -0.002 [-0.006, +0.002] | -0.003 [-0.007, +0.000] | +0.004 [-0.000, +0.009] | -0.001 [-0.007, +0.003] | **+0.007 [+0.003, +0.012]** | 0.005 |
| Ens. PHerc. 343 recipe | **-0.119 [-0.130, -0.108]** | **-0.122 [-0.133, -0.112]** | **-0.034 [-0.055, -0.016]** | **-0.025 [-0.059, -0.000]** | **-0.028 [-0.050, -0.010]** | 0.015 |

### Nieuwlaar's native 113 keV benchmark (`p0139_native`)

| Reader | `native78_compat` | `native78_exact` (primary) | MDE (primary) |
|---|---|---|---|
| Reader v2 | **-0.010 [-0.016, -0.004]** | **-0.008 [-0.014, -0.003]** | 0.008 |
| d9v4C | **-0.008 [-0.013, -0.002]** | **-0.005 [-0.010, -0.000]** | 0.007 |
| dense_native | **-0.007 [-0.011, -0.002]** | **-0.007 [-0.011, -0.002]** | 0.006 |
| Hecate 9.6 µm | **-0.070 [-0.082, -0.060]** | **-0.067 [-0.079, -0.058]** | 0.015 |
| v8-in | **-0.051 [-0.061, -0.040]** | **-0.050 [-0.060, -0.039]** | 0.015 |
| v8-in, released stitching | **-0.055 [-0.065, -0.044]** | **-0.054 [-0.064, -0.043]** | 0.015 |
| ink_9um s42 | **-0.125 [-0.142, -0.111]** | **-0.121 [-0.138, -0.106]** | 0.022 |
| ink_9um s43 (60k) | **-0.115 [-0.130, -0.101]** | **-0.109 [-0.123, -0.096]** | 0.020 |
| Ens. V3 + Hecate + d9v4C | **-0.005 [-0.008, -0.001]** † | -0.003 [-0.006, +0.001] † | 0.005 |
| Ens. V3 + Hecate | **-0.044 [-0.054, -0.036]** † | **-0.040 [-0.049, -0.032]** † | 0.012 |
| Ens. PHerc. 343 recipe | **-0.049 [-0.058, -0.041]** † | **-0.043 [-0.052, -0.036]** † | 0.012 |

### False ink on blank papyrus (`p0139_blank`)

| Reader | `fa80_exact` (primary) | `fa80_russo` | `auc78_w047` | MDE (primary) |
|---|---|---|---|---|
| Reader v2 | **+0.043 [+0.025, +0.070]** | **+0.048 [+0.028, +0.075]** | **-0.037 [-0.048, -0.027]** | 0.034 |
| d9v4C | **+0.065 [+0.046, +0.092]** | **+0.081 [+0.057, +0.102]** | **-0.035 [-0.044, -0.026]** | 0.034 |
| dense_native | **+0.053 [+0.032, +0.078]** | **+0.056 [+0.033, +0.076]** | **-0.038 [-0.050, -0.027]** | 0.033 |
| Hecate 9.6 µm | **+0.472 [+0.371, +0.558]** | **+0.470 [+0.388, +0.569]** | **-0.138 [-0.165, -0.112]** | 0.135 |
| v8-in | **+0.381 [+0.304, +0.464]** | **+0.405 [+0.329, +0.476]** | **-0.122 [-0.143, -0.100]** | 0.113 |
| v8-in, released stitching | **+0.383 [+0.308, +0.465]** | **+0.408 [+0.334, +0.478]** | **-0.125 [-0.146, -0.103]** | 0.112 |
| ink_9um s42 | **+0.386 [+0.328, +0.463]** | **+0.430 [+0.344, +0.489]** | **-0.185 [-0.210, -0.162]** | 0.100 |
| ink_9um s43 (60k) | **+0.342 [+0.286, +0.417]** | **+0.365 [+0.311, +0.433]** | **-0.163 [-0.187, -0.140]** | 0.093 |
| Ens. V3 + Hecate + d9v4C | **+0.048 [+0.028, +0.072]** | **+0.052 [+0.031, +0.075]** | **-0.051 [-0.068, -0.035]** | 0.032 |
| Ens. V3 + Hecate | **+0.131 [+0.092, +0.177]** | **+0.133 [+0.098, +0.177]** | **-0.018 [-0.024, -0.012]** | 0.061 |
| Ens. PHerc. 343 recipe | **+0.192 [+0.141, +0.236]** | **+0.197 [+0.154, +0.245]** | **-0.063 [-0.077, -0.049]** | 0.069 |

### PHerc1447 (`p1447`)

| Reader | `hf_mask` (primary) | `hf_mask_edge200` | MDE (primary) |
|---|---|---|---|
| Reader v2 | -0.013 [-0.027, +0.000] | -0.013 [-0.027, +0.001] | 0.020 |
| d9v4C | **-0.039 [-0.054, -0.026]** | **-0.041 [-0.056, -0.026]** | 0.020 |
| dense_native | **-0.045 [-0.065, -0.025]** | **-0.043 [-0.062, -0.024]** | 0.027 |
| Hecate 9.6 µm | **-0.052 [-0.080, -0.026]** | **-0.058 [-0.086, -0.033]** | 0.038 |
| v8-in | **+0.026 [+0.002, +0.052]** | **+0.024 [+0.001, +0.051]** | 0.035 |
| v8-in, released stitching | **+0.025 [+0.001, +0.050]** | +0.023 [-0.000, +0.050] | 0.035 |
| ink_9um s42 | **-0.115 [-0.140, -0.090]** | **-0.114 [-0.140, -0.089]** | 0.037 |
| ink_9um s43 (60k) | **-0.106 [-0.133, -0.079]** | **-0.108 [-0.134, -0.082]** | 0.038 |
| Ens. V3 + Hecate + d9v4C | +0.005 [-0.003, +0.014] | +0.000 [-0.008, +0.009] | 0.012 |
| Ens. V3 + Hecate | +0.005 [-0.003, +0.014] | +0.000 [-0.008, +0.008] | 0.012 |
| Ens. PHerc. 343 recipe | **-0.026 [-0.043, -0.008]** | **-0.029 [-0.046, -0.011]** | 0.025 |

### PHerc0343P, infrared camera truth (`p0343p_ir`)

| Reader | `ir_camera` (primary) | MDE (primary) |
|---|---|---|
| Reader v2 | **+0.060 [+0.001, +0.119]** | 0.085 |
| d9v4C | +0.060 [-0.000, +0.127] | 0.092 |
| dense_native | -0.028 [-0.108, +0.058] | 0.116 |
| Hecate 9.6 µm | -0.031 [-0.101, +0.046] | 0.107 |
| v8-in | -0.027 [-0.093, +0.054] | 0.105 |
| v8-in, released stitching | -0.030 [-0.097, +0.050] | 0.104 |
| ink_9um s42 | **-0.151 [-0.258, -0.061]** | 0.140 |
| ink_9um s43 (60k) | -0.065 [-0.169, +0.037] | 0.145 |
| Ens. V3 + Hecate + d9v4C | **+0.078 [+0.038, +0.125]** | 0.063 |
| Ens. V3 + Hecate | **+0.058 [+0.017, +0.106]** | 0.065 |
| Ens. PHerc. 343 recipe | -0.002 [-0.070, +0.068] | 0.099 |

### Letter shape (`hp8`)

| Reader | `hp_exact` (primary) | `human_near2mm_exact` | MDE (primary) |
|---|---|---|---|
| Reader v2 | **-0.017 [-0.022, -0.012]** | **-0.031 [-0.041, -0.022]** | 0.007 |
| d9v4C | **+0.040 [+0.034, +0.046]** | **-0.032 [-0.041, -0.023]** | 0.008 |
| dense_native | **-0.076 [-0.082, -0.070]** | **-0.047 [-0.059, -0.036]** | 0.008 |
| Hecate 9.6 µm | **-0.089 [-0.097, -0.081]** | **-0.016 [-0.029, -0.003]** | 0.011 |
| v8-in | **-0.108 [-0.115, -0.099]** | **-0.076 [-0.093, -0.053]** | 0.011 |
| v8-in, released stitching | **-0.117 [-0.125, -0.109]** | **-0.079 [-0.096, -0.056]** | 0.011 |
| ink_9um s42 | **-0.110 [-0.117, -0.103]** | **-0.091 [-0.111, -0.072]** | 0.010 |
| ink_9um s43 (60k) | **-0.104 [-0.110, -0.097]** | **-0.097 [-0.118, -0.079]** | 0.009 |
| Ens. V3 + Hecate + d9v4C | **-0.010 [-0.015, -0.005]** | **+0.012 [+0.007, +0.019]** | 0.007 |
| Ens. V3 + Hecate | **-0.043 [-0.048, -0.038]** | **+0.015 [+0.009, +0.021]** | 0.007 |
| Ens. PHerc. 343 recipe | **-0.058 [-0.064, -0.052]** | -0.009 [-0.022, +0.003] | 0.008 |

### Reader v2's other held-out segments (`v2_heldout`)

| Reader | `map_exact` (primary) | `map_compat` | MDE (primary) |
|---|---|---|---|
| Reader v2 | **-0.015 [-0.023, -0.007]** | **-0.018 [-0.026, -0.009]** | 0.012 |
| d9v4C | **-0.029 [-0.038, -0.020]** | **-0.036 [-0.044, -0.027]** | 0.013 |
| dense_native | **-0.228 [-0.242, -0.211]** | **-0.229 [-0.243, -0.213]** | 0.022 |
| Hecate 9.6 µm | **-0.136 [-0.150, -0.123]** | **-0.141 [-0.154, -0.127]** | 0.020 |
| v8-in | **-0.056 [-0.069, -0.043]** | **-0.059 [-0.071, -0.046]** | 0.018 |
| v8-in, released stitching | **-0.058 [-0.071, -0.045]** | **-0.060 [-0.074, -0.047]** | 0.019 |
| ink_9um s42 | **-0.340 [-0.356, -0.322]** | **-0.338 [-0.355, -0.320]** | 0.024 |
| ink_9um s43 (60k) | **-0.303 [-0.318, -0.287]** | **-0.303 [-0.318, -0.287]** | 0.022 |
| Ens. V3 + Hecate + d9v4C | **+0.011 [+0.004, +0.017]** | **+0.007 [+0.001, +0.014]** | 0.009 |
| Ens. V3 + Hecate | **+0.007 [+0.001, +0.014]** | +0.005 [-0.001, +0.012] | 0.010 |
| Ens. PHerc. 343 recipe | **-0.245 [-0.258, -0.233]** | **-0.248 [-0.260, -0.235]** | 0.018 |

## Exact against plain-resize label transfer

The same readers and pixels scored with the reference moved by plain resize (`_compat`) and by the exact canvas map
(`_exact`). On the native benchmark both routes use the same AUC; on the map protocols the `_compat` route also
uses Reader v2's subsampled AUC. Differences are exact − compat, from the unrounded means.

| Reader | native 113 keV: compat → exact | `p0841` map | `p0009b` map | `v2_heldout` map |
|---|---|---|---|---|
| Reader V3 | 0.968 → 0.972 (+0.004) | +0.004 | +0.002 | +0.001 |
| Reader v2 | 0.959 → 0.964 (+0.005) | +0.005 | +0.004 | +0.003 |
| d9v4C | 0.961 → 0.967 (+0.006) | +0.010 | +0.009 | +0.007 |
| dense_native | 0.962 → 0.965 (+0.004) | +0.006 | +0.004 | +0.002 |
| Hecate 9.6 µm | 0.898 → 0.905 (+0.007) | +0.009 | +0.006 | +0.005 |
| v8-in | 0.917 → 0.922 (+0.005) | +0.005 | +0.006 | +0.004 |
| v8-in, released stitching | 0.913 → 0.918 (+0.005) | +0.005 | +0.006 | +0.004 |
| ink_9um s42 | 0.843 → 0.851 (+0.008) | +0.004 | +0.003 | -0.001 |
| ink_9um s43 (60k) | 0.854 → 0.863 (+0.010) | +0.004 | +0.004 | +0.000 |
| Ens. V3 + Hecate + d9v4C | 0.964 → 0.970 (+0.006) † | +0.007 | +0.005 | +0.005 |
| Ens. V3 + Hecate | 0.924 → 0.932 (+0.008) † | +0.006 | +0.004 | +0.004 |
| Ens. PHerc. 343 recipe | 0.920 → 0.929 (+0.009) † | +0.009 | +0.006 | +0.003 |

## The v8-in stitching fix

`v8in` is v8-in with J. Wallis's fix of its tile stitching (normalising by the blend weight), as inksweep runs it;
`v8in_released` is the released stitching. Means from the tables above; the difference is from the unrounded means.

| Benchmark | Protocol | Released stitching | Fixed | Difference |
|---|---|---|---|---|
| `p0841` | `human_strict_exact` | 0.821 | 0.823 | +0.0017 |
| `p0841` | `human_sup_compat` | 0.820 | 0.821 | +0.0015 |
| `p0841` | `human_union_compat` | 0.801 | 0.801 | +0.0010 |
| `p0841` | `human_near2mm_exact` | 0.809 | 0.811 | +0.0024 |
| `p0841` | `map_compat` | 0.839 | 0.840 | +0.0017 |
| `p0841` | `map_exact` | 0.844 | 0.846 | +0.0018 |
| `p0009b` | `map_exact` | 0.769 | 0.771 | +0.0019 |
| `p0009b` | `map_compat` | 0.763 | 0.765 | +0.0018 |
| `p0009b` | `human_union_compat` | 0.870 | 0.871 | +0.0013 |
| `p0009b` | `human_strict_exact` | 0.899 | 0.901 | +0.0015 |
| `p0009b` | `human_near2mm_exact` | 0.856 | 0.859 | +0.0023 |
| `p0139_native` | `native78_compat` | 0.913 | 0.917 | +0.0040 |
| `p0139_native` | `native78_exact` | 0.918 | 0.922 | +0.0041 |
| `p0139_blank` | `fa80_exact` | 0.438 | 0.436 | -0.0021 |
| `p0139_blank` | `fa80_russo` | 0.464 | 0.461 | -0.0031 |
| `p0139_blank` | `fa80_nieuwlaar` | 0.248 | 0.246 | -0.0018 |
| `p0139_blank` | `auc78_w047` | 0.808 | 0.811 | +0.0027 |
| `p1447` | `hf_mask` | 0.836 | 0.837 | +0.0011 |
| `p1447` | `hf_mask_edge200` | 0.833 | 0.834 | +0.0011 |
| `p0343p_ir` | `ir_camera` | 0.744 | 0.747 | +0.0034 |
| `hp8` | `hp_exact` | 0.028 | 0.037 | +0.0093 |
| `hp8` | `human_near2mm_exact` | 0.808 | 0.811 | +0.0036 |
| `v2_heldout` | `map_exact` | 0.808 | 0.810 | +0.0019 |
| `v2_heldout` | `map_compat` | 0.804 | 0.806 | +0.0019 |

Paired against each other (`inkbench compare v8in v8in_released`, 2000 draws):

| Benchmark | Protocol | Difference [95 % interval] |
|---|---|---|
| `p0841` | `human_strict_exact` | +0.0017 [+0.0014, +0.0021] |
| `p0841` | `human_sup_compat` | +0.0016 [+0.0012, +0.0019] |
| `p0841` | `human_union_compat` | +0.0010 [+0.0006, +0.0013] |
| `p0841` | `human_near2mm_exact` | +0.0017 [+0.0013, +0.0020] |
| `p0841` | `map_compat` | +0.0017 [+0.0014, +0.0020] |
| `p0841` | `map_exact` | +0.0018 [+0.0015, +0.0022] |
| `p0009b` | `map_exact` | +0.0019 [+0.0015, +0.0024] |
| `p0009b` | `map_compat` | +0.0018 [+0.0014, +0.0022] |
| `p0009b` | `human_union_compat` | +0.0013 [+0.0011, +0.0015] |
| `p0009b` | `human_strict_exact` | +0.0015 [+0.0012, +0.0020] |
| `p0009b` | `human_near2mm_exact` | +0.0016 [+0.0014, +0.0018] |
| `p0139_native` | `native78_compat` | +0.0040 [+0.0035, +0.0046] |
| `p0139_native` | `native78_exact` | +0.0041 [+0.0036, +0.0047] |
| `p0139_blank` | `fa80_exact` | -0.0021 [-0.0098, +0.0033] |
| `p0139_blank` | `fa80_russo` | -0.0031 [-0.0094, +0.0039] |
| `p0139_blank` | `auc78_w047` | +0.0027 [+0.0018, +0.0037] |
| `p1447` | `hf_mask` | +0.0011 [+0.0009, +0.0013] |
| `p1447` | `hf_mask_edge200` | +0.0011 [+0.0010, +0.0013] |
| `p0343p_ir` | `ir_camera` | +0.0034 [+0.0017, +0.0055] |
| `hp8` | `hp_exact` | +0.0093 [+0.0086, +0.0100] |
| `hp8` | `human_near2mm_exact` | +0.0028 [+0.0022, +0.0036] |
| `v2_heldout` | `map_exact` | +0.0019 [+0.0014, +0.0026] |
| `v2_heldout` | `map_compat` | +0.0019 [+0.0013, +0.0026] |
