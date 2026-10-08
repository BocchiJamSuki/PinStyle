"""D5 report, rebuilt from logs alone: the revealed blind-review labels
(runs/d5/review_revealed.csv), the review key and the spending ledger.

    python scripts/make_report.py

Writes runs/d5/report/{report.md, summary.csv, grid_<case>.png}. Tables only count labels;
nothing is inferred. CC BY attribution is in every caption.
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
D5 = ROOT / "runs" / "d5"
OUT = D5 / "report"
TAX = ["lost detail", "misplaced detail", "style drift", "structure change", "not controllable"]
METHODS = ["global-only", "PinStyle", "tencent", "alibaba"]
MODEL = {
    "global-only": "SDXL + MistoLine + IP-Adapter Plus (ours)",
    "PinStyle": "global + Engine A, 1 point pair (ours)",
    "tencent": "Tencent TokenHub hy-image-v3",
    "alibaba": "Alibaba Model Studio qwen-image-edit-plus-2025-12-15",
}
ATTRIB = "Source images: David Revoy, Pepper&Carrot, CC BY 4.0."
TH = 300


REVIEWERS = {
    "owner": ("review_revealed.csv", "the project owner, blind"),
    "developer": (
        "review_revealed_developer.csv",
        "Claude Code (developer), NOT blind: it knew the method of every item and built "
        "PinStyle. Its own criteria: the draft decides content and design colours (hard); "
        "the reference decides rendering (hard); the reference's version of the accessory "
        "is a bonus",
    ),
}


def load_rows(name: str = "review_revealed.csv") -> list[dict]:
    with (D5 / name).open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def grid(case: str, rows: list[dict], key: dict) -> Path:
    by = {(r["method"], int(r["attempt"])): r for r in rows if r["case"] == case}
    sheet = Image.new("RGB", (TH * 3 + 160, TH * len(METHODS) + 30), "white")
    d = ImageDraw.Draw(sheet)
    for y, m in enumerate(METHODS):
        d.text((6, y * TH + TH // 2), m, fill=(0, 0, 0))
        for a in (1, 2, 3):
            r = by[(m, a)]
            im = Image.open(key[r["item"]]["src"]).convert("RGB")
            im.thumbnail((TH, TH))
            x0, y0 = 160 + (a - 1) * TH, y * TH
            sheet.paste(im, (x0, y0))
            ok = r["acceptable"] == "yes"
            d.rectangle((x0, y0, x0 + 70, y0 + 16), fill=(0, 140, 0) if ok else (180, 0, 0))
            d.text((x0 + 3, y0 + 2), f"a{a} {'OK' if ok else 'NO'}", fill=(255, 255, 255))
    d.text((6, TH * len(METHODS) + 8), f"{case}. {ATTRIB}", fill=(0, 0, 0))
    out = OUT / f"grid_{case}.png"
    sheet.save(out)
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = load_rows()
    key = json.loads((D5 / "review_key.json").read_text(encoding="utf-8"))
    cases = sorted({r["case"] for r in rows})
    summary = []
    for case in cases:
        grid(case, rows, key)
        for m in METHODS:
            rs = sorted(
                (r for r in rows if r["case"] == case and r["method"] == m),
                key=lambda r: int(r["attempt"]),
            )
            ok = [int(r["attempt"]) for r in rs if r["acceptable"] == "yes"]
            summary.append(
                {
                    "case": case,
                    "method": m,
                    "model": MODEL[m],
                    "attempts": len(rs),
                    "acceptable": len(ok),
                    "attempts_until_acceptable": ok[0] if ok else f"> {len(rs)}",
                    **{t: sum(int(r[t]) for r in rs) for t in TAX},
                }
            )
    with (OUT / "summary.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(summary[0]))
        w.writeheader()
        w.writerows(summary)

    spent = defaultdict(float)
    ledger = [json.loads(x) for x in (D5 / "ledger.jsonl").read_text().splitlines() if x]
    for e in ledger:
        spent[e["provider"]] += e["cost_cny"]
    notes = defaultdict(set)
    for r in rows:
        if r["note"].strip():
            notes[(r["case"], r["method"])].add(r["note"].strip())

    md = [
        "# D5 comparison report",
        "",
        "Built by `scripts/make_report.py` from `runs/d5/review_revealed.csv`, "
        "`runs/d5/review_key.json` and `runs/d5/ledger.jsonl`.",
        "",
        "- Reviewer: the project owner. Blind: the 24 outputs were shuffled per case and "
        "the method names hidden until the labels were saved.",
        "- Attempts: up to 3 per method and case. For the services, attempts 2–3 name the "
        "accessory and its place. For our methods, attempts are seeds 0–2 of the same "
        "settings.",
        f"- Spend: Tencent CNY {spent['tencent']:.2f}, Alibaba CNY {spent['alibaba']:.2f} "
        "(each including one trial call; cap CNY 4.00).",
        "",
    ]
    for case in cases:
        md += [
            f"## {case}",
            "",
            "| Method | Acceptable | Attempts until acceptable | "
            + " | ".join(TAX)
            + " | Reviewer notes |",
            "|---|---|---|" + "---|" * len(TAX) + "---|",
        ]
        for s in (s for s in summary if s["case"] == case):
            n = "; ".join(sorted(notes[(case, s["method"])])) or ""
            md.append(
                f"| {s['method']} ({s['model']}) | {s['acceptable']}/{s['attempts']} | "
                f"{s['attempts_until_acceptable']} | "
                + " | ".join(str(s[t]) for t in TAX)
                + f" | {n} |"
            )
        md += ["", f"Grid: `runs/d5/report/grid_{case}.png`. {ATTRIB}", ""]
    md += extra_reviewers(rows, cases)
    (OUT / "report.md").write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md))


def extra_reviewers(owner_rows: list[dict], cases: list[str]) -> list[str]:
    """One acceptability table per reviewer, side by side, plus per-item agreement with the
    owner. Reviews are never merged."""
    reviews = {"owner": owner_rows}
    for name, (fname, _) in REVIEWERS.items():
        if name != "owner" and (D5 / fname).exists():
            reviews[name] = load_rows(fname)
    if len(reviews) == 1:
        return []
    md = ["## Reviewers compared", ""]
    md += [f"- **{n}**: {REVIEWERS[n][1]}." for n in reviews]
    md += [
        "",
        "| Case | Method | " + " | ".join(reviews) + " |",
        "|---|---|" + "---|" * len(reviews),
    ]
    for case in cases:
        for m in METHODS:
            cells = []
            for rows in reviews.values():
                rs = [r for r in rows if r["case"] == case and r["method"] == m]
                cells.append(f"{sum(r['acceptable'] == 'yes' for r in rs)}/{len(rs)}")
            md.append(f"| {case} | {m} | " + " | ".join(cells) + " |")
    own = {r["item"]: r["acceptable"] for r in owner_rows}
    for n, rows in reviews.items():
        if n != "owner":
            agree = sum(own.get(r["item"]) == r["acceptable"] for r in rows)
            md += ["", f"Item-level agreement, owner vs {n}: {agree}/{len(rows)}."]
            notes = sorted({(r["case"], r["method"], r["note"]) for r in rows if r["note"]})
            md += ["", f"{n} notes:", ""]
            md += [f"- {c} / {m}: {t}" for c, m, t in notes]
    return md + [""]


if __name__ == "__main__":
    main()
