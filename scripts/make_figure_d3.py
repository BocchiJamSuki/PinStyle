"""D3 figure from a `pinstyle run` directory: draft | reference | global-only | PinStyle, plus
zoomed crops of the region (box from the run record). CC BY attribution goes in the caption.

Usage: python scripts/make_figure_d3.py RUN_DIR OUT.png
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
H = 512


def main() -> None:
    run, out = Path(sys.argv[1]), Path(sys.argv[2])
    rec = json.loads((run / "record.json").read_text())
    ref = Image.open(ROOT / "assets/demo" / f"{rec['reference']}.jpg").convert("RGB")
    glob_out = Image.open(run / "global.png").convert("RGB")
    ours = Image.open(run / "pinstyle.png").convert("RGB")
    draft = Image.open(run / "draft.png").convert("RGB").resize(glob_out.size)
    top = [draft, ref, glob_out, ours]
    top = [i.resize((round(i.width * H / i.height), H)) for i in top]
    zooms = []
    for reg in rec["engine_info"]["regions"].values():
        x0, y0, x1, y1 = reg["box"]
        zooms += [i.crop((x0, y0, x1, y1)).resize((H, H)) for i in (draft, glob_out, ours)]
    labels = ["draft", "reference", "global-only", "PinStyle"]
    labels += ["draft (zoom)", "global-only (zoom)", "PinStyle (zoom)"]
    w = max(sum(i.width for i in top), sum(i.width for i in zooms))
    sheet = Image.new("RGB", (w, 2 * H + 40), "white")
    d = ImageDraw.Draw(sheet)
    for y, row in ((0, top), (H + 20, zooms)):
        x = 0
        for i in row:
            sheet.paste(i, (x, y))
            d.text((x + 6, y + 6), labels.pop(0) if labels else "", fill=(255, 255, 0))
            x += i.width
    d.text(
        (6, 2 * H + 24),
        f"run {run.name}; source and reference: David Revoy, Pepper&Carrot, CC BY 4.0",
        fill=(0, 0, 0),
    )
    sheet.save(out)


if __name__ == "__main__":
    main()
