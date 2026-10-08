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
    low_vram: bool = False
    _active: str = ""

    def use(self, name: str):
        """The named pipeline, ready to run. In low-VRAM mode (ADR-0010) the shared modules
        live in CPU RAM and model offload hooks are (re)attached for the pipeline about to
        run; switching pipelines re-hooks the same modules."""
        pipe = getattr(self, name)
        if self.low_vram and self._active != name:
            pipe.enable_model_cpu_offload()
            self._active = name
        return pipe


def low_vram_default() -> bool:
    """PINSTYLE_LOW_VRAM=1/0 forces it; otherwise on when the GPU has < 16 GiB (the full
    stack needs ~12 GiB resident and ~13.4 GiB peak at 1024 px, D0/D2 on the 4090)."""
    env = os.environ.get("PINSTYLE_LOW_VRAM")
    if env is not None:
        return env == "1"
    return torch.cuda.get_device_properties(0).total_memory < 16 * 2**30


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
    cn = ControlNetModel.from_pretrained(
        MODELS / "controlnet_lineart", variant="fp16", torch_dtype=dt
    )
    enc = CLIPVisionModelWithProjection.from_pretrained(
        MODELS / "ip_adapter/models/image_encoder", torch_dtype=dt
    )
    pipe = StableDiffusionXLControlNetPipeline.from_pretrained(
        MODELS / "sdxl",
        vae=vae,
        controlnet=cn,
        image_encoder=enc,
        variant="fp16",
        torch_dtype=dt,
        add_watermarker=False,
    )
    pipe.scheduler = DPMSolverMultistepScheduler.from_config(
        pipe.scheduler.config, use_karras_sigmas=True
    )
    pipe.load_ip_adapter(
        str(MODELS / "ip_adapter"),
        subfolder="sdxl_models",
        weight_name=IPA_WEIGHT,
        image_encoder_folder=None,
    )
    low = low_vram_default()
    if not low:
        pipe.to(device)
    # from_pipe casts shared modules to fp32 unless torch_dtype is given (D2: OOM at 1024 px).
    img2img = StableDiffusionXLControlNetImg2ImgPipeline.from_pipe(pipe, torch_dtype=dt)
    inpaint = StableDiffusionXLControlNetInpaintPipeline.from_pipe(pipe, torch_dtype=dt)
    return Stack(pipe, img2img, inpaint, revisions(), low_vram=low)
