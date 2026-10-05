"""Core demo types (subset of ARCHITECTURE §4.2) and the LocalEngine interface (§5.1)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

from PIL import Image

NormXY = tuple[float, float]  # (x, y) in [0, 1], origin top-left


@dataclass(frozen=True)
class PointPair:
    id: str
    ref_xy: NormXY
    tgt_xy: NormXY
    ref_index: int = 0
    source: Literal["manual", "geometric", "semantic"] = "manual"


@dataclass(frozen=True)
class RegionSettings:
    region_id: str
    pair_ids: tuple[str, ...]
    strength: float = 0.6
    tags: tuple[str, ...] = ()
    negative_tgt_xy: tuple[NormXY, ...] = field(default_factory=tuple)


class LocalEngine(Protocol):
    name: str
    version: str

    def apply(
        self,
        global_output: Image.Image,
        draft: Image.Image,
        references: Sequence[Image.Image],
        point_pairs: Sequence[PointPair],
        region_settings: Sequence[RegionSettings],
        *,
        seed: int,
    ) -> tuple[Image.Image, dict[str, Any]]: ...
