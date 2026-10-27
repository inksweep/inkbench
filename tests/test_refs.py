"""Label transfer of a prepared segment (refs.SegmentRefs) on a small synthetic segment: the exact route puts a dot
drawn on the fine canvas where the canvas map says, the plain resize ~7 px further down and right."""
import json

import numpy as np
import pytest

from inkbench import canvasmap as C
from inkbench.refs import SegmentRefs

COARSE, FINE = C.MeshGeom(40, 30), C.MeshGeom(156, 117)          # rho = 40 / 156, as for 2.4 um -> 9.4 um


def _mesh(d, geom):
    import tifffile

    d.mkdir(parents=True)
    (d / "meta.json").write_text(json.dumps({"scale": [geom.scale_x, geom.scale_y]}))
    tifffile.imwrite(d / "x.tif", np.zeros((geom.rows, geom.cols), np.float32))


@pytest.fixture
def seg(tmp_path):
    import tifffile
    import zarr

    d = tmp_path / "PHerc0000" / "20990101000000-test"
    h, w = COARSE.canvas_shape
    sv = zarr.open_array(str(d / "sv"), mode="w", shape=(3, h, w), chunks=(3, 128, 128), dtype="u1", zarr_format=2,
                         fill_value=0)
    sv[:] = 100
    _mesh(d / "mesh" / "x-on-20990101000001-c.tifxyz", COARSE)
    _mesh(d / "mesh" / "x-on-20990101000002-f.tifxyz", FINE)
    fine = np.zeros(FINE.canvas_shape, np.uint8)
    fine[1500:1520, 1100:1120] = 255                               # a 20 px dot on the fine canvas
    (d / "teacher").mkdir()
    tifffile.imwrite(d / "teacher" / "map.tif", fine)
    (d / "segment.json").write_text(json.dumps(dict(
        coarse_volume="20990101000001",
        meshes={"20990101000001": "x-on-20990101000001-c.tifxyz", "20990101000002": "x-on-20990101000002-f.tifxyz"},
        teachers={"canon": {"file": "map.tif", "volume": "20990101000002"}})))
    return d


def test_canvas_check_and_routes(seg):
    r = SegmentRefs(seg)
    assert r.canvas_check()["ok"] and r.shape == COARSE.canvas_shape
    exact = r.teacher("canon", "exact")
    compat = r.teacher("canon", "compat")
    assert exact.shape == compat.shape == COARSE.canvas_shape
    assert (seg / "teacher_canon_exact_cv2.npy").is_file()          # cached next to the segment data
    (ye, xe), (yc, xc) = _centroid(exact), _centroid(compat)
    assert ye == pytest.approx(C.fine_to_coarse(1509.5, FINE, COARSE, 0), abs=0.3)
    assert xe == pytest.approx(C.fine_to_coarse(1109.5, FINE, COARSE, 1), abs=0.3)
    off = C.naive_offset_px(FINE, COARSE, 1509.5, 0)               # the plain resize lands ~7.4 px off
    assert -off == pytest.approx(7.44, abs=0.05)
    assert yc - ye == pytest.approx(-off, abs=0.3) and xc - xe == pytest.approx(-off, abs=0.3)
    np.testing.assert_array_equal(r.teacher("canon", "exact"), exact)   # read back from the cache


def _centroid(img):
    v = np.nan_to_num(img).astype(np.float64)
    ys, xs = np.indices(v.shape)
    return (ys * v).sum() / v.sum(), (xs * v).sum() / v.sum()
