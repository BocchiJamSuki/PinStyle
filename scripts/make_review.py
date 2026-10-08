"""D5 blind review set: shuffle every method's outputs per case, hide method names, and write a
local HTML form. The reviewer saves labels as JSON; `--reveal LABELS.json` joins them with the
hidden key and writes the tables (report inputs).

    python scripts/make_review.py              # builds local_runs/review/index.html
    python scripts/make_review.py --reveal local_runs/review/review_labels.json

Sources (`configs/review.yaml`): our runs (global.png = global-only, pinstyle.png = PinStyle)
and the cached external outputs in runs/d5/outputs/<provider>/<case>_a<n>.png.
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import random
import shutil
import sys
from pathlib import Path

from omegaconf import OmegaConf

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "local_runs" / "review"
TAXONOMY = ["lost detail", "misplaced detail", "style drift", "structure change",
            "not controllable"]


def collect(cfg) -> list[dict]:
    items = []
    for case, spec in cfg.cases.items():
        for a, run in enumerate(spec.our_runs, start=1):
            d = ROOT / run
            items.append({"case": case, "method": "global-only", "attempt": a,
                          "src": d / "global.png", "run": d.name})
            items.append({"case": case, "method": "PinStyle", "attempt": a,
                          "src": d / "pinstyle.png", "run": d.name})
        for prov in cfg.providers:
            for a in range(1, cfg.attempts + 1):
                items.append({"case": case, "method": prov, "attempt": a,
                              "src": ROOT / f"runs/d5/outputs/{prov}/{case}_a{a}.png",
                              "run": f"runs/d5 {prov} {case} a{a}"})
    return items


def build(cfg) -> None:
    items = collect(cfg)
    rng = random.Random(cfg.shuffle_seed)
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "img").mkdir(parents=True)
    key = {}
    cases_html = []
    for case, spec in cfg.cases.items():
        its = [i for i in items if i["case"] == case]
        rng.shuffle(its)
        cards = []
        for n, it in enumerate(its, start=1):
            iid = f"{case}-{n:02d}"
            shutil.copy(it["src"], OUT / "img" / f"{iid}.png")
            key[iid] = {k: str(v) for k, v in it.items()}
            boxes = "".join(
                f'<label><input type="checkbox" name="{iid}|{t}"> {t}</label>' for t in TAXONOMY
            )
            cards.append(
                f'<div class="card"><h3>{iid}</h3><img src="img/{iid}.png">'
                f'<div><label><input type="radio" name="{iid}|ok" value="yes"> acceptable</label>'
                f'<label><input type="radio" name="{iid}|ok" value="no"> not acceptable</label>'
                f"</div><div>{boxes}</div>"
                f'<textarea name="{iid}|note" placeholder="note"></textarea></div>'
            )
        for role, rel in (("draft", spec.draft), ("reference", spec.reference)):
            shutil.copy(ROOT / rel, OUT / "img" / f"{case}-{role}.png")
        cases_html.append(
            f"<h2>{html.escape(case)}</h2><p>{html.escape(spec.question)}</p>"
            f'<div class="ctx"><figure><img src="img/{case}-draft.png"><figcaption>draft'
            f'</figcaption></figure><figure><img src="img/{case}-reference.png"><figcaption>'
            f"reference</figcaption></figure></div>" + "".join(cards)
        )
    (ROOT / "runs" / "d5").mkdir(parents=True, exist_ok=True)
    (ROOT / "runs/d5/review_key.json").write_text(json.dumps(key, indent=2))
    page = PAGE.replace("{{BODY}}", "".join(cases_html))
    (OUT / "index.html").write_text(page, encoding="utf-8")
    print(f"{len(key)} items -> {OUT / 'index.html'} (key: runs/d5/review_key.json)")


def reveal(labels_path: Path) -> None:
    key = json.loads((ROOT / "runs/d5/review_key.json").read_text())
    labels = json.loads(labels_path.read_text())
    rows = []
    for iid, k in key.items():
        lab = labels.get(iid, {})
        rows.append({"item": iid, "case": k["case"], "method": k["method"],
                     "attempt": int(k["attempt"]), "run": k["run"],
                     "acceptable": lab.get("ok", ""),
                     **{t: int(t in lab.get("tags", [])) for t in TAXONOMY},
                     "note": lab.get("note", "")})
    rows.sort(key=lambda r: (r["case"], r["method"], r["attempt"]))
    with (ROOT / "runs/d5/review_revealed.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print("written runs/d5/review_revealed.csv")


PAGE = """<!doctype html><html><head><meta charset="utf-8"><title>PinStyle blind review</title>
<style>body{font-family:sans-serif;margin:16px;background:#fafafa;color:#222}
.card{display:inline-block;vertical-align:top;width:340px;margin:6px;padding:8px;
background:#fff;border:1px solid #ccc}.card img{width:100%}.card label{display:block;
font-size:13px}textarea{width:100%}.ctx figure{display:inline-block;width:300px;margin:6px}
.ctx img{width:100%}button{font-size:16px;padding:8px 16px;position:sticky;top:8px}</style>
</head><body><h1>Blind review</h1><p>Method names are hidden and order is shuffled. For
each image: acceptable or not, and any failure types. A misrendered accessory (wrong colour,
material or shape) counts as a detail failure. Then press Save and send the JSON file.</p>
<button onclick="save()">Save labels (JSON)</button>{{BODY}}
<script>function save(){const o={};document.querySelectorAll('input,textarea').forEach(e=>{
const [id,f]=e.name.split('|');o[id]=o[id]||{tags:[]};
if(f==='ok'&&e.checked)o[id].ok=e.value;else if(f==='note')o[id].note=e.value;
else if(e.type==='checkbox'&&e.checked)o[id].tags.push(f);});
const a=document.createElement('a');a.href=URL.createObjectURL(new Blob(
[JSON.stringify(o,null,1)],{type:'application/json'}));a.download='review_labels.json';
a.click();}</script></body></html>"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reveal", type=Path)
    args = ap.parse_args()
    cfg = OmegaConf.load(ROOT / "configs" / "review.yaml")
    reveal(args.reveal) if args.reveal else build(cfg)


if __name__ == "__main__":
    sys.exit(main())
