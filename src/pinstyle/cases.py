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


def load_case(case_id: str) -> Case:
    spec = OmegaConf.load(CASES_FILE).cases[case_id]
    src, ref = require(spec.source), require(spec.reference)
    if spec.draft_source != "simulated":
        raise NotImplementedError("only simulated drafts exist for the current sources")
    draft = simulate_draft(Image.open(src.path), mode=spec.draft_mode)
    return Case(case_id, src, ref, draft, spec.draft_source, spec.prompt, list(spec.accessories))


def case_ids() -> list[str]:
    return list(OmegaConf.load(CASES_FILE).cases.keys())
