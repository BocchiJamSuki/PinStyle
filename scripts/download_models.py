"""Download the demo models (network). Records the resolved revision and sha256 of every file
in models/MANIFEST.json. Run on the GPU server: python scripts/download_models.py
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from huggingface_hub import HfApi, snapshot_download
from omegaconf import OmegaConf

ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 24), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    cfg = OmegaConf.load(ROOT / "configs" / "demo.yaml")
    models_dir = ROOT / cfg.paths.models
    manifest: dict = {}
    api = HfApi()
    for key, spec in cfg.models.items():
        revision = api.model_info(spec.repo).sha
        local = models_dir / key
        snapshot_download(spec.repo, revision=revision, allow_patterns=list(spec.allow),
                          local_dir=local)
        files = {str(p.relative_to(local)).replace("\\", "/"): sha256(p)
                 for p in sorted(local.rglob("*")) if p.is_file() and ".cache" not in p.parts}
        manifest[key] = {"repo": spec.repo, "revision": revision, "files": files}
        print(f"{key}: {spec.repo}@{revision[:10]} ({len(files)} files)", flush=True)
    (models_dir / "MANIFEST.json").write_text(json.dumps(manifest, indent=2))
    print("MANIFEST written")


if __name__ == "__main__":
    main()
