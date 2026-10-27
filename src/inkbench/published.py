"""Published numbers the harness reproduces: the check that its data, label transfer, scoring rules and predictions
match each author's own evaluation before any comparison is read.

Each entry: (benchmark, protocol, reader, per-segment values in catalog order or a single mean, source[, kind]).
``kind`` "approx" marks rows made by a different pipeline than the one re-run here (e.g. Reader v2's own Hecate
resampling script): their verdict is INFO beyond the WARN band, never FAIL.
Reader names are inksweep's (``readerv3``, ``readerv2``, ``d9v4c``, ``dnative``, ``hecate``, ``v8in``, ``ink9_s42``,
``ink9_s43_060k``); ``ext:<file>`` rows score a published map file directly (no GPU, a pure check of the scorer).
Tolerances: an external-map row must match to 0.002 (same pixels, same rule); a re-inferred row to 0.015 per
benchmark mean (PASS), 0.03 (WARN, the 0841 noise floor), else FAIL.
"""
from __future__ import annotations

PUBLISHED: list[tuple[str, str, str, object, str]] = [
    # --- PHerc0841 human labels
    ("p0841", "human_union_compat", "readerv2", [0.832, 0.8387, 0.8005],
     "DomRusso2/reader-v2 results/040000.json (v2_run.evaluate: union of supervision+validation, resized labels)"),
    ("p0841", "human_union_compat", "hecate", [0.8887, 0.8013, 0.8752], "DomRusso2/reader-v2 results/0841_regions.json",
     "approx"),
    ("p0841", "human_union_compat", "dnative", [0.8287, 0.8256, 0.7454], "DomRusso2/reader-v2 results/0841_regions.json"),
    ("p0841", "human_union_compat", "ink9_s43_060k", [0.7555, 0.7095, 0.7326],
     "DomRusso2/reader-v2 results/0841_regions.json (released_s43_60k)"),
    ("p0841", "human_sup_compat", "readerv2", [0.8755, 0.8263, 0.8193],
     "DomRusso2/reader-v2 results/0841_regions.json (in_supervision)"),
    ("p0841", "human_sup_compat", "hecate", [0.9119, 0.7841, 0.8936], "DomRusso2/reader-v2 results/0841_regions.json",
     "approx"),
    ("p0841", "human_near2mm_exact", "readerv3", [0.8882, 0.8444, 0.8561],
     "TAUIL-Abd-Elilah/9um-reader-letter-shape results/v3_row (labels aligned by NCC; we use the exact canvas map)"),
    ("p0841", "human_near2mm_exact", "readerv2", [0.8367, 0.8332, 0.8137], "TAUIL results/v3_row"),
    ("p0841", "human_near2mm_exact", "d9v4c", [0.8329, 0.8458, 0.8165], "TAUIL results/v3_row"),
    ("p0841", "map_compat", "readerv2", [0.8644, 0.8679, 0.8412], "DomRusso2/reader-v2 results/040000.json (auc_map)"),
    # --- PHerc0009B held out (116 keV)
    ("p0009b", "map_compat", "readerv2", [0.9144, 0.7576, 0.8456, 0.8193], "DomRusso2/reader-v2 results/040000.json"),
    ("p0009b", "human_union_compat", "readerv2", [0.9266, None, None, None], "DomRusso2/reader-v2 results/040000.json"),
    ("p0009b", "human_union_compat", "readerv3", [0.9431, None, None, None],
     "DomRusso2/reader-v3 results/suite_reader-v3.json (0009B_125754)"),
    ("p0009b", "human_union_compat", "hecate", [0.8928, None, None, None], "DomRusso2/reader-v3 results/suite_hecate.json",
     "approx"),
    ("p0009b", "human_union_compat", "v8in_released", [0.8699, None, None, None],
     "DomRusso2/reader-v3 results/suite_base21.json (v8-in stride 21, released code)"),
    ("p0009b", "human_near2mm_exact", "readerv3", [0.9385, None, None, None], "TAUIL results/v3_row"),
    ("p0009b", "human_near2mm_exact", "readerv2", [0.9171, None, None, None], "TAUIL results/v3_row"),
    # --- PHerc0139 native 113 keV (Nieuwlaar)
    ("p0139_native", "native78_compat", "dnative", [0.9548, 0.9685],
     "Nieuwlaar/ink9um-dense-native training/BENCHMARK.csv (dense_native-016000)"),
    ("p0139_native", "native78_compat", "ink9_s42", [0.8135, 0.8724],
     "Nieuwlaar native-eval/RESULTS_full.csv (released-s42-075000)"),
    # --- PHerc0139 blank w053 / ink w047
    ("p0139_blank", "fa80_russo", "readerv3", 0.0545, "DomRusso2/reader-v3 results/suite_reader-v3.json (FA80_w053)"),
    ("p0139_blank", "fa80_russo", "readerv2", 0.0925, "DomRusso2/reader-v3 results/suite_v2.json"),
    ("p0139_blank", "fa80_russo", "hecate", 0.5765, "DomRusso2/reader-v3 results/suite_hecate.json", "approx"),
    ("p0139_blank", "fa80_russo", "v8in_released", 0.4608, "DomRusso2/reader-v3 results/suite_base21.json"),
    ("p0139_blank", "auc78_w047", "readerv3", 0.9298, "DomRusso2/reader-v3 results/suite_reader-v3.json (w047)"),
    ("p0139_blank", "auc78_w047", "readerv2", 0.8971, "DomRusso2/reader-v3 results/suite_v2.json"),
    ("p0139_blank", "auc78_w047", "hecate", 0.7756, "DomRusso2/reader-v3 results/suite_hecate.json", "approx"),
    ("p0139_blank", "fa80_nieuwlaar", "ink9_s42", 0.269, "Nieuwlaar README section 5 (released checkpoint, 26.9 %)"),
    # --- PHerc1447 (HF surfaces)
    ("p1447", "hf_mask", "ext:predictions/v8in.png", [0.862, 0.810],
     "HF YoussefMoNader/ink-8um-pherc1447-surfaces dataset card (base v8-in, reversed layers)"),
    ("p1447", "hf_mask", "v8in_released", [0.862, 0.810],
     "HF ink-8um-pherc1447-surfaces dataset card (base v8-in re-run with the released code, reversed layers)"),
    ("p1447", "hf_mask_edge200", "readerv3", [0.850, 0.774],
     "Jashann/vesuvius-sheet-chain score_vs_labels (mask, CT present, >= 200 px from the render edge)"),
    ("p1447", "hf_mask_edge200", "readerv2", [0.837, 0.758], "Jashann/vesuvius-sheet-chain"),
    # --- PHerc0343P camera truth
    ("p0343p_ir", "ir_camera", "ext:maps/reader-v3.png", 0.7739, "DomRusso2/ir-truth-9um results/scores.json"),
    ("p0343p_ir", "ir_camera", "ext:maps/reader-v2.png", 0.8339, "DomRusso2/ir-truth-9um results/scores.json"),
    ("p0343p_ir", "ir_camera", "ext:maps/v8-in.png", 0.7438, "DomRusso2/ir-truth-9um results/scores.json"),
    ("p0343p_ir", "ir_camera", "ext:maps/hecate-9.6um.png", 0.7213, "DomRusso2/ir-truth-9um results/scores.json"),
    ("p0343p_ir", "ir_camera", "ext:maps/team-2.2um-model-map.png", 0.909, "DomRusso2/ir-truth-9um results/scores.json"),
    ("p0343p_ir", "ir_camera", "readerv3", 0.7739, "DomRusso2/ir-truth-9um (re-inferred on the published SV)"),
    ("p0343p_ir", "ir_camera", "v8in_released", 0.7438, "DomRusso2/ir-truth-9um (re-inferred on the published SV)"),
    # --- letter-scale (TAUIL's harness, 8 segments in catalog order)
    ("hp8", "hp_exact", "readerv3", [0.1933, 0.1105, 0.1512, 0.1593, 0.1847, 0.1161, 0.132, 0.1348],
     "TAUIL results/v3_row/results_v3_row.json (hp_r)"),
    ("hp8", "hp_exact", "readerv2", [0.1719, 0.1116, 0.1393, 0.1446, 0.1469, 0.0988, 0.1174, 0.1048], "TAUIL v3_row"),
    ("hp8", "hp_exact", "d9v4c", [0.2416, 0.1677, 0.1833, 0.1919, 0.1982, 0.1515, 0.1697, 0.1549], "TAUIL v3_row"),
    ("hp8", "human_near2mm_exact", "readerv3", [0.9385, 0.9067, 0.8456, 0.8976, 0.9366, 0.8882, 0.8444, 0.8561],
     "TAUIL v3_row (human_auc)"),
    ("hp8", "human_near2mm_exact", "readerv2", [0.9171, 0.8723, 0.8114, 0.8624, 0.9046, 0.8367, 0.8332, 0.8137],
     "TAUIL v3_row (human_auc)"),
    # --- Reader v2's other held-out segments
    ("v2_heldout", "map_compat", "readerv2", [0.8167, 0.7551, 0.8058, 0.7282, 0.9871, 0.9888],
     "DomRusso2/reader-v2 results/040000.json"),
]

TOL_EXTERNAL = 0.002
TOL_PASS = 0.015
TOL_WARN = 0.03


def verdict(got: float, want: float, external: bool, kind: str = "exact") -> str:
    if got != got or want is None:
        return "n/a"
    d = abs(got - want)
    if external:
        return "PASS" if d <= TOL_EXTERNAL else "FAIL"
    worst = "INFO" if kind == "approx" else "FAIL"
    return "PASS" if d <= TOL_PASS else ("WARN" if d <= TOL_WARN else worst)
