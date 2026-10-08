"""Demo cases: approved source + reference images (via the manifest checker) and the draft."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from omegaconf import OmegaConf
from PIL import Image

from pinstyle.lineart import simulate_draft
from pinstyle.manifest import Asset, require

REPO_ROOT = Path(__file__).resolve().parents[2]
CASES_FILE = REPO_ROOT / "configs" / "cases.yaml"
# Optional, gitignored debug cases (unverified or AI-generated images; never demo/report).
DEBUG_DIR = REPO_ROOT / "assets" / "debug"
DEBUG_CASES_FILE = DEBUG_DIR / "cases.yaml"


@dataclass
class Case:
    id: str
    source: Asset
    reference: Asset
    draft: Image.Image
    draft_source: str
    prompt: str
    accessories: list[str]

    def source_image(self) -> Image.Image:
        return Image.open(self.source.path).convert("RGB")

    def reference_image(self) -> Image.Image:
        return Image.open(self.reference.path).convert("RGB")


def _debug_specs() -> dict:
    if not DEBUG_CASES_FILE.exists():
        return {}
    return dict(OmegaConf.load(DEBUG_CASES_FILE).get("cases") or {})


def _debug_asset(rel: str) -> Asset:
    note = "debug image, unverified provenance (assets/debug); not for demo or reports"
    return Asset(f"debug:{rel}", DEBUG_DIR / rel, {"attribution": note})


def load_case(case_id: str) -> Case:
    debug = _debug_specs()
    if case_id in debug:
        spec = debug[case_id]
        if not case_id.startswith("debug_"):
            raise ValueError(f"debug case ids must start with 'debug_': {case_id}")
        src, ref = _debug_asset(spec.draft_file), _debug_asset(spec.reference_file)
        draft = Image.open(src.path).convert("RGB")
        if spec.get("draft_source", "provided") == "simulated":
            draft = simulate_draft(draft, mode=spec.get("draft_mode", "flat"))
        return Case(
            case_id,
            src,
            ref,
            draft,
            spec.get("draft_source", "provided"),
            spec.prompt,
            list(spec.get("accessories", [])),
        )
    spec = OmegaConf.load(CASES_FILE).cases[case_id]
    src, ref = require(spec.source), require(spec.reference)
    if spec.draft_source != "simulated":
        raise NotImplementedError("only simulated drafts exist for the current sources")
    draft = simulate_draft(Image.open(src.path), mode=spec.draft_mode)
    return Case(case_id, src, ref, draft, spec.draft_source, spec.prompt, list(spec.accessories))


def case_ids() -> list[str]:
    return list(OmegaConf.load(CASES_FILE).cases.keys()) + list(_debug_specs())
