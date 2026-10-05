"""MANIFEST.csv checker (ADR-0007): only approved CC0 / CC BY works by verified authors,
never AI-generated images, may be used in the demo or sent to external services."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = REPO_ROOT / "assets" / "demo" / "MANIFEST.csv"
ALLOWED_LICENSES = {"CC0-1.0", "CC-BY-2.0", "CC-BY-3.0", "CC-BY-4.0"}
REQUIRED = ("id", "file", "author", "license", "source_url", "authorship_evidence",
            "attribution", "ai_generated", "status", "approved_by")


class ManifestError(ValueError):
    pass


@dataclass(frozen=True)
class Asset:
    id: str
    path: Path
    row: dict[str, str]

    @property
    def attribution(self) -> str:
        return self.row["attribution"]


def load(manifest: Path = DEFAULT_MANIFEST) -> dict[str, dict[str, str]]:
    with manifest.open(encoding="utf8", newline="") as f:
        rows = list(csv.DictReader(f))
    return {r["id"]: r for r in rows}


def check_row(row: dict[str, str]) -> None:
    missing = [k for k in REQUIRED if not row.get(k, "").strip()]
    if missing:
        raise ManifestError(f"{row.get('id')}: missing {missing}")
    if row["license"] not in ALLOWED_LICENSES:
        raise ManifestError(f"{row['id']}: license {row['license']} not CC0/CC BY")
    if row["ai_generated"].strip().lower() != "false":
        raise ManifestError(f"{row['id']}: AI-generated images are for debugging only")
    if row["status"] != "approved":
        raise ManifestError(f"{row['id']}: not approved (status={row['status']})")


def require(asset_id: str, manifest: Path = DEFAULT_MANIFEST) -> Asset:
    """Return an approved asset or raise. Use before any demo use or external upload."""
    rows = load(manifest)
    if asset_id not in rows:
        raise ManifestError(f"{asset_id}: not in manifest")
    row = rows[asset_id]
    check_row(row)
    return Asset(asset_id, manifest.parent / row["file"], row)
