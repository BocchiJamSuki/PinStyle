"""CLI:
python -m pinstyle.cli global --case ID [--seeds 0 1 2] [overrides...]
python -m pinstyle.cli run --case ID --pairs pairs.json [--seeds 0 1 2] [--strength S]
"""

from __future__ import annotations

import argparse
import logging
from dataclasses import fields
from pathlib import Path

from pinstyle.cases import load_case
from pinstyle.global_path import GlobalSettings, run_global
from pinstyle.runs import new_run_dir, write_record

log = logging.getLogger("pinstyle")


def add_settings_args(ap: argparse.ArgumentParser) -> None:
    for f in fields(GlobalSettings):
        if f.name in ("prompt", "seed"):
            continue
        ap.add_argument(f"--{f.name.replace('_', '-')}", type=type(f.default), default=None)


def settings_from(args: argparse.Namespace, prompt: str, seed: int) -> GlobalSettings:
    s = GlobalSettings(prompt=prompt, seed=seed)
    for f in fields(GlobalSettings):
        v = getattr(args, f.name, None)
        if v is not None and f.name not in ("prompt", "seed"):
            setattr(s, f.name, v)
    return s


def cmd_global(args: argparse.Namespace) -> None:
    from pinstyle.models import sdxl_stack

    stack = sdxl_stack()
    case = load_case(args.case)
    for seed in args.seeds:
        s = settings_from(args, case.prompt, seed)
        out, info, ctrl = run_global(stack, case.draft, case.reference_image(), s)
        run_dir = new_run_dir(f"global_{case.id}_s{seed}")
        out.save(run_dir / "global.png")
        case.draft.save(run_dir / "draft.png")
        ctrl.save(run_dir / "control.png")
        write_record(
            run_dir,
            kind="global",
            case=case.id,
            seed=seed,
            source=case.source.id,
            reference=case.reference.id,
            draft_source=case.draft_source,
            models=stack.revisions,
            **info,
        )
        log.info("%s seed=%d latency=%.1fs -> %s", case.id, seed, info["latency_s"], run_dir)


def load_pairs(path: str, strength: float | None):
    import json

    from pinstyle.types import PointPair, RegionSettings

    spec = json.loads(Path(path).read_text())
    pairs = [
        PointPair(p["id"], tuple(p["ref_xy"]), tuple(p["tgt_xy"]), p.get("ref_index", 0))
        for p in spec["pairs"]
    ]
    regions = [
        RegionSettings(
            r["region_id"],
            tuple(r["pair_ids"]),
            strength if strength is not None else r.get("strength", 0.6),
            tuple(r.get("tags", ())),
            tuple(tuple(xy) for xy in r.get("negative_tgt_xy", ())),
        )
        for r in spec["regions"]
    ]
    return spec, pairs, regions


def outside_change(a, b, masks) -> dict:
    """Mean absolute difference (0-255) and SSIM between a and b outside the union of masks."""
    import numpy as np
    from skimage.metrics import structural_similarity

    x, y = np.asarray(a, dtype=np.float32), np.asarray(b, dtype=np.float32)
    keep = ~np.any(np.stack(list(masks)), axis=0) if masks else np.ones(x.shape[:2], bool)
    _, smap = structural_similarity(x, y, channel_axis=2, data_range=255, full=True)
    return {
        "mad_outside": round(float(np.abs(x - y)[keep].mean()), 3),
        "ssim_outside": round(float(smap.mean(axis=2)[keep].mean()), 4),
    }


def cmd_run(args: argparse.Namespace) -> None:
    from pinstyle.engine_a import EngineA
    from pinstyle.models import sdxl_stack

    stack = sdxl_stack()
    case = load_case(args.case)
    spec, pairs, regions = load_pairs(args.pairs, args.strength)
    engine = EngineA(stack)
    for seed in args.seeds:
        s = settings_from(args, case.prompt, seed)
        glob_out, ginfo, ctrl = run_global(stack, case.draft, case.reference_image(), s)
        out, info = engine.apply(
            glob_out, case.draft, [case.reference_image()], pairs, regions, seed=seed
        )
        run_dir = new_run_dir(f"pinstyle_{case.id}_s{seed}")
        glob_out.save(run_dir / "global.png")
        out.save(run_dir / "pinstyle.png")
        case.draft.save(run_dir / "draft.png")
        for rid, layer in info.pop("layers").items():
            layer.save(run_dir / f"layer_{rid}.png")
        masks = info.pop("masks")
        write_record(
            run_dir,
            kind="pinstyle",
            case=case.id,
            seed=seed,
            source=case.source.id,
            reference=case.reference.id,
            draft_source=case.draft_source,
            models=stack.revisions,
            pairs_file=spec,
            global_info=ginfo,
            engine_info=info,
            change_vs_global=outside_change(glob_out, out, masks.values()),
        )
        lat = sum(r["latency_s"] for r in info["regions"].values())
        log.info("%s seed=%d local=%.1fs -> %s", case.id, seed, lat, run_dir)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ap = argparse.ArgumentParser(prog="pinstyle")
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("global")
    g.add_argument("--case", required=True)
    g.add_argument("--seeds", type=int, nargs="+", default=[0])
    add_settings_args(g)
    r = sub.add_parser("run")
    r.add_argument("--case", required=True)
    r.add_argument("--pairs", required=True)
    r.add_argument("--seeds", type=int, nargs="+", default=[0])
    r.add_argument("--strength", type=float, default=None)
    add_settings_args(r)
    args = ap.parse_args()
    {"global": cmd_global, "run": cmd_run}[args.cmd](args)


if __name__ == "__main__":
    main()
