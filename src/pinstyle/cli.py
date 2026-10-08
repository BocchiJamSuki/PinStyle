"""CLI: `python -m pinstyle.cli global --case ID [--seeds 0 1 2] [overrides...]`."""

from __future__ import annotations

import argparse
import logging
from dataclasses import fields

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


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ap = argparse.ArgumentParser(prog="pinstyle")
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("global")
    g.add_argument("--case", required=True)
    g.add_argument("--seeds", type=int, nargs="+", default=[0])
    add_settings_args(g)
    args = ap.parse_args()
    {"global": cmd_global}[args.cmd](args)


if __name__ == "__main__":
    main()
