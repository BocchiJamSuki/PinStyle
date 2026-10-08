"""Point-pair state for the app (pure logic, unit-tested).

A pair is made by clicking the reference, then the draft. Coordinates are normalized (x, y) in
[0, 1]. Pairs in the same group form one region; a pair with no group is its own region.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from PIL import Image, ImageDraw

from pinstyle.types import NormXY, PointPair, RegionSettings

COLOURS = [
    (230, 25, 75),
    (60, 180, 75),
    (255, 225, 25),
    (0, 130, 200),
    (245, 130, 48),
    (145, 30, 180),
    (70, 240, 240),
    (240, 50, 230),
]
TABLE_HEADERS = ["id", "ref x", "ref y", "draft x", "draft y", "strength", "group", "tags"]


@dataclass(frozen=True)
class Pair:
    id: str
    ref_xy: NormXY
    tgt_xy: NormXY
    strength: float = 0.6
    group: str = ""
    tags: str = ""


@dataclass(frozen=True)
class PairState:
    pairs: tuple[Pair, ...] = ()
    pending_ref: NormXY | None = None
    next_id: int = 1
    default_tags: str = field(default="")


def normalize(px: tuple[float, float], size: tuple[int, int]) -> NormXY:
    w, h = size
    return (min(max(px[0] / w, 0.0), 1.0), min(max(px[1] / h, 0.0), 1.0))


def click_ref(state: PairState, xy: NormXY) -> PairState:
    """Start (or restart) a pair on the reference."""
    return replace(state, pending_ref=xy)


def click_tgt(state: PairState, xy: NormXY) -> PairState:
    """Complete the pending pair on the draft. Ignored if no reference point is pending."""
    if state.pending_ref is None:
        return state
    p = Pair(f"p{state.next_id}", state.pending_ref, xy, tags=state.default_tags)
    return replace(state, pairs=(*state.pairs, p), pending_ref=None, next_id=state.next_id + 1)


def delete(state: PairState, pair_id: str) -> PairState:
    return replace(state, pairs=tuple(p for p in state.pairs if p.id != pair_id))


def clear(state: PairState) -> PairState:
    return PairState()


def to_table(state: PairState) -> list[list]:
    return [
        [
            p.id,
            round(p.ref_xy[0], 3),
            round(p.ref_xy[1], 3),
            round(p.tgt_xy[0], 3),
            round(p.tgt_xy[1], 3),
            p.strength,
            p.group,
            p.tags,
        ]
        for p in state.pairs
    ]


def from_table(state: PairState, rows: list[list]) -> PairState:
    """Apply edits to strength, group and tags from the table. Coordinates and ids are not
    editable; rows whose id is unknown are ignored."""
    by_id = {str(r[0]): r for r in rows if r and r[0] not in (None, "")}
    out = []
    for p in state.pairs:
        r = by_id.get(p.id)
        if r is None:
            out.append(p)
            continue
        try:
            strength = min(max(float(r[5]), 0.0), 1.0)
        except (TypeError, ValueError):
            strength = p.strength
        out.append(
            replace(p, strength=strength, group=str(r[6] or "").strip(), tags=str(r[7] or ""))
        )
    return replace(state, pairs=tuple(out))


def to_engine(state: PairState) -> tuple[list[PointPair], list[RegionSettings]]:
    """Point pairs and regions for LocalEngine.apply. A region's strength is the mean of its
    pairs' strengths; its tags are the union, in order."""
    pairs = [PointPair(p.id, p.ref_xy, p.tgt_xy) for p in state.pairs]
    groups: dict[str, list[Pair]] = {}
    for p in state.pairs:
        groups.setdefault(p.group or p.id, []).append(p)
    regions = []
    for gid, members in groups.items():
        tags: list[str] = []
        for m in members:
            for t in (x.strip() for x in m.tags.split(",")):
                if t and t not in tags:
                    tags.append(t)
        strength = sum(m.strength for m in members) / len(members)
        regions.append(
            RegionSettings(f"r_{gid}", tuple(m.id for m in members), strength, tuple(tags))
        )
    return pairs, regions


def draw_markers(img: Image.Image, state: PairState, side: str) -> Image.Image:
    """Numbered markers for side "ref" or "tgt"; the pending reference point is hollow."""
    out = img.convert("RGB").copy()
    d = ImageDraw.Draw(out)
    w, h = out.size
    r = max(6, round(min(w, h) * 0.012))
    for i, p in enumerate(state.pairs):
        x, y = p.ref_xy if side == "ref" else p.tgt_xy
        c = COLOURS[i % len(COLOURS)]
        cx, cy = x * w, y * h
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=c, outline=(0, 0, 0), width=2)
        d.text((cx + r + 2, cy - r), p.id, fill=c, stroke_width=2, stroke_fill=(0, 0, 0))
    if side == "ref" and state.pending_ref is not None:
        cx, cy = state.pending_ref[0] * w, state.pending_ref[1] * h
        d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(255, 255, 255), width=3)
    return out
