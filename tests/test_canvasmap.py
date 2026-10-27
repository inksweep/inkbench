import numpy as np
import pytest

from inkbench import canvasmap as C

F32_STEP = float(np.float32(0.05))          # published meshes store 0.05 as float32 (0.0500000007)

# Three rows of slchicoineau-creator/tifxyz-canvas-map results/pair_maps.tsv (fine rows/cols, coarse rows/cols, y_a,
# y_b, x_a, x_b): the published map of real PHerc0009B mesh pairs, which this implementation must reproduce.
PAIR_ROWS = [
    (926, 738, 257, 205, -7.585891426, 0.277537801112, -7.583363879, 0.277777781917),
    (734, 1062, 204, 295, -7.581774266, 0.277929159455, -7.583377290, 0.277777781916),
    (749, 723, 208, 201, -7.584143142, 0.277703608945, -7.580942812, 0.278008302898),
]


@pytest.mark.parametrize("row", PAIR_ROWS)
def test_coefficients_reproduce_published_pair_maps(row):
    fr, fc, cr, cc, ya, yb, xa, xb = row
    fine = C.MeshGeom(fr, fc, F32_STEP, F32_STEP)
    coarse = C.MeshGeom(cr, cc, F32_STEP, F32_STEP)
    k = C.coeffs(fine, coarse)
    # agreement to 1e-4 px (sub-micron): the table's last digits depend on float32 vs double grid steps per mesh
    assert k["y_a"] == pytest.approx(ya, abs=1e-4) and k["y_b"] == pytest.approx(yb, abs=1e-7)
    assert k["x_a"] == pytest.approx(xa, abs=1e-4) and k["x_b"] == pytest.approx(xb, abs=1e-7)


def test_closed_form_and_inverse():
    fine, coarse = C.MeshGeom(823, 928), C.MeshGeom(211, 238)
    p = np.array([0.0, 100.5, 4000.0, 16000.0])
    for axis in (0, 1):
        rho = coarse.n(axis) / fine.n(axis)
        assert np.allclose(C.fine_to_coarse(p, fine, coarse, axis), (p + 10.5) * rho - 10.5)
        assert np.allclose(C.coarse_to_fine(C.fine_to_coarse(p, fine, coarse, axis), fine, coarse, axis), p)
    # the plain resize is ~7.8 coarse px off on this pair (villa#2243: -10 (1 - rho))
    off = C.naive_offset_px(fine, coarse, 0.0, 0)
    assert off == pytest.approx(-10 * (1 - 211 / 823), abs=1e-9)


def test_warp_moves_a_dot_to_its_exact_position():
    fine, coarse = C.MeshGeom(400, 300), C.MeshGeom(103, 77)
    img = np.zeros(fine.canvas_shape, np.uint8)
    yf, xf = 4001, 2999
    img[yf - 6:yf + 7, xf - 6:xf + 7] = 255
    out = C.warp_fine_to_coarse(img, fine, coarse, kind="map")
    yc, xc = np.unravel_index(np.nanargmax(out), out.shape)
    assert abs(yc - C.fine_to_coarse(yf, fine, coarse, 0)) <= 1.0
    assert abs(xc - C.fine_to_coarse(xf, fine, coarse, 1)) <= 1.0
    naive = C.naive_fine_to_coarse(img, coarse.canvas_shape, "map")
    yn, xn = np.unravel_index(np.argmax(naive), naive.shape)
    assert yn - yc >= 6                                        # plain resize lands ~7 px further down/right
    m = C.warp_fine_to_coarse(img > 0, fine, coarse, kind="mask")
    assert m.dtype == bool and m.any()


def test_level_of():
    fine = C.MeshGeom(823, 928)
    assert C.level_of(fine.canvas_shape, fine) == 0
    assert C.level_of((fine.canvas(0) // 4, fine.canvas(1) // 4), fine) == 2
    with pytest.raises(ValueError):
        C.level_of((123, 456), fine)
