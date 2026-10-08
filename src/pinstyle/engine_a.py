"""Engine A (training-free): point pairs -> SAM 2 masks -> masked IP-Adapter correction.

For each region: the target mask comes from the draft (where the accessory is still drawn),
the reference mask from the reference. A crop around the target region is upscaled to the
working size and inpainted on the global output with
  - IP-Adapter images [reference region crop, full reference] and ip_adapter_masks
    [region mask, complement], scales [region scale, global scale];
  - the line-art ControlNet on the draft crop;
then pasted back with a feathered mask. Region strength s maps to
IP scale = ip_min + (ip_max - ip_min) * s and denoise = d_min + (d_max - d_min) * s.
"""

from __future__ import annotations

import time
from collections.abc import Sequence
from dataclasses import asdict, dataclass

import numpy as np
import torch
from PIL import Image

from pinstyle.lineart import control_image
from pinstyle.segmentation import bbox, dilate, feather, sam_mask
from pinstyle.types import PointPair, RegionSettings


@dataclass
class EngineAConfig:
    work_size: int = 1024
    crop_margin: float = 0.6
    min_crop_frac: float = 0.25  # of the image's shorter side
    dilate_px: int = 12  # at output resolution
    feather_sigma: float = 6.0
    ip_min: float = 0.4
    ip_max: float = 1.0
    global_ip_scale: float = 0.4
    d_min: float = 0.45
    d_max: float = 0.9
    structure_strength: float = 0.8
    steps: int = 30
    guidance: float = 6.0
    prompt: str = "high quality illustration, detailed accessory"
    negative_prompt: str = "lowres, blurry, deformed, watermark, text"


class EngineA:
    name = "engine_a"
    version = "0.1"

    def __init__(self, stack, cfg: EngineAConfig | None = None):
        self.stack = stack
        self.cfg = cfg or EngineAConfig()

    def apply(
        self,
        global_output: Image.Image,
        draft: Image.Image,
        references: Sequence[Image.Image],
        point_pairs: Sequence[PointPair],
        region_settings: Sequence[RegionSettings],
        *,
        seed: int,
    ):
        from diffusers.image_processor import IPAdapterMaskProcessor

        c = self.cfg
        out = global_output.convert("RGB")
        draft = draft.convert("RGB").resize(out.size, Image.Resampling.LANCZOS)
        pairs = {p.id: p for p in point_pairs}
        info: dict = {
            "engine": self.name,
            "version": self.version,
            "seed": seed,
            "config": asdict(c),
            "regions": {},
        }
        layers: dict[str, Image.Image] = {}
        masks: dict[str, np.ndarray] = {}
        maskproc = IPAdapterMaskProcessor()

        for reg in region_settings:
            t0 = time.perf_counter()
            rp = [pairs[i] for i in reg.pair_ids]
            ref = references[rp[0].ref_index].convert("RGB")
            tgt_mask = sam_mask(draft, [p.tgt_xy for p in rp], reg.negative_tgt_xy)
            ref_mask = sam_mask(ref, [p.ref_xy for p in rp])
            tgt_mask = dilate(tgt_mask, c.dilate_px)

            # crop around the target region and upscale to the working size
            min_side = int(c.min_crop_frac * min(out.size))
            box = bbox(tgt_mask, c.crop_margin, min_side)
            ws = c.work_size
            crop_out = out.crop(box).resize((ws, ws), Image.Resampling.LANCZOS)
            crop_draft = draft.crop(box).resize((ws, ws), Image.Resampling.LANCZOS)
            m = Image.fromarray(tgt_mask[box[1] : box[3], box[0] : box[2]].astype(np.uint8) * 255)
            m = m.resize((ws, ws), Image.Resampling.NEAREST)

            rbox = bbox(ref_mask, 0.25, 64)
            ref_crop = ref.crop(rbox)

            s = reg.strength
            ip_region = c.ip_min + (c.ip_max - c.ip_min) * s
            denoise = c.d_min + (c.d_max - c.d_min) * s
            m_np = np.asarray(m) > 127
            ip_masks = maskproc.preprocess(
                [
                    Image.fromarray(m_np.astype(np.uint8) * 255),
                    Image.fromarray((~m_np).astype(np.uint8) * 255),
                ],
                height=ws,
                width=ws,
            )
            ip_masks = [
                ip_masks.reshape(1, ip_masks.shape[0], ip_masks.shape[2], ip_masks.shape[3])
            ]
            pipe = self.stack.inpaint
            pipe.set_ip_adapter_scale([[ip_region, c.global_ip_scale]])
            gen = torch.Generator("cuda").manual_seed(seed)
            res = pipe(
                prompt=c.prompt,
                negative_prompt=c.negative_prompt,
                image=crop_out,
                mask_image=m,
                control_image=control_image(crop_draft),
                ip_adapter_image=[[ref_crop, ref]],
                cross_attention_kwargs={"ip_adapter_masks": ip_masks},
                strength=denoise,
                controlnet_conditioning_scale=c.structure_strength,
                num_inference_steps=c.steps,
                guidance_scale=c.guidance,
                width=ws,
                height=ws,
                generator=gen,
            ).images[0]

            # paste back with a feathered mask
            bw, bh = box[2] - box[0], box[3] - box[1]
            patch = res.resize((bw, bh), Image.Resampling.LANCZOS)
            alpha_full = feather(tgt_mask, c.feather_sigma)
            alpha = alpha_full[box[1] : box[3], box[0] : box[2]][..., None]
            base = np.asarray(out, dtype=np.float32)
            region = base[box[1] : box[3], box[0] : box[2]]
            blended = region * (1 - alpha) + np.asarray(patch, dtype=np.float32) * alpha
            base[box[1] : box[3], box[0] : box[2]] = blended
            out = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))

            layer = Image.new("RGBA", out.size, (0, 0, 0, 0))
            la = Image.fromarray((alpha[..., 0] * 255).astype(np.uint8))
            layer.paste(patch.convert("RGBA"), box[:2], la)
            layers[reg.region_id] = layer
            masks[reg.region_id] = tgt_mask
            info["regions"][reg.region_id] = {
                "box": list(box),
                "ref_box": list(rbox),
                "ip_scale": round(ip_region, 3),
                "denoise": round(denoise, 3),
                "mask_px": int(tgt_mask.sum()),
                "ref_mask_px": int(ref_mask.sum()),
                "latency_s": round(time.perf_counter() - t0, 2),
            }
        info["layers"] = layers
        info["masks"] = masks
        return out, info
