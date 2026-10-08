import cv2
import numpy as np
from PIL import Image

from pinstyle.colour import blend_chroma


def lab(img):
    return cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2LAB).astype(int)


def test_strength_one_is_identity():
    out = Image.new("RGB", (32, 32), (200, 40, 40))
    draft = Image.new("RGB", (32, 32), (40, 40, 200))
    assert np.array_equal(np.asarray(blend_chroma(out, draft, 1.0)), np.asarray(out))


def test_strength_zero_takes_draft_chroma_keeps_lightness():
    out = Image.new("RGB", (32, 32), (200, 40, 40))  # red
    draft = Image.new("RGB", (32, 32), (40, 40, 200))  # blue
    res = lab(blend_chroma(out, draft, 0.0, smooth_px=0))
    lo, ld = lab(out), lab(draft)
    assert abs(res[..., 1:] - ld[..., 1:]).max() <= 6  # chroma from the draft (gamut clip)
    assert abs(res[..., 0] - lo[..., 0]).mean() < abs(res[..., 0] - ld[..., 0]).mean()


def test_half_is_between():
    out = Image.new("RGB", (16, 16), (200, 40, 40))
    draft = Image.new("RGB", (16, 16), (40, 40, 200))
    a = lab(blend_chroma(out, draft, 0.5, smooth_px=0))[..., 2].mean()
    assert lab(draft)[..., 2].mean() < a < lab(out)[..., 2].mean()


def test_lock_mask_forces_draft_colour_locally():
    out = Image.new("RGB", (16, 16), (200, 40, 40))
    draft = Image.new("RGB", (16, 16), (40, 40, 200))
    m = np.zeros((16, 16), bool)
    m[:8] = True
    res = lab(blend_chroma(out, draft, 1.0, smooth_px=0, lock_mask=m))
    assert abs(res[:8, :, 2] - lab(draft)[:8, :, 2]).max() <= 6
    assert np.array_equal(res[8:], lab(out)[8:])


def test_draft_size_mismatch_is_resized():
    out = Image.new("RGB", (40, 20), (120, 120, 120))
    draft = Image.new("RGB", (400, 200), (10, 200, 10))
    assert blend_chroma(out, draft, 0.0).size == (40, 20)
