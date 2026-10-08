"""Colour vs rendering experiment (D5 follow-up). For each case, seed and generation mode,
one global pass is run; colour_strength 1.0 / 0.5 / 0.0 are then applied to the same output
(the chroma blend is a post-process), so the variants differ only in colour.

    python scripts/exp_colour.py [--cases shichimi_flat pepper_bergen_flat] [--seeds 0 1 2]

Writes runs/<run_id>_colour_<case>_<mode>_s<seed>/ with global_c1.0.png, global_c0.5.png,
global_c0.0.png and record.json (settings, latency, peak VRAM, hardware).
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from dataclasses import replace
from pathlib import Path

os.environ.setdefault("HF_HUB_OFFLINE", "1")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import torch  # noqa: E402
from PIL import Image  # noqa: E402

from pinstyle.cases import load_case  # noqa: E402
from pinstyle.colour import blend_chroma  # noqa: E402
from pinstyle.global_path import GlobalSettings, fit_size, run_global  # noqa: E402
from pinstyle.models import sdxl_stack  # noqa: E402
from pinstyle.runs import new_run_dir, write_record  # noqa: E402

log = logging.getLogger("pinstyle.exp_colour")
MODES = {
    "txt2img": dict(mode="txt2img", structure_strength=1.0),
    "img2img": dict(mode="img2img", structure_strength=1.0, img2img_strength=0.75),
}
STRENGTHS = (1.0, 0.5, 0.0)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", nargs="+", default=["shichimi_flat", "pepper_bergen_flat"])
    ap.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2])
    ap.add_argument("--modes", nargs="+", default=list(MODES))
    args = ap.parse_args()
    stack = sdxl_stack()
    hw = torch.cuda.get_device_name(0)
    for cid in args.cases:
        case = load_case(cid)
        for mode in args.modes:
            for seed in args.seeds:
                s = replace(GlobalSettings(prompt=case.prompt, seed=seed), **MODES[mode])
                out, info, ctrl = run_global(stack, case.draft, case.reference_image(), s)
                d = new_run_dir(f"colour_{cid}_{mode}_s{seed}")
                draft_r = case.draft.convert("RGB").resize(
                    fit_size(case.draft, s.resolution), Image.Resampling.LANCZOS
                )
                for c in STRENGTHS:
                    blend_chroma(out, draft_r, c).save(d / f"global_c{c}.png")
                draft_r.save(d / "draft.png")
                write_record(
                    d,
                    kind="colour_experiment",
                    case=cid,
                    seed=seed,
                    gen_mode=mode,
                    colour_strengths=list(STRENGTHS),
                    hardware=f"{hw}, low_vram={stack.low_vram}",
                    models=stack.revisions,
                    **info,
                )
                log.info("%s %s s%d %.1fs -> %s", cid, mode, seed, info["latency_s"], d)


if __name__ == "__main__":
    main()
