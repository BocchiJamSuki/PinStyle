import numpy as np

from pinstyle.segmentation import bbox, dilate, feather


def _mask():
    m = np.zeros((100, 200), bool)
    m[40:50, 90:100] = True
    return m


def test_dilate_grows():
    assert dilate(_mask(), 3).sum() > _mask().sum()


def test_feather_range():
    f = feather(_mask(), 2.0)
    assert 0.0 <= f.min() and f.max() <= 1.0 and 0 < f[45, 95] <= 1


def test_bbox_square_inside_image():
    x0, y0, x1, y1 = bbox(_mask(), 0.5, 30)
    assert x1 - x0 == y1 - y0 >= 30
    assert x0 <= 90 and x1 >= 100 and 0 <= y0 and y1 <= 100


def test_inside_shrinks_only_interior_edges():
    from pinstyle.segmentation import inside

    k = inside((100, 80), (0, 20, 80, 100), 5)
    assert k[25:, :].all()  # left/right/bottom are image borders: kept
    assert not k[20:25].any()  # top edge is interior: shrunk by the band
    assert not k[:20].any()
