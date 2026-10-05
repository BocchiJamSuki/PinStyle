"""Make a labelled contact sheet from a list of image URLs or paths (for D1 shortlisting).

Usage: python scripts/contact_sheet.py OUT.jpg ITEM [ITEM ...]   (ITEM = URL or path)
Downloads go to the directory of OUT (gitignored local_runs/ on the laptop).
"""

from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw

THUMB = 360


def load(item: str, cache: Path) -> Image.Image:
    if item.startswith("http"):
        dest = cache / item.rsplit("/", 1)[-1]
        if not dest.exists():
            urllib.request.urlretrieve(item, dest)
        item = str(dest)
    return Image.open(item).convert("RGB")


def main() -> None:
    out = Path(sys.argv[1])
    items = sys.argv[2:]
    out.parent.mkdir(parents=True, exist_ok=True)
    cols = 4
    rows = (len(items) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * THUMB, rows * (THUMB + 24)), "white")
    draw = ImageDraw.Draw(sheet)
    for i, item in enumerate(items):
        im = load(item, out.parent)
        im.thumbnail((THUMB, THUMB))
        x, y = (i % cols) * THUMB, (i // cols) * (THUMB + 24)
        sheet.paste(im, (x + (THUMB - im.width) // 2, y))
        draw.text((x + 4, y + THUMB + 4), f"{i}: {Path(item).name[:48]}", fill="black")
    sheet.save(out, quality=90)
    print(out)


if __name__ == "__main__":
    main()
