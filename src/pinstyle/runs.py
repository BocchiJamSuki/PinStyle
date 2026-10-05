"""Run directories and run records (config, seed, commit, environment, timings)."""

from __future__ import annotations

import json
import platform
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNS_DIR = REPO_ROOT / "runs"


def git_state() -> dict[str, Any]:
    def _git(*args: str) -> str:
        try:
            return subprocess.check_output(["git", *args], cwd=REPO_ROOT, text=True).strip()
        except (OSError, subprocess.CalledProcessError):
            return ""

    return {"commit": _git("rev-parse", "HEAD"), "dirty": bool(_git("status", "--porcelain"))}


def new_run_id(kind: str) -> str:
    return f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}_{kind}"


def new_run_dir(kind: str, root: Path = RUNS_DIR) -> Path:
    d = root / new_run_id(kind)
    d.mkdir(parents=True, exist_ok=False)
    return d


def write_record(run_dir: Path, **fields: Any) -> Path:
    """Write record.json with git state and environment alongside the given fields."""
    record = {
        "run_id": run_dir.name,
        "created_utc": datetime.now(UTC).isoformat(),
        "git": git_state(),
        "python": platform.python_version(),
        **fields,
    }
    path = run_dir / "record.json"
    path.write_text(json.dumps(record, indent=2, default=str))
    return path
