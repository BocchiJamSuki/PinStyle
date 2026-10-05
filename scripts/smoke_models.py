"""D0 model smoke test: load every demo model from models/ (offline), run one small
ControlNet + IP-Adapter generation and one SAM 2 mask, and record VRAM per component.

Writes runs/<run_id>/record.json and smoke.png. Uses a synthetic test image (no rights issue).
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("HF_HUB_OFFLINE", "1")

import numpy as np  # noqa: E402
import torch  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from pinstyle.runs import new_run_dir, write_record  # noqa: E402

M = ROOT / "models"


def gib() -> float:
    return round(torch.cuda.memory_allocated() / 2**30, 3)


def test_image(size: int = 512) -> Image.Image:
    img = Image.new("RGB", (size, size), "white")
    d = ImageDraw.Draw(img)
    d.ellipse((128, 96, 384, 352), outline="black", width=6)
    d.rectangle((200, 360, 312, 480), outline="black", width=6)
    d.ellipse((240, 300, 272, 332), fill="red")
    return img


def main() -> int:
    from diffusers import AutoencoderKL, ControlNetModel, StableDiffusionXLControlNetPipeline
    from transformers import (
        AutoImageProcessor,
        AutoModel,
        CLIPVisionModelWithProjection,
        Sam2Model,
        Sam2Processor,
    )

    vram: dict[str, float] = {}
    timings: dict[str, float] = {}
    base = gib()

    t = time.perf_counter()
    vae = AutoencoderKL.from_pretrained(M / "vae", torch_dtype=torch.float16)
    cn = ControlNetModel.from_pretrained(M / "controlnet_lineart", variant="fp16",
                                         torch_dtype=torch.float16)
    enc = CLIPVisionModelWithProjection.from_pretrained(M / "ip_adapter/models/image_encoder",
                                                        torch_dtype=torch.float16)
    pipe = StableDiffusionXLControlNetPipeline.from_pretrained(
        M / "sdxl", vae=vae, controlnet=cn, image_encoder=enc, variant="fp16",
        torch_dtype=torch.float16, add_watermarker=False)
    pipe.load_ip_adapter(str(M / "ip_adapter"), subfolder="sdxl_models",
                         weight_name="ip-adapter-plus_sdxl_vit-h.safetensors",
                         image_encoder_folder=None)
    pipe.to("cuda")
    timings["load_sdxl_stack_s"] = round(time.perf_counter() - t, 1)
    vram["sdxl_stack_incl_cn_ipa_encoder"] = round(gib() - base, 3)

    for name, mod in [("unet", pipe.unet), ("text_encoders", None), ("vae", pipe.vae),
                      ("controlnet", pipe.controlnet), ("image_encoder", pipe.image_encoder)]:
        if name == "text_encoders":
            mods = [pipe.text_encoder, pipe.text_encoder_2]
        else:
            mods = [mod]
        n = sum(p.numel() * p.element_size() for m in mods for p in m.parameters())
        vram[f"weights_{name}"] = round(n / 2**30, 3)

    img = test_image()
    pipe.set_ip_adapter_scale(0.6)
    torch.cuda.reset_peak_memory_stats()
    t = time.perf_counter()
    out = pipe(prompt="a colorful illustration", image=img, ip_adapter_image=img,
               num_inference_steps=4, height=512, width=512,
               generator=torch.Generator("cuda").manual_seed(0)).images[0]
    timings["gen_512_4steps_s"] = round(time.perf_counter() - t, 2)
    vram["peak_gen_512"] = round(torch.cuda.max_memory_allocated() / 2**30, 3)

    t = time.perf_counter()
    before = gib()
    sam = Sam2Model.from_pretrained(M / "sam2", torch_dtype=torch.bfloat16).to("cuda")
    proc = Sam2Processor.from_pretrained(M / "sam2")
    vram["sam2"] = round(gib() - before, 3)
    inputs = proc(images=img, input_points=[[[[256, 316]]]], input_labels=[[[1]]],
                  return_tensors="pt").to("cuda")
    with torch.no_grad():
        o = sam(**{k: (v.to(torch.bfloat16) if v.dtype == torch.float32 else v)
                   for k, v in inputs.items()})
    masks = proc.post_process_masks(o.pred_masks.float().cpu(), inputs["original_sizes"])[0]
    mask_px = int(np.asarray(masks[0, 0]).sum())
    timings["sam2_load_and_mask_s"] = round(time.perf_counter() - t, 2)

    before = gib()
    dino = AutoModel.from_pretrained(M / "dinov2", torch_dtype=torch.float16).to("cuda")
    dproc = AutoImageProcessor.from_pretrained(M / "dinov2")
    with torch.no_grad():
        feat = dino(**dproc(images=img, return_tensors="pt").to("cuda", torch.float16))
    vram["dinov2"] = round(gib() - before, 3)
    vram["total_resident"] = gib()
    vram["peak_overall"] = round(torch.cuda.max_memory_allocated() / 2**30, 3)

    run_dir = new_run_dir("smoke_models")
    out.save(run_dir / "smoke.png")
    manifest = json.loads((M / "MANIFEST.json").read_text())
    write_record(
        run_dir, kind="smoke_models", seed=0,
        models={k: f"{v['repo']}@{v['revision']}" for k, v in manifest.items()},
        torch=torch.__version__, cuda=torch.version.cuda, device=torch.cuda.get_device_name(0),
        vram_gib=vram, timings=timings,
        checks={"sam2_mask_pixels": mask_px,
                "dinov2_tokens": list(feat.last_hidden_state.shape)},
    )
    print(json.dumps({"vram_gib": vram, "timings": timings, "sam2_mask_pixels": mask_px},
                     indent=2))
    print(f"run dir: {run_dir}")
    return 0 if mask_px > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
