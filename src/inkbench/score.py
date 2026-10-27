"""Score readers on every protocol of a benchmark (CPU only); keep the block statistics for the bootstrap.

Outputs (under the results folder, see :mod:`inkbench.paths`):
  scores/<benchmark>/<reader>.json      per protocol: per-segment values, the benchmark mean, notes, leakage flags
  blocks/<benchmark>/<reader>.npz       per protocol and segment: block statistics (:mod:`inkbench.bootstrap`)
  scores/<benchmark>/_external.json     published map files scored directly (1447 ``predictions/``, IR-truth maps)

The regions and classes follow each published evaluation (see NOTICE): Reader v2's ``v2_run.evaluate`` (union of
supervision and validation, the 0009B union taken on the fine canvas, map classes >= 128 / <= 40), TAUIL's near-2 mm
human-label region, Nieuwlaar's ``native_bench.py`` classes and false-positive control, Reader v2's ``bkill`` blank
test, the PHerc1447 dataset card's mask rule and Jashann's ``score_vs_labels`` edge rule, and the IR-truth
``score_map.py``.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

import numpy as np

from . import metrics as M
from . import paths
from .bootstrap import SegBlocks, auc_blocks, fa_blocks, hp_blocks
from .catalog import BENCHMARKS, W047, W053, Benchmark
from .data import local_segment
from .inputs import CROP, Input, inputs_for
from .provenance import trained_on, trained_on_any
from .zio import open_array, read_image

LOG = logging.getLogger("inkbench.score")


def available_readers() -> list[str]:
    """Every reader (or ensemble) with at least one raw prediction map."""
    names = set()
    for d in paths.preds().glob("**/ink/*"):
        if d.is_dir() and (d / "raw").is_dir():
            names.add(d.name)
    return sorted(names)


def reader_spec(name: str, plugins: Optional[dict[str, str]] = None):
    """The inksweep ReaderSpec whose map conventions score ``name``: a plugin, a registered ensemble (scored with
    Reader V3's 8-bit storage and calibration, see :mod:`inkbench.ensemble`) or an inksweep built-in."""
    from inksweep.readers import get_reader, load_plugin

    from .ensemble import ensemble_spec, registered

    plugins = plugins or {}
    if name in plugins:
        s = load_plugin(plugins[name])
        return s if s.name == name else s.with_options(name=name)
    if name in registered():
        return ensemble_spec(name)
    return get_reader(name)


def leakage(name: str, sample: str, segment_folder: str) -> str:
    """``trained_on`` of a reader, or of every member of a registered ensemble (:func:`trained_on_any`)."""
    from .ensemble import registered

    members = registered().get(name)
    if members:
        return trained_on_any(members, sample, segment_folder)
    return trained_on(name, sample, segment_folder)


def _map(inp: Input, spec, orientation: Optional[str] = None) -> Optional[np.ndarray]:
    from .predict import score_map

    try:
        shape = open_array(inp.surface).shape[1:] if not inp.surface.endswith("layers") else _layers_shape(inp)
        return score_map(inp, spec, orientation or inp.reading, tuple(shape))
    except FileNotFoundError:
        return None


def _layers_shape(inp: Input) -> tuple[int, int]:
    import tifffile

    first = sorted(Path(inp.surface).glob("*.tif"))[0]
    with tifffile.TiffFile(first) as tf:
        return tuple(int(v) for v in tf.pages[0].shape[:2])


def _input(bench: Benchmark, seg) -> Input:
    d = local_segment(seg)
    want = f"{seg.sample}/{d.name}"
    for i in inputs_for([bench.name]):
        if i.key == want:
            return i
    raise LookupError(want)


# ----------------------------------------------------------------------------------------------- per kind
def score_human_map(bench: Benchmark, spec) -> tuple[dict, dict]:
    from .refs import SegmentRefs

    res: dict = {p: {"per_segment": {}, "notes": []} for p in bench.protocols}
    blocks: dict = {p: [] for p in bench.protocols}
    resizer = "torch" if bench.name == "p0009b" else "cv2"
    for seg in bench.segs:
        inp = _input(bench, seg)
        q = _map(inp, spec)
        if q is None:
            continue
        r = SegmentRefs(local_segment(seg))
        v = r.valid_mid
        for proto in bench.protocols:
            target, _, route = proto.rpartition("_")
            val, sb, note = None, None, ""
            try:
                if target == "map":
                    t = r.teacher("canon", route, resizer)
                    if t is None:
                        continue
                    pos, neg = v & (t >= 128), v & (t <= 40)
                    val = M.auc_russo(q[pos], q[neg]) if route == "compat" else M.auc_u8(q[pos], q[neg])
                    sb = auc_blocks(q, pos, neg)
                elif target.startswith("human"):
                    lab = r.labels(route)
                    if lab is None or "inklabels" not in lab:
                        continue
                    if bench.name == "p0009b" and seg.tag != bench.meta.get("human_segment"):
                        continue
                    ink = lab["inklabels"]
                    sup = lab.get("supervision", np.zeros_like(ink))
                    val_m = lab.get("validation", np.zeros_like(ink))
                    if target == "human_near2mm":
                        from scipy import ndimage

                        h = lab["ink_frac"]
                        near = ndimage.distance_transform_edt(h < 0.5) <= 214
                        pos, neg = v & (h >= 0.5), v & near & (h < 0.05)
                        val = M.auc_tauil(q[pos], q[neg])
                    else:
                        if target == "human_union":         # 0009B: union on the fine canvas, then resized
                            reg = lab["union_fine"] if bench.name == "p0009b" and "union_fine" in lab else sup | val_m
                        elif target == "human_sup":
                            reg = sup
                        else:                                     # strict: validation AND supervision
                            reg = sup & val_m
                            if reg.sum() < 1000:
                                reg, note = sup, "validation & supervision empty: supervision only"
                        pos, neg = v & reg & ink, v & reg & ~ink
                        val = M.auc_russo(q[pos], q[neg]) if route == "compat" else M.auc_u8(q[pos], q[neg])
                    sb = auc_blocks(q, pos, neg)
            except (LookupError, ValueError) as e:
                note = f"skipped: {e}"
            if val is not None:
                res[proto]["per_segment"][seg.tag] = val
                blocks[proto].append((seg.tag, sb))
            if note:
                res[proto]["notes"].append(f"{seg.tag}: {note}")
    return res, blocks


def _nieuwlaar_scores(q: np.ndarray, spec) -> tuple[np.ndarray, np.ndarray]:
    """(scores as native_bench reads them, uint8 with the same ranking for the blocks): the ``(v - 64) / 128`` rescale
    applies only to label-smoothed (villa-family) maps; probability maps are used as they are."""
    if spec.calibration == "label_smoothing_0.5":
        return M.nieuwlaar_pred(q), np.clip(q, 64, 192).astype(np.uint8)
    return q.astype(np.float32) / 255.0, q


def score_native78(bench: Benchmark, spec) -> tuple[dict, dict]:
    from .refs import SegmentRefs

    res = {p: {"per_segment": {}, "misreg_max": {}, "notes": []} for p in bench.protocols}
    blocks = {p: [] for p in bench.protocols}
    for seg in bench.segs:
        inp = _input(bench, seg)
        q = _map(inp, spec)
        if q is None:
            continue
        r = SegmentRefs(local_segment(seg))
        v = r.valid_max
        p, qb = _nieuwlaar_scores(q, spec)
        for proto in bench.protocols:
            route = proto.rpartition("_")[2]
            try:
                t = r.teacher("78kev", route)
            except (LookupError, ValueError) as e:
                res[proto]["notes"].append(f"{seg.tag}: {e}")
                continue
            if t is None:
                continue
            t8 = np.rint(np.nan_to_num(t)).clip(0, 255).astype(np.uint8)
            ink, noink, lo, hi = M.native78_classes(t8, v)
            res[proto]["per_segment"][seg.tag] = M.auc_nieuwlaar(ink, noink, p)
            res[proto]["misreg_max"][seg.tag] = M.misregistration_auc(p, ink, noink, v)["max"]
            blocks[proto].append((seg.tag, auc_blocks(qb, ink, noink)))
    return res, blocks


def score_blank(bench: Benchmark, spec) -> tuple[dict, dict]:
    from .inputs import blank_crops
    from .refs import SegmentRefs

    res = {p: {"per_segment": {}, "notes": []} for p in bench.protocols}
    blocks: dict = {p: [] for p in bench.protocols}
    crops = blank_crops()
    for route, proto in (("compat", "fa80_russo"), ("exact", "fa80_exact")):
        if proto not in bench.protocols and not (proto == "fa80_russo" and "auc78_w047" in bench.protocols):
            continue
        d47 = local_segment(W047)
        r47 = SegmentRefs(d47)
        try:
            ref = (np.load(d47 / "ref78_torch_area.npy") if route == "compat" else r47.teacher("78kev", "exact"))
        except (LookupError, ValueError) as e:
            if proto in res:
                res[proto]["notes"].append(f"w047: {e}")
            continue
        pos_l, neg_l, blank_l, sb_pos, sb_blank = [], [], [], [], []
        for tag, seg in (("w047", W047), ("w053", W053)):
            for k, c in enumerate(crops[tag]["crops"]):
                key = f"{seg.sample}/{crops[tag]['segment']}/crop_{c['y0']}_{c['x0']}"
                inp = Input(key, c["path"], float(crops[tag]["voxel_um"]), bench.orientation, (bench.orientation,))
                from .predict import score_map

                try:
                    q = score_map(inp, spec, bench.orientation, (CROP, CROP))
                except FileNotFoundError:
                    return res, blocks
                vv = np.asarray(open_array(c["path"])[14]) > 0
                if tag == "w047":
                    rr = ref[c["y0"]:c["y0"] + CROP, c["x0"]:c["x0"] + CROP]
                    pos, neg = vv & (rr >= 128), vv & (rr <= 40)
                    pos_l.append(q[pos]); neg_l.append(q[neg])
                    sb_pos.append((k, q, pos))
                else:
                    blank_l.append(q[vv])
                    sb_blank.append((k, q, vv))
        pos, neg, blank = (np.concatenate(a) for a in (pos_l, neg_l, blank_l))
        fa, thr = M.fa_at_recall(pos, blank)
        if proto in bench.protocols:
            res[proto]["per_segment"]["w053"] = fa
            res[proto]["threshold"] = thr
            blocks[proto].append(("w053", _fa_blocks_multi(sb_pos, sb_blank)))
        if route == "compat" and "auc78_w047" in bench.protocols:
            res["auc78_w047"]["per_segment"]["w047"] = M.auc_russo(pos, neg)
            blocks["auc78_w047"].append(("w047", _auc_blocks_multi(sb_pos, ref, crops["w047"]["crops"])))
    if "fa80_nieuwlaar" in bench.protocols:
        try:
            r47, r53 = SegmentRefs(local_segment(W047)), SegmentRefs(local_segment(W053))
            i47, i53 = _input(bench, W047), _input(bench, W053)
            q47, q53 = _map(i47, spec), _map(i53, spec)
            if q47 is not None and q53 is not None:
                t = np.rint(np.nan_to_num(r47.teacher("78kev", "compat"))).astype(np.uint8)
                fp = M.nieuwlaar_fp_control(t, r47.valid_max, _nieuwlaar_scores(q47, spec)[0], r53.valid_max,
                                            _nieuwlaar_scores(q53, spec)[0])
                res["fa80_nieuwlaar"]["per_segment"]["w053"] = fp["blank_flagged_valid_frac"]
                res["fa80_nieuwlaar"]["detail"] = fp
        except (LookupError, ValueError, FileNotFoundError) as e:
            res["fa80_nieuwlaar"]["notes"].append(str(e))
    return res, blocks


def _fa_blocks_multi(pos_parts, blank_parts) -> SegBlocks:
    arrs_p, ids_p, arrs_b, ids_b = [], [], [], []
    for k, q, m in pos_parts:
        sb = fa_blocks(q, m, q, np.zeros_like(m))
        arrs_p.append(sb.arrays["pos"]); ids_p.append(sb.block_ids["pos"] + 10_000_000 * k)
    for k, q, m in blank_parts:
        sb = fa_blocks(q, np.zeros_like(m), q, m)
        arrs_b.append(sb.arrays["blank"]); ids_b.append(sb.block_ids["blank"] + 10_000_000 * k)
    return SegBlocks("fa", {"pos": np.concatenate(arrs_p), "blank": np.concatenate(arrs_b)},
                     {"pos": np.concatenate(ids_p), "blank": np.concatenate(ids_b)})


def _auc_blocks_multi(pos_parts, ref, crops) -> SegBlocks:
    ap, an, ids = [], [], []
    for (k, q, pm), c in zip(pos_parts, crops):
        rr = ref[c["y0"]:c["y0"] + CROP, c["x0"]:c["x0"] + CROP]
        neg = (rr <= 40) & (np.asarray(open_array(c["path"])[14]) > 0)
        sb = auc_blocks(q, pm, neg)
        ap.append(sb.arrays["pos"]); an.append(sb.arrays["neg"]); ids.append(sb.block_ids["pos"] + 10_000_000 * k)
    i = np.concatenate(ids)
    return SegBlocks("auc", {"pos": np.concatenate(ap), "neg": np.concatenate(an)}, {"pos": i, "neg": i})


def score_hf1447(bench: Benchmark, spec) -> tuple[dict, dict]:
    """``hf_mask``: inside the dataset's certainty mask (label > 127 = ink), as the dataset card scores.
    ``hf_mask_edge200``: Jashann's rule for the published Reader V3 / v2 rows: mask, CT present in the middle layer,
    and >= 200 px from the edge of the rendered area."""
    from scipy import ndimage

    res = {p: {"per_segment": {}, "blind_orientation": {}, "notes": []} for p in bench.protocols}
    blocks = {p: [] for p in bench.protocols}
    for seg in bench.segs:
        d = local_segment(seg)
        lab = read_image(d / "labels" / "inklabels.png")
        mask = read_image(d / "labels" / "mask.png") > 0
        inp = _input(bench, seg)
        q = _map(inp, spec)
        if q is None:
            continue
        regions = {"hf_mask": mask}
        if "hf_mask_edge200" in bench.protocols:
            import tifffile

            layers = sorted((d / "layers").glob("*.tif"))
            ct = tifffile.imread(layers[len(layers) // 2]) > 0
            regions["hf_mask_edge200"] = mask & ct & (ndimage.distance_transform_edt(ct) >= 200)
        other = [o for o in inp.orientations if o != inp.reading]
        qb = _map(inp, spec, other[0]) if other else None
        for proto, reg in regions.items():
            pos, neg = reg & (lab > 127), reg & (lab <= 127)
            res[proto]["per_segment"][seg.tag] = M.auc_u8(q[pos], q[neg])
            blocks[proto].append((seg.tag, auc_blocks(q, pos, neg)))
            if qb is not None:
                res[proto]["blind_orientation"][seg.tag] = M.auc_u8(qb[pos], qb[neg])
    return res, blocks


def ir_masks() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    d = paths.data() / "ir_truth" / "data"
    return (read_image(d / "truth_ink.png") > 0, read_image(d / "truth_noink.png") > 0, read_image(d / "valid.png") > 0)


def score_ir(bench: Benchmark, spec) -> tuple[dict, dict]:
    ink, noink, valid = ir_masks()
    res = {"ir_camera": {"per_segment": {}, "notes": []}}
    blocks = {"ir_camera": []}
    inp = _input(bench, bench.segs[0])
    q = _map(inp, spec)
    if q is None:
        return res, blocks
    if q.shape != ink.shape:
        res["ir_camera"]["notes"].append(f"IR truth canvas {ink.shape} != prediction {q.shape}: not scored")
        return res, blocks
    r = M.ir_truth_score(q.astype(np.float32), ink, noink, valid)
    res["ir_camera"]["per_segment"]["343P_ir"] = r["auc"]
    res["ir_camera"]["detail"] = r
    qq = M.ir_quantise(q.astype(np.float32), valid)
    blocks["ir_camera"].append(("343P_ir", auc_blocks(qq, ink, noink)))
    other = [o for o in inp.orientations if o != inp.reading]
    if other:
        qb = _map(inp, spec, other[0])
        if qb is not None:
            res["ir_camera"]["blind_orientation"] = M.ir_truth_score(qb.astype(np.float32), ink, noink, valid)["auc"]
    return res, blocks


def score_hp(bench: Benchmark, spec) -> tuple[dict, dict]:
    from .refs import SegmentRefs

    res = {p: {"per_segment": {}, "null_max": {}, "notes": []} for p in bench.protocols}
    blocks = {p: [] for p in bench.protocols}
    for seg in bench.segs:
        inp = _input(bench, seg)
        q = _map(inp, spec)
        if q is None:
            continue
        r = SegmentRefs(local_segment(seg))
        v = r.valid_mid
        try:
            t = r.teacher("canon", "exact")
        except (LookupError, ValueError) as e:
            res["hp_exact"]["notes"].append(f"{seg.tag}: {e}")
            continue
        if t is None:
            continue
        valid = v & np.isfinite(t)
        key = np.nan_to_num(t) / 255.0
        h = M.hp_score(key, q.astype(np.float32) / 255.0, valid)
        res["hp_exact"]["per_segment"][seg.tag] = h["hp_r"]
        res["hp_exact"]["null_max"][seg.tag] = h["null_max"]
        core = valid & (M._gauss(valid.astype(np.float32), 2 * M.HP_SIGMA_PX) > 0.999)
        blocks["hp_exact"].append((seg.tag, hp_blocks(h["_hp_pred"], h["_hp_key"], h["_mask"], grid_mask=core)))
        if "human_near2mm_exact" in bench.protocols:
            try:
                lab = r.labels("exact")
            except (LookupError, ValueError) as e:
                res["human_near2mm_exact"]["notes"].append(f"{seg.tag}: {e}")
                lab = None
            if lab is not None and "ink_frac" in lab:
                from scipy import ndimage

                hf = lab["ink_frac"]
                near = ndimage.distance_transform_edt(hf < 0.5) <= 214
                pos, neg = v & (hf >= 0.5), v & near & (hf < 0.05)
                val = M.auc_tauil(q[pos], q[neg])
                if val is not None:
                    res["human_near2mm_exact"]["per_segment"][seg.tag] = val
                    blocks["human_near2mm_exact"].append((seg.tag, auc_blocks(q, pos, neg)))
    return res, blocks


SCORERS = {"human": score_human_map, "map": score_human_map, "native78": score_native78, "blank": score_blank,
           "hf1447": score_hf1447, "ir": score_ir, "hp": score_hp}


def score_external(bench_name: str) -> dict:
    """Published map files scored directly (pure scorer checks): 1447 ``predictions/v8in.png``, the IR-truth maps."""
    out = {}
    if bench_name == "p1447":
        for seg in BENCHMARKS["p1447"].segs:
            d = local_segment(seg)
            lab, mask = read_image(d / "labels" / "inklabels.png"), read_image(d / "labels" / "mask.png") > 0
            for f in sorted((d / "predictions").glob("*.png")):
                p = read_image(f)
                p = p if p.dtype == np.uint8 else (p >> 8).astype(np.uint8)
                pos, neg = mask & (lab > 127), mask & (lab <= 127)
                out.setdefault(f"ext:predictions/{f.name}", {})[seg.tag] = M.auc_u8(p[pos], p[neg])
    if bench_name == "p0343p_ir":
        ink, noink, valid = ir_masks()
        for f in sorted((paths.data() / "ir_truth" / "maps").glob("*.png")):
            out[f"ext:maps/{f.name}"] = {"343P_ir": M.ir_truth_score(read_image(f).astype(np.float32), ink, noink,
                                                                     valid)["auc"]}
    return out


def score_benchmark(bench_name: str, readers: Optional[list[str]] = None, plugins: Optional[dict] = None) -> dict:
    """Score ``readers`` (default: every reader with predictions) on every protocol of ``bench_name``; returns
    {reader: {protocol: benchmark mean}}."""
    bench = BENCHMARKS[bench_name]
    plugins = plugins or {}
    out_dir = paths.results() / "scores" / bench_name
    blk_dir = paths.results() / "blocks" / bench_name
    out_dir.mkdir(parents=True, exist_ok=True)
    blk_dir.mkdir(parents=True, exist_ok=True)
    summary = {}
    for name in readers or available_readers():
        spec = reader_spec(name, plugins)
        res, blocks = SCORERS[bench.kind](bench, spec)
        for proto, r in res.items():
            vals = [x for x in r["per_segment"].values() if x is not None and x == x]
            r["mean"] = float(np.mean(vals)) if vals else None
            r["trained_on"] = {s.tag: leakage(name, s.sample, local_segment(s).name) for s in bench.segs}
        (out_dir / f"{name}.json").write_text(json.dumps(res, indent=1, default=float))
        flat = {}
        for proto, items in blocks.items():
            for tag, sb in items:
                flat.update(sb.save_dict(f"{proto}|{tag}"))
        if flat:
            np.savez_compressed(blk_dir / f"{name}.npz", **flat)
        summary[name] = {p: r.get("mean") for p, r in res.items()}
        LOG.info("%s %s: %s", bench_name, name, summary[name])
    ext = score_external(bench_name)
    if ext:
        (out_dir / "_external.json").write_text(json.dumps(ext, indent=1))
    return summary


def load_blocks(bench_name: str, reader: str, protocol: str) -> list[tuple[str, SegBlocks]]:
    """The block statistics of one reader on one protocol, as (segment tag, SegBlocks) sorted by tag."""
    p = paths.results() / "blocks" / bench_name / f"{reader}.npz"
    if not p.is_file():
        return []
    z = dict(np.load(p, allow_pickle=False))
    tags = sorted({k.split("|")[1] for k in z if k.startswith(f"{protocol}|") and k.endswith("|kind")})
    return [(t, SegBlocks.from_dict(z, f"{protocol}|{t}")) for t in tags]
