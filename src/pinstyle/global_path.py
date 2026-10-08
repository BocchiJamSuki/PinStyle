"""Global path: SDXL + line-art ControlNet on the draft + IP-Adapter (InstantStyle block
scales) on the reference. Mode "txt2img" generates from noise under the ControlNet;
mode "img2img" starts from the draft."""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass

import torch
from PIL import Image

from pinstyle.colour import blend_chroma
from pinstyle.lineart import control_image

NEG = "lowres, blurry, deformed, watermark, text, signature"


@dataclass
class GlobalSettings:
    prompt: str = "a finished digital painting of a character, high quality illustration"
    negative_prompt: str = NEG
    mode: str = "txt2img"  # or "img2img"
    style_strength: float = 1.0  # rendering: IP-Adapter scale on style blocks
    # colour: 1 = colours from the generation (the reference's), 0 = the draft's colours
    # (Lab chroma blend, lightness kept; needs a coloured draft). See pinstyle.colour.
    colour_strength: float = 1.0
    style_blocks: str = "instantstyle"  # "instantstyle" (up.block_0) or "all"
    structure_strength: float = 0.7  # ControlNet conditioning scale
    img2img_strength: float = 0.8
    steps: int = 30
    guidance: float = 6.0
    resolution: int = 1024
    seed: int = 0


def fit_size(img: Image.Image, long_side: int) -> tuple[int, int]:
    w, h = img.size
    s = long_side / max(w, h)
    return max(64, round(w * s / 64) * 64), max(64, round(h * s / 64) * 64)


def ip_scale(s: GlobalSettings) -> float | dict:
    if s.style_blocks == "all":
        return s.style_strength
    return {"up": {"block_0": [0.0, s.style_strength, 0.0]}}


def run_global(
    stack, draft: Image.Image, reference: Image.Image, s: GlobalSettings
) -> tuple[Image.Image, dict, Image.Image]:
    """Return (output, info, control image)."""
    size = fit_size(draft, s.resolution)
    draft_r = draft.convert("RGB").resize(size, Image.Resampling.LANCZOS)
    ctrl = control_image(draft_r)
    gen = torch.Generator("cuda").manual_seed(s.seed)
    common = dict(
        prompt=s.prompt,
        negative_prompt=s.negative_prompt,
        ip_adapter_image=reference.convert("RGB"),
        controlnet_conditioning_scale=s.structure_strength,
        num_inference_steps=s.steps,
        guidance_scale=s.guidance,
        generator=gen,
    )
    t0 = time.perf_counter()
    if s.mode == "txt2img":
        stack.txt2img.set_ip_adapter_scale(ip_scale(s))
        out = stack.txt2img(image=ctrl, width=size[0], height=size[1], **common).images[0]
    elif s.mode == "img2img":
        stack.img2img.set_ip_adapter_scale(ip_scale(s))
        out = stack.img2img(
            image=draft_r, control_image=ctrl, strength=s.img2img_strength, **common
        ).images[0]
    else:
        raise ValueError(s.mode)
    torch.cuda.synchronize()
    if s.colour_strength < 1.0:
        out = blend_chroma(out, draft_r, s.colour_strength)
    info = {
        "settings": asdict(s),
        "size": list(size),
        "latency_s": round(time.perf_counter() - t0, 2),
        "peak_vram_gib": round(torch.cuda.max_memory_allocated() / 2**30, 2),
    }
    return out, info, ctrl
