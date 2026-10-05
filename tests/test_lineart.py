import numpy as np
from PIL import Image, ImageDraw

from pinstyle.lineart import control_image, extract_lines, simulate_draft


def _img():
    im = Image.new("RGB", (128, 128), (200, 120, 80))
    ImageDraw.Draw(im).ellipse((30, 30, 98, 98), fill=(20, 40, 160))
    return im


def test_lines_are_dark_on_light():
    lines = np.asarray(extract_lines(_img()))
    assert lines.mean() > 200 and lines.min() < 100


def test_draft_and_control_shapes():
    d = simulate_draft(_img(), "lines")
    c = np.asarray(control_image(d))
    assert d.size == (128, 128) and c.shape == (128, 128, 3)
    assert c.mean() < 60  # mostly black with white lines
