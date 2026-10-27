"""The table logic on hand-made score files (no data, no inksweep)."""
import json

from inkbench import table


def test_leak_cell():
    s = {"a": {"trained_on": {"w00": "unknown", "ag896": "yes", "ag405": "no"}}}
    assert table.leak_cell(s, ["a"]) == "ag896,w00?"
    assert table.leak_cell({"a": {"trained_on": {"x": "no"}}}, ["a"]) == "no"
    assert table.leak_cell({"a": {"trained_on": {"x": "n/a"}}}, ["a"]) == "n/a"
    assert table.leak_cell({"a": {"trained_on": {}}}, ["a"]) == "no"


def _put(root, bench, reader, proto, per_segment):
    p = root / "scores" / bench / f"{reader}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    s = json.loads(p.read_text()) if p.is_file() else {}
    s[proto] = {"per_segment": per_segment}
    p.write_text(json.dumps(s))


def test_reproduction_verdicts(tmp_path, monkeypatch):
    monkeypatch.setenv("INKBENCH_RESULTS", str(tmp_path))
    _put(tmp_path, "p0139_blank", "readerv3", "fa80_russo", {"w053": 0.0545 + 0.001})
    _put(tmp_path, "p0139_blank", "readerv2", "fa80_russo", {"w053": 0.0925 + 0.02})
    _put(tmp_path, "p0139_blank", "hecate", "fa80_russo", {"w053": 0.5765 - 0.05})
    _put(tmp_path, "p0139_blank", "readerv3", "auc78_w047", {"w047": 0.9298 + 0.05})
    _put(tmp_path, "p0841", "readerv2", "human_union_compat", {"w00": 0.832, "ag896": 0.8387})   # one segment short
    _put(tmp_path, "p0841", "dnative", "human_union_compat", {"w00": 0.8287, "ag896": 0.8256, "ag405": 0.7454})
    rows = {(r["benchmark"], r["protocol"], r["reader"]): r for r in table.reproduction()}
    assert len(rows) == 44
    assert rows["p0139_blank", "fa80_russo", "readerv3"]["verdict"] == "PASS"
    assert rows["p0139_blank", "fa80_russo", "readerv2"]["verdict"] == "WARN"
    assert rows["p0139_blank", "fa80_russo", "hecate"]["verdict"] == "INFO"            # an "approx" row
    assert rows["p0139_blank", "auc78_w047", "readerv3"]["verdict"] == "FAIL"
    assert rows["p0139_blank", "auc78_w047", "readerv2"]["verdict"] == "missing"
    assert rows["p0841", "human_union_compat", "readerv2"]["verdict"] == "missing"
    r = rows["p0841", "human_union_compat", "dnative"]
    assert r["verdict"] == "PASS" and r["delta"] == 0.0 and r["worst_segment_delta"] == 0.0
    counts = table.verdict_counts(list(rows.values()))
    assert counts == {"PASS": 2, "WARN": 1, "FAIL": 1, "INFO": 1, "missing": 39, "n/a": 0}
    text = table.render_reproduction()
    assert "| p0139_blank | auc78_w047 | readerv3 | 0.9298 | 0.9798 | 0.0500 | FAIL |" in text
    assert json.loads((tmp_path / "REPRODUCTION.json").read_text())["counts"] == counts
