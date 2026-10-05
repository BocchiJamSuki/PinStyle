"""Load the demo models once from models/ (offline) and keep them resident in fp16."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from functools import cache
from pathlib import Path

os.environ.setdefault("HF_HUB_OFFLINE", "1")

import torch  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
MODELS = REPO_ROOT / "models"
IPA_WEIGHT = "ip-adapter-plus_sdxl_vit-h.safetensors"


@dataclass
class Stack:
    txt2img: object  # StableDiffusionXLControlNetPipeline
    img2img: object  # StableDiffusionXLControlNetImg2ImgPipeline (shares modules)
    inpaint: object  # StableDiffusionXLControlNetInpaintPipeline (shares modules)
    revisions: dict[str, str]


def revisions() -> dict[str, str]:
    manifest = json.loads((MODELS / "MANIFEST.json").read_text())
    return {k: f"{v['repo']}@{v['revision']}" for k, v in manifest.items()}


@cache
def sdxl_stack(device: str = "cuda") -> Stack:
    from diffusers import (
        AutoencoderKL,
        ControlNetModel,
        DPMSolverMultistepScheduler,
        StableDiffusionXLControlNetImg2ImgPipeline,
        StableDiffusionXLControlNetInpaintPipeline,
        StableDiffusionXLControlNetPipeline,
    )
    from transformers import CLIPVisionModelWithProjection

    dt = torch.float16
    vae = AutoencoderKL.from_pretrained(MODELS / "vae", torch_dtype=dt)
    cn = ControlNetModel.from_pretrained(MODELS / "controlnet_lineart", variant="fp16",
                                         torch_dtype=dt)
    enc = CLIPVisionModelWithProjection.from_pretrained(
        MODELS / "ip_adapter/models/image_encoder", torch_dtype=dt)
    pipe = StableDiffusionXLControlNetPipeline.from_pretrained(
        MODELS / "sdxl", vae=vae, controlnet=cn, image_encoder=enc, variant="fp16",
        torch_dtype=dt, add_watermarker=False)
    pipe.scheduler = DPMSolverMultistepScheduler.from_config(
        pipe.scheduler.config, use_karras_sigmas=True)
    pipe.load_ip_adapter(str(MODELS / "ip_adapter"), subfolder="sdxl_models",
                         weight_name=IPA_WEIGHT, image_encoder_folder=None)
    pipe.to(device)
    img2img = StableDiffusionXLControlNetImg2ImgPipeline.from_pipe(pipe)
    inpaint = StableDiffusionXLControlNetInpaintPipeline.from_pipe(pipe)
    return Stack(pipe, img2img, inpaint, revisions())
