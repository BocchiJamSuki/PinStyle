"""D5: run the external services on the demo cases (network, paid). Laptop or server.

    python scripts/run_compare.py --trial            # 1 call per provider, format check
    python scripts/run_compare.py --run [--providers tencent alibaba]

Keys come from .env. Before anything is sent, the planned number of calls is priced and checked
against the cap (CNY 4 per provider). Every response is cached; repeated inputs are not sent.
Images are labelled A (draft) and B (reference) in the prompt; each provider orders them as
its API requires (Alibaba: B first, then A, so the output follows the draft's aspect ratio).
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from omegaconf import OmegaConf  # noqa: E402

from pinstyle.cases import load_case  # noqa: E402
from pinstyle.compare import runner  # noqa: E402
from pinstyle.compare.providers import PROVIDERS  # noqa: E402

log = logging.getLogger("pinstyle.compare")


def load_env() -> None:
    env = ROOT / ".env"
    for line in env.read_text().splitlines() if env.exists() else []:
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


def prompt_for(cfg, case_id: str, attempt: int, provider: str) -> str:
    """The shared template, with images numbered in the order the provider receives them
    (Alibaba: reference first, then draft)."""
    p = cfg.template
    if attempt >= 2:
        c = cfg.cases[case_id]
        p = f"{p} {cfg.accessory_hint.format(accessory=c.accessory, where=c.where)}"
    a, b = ("Image 2", "Image 1") if provider == "alibaba" else ("Image 1", "Image 2")
    return p.replace("Image A", a).replace("Image B", b)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--trial", action="store_true")
    g.add_argument("--run", action="store_true")
    ap.add_argument("--providers", nargs="+", default=list(PROVIDERS))
    args = ap.parse_args()
    load_env()
    cfg = OmegaConf.load(ROOT / "configs" / "compare.yaml")
    ledger = runner.Ledger(runner.D5 / "ledger.jsonl")

    if args.trial:
        jobs = [("shichimi_flat", 0)]
    else:
        jobs = [(c, a) for c in cfg.cases for a in range(1, cfg.attempts + 1)]
    cases = {c: load_case(c) for c, _ in jobs}

    for name in args.providers:
        p = PROVIDERS[name]
        planned = sum(
            1 for c, a in jobs
            if not _cached(p, cases[c], prompt_for(cfg, c, max(a, 1), name), a)
        )
        log.info("budget %s", json.dumps(runner.check_budget(ledger, p, planned, runner.CAP_CNY)))
        for c, a in jobs:
            case = cases[c]
            prompt = prompt_for(cfg, c, max(a, 1), name)
            img, rec = runner.generate(
                p, case.draft, case.reference_image(), prompt, seed=a,
                tag={"case": c, "attempt": a, "trial": args.trial},
            )
            out = runner.D5 / "outputs" / name / f"{c}_a{a}.png"
            out.parent.mkdir(parents=True, exist_ok=True)
            img.save(out)
            log.info("%s %s a%d cached=%s size=%s model=%s usage=%s -> %s", name, c, a,
                     rec["cached"], img.size, rec.get("response_model"), rec.get("usage"), out)
        log.info("%s spent CNY %.2f of cap %.2f", name, ledger.spent(name), runner.CAP_CNY)


def _cached(p, case, prompt, seed) -> bool:
    body = p.request_body(case.draft, case.reference_image(), prompt, seed)
    key = runner.body_key(p, body)
    return (runner.D5 / "cache" / p.name / f"{key}.png").exists()


if __name__ == "__main__":
    main()
