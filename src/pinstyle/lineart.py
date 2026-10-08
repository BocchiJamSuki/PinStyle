"""Draft simulation and ControlNet conditioning.

A simulated draft is made from a finished work: line art (XDoG-style edges) optionally over
flat colours (k-means quantization). The ControlNet input is the line art as white lines on
black, which is what line-art ControlNets such as MistoLine expect.
"""

from __future__ import annotations

import cv2
import numpy as np
from PIL import Image


def extract_lines(
    img: Image.Image,
    sigma: float = 1.0,
    k: float = 1.6,
    tau: float = 0.98,
    eps: float = -0.02,
    phi: float = 200.0,
) -> Image.Image:
    """XDoG line extraction. Returns black lines on white ("L" mode)."""
    gray = np.asarray(img.convert("L"), dtype=np.float32) / 255.0
    g1 = cv2.GaussianBlur(gray, (0, 0), sigma)
    g2 = cv2.GaussianBlur(gray, (0, 0), sigma * k)
    d = g1 - tau * g2
    out = np.where(d >= eps, 1.0, 1.0 + np.tanh(phi * (d - eps)))
    lines = (np.clip(out, 0, 1) * 255).astype(np.uint8)
    return Image.fromarray(lines, "L")


def flat_colours(img: Image.Image, k: int = 8, seed: int = 0) -> Image.Image:
    """k-means colour quantization after an edge-preserving smoothing pass."""
    rgb = np.asarray(img.convert("RGB"))
    smooth = cv2.bilateralFilter(rgb, 9, 60, 9)
    data = smooth.reshape(-1, 3).astype(np.float32)
    cv2.setRNGSeed(seed)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0)
    _, labels, centers = cv2.kmeans(data, k, None, criteria, 3, cv2.KMEANS_PP_CENTERS)
    flat = centers.astype(np.uint8)[labels.flatten()].reshape(rgb.shape)
    return Image.fromarray(flat)


def simulate_draft(img: Image.Image, mode: str = "lines", k: int = 8) -> Image.Image:
    """mode="lines": line art only; mode="flat": line art over flat colours."""
    lines = np.asarray(extract_lines(img), dtype=np.float32) / 255.0
    if mode == "lines":
        base = np.ones((*lines.shape, 3), dtype=np.float32)
    elif mode == "flat":
        base = np.asarray(flat_colours(img, k=k), dtype=np.float32) / 255.0
    else:
        raise ValueError(mode)
    out = base * lines[..., None]
    return Image.fromarray((out * 255).astype(np.uint8))


def control_image(draft: Image.Image) -> Image.Image:
    """White lines on black from a draft (black lines on light background)."""
    lines = extract_lines(draft) if draft.mode != "L" else draft
    inv = 255 - np.asarray(lines)
    return Image.fromarray(inv).convert("RGB")
