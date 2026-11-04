"""Physical-source evidence is additive to score values and exact-ID flags."""
import json

import pytest

from inkbench import provenance as P
from inkbench import score, table


def test_reader_v2_evidence_is_specific_and_internally_consistent():
    for suffix, expected in (("371", (21343, 15894, 15208)), ("377", (26222, 16255, 15547))):
        folder = f"202507160552{'29' if suffix == '371' else '30'}-z_dbg_gen_00{suffix}_inp_hr"
        assert P.trained_on("readerv2", "PHerc0500P2", folder) == "no"
        evidence = P.source_overlap_evidence("readerv2", "PHerc0500P2", folder)
        ink = evidence["score_grid_by_class"]["ink"]
        assert (ink["usable_scored_pixels"], ink["possible_corner_reuse_any_jitter"],
                ink["possible_corner_reuse_all_five_jitters"]) == expected
        for counts in evidence["score_grid_by_class"].values():
            assert 0 < counts["possible_corner_reuse_all_five_jitters"] <= counts[
                "possible_corner_reuse_any_jitter"] <= counts["usable_scored_pixels"]
        assert P.source_overlap_evidence("readerv3", "PHerc0500P2", folder) is None
    assert P.source_overlap_evidence("readerv2", "PHerc0343P", "20250904233748-0_b2") is None
    assert P.source_overlap_evidence("readerv2", "PHerc0500P2", "20250611171745-z_dbg_gen_00225") is None


def test_score_file_keeps_auc_and_exact_id_flag(tmp_path, monkeypatch):
    monkeypatch.setenv("INKBENCH_RESULTS", str(tmp_path))
    monkeypatch.setattr(score, "reader_spec", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(score, "local_segment", lambda seg: tmp_path / seg.prefix)
    monkeypatch.setattr(score, "score_external", lambda _name: {})

    def fake_map(bench, _spec):
        per_segment = {s.tag: 0.8 for s in bench.segs}
        return ({proto: {"per_segment": per_segment.copy(), "notes": []}
                 for proto in ("map_exact", "map_compat")}, {"map_exact": [], "map_compat": []})

    monkeypatch.setitem(score.SCORERS, "map", fake_map)
    summary = score.score_benchmark("v2_heldout", ["readerv2"])["readerv2"]
    assert summary == pytest.approx({"map_exact": 0.8, "map_compat": 0.8})
    file = json.loads((tmp_path / "scores" / "v2_heldout" / "readerv2.json").read_text())
    scored = file["map_exact"]
    assert scored["mean"] == pytest.approx(0.8)
    assert all(value == 0.8 for value in scored["per_segment"].values())
    assert scored["trained_on"]["0500P2_371"] == scored["trained_on"]["0500P2_377"] == "no"
    assert set(scored["source_overlap_evidence"]) == {"0500P2_371", "0500P2_377"}
    assert "source_overlap_evidence" not in file["map_compat"]
    assert table.leak_cell({"map_exact": scored}, ["map_exact"]) == "no"
    assert table.source_overlap_cell({"map_exact": scored}, ["map_exact"]) == "0500P2_371,0500P2_377"
