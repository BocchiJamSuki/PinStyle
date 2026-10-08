"""SAM 2.1 (transformers) point-prompt masks and mask operations."""

from __future__ import annotations

from collections.abc import Sequence
from functools import cache

import cv2
import numpy as np
from PIL import Image

from pinstyle.types import NormXY


@cache
def _sam(device: str = "cuda"):
    import torch
    from transformers import Sam2Model, Sam2Processor

    from pinstyle.models import MODELS

    model = Sam2Model.from_pretrained(MODELS / "sam2", torch_dtype=torch.bfloat16).to(device)
    return model.eval(), Sam2Processor.from_pretrained(MODELS / "sam2")


def sam_mask(
    img: Image.Image, positive: Sequence[NormXY], negative: Sequence[NormXY] = ()
) -> np.ndarray:
    """Binary mask (bool HxW) for one object from normalized point prompts."""
    import torch

    model, proc = _sam()
    w, h = img.size
    pts = [[x * w, y * h] for x, y in positive] + [[x * w, y * h] for x, y in negative]
    labels = [1] * len(positive) + [0] * len(negative)
    inputs = proc(
        images=img.convert("RGB"),
        input_points=[[pts]],
        input_labels=[[labels]],
        return_tensors="pt",
    ).to(model.device)
    batch = {
        k: (v.to(torch.bfloat16) if torch.is_floating_point(v) else v) for k, v in inputs.items()
    }
    with torch.no_grad():
        out = model(**batch, multimask_output=True)
    masks = proc.post_process_masks(out.pred_masks.float().cpu(), inputs["original_sizes"])[0]
    scores = out.iou_scores.float().cpu()[0, 0]
    best = int(scores.argmax())
    return np.asarray(masks[0, best]).astype(bool)


def dilate(mask: np.ndarray, px: int) -> np.ndarray:
    if px <= 0:
        return mask
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * px + 1, 2 * px + 1))
    return cv2.dilate(mask.astype(np.uint8), k).astype(bool)


def feather(mask: np.ndarray, sigma: float) -> np.ndarray:
    m = mask.astype(np.float32)
    if sigma <= 0:
        return m
    return np.clip(cv2.GaussianBlur(m, (0, 0), sigma), 0.0, 1.0)


def bbox(mask: np.ndarray, margin: float, min_size: int) -> tuple[int, int, int, int]:
    """Square-ish box around the mask with relative margin, clipped to the image."""
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        raise ValueError("empty mask")
    h, w = mask.shape
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    side = max(x1 - x0, y1 - y0, 1) * (1 + 2 * margin)
    side = int(min(max(side, min_size), w, h))
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    left = int(np.clip(cx - side / 2, 0, w - side))
    top = int(np.clip(cy - side / 2, 0, h - side))
    return left, top, left + side, top + side


def inside(shape: tuple[int, int], box: tuple[int, int, int, int], band: int) -> np.ndarray:
    """Bool mask of the box, shrunk by `band` px on edges that lie inside the image (edges on
    the image border are kept, since nothing lies beyond them)."""
    h, w = shape
    x0, y0, x1, y1 = box
    keep = np.zeros((h, w), bool)
    keep[
        y0 + (band if y0 > 0 else 0) : y1 - (band if y1 < h else 0),
        x0 + (band if x0 > 0 else 0) : x1 - (band if x1 < w else 0),
    ] = True
    return keep
