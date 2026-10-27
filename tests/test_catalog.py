import pytest

from inkbench import catalog, published
from inkbench import provenance as P


def test_training_flags_of_public_readers():
    assert P.trained_on("readerv3", "PHerc0139", "20260126000000-w045_2026012619") == "yes"
    assert P.trained_on("readerv3", "PHerc0841", "20260220213127-w00") == "no"
    assert P.trained_on("readerv3", "PHerc0343P", "20250511003658-tifxyz") == "yes"
    assert P.trained_on("readerv2", "PHerc0009B", "20250919125754-auto_grown_x") == "no"
    assert P.trained_on("d9v4c", "PHerc0009B", "20250510172639") == "yes"
    assert P.trained_on("ink9_s42", "PHerc0139", "20260115000000-w044_2026011522") == "yes"
    assert P.trained_on("ink9_s43_060k", "PHerc0139", "20260115000000-w044_2026011522") == "yes"
    assert P.trained_on("dnative", "PHerc0139", "20260203000000-w032_2026020303") == "yes"
    assert P.trained_on("dnative", "PHerc0139", "20260422000000-title_2026042222_zmid_flatboi") == "no"
    assert P.trained_on("hecate", "PHerc0841", "20260220213127-w00") == "unknown"
    assert P.trained_on("v8in", "PHerc0139", "20260422000000-title_x") == "unknown"
    assert P.trained_on("v8in_released", "PHerc0841", "20260220213127-w00") == "no"
    assert P.trained_on("my_plugin", "PHerc0841", "20260220213127-w00") == "n/a"
    # PHerc1447's HF windings have no 14-digit id; no published training set lists the scroll
    assert P.trained_on("readerv3", "PHerc1447", "w058") == "no"
    assert P.trained_on("dnative", "PHerc1447", "w058") == "no"
    assert P.trained_on("v8in", "PHerc1447", "w060") == "no"
    assert P.trained_on("hecate", "PHerc1447", "w060") == "unknown"


def test_ensemble_flags_are_the_members_flags():
    ir = ("PHerc0343P", "20250511003658-tifxyz")
    assert P.trained_on_any(["readerv3", "hecate", "d9v4c"], *ir) == "yes"
    assert P.trained_on_any(["dnative", "hecate"], *ir) == "unknown"
    assert P.trained_on_any(["dnative", "ink9_s42"], "PHerc0841", "20260220213127-w00") == "no"
    assert P.trained_on_any(["dnative", "my_plugin"], "PHerc0841", "20260220213127-w00") == "unknown"


def test_seg_id():
    assert P.seg_id("20250919125754-auto_grown_20250919055754487_inp_hr") == "20250919125754"
    with pytest.raises(ValueError):
        P.seg_id("w058")


def test_benchmarks_are_consistent():
    assert len(catalog.BENCHMARKS) == 8
    for b in catalog.BENCHMARKS.values():
        assert b.primary in b.protocols, b.name
        assert len({s.tag for s in b.segs}) == len(b.segs), b.name
        assert b.orientation in ("forward", "reverse")
    assert len(catalog.all_segments()) == len({(s.sample, s.prefix) for s in catalog.all_segments()})


def test_bench_list():
    assert catalog.bench_list("all") == list(catalog.BENCHMARKS)
    assert catalog.bench_list("hp8,p0841") == ["p0841", "hp8"]
    with pytest.raises(ValueError):
        catalog.bench_list("p0841,nope")


def test_published_rows_are_consistent():
    assert len(published.PUBLISHED) == 44
    for bench, proto, reader, want, src, *rest in published.PUBLISHED:
        assert not rest or rest[0] in ("exact", "approx")
        b = catalog.BENCHMARKS[bench]
        assert proto in b.protocols, (bench, proto)
        if isinstance(want, list):
            assert len(want) == len(b.segs), (bench, proto, reader)
        assert src


def test_verdict_bands():
    v = published.verdict
    assert v(0.8000, 0.8030, external=True) == "FAIL" and v(0.8000, 0.8010, external=True) == "PASS"
    assert v(0.80, 0.81, external=False) == "PASS"
    assert v(0.80, 0.825, external=False) == "WARN"
    assert v(0.80, 0.84, external=False) == "FAIL"
    assert v(0.80, 0.84, external=False, kind="approx") == "INFO"
    assert v(float("nan"), 0.8, external=False) == "n/a"
