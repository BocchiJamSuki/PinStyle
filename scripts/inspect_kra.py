"""List the layers of a Krita .kra file (or a .zip containing one) and optionally export
the merged image and named layers as PNG.

Usage: python scripts/inspect_kra.py FILE [--out DIR] [--export NAME ...]
"""

from __future__ import annotations

import argparse
import io
import re
import zipfile
from pathlib import Path


def open_kra(path: Path) -> zipfile.ZipFile:
    z = zipfile.ZipFile(path)
    if "maindoc.xml" in z.namelist():
        return z
    inner = next(n for n in z.namelist() if n.endswith(".kra"))
    return zipfile.ZipFile(io.BytesIO(z.read(inner)))


def layers(kra: zipfile.ZipFile) -> list[dict[str, str]]:
    xml = kra.read("maindoc.xml").decode("utf8")
    out = []
    for m in re.finditer(r"<layer [^>]*>", xml):
        attrs = dict(re.findall(r'(\w+)="([^"]*)"', m.group(0)))
        out.append({k: attrs.get(k, "") for k in ("name", "nodetype", "visible", "filename")})
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("file", type=Path)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    kra = open_kra(args.file)
    for layer in layers(kra):
        print(f"{layer['name']!r:40} {layer['nodetype']:16} visible={layer['visible']}")
    if args.out:
        args.out.mkdir(parents=True, exist_ok=True)
        for name in kra.namelist():
            if name in ("mergedimage.png", "preview.png"):
                (args.out / name).write_bytes(kra.read(name))
                print("exported", name)


if __name__ == "__main__":
    main()
