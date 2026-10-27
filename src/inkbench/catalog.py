"""The benchmarks: which segments, which reference data, which reading orientation.

Segment folders are given by a unique prefix of the open-data folder name (Reader v2's ids are 40-character
prefixes); ``tag`` is the short name used in tables.

Kinds:
  human     native SV + human labels drawn on the fine canvas (PHerc0841; PHerc0009B 125754)
  map       native SV + the organisers' 2.4 um ink map of the same segment (Reader v2 held-out suite)
  native78  PHerc0139 113 keV SV + the 78 keV map (Nieuwlaar's frozen benchmark: title, w024)
  blank     PHerc0139 w047 (ink, operating point) + w053 (known blank)
  hf1447    PHerc1447 w058 / w060 from HF YoussefMoNader/ink-8um-pherc1447-surfaces (24 layers, refined labels)
  ir        PHerc0343P segment 20250511003658, IR-photo letters (DomRusso2/ir-truth-9um)
  hp        letter-scale score against the 2.4 um map (TAUIL's eight held-out segments)
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Seg:
    sample: str
    prefix: str
    tag: str


@dataclass(frozen=True)
class Benchmark:
    name: str
    kind: str
    segs: tuple[Seg, ...]
    orientation: str = "forward"         # reading orientation on these renders (published SVs read forward)
    primary: str = ""                    # the headline protocol of the benchmark
    protocols: tuple[str, ...] = ()
    notes: str = ""
    meta: dict = field(default_factory=dict)


P0841 = (Seg("PHerc0841", "20260220213127-w00", "w00"),
         Seg("PHerc0841", "20260220214732-auto_grown_20260220144552", "ag896"),
         Seg("PHerc0841", "20260221022814-auto_grown_20260220174252", "ag405"))
P0009B = (Seg("PHerc0009B", "20250919125754", "125754"), Seg("PHerc0009B", "20250510172639", "172639"),
          Seg("PHerc0009B", "20250919133208", "133208"), Seg("PHerc0009B", "20250919140325", "140325"))
TITLE = Seg("PHerc0139", "20260422000000-title", "title")
W024 = Seg("PHerc0139", "20260215000000-w024", "w024")
W047 = Seg("PHerc0139", "20260206000001-w047", "w047")
W053 = Seg("PHerc0139", "20260220000000-w053", "w053")
HP8 = (Seg("PHerc0009B", "20250919125754", "0009B_125754"), Seg("PHerc0139", "20250108000005-w030", "0139_w030"),
       Seg("PHerc0139", "20260126000000-w045", "0139_w045"), Seg("PHerc0500P2", "20250825181859--1", "0500P2_1"),
       Seg("PHerc0814", "20260226000000-46527", "0814_46527"), P0841[0], P0841[1], P0841[2])
V2_HELDOUT = (Seg("PHerc0500P2", "20250716055229-z_dbg_gen_00371", "0500P2_371"),
              Seg("PHerc0500P2", "20250716055230-z_dbg_gen_00377", "0500P2_377"),
              Seg("PHerc0343P", "20250904233748-0_b2", "0343P_0b2"),
              Seg("PHerc0343P", "20250905172054-1_b2", "0343P_1b2"),
              Seg("PHerc0172", "20250926122938-w082", "0172_w082"),
              Seg("PHerc0172", "20250926132117-w083", "0172_w083"))

BENCHMARKS: dict[str, Benchmark] = {b.name: b for b in (
    Benchmark("p0841", "human", P0841, primary="human_strict_exact",
              protocols=("human_strict_exact", "human_sup_compat", "human_union_compat", "human_near2mm_exact",
                         "map_compat", "map_exact"),
              notes="a scroll in no published training list (one patch, three overlapping segments; ~+-0.03 AUC "
                    "noise floor)"),
    Benchmark("p0009b", "map", P0009B, primary="map_exact",
              protocols=("map_exact", "map_compat", "human_union_compat", "human_strict_exact", "human_near2mm_exact"),
              notes="116 keV; held out by Reader v2/V3 (other 0009B segments trained); d9v4C trained 3 of 4",
              meta={"human_segment": "125754"}),
    Benchmark("p0139_native", "native78", (TITLE, W024), primary="native78_exact",
              protocols=("native78_compat", "native78_exact"),
              notes="Nieuwlaar's frozen native 113 keV benchmark (78 keV-map classes; teacher family = canonical)"),
    Benchmark("p0139_blank", "blank", (W047, W053), primary="fa80_exact",
              protocols=("fa80_exact", "fa80_russo", "fa80_nieuwlaar", "auc78_w047"),
              notes="false ink on known-blank w053 at 80 % ink recall on w047 (published SV crops)"),
    Benchmark("p1447", "hf1447", (Seg("PHerc1447", "w058", "w058"), Seg("PHerc1447", "w060", "w060")),
              orientation="reverse", primary="hf_mask",
              protocols=("hf_mask", "hf_mask_edge200"),
              notes="Grand Prize-eligible scroll, in no reader's published training set; labels refined with v8-in "
                    "in the loop"),
    Benchmark("p0343p_ir", "ir", (Seg("PHerc0343P", "20250511003658", "343P_ir"),), primary="ir_camera",
              protocols=("ir_camera",),
              notes="camera truth (one fragment, two lines); Reader v2/V3 and d9v4C trained on this segment"),
    Benchmark("hp8", "hp", HP8, primary="hp_exact", protocols=("hp_exact", "human_near2mm_exact"),
              notes="TAUIL's 8 held-out segments; 0139 w030/w045 and 0814 46527 were trained on by Reader v2/V3"),
    Benchmark("v2_heldout", "map", V2_HELDOUT, primary="map_exact", protocols=("map_exact", "map_compat"),
              notes="Reader v2's other held-out segments (other segments of these objects were trained on)"),
)}

#: Resources outside the open-data bucket, pinned.
HF_1447 = dict(repo="YoussefMoNader/ink-8um-pherc1447-surfaces", rev="7e4d918712a8d8642a6fdeee45b80217c1e98317",
               licence="CC-BY-NC-4.0")
IR_TRUTH = dict(repo="DomRusso2/ir-truth-9um", rev="7e96b969d3a1407504db4826543136573bda78b8",
                licence="code MIT; data derived from Vesuvius Challenge open data (CC-BY-NC-4.0)",
                files=("data/truth_ink.png", "data/truth_noink.png", "data/valid.png", "data/pose_front_to_8.64um.json",
                       "maps/reader-v3.png", "maps/reader-v2.png", "maps/v8-in.png", "maps/hecate-9.6um.png",
                       "maps/team-2.2um-model-map.png", "results/scores.json"),
                sizes={"data/truth_ink.png": 25880, "data/truth_noink.png": 77314, "data/valid.png": 31617,
                       "data/pose_front_to_8.64um.json": 354, "maps/reader-v3.png": 2214234,
                       "maps/reader-v2.png": 1621119, "maps/v8-in.png": 6727865, "maps/hecate-9.6um.png": 1293465,
                       "maps/team-2.2um-model-map.png": 1149133, "results/scores.json": 716})


def all_segments() -> list[Seg]:
    seen, out = set(), []
    for b in BENCHMARKS.values():
        for s in b.segs:
            if (s.sample, s.prefix) not in seen:
                seen.add((s.sample, s.prefix))
                out.append(s)
    return out


def bench_list(text: str) -> list[str]:
    """``"all"`` or a comma list of benchmark names -> names, in catalog order; raises on an unknown name."""
    if text in ("", "all"):
        return list(BENCHMARKS)
    names = [t.strip() for t in text.split(",") if t.strip()]
    bad = [n for n in names if n not in BENCHMARKS]
    if bad:
        raise ValueError(f"unknown benchmark(s) {bad}; known: {', '.join(BENCHMARKS)}")
    return [n for n in BENCHMARKS if n in names]
