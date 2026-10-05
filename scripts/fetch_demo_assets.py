"""Download the approved demo images listed in assets/demo/MANIFEST.csv (network) and store
them resized to a long side of 1536 px. Every row is checked with the manifest checker first.
"""

from __future__ import annotations

import io
import sys
import urllib.request
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pinstyle.manifest import DEFAULT_MANIFEST, load, require  # noqa: E402

LONG_SIDE = 1536


def main() -> None:
    for asset_id, row in load().items():
        asset = require(asset_id)
        if asset.path.exists():
            print(f"skip {asset_id}")
            continue
        req = urllib.request.Request(row["source_url"], headers={"User-Agent": "PinStyle-demo"})
        data = urllib.request.urlopen(req, timeout=300).read()
        im = Image.open(io.BytesIO(data)).convert("RGB")
        im.thumbnail((LONG_SIDE, LONG_SIDE), Image.Resampling.LANCZOS)
        im.save(asset.path, quality=92)
        print(f"{asset_id}: {im.size} -> {asset.path.relative_to(DEFAULT_MANIFEST.parent)}")


if __name__ == "__main__":
    main()
