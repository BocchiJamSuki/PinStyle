"""Separate colour from rendering (D5 follow-up).

The global pass takes both rendering (shading, brushwork, line quality) and colour from the
reference. `colour_strength` decides where the colours come from: 1 keeps the generated colours
(the reference's), 0 uses the draft's colours. The output's lightness (Lab L) is always kept,
so shading and brushwork stay the reference's; only chroma (a, b) is blended toward the draft.
The draft's chroma is smoothed first, so line art and flat-colour edges do not print through.
"""

from __future__ import annotations

import cv2
import numpy as np
from PIL import Image


def blend_chroma(
    output: Image.Image,
    draft: Image.Image,
    colour_strength: float,
    smooth_px: float = 3.0,
    lock_mask: np.ndarray | None = None,
) -> Image.Image:
    """Return output with its Lab chroma moved toward the draft's by (1 - colour_strength).

    lock_mask (bool HxW at output size), if given, forces draft colours (strength 0) there."""
    c = float(np.clip(colour_strength, 0.0, 1.0))
    if c >= 1.0 and lock_mask is None:
        return output.convert("RGB")
    out = np.asarray(output.convert("RGB"))
    dr = np.asarray(draft.convert("RGB").resize(output.size, Image.Resampling.LANCZOS))
    lab_o = cv2.cvtColor(out, cv2.COLOR_RGB2LAB).astype(np.float32)
    lab_d = cv2.cvtColor(dr, cv2.COLOR_RGB2LAB).astype(np.float32)
    ab_d = lab_d[..., 1:]
    if smooth_px > 0:
        ab_d = cv2.GaussianBlur(ab_d, (0, 0), smooth_px)
    w = np.full(out.shape[:2], c, dtype=np.float32)
    if lock_mask is not None:
        w[lock_mask] = 0.0
    w = w[..., None]
    lab = lab_o.copy()
    lab[..., 1:] = w * lab_o[..., 1:] + (1 - w) * ab_d
    rgb = cv2.cvtColor(np.clip(lab, 0, 255).astype(np.uint8), cv2.COLOR_LAB2RGB)
    return Image.fromarray(rgb)
