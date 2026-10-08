"""D5 runner for external services: response cache, key-free spending ledger, budget guard.

- Cache key = sha256 of (provider, model, input image hashes, prompt, parameters). A cached
  request is never sent again.
- Ledger: runs/d5/ledger.jsonl, one line per paid call, with no keys.
- Budget: the ledger total plus the planned calls must stay within the cap per provider
  (80% of the CNY 5 balance, ADR-0009); otherwise nothing is sent.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from pinstyle.compare.providers import ImageProvider, call

REPO_ROOT = Path(__file__).resolve().parents[3]
D5 = REPO_ROOT / "runs" / "d5"
CAP_CNY = 4.0


class BudgetExceeded(RuntimeError):
    pass


def img_sha256(img: Image.Image) -> str:
    return hashlib.sha256(img.convert("RGB").tobytes() + str(img.size).encode()).hexdigest()


def body_key(provider: ImageProvider, body: dict) -> str:
    def strip(o):  # replace inline images by their hashes
        if isinstance(o, dict):
            return {k: strip(v) for k, v in o.items()}
        if isinstance(o, list):
            return [strip(v) for v in o]
        if isinstance(o, str) and o.startswith("data:image"):
            return "sha256:" + hashlib.sha256(o.encode()).hexdigest()
        return o

    canon = json.dumps({"p": provider.name, "m": provider.model, "b": strip(body)}, sort_keys=True)
    return hashlib.sha256(canon.encode()).hexdigest()


@dataclass
class Ledger:
    path: Path

    def entries(self) -> list[dict]:
        if not self.path.exists():
            return []
        return [json.loads(x) for x in self.path.read_text().splitlines() if x.strip()]

    def spent(self, provider: str) -> float:
        return round(sum(e["cost_cny"] for e in self.entries() if e["provider"] == provider), 4)

    def add(self, entry: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a") as f:
            f.write(json.dumps(entry) + "\n")


def check_budget(ledger: Ledger, provider: ImageProvider, planned_calls: int, cap: float) -> dict:
    spent = ledger.spent(provider.name)
    est = round(planned_calls * provider.price_cny, 4)
    info = {
        "provider": provider.name,
        "spent_cny": spent,
        "planned_calls": planned_calls,
        "estimate_cny": est,
        "cap_cny": cap,
    }
    if spent + est > cap + 1e-9:
        raise BudgetExceeded(json.dumps(info))
    return info


def generate(
    provider: ImageProvider,
    draft: Image.Image,
    reference: Image.Image,
    prompt: str,
    seed: int,
    *,
    tag: dict,
    root: Path = D5,
    cap: float = CAP_CNY,
    send=call,
) -> tuple[Image.Image, dict]:
    """One output image, from the cache if this exact request was made before."""
    body = provider.request_body(draft, reference, prompt, seed)
    key = body_key(provider, body)
    cdir = root / "cache" / provider.name
    png, rec_path = cdir / f"{key}.png", cdir / f"{key}.json"
    if png.exists() and rec_path.exists():
        rec = json.loads(rec_path.read_text())
        rec["cached"] = True
        return Image.open(png).convert("RGB"), rec
    ledger = Ledger(root / "ledger.jsonl")
    check_budget(ledger, provider, 1, cap)
    res = send(provider, body)
    cdir.mkdir(parents=True, exist_ok=True)
    res.image.save(png)
    rec = {
        "key": key,
        "provider": provider.name,
        "requested_model": provider.model,
        "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "prompt": prompt,
        "seed": seed,
        "params": {k: v for k, v in _params(body).items()},
        "input_sha256": {"draft": img_sha256(draft), "reference": img_sha256(reference)},
        "output_sha256": img_sha256(res.image),
        "output_size": list(res.image.size),
        "price_cny": provider.price_cny,
        **tag,
        **res.meta,
    }
    rec_path.write_text(json.dumps(rec, indent=2, ensure_ascii=False))
    ledger.add(
        {
            "utc": rec["utc"],
            "provider": provider.name,
            "model": provider.model,
            "key": key,
            "images": 1,
            "cost_cny": provider.price_cny,
            "running_total_cny": round(ledger.spent(provider.name) + provider.price_cny, 4),
            "request_id": rec.get("request_id"),
            **tag,
        }
    )
    rec["cached"] = False
    return res.image, rec


def _params(body: dict) -> dict:
    """Request parameters without prompt and images."""
    if "parameters" in body:
        return dict(body["parameters"])
    return {k: v for k, v in body.items() if k not in ("images", "prompt")}
