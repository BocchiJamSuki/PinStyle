from PIL import Image

from pinstyle.app.pairs import (
    PairState,
    clear,
    click_ref,
    click_tgt,
    delete,
    draw_markers,
    from_compact,
    from_table,
    normalize,
    to_compact,
    to_engine,
    to_table,
    undo,
)


def two_pairs() -> PairState:
    s = PairState()
    s = click_tgt(click_ref(s, (0.1, 0.2)), (0.5, 0.6))
    return click_tgt(click_ref(s, (0.3, 0.3)), (0.7, 0.8))


def test_normalize_clamps():
    assert normalize((50, 25), (100, 50)) == (0.5, 0.5)
    assert normalize((150, -5), (100, 50)) == (1.0, 0.0)


def test_pair_needs_reference_first():
    s = click_tgt(PairState(), (0.5, 0.5))
    assert s.pairs == ()


def test_click_order_makes_pairs_with_ids():
    s = two_pairs()
    assert [p.id for p in s.pairs] == ["p1", "p2"]
    assert s.pairs[0].ref_xy == (0.1, 0.2) and s.pairs[0].tgt_xy == (0.5, 0.6)
    assert s.pending_ref is None


def test_reclicking_reference_replaces_pending():
    s = click_ref(click_ref(PairState(), (0.1, 0.1)), (0.2, 0.2))
    s = click_tgt(s, (0.9, 0.9))
    assert s.pairs[0].ref_xy == (0.2, 0.2)


def test_delete_keeps_ids_unique():
    s = delete(two_pairs(), "p1")
    s = click_tgt(click_ref(s, (0.0, 0.0)), (1.0, 1.0))
    assert [p.id for p in s.pairs] == ["p2", "p3"]


def test_clear_keeps_default_tags():
    s = clear(PairState(default_tags="horn"))
    assert s.pairs == () and s.default_tags == "horn"
    assert clear(two_pairs()).pairs == ()


def test_undo_cancels_pending_then_removes_last():
    s = click_ref(two_pairs(), (0.9, 0.9))
    s = undo(s)
    assert s.pending_ref is None and len(s.pairs) == 2
    s = undo(s)
    assert [p.id for p in s.pairs] == ["p1"]
    assert undo(undo(s)).pairs == ()


def test_compact_table_edits_tags_only():
    s = two_pairs()
    rows = to_compact(s)
    assert rows == [["p1", ""], ["p2", ""]]
    rows[1][1] = "white horn hair ornament"
    s2 = from_compact(s, rows)
    assert s2.pairs[1].tags == "white horn hair ornament"
    assert s2.pairs[1].tgt_xy == s.pairs[1].tgt_xy and s2.pairs[0].tags == ""


def test_table_edits_strength_group_tags_and_clamps():
    s = two_pairs()
    rows = to_table(s)
    rows[0][5], rows[0][6], rows[0][7] = 1.7, "rib", "red ribbon"
    rows[1][5], rows[1][6] = "bad", "rib"
    s2 = from_table(s, rows)
    assert s2.pairs[0].strength == 1.0
    assert s2.pairs[1].strength == 0.6
    assert s2.pairs[0].tgt_xy == s.pairs[0].tgt_xy


def test_to_engine_groups_regions():
    s = two_pairs()
    rows = to_table(s)
    rows[0][5], rows[0][6], rows[0][7] = 0.8, "rib", "red ribbon"
    rows[1][5], rows[1][6], rows[1][7] = 0.4, "rib", "red ribbon, bow"
    pairs, regions = to_engine(from_table(s, rows))
    assert len(pairs) == 2
    assert len(regions) == 1
    r = regions[0]
    assert r.pair_ids == ("p1", "p2")
    assert abs(r.strength - 0.6) < 1e-9
    assert r.tags == ("red ribbon", "bow")


def test_ungrouped_pairs_are_separate_regions():
    _, regions = to_engine(two_pairs())
    assert [r.pair_ids for r in regions] == [("p1",), ("p2",)]


def test_markers_draw_without_error():
    img = Image.new("RGB", (64, 48), "white")
    s = click_ref(two_pairs(), (0.5, 0.5))
    assert draw_markers(img, s, "ref").size == (64, 48)
    assert draw_markers(img, s, "tgt").getpixel((32, 28)) != (255, 255, 255)
