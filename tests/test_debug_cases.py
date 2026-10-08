import pytest
from PIL import Image

from pinstyle import cases


def setup_debug(tmp_path, monkeypatch, case_id="debug_x"):
    Image.new("RGB", (64, 80), "white").save(tmp_path / "d.png")
    Image.new("RGB", (64, 80), "red").save(tmp_path / "r.png")
    (tmp_path / "cases.yaml").write_text(
        f"cases:\n  {case_id}:\n    draft_file: d.png\n    reference_file: r.png\n"
        "    prompt: p\n    accessories: [brooch]\n"
    )
    monkeypatch.setattr(cases, "DEBUG_DIR", tmp_path)
    monkeypatch.setattr(cases, "DEBUG_CASES_FILE", tmp_path / "cases.yaml")


def test_debug_case_loads_without_manifest_and_is_marked(tmp_path, monkeypatch):
    setup_debug(tmp_path, monkeypatch)
    assert "debug_x" in cases.case_ids()
    c = cases.load_case("debug_x")
    assert c.draft.size == (64, 80) and c.draft_source == "provided"
    assert c.reference.id.startswith("debug:") and "not for demo" in c.reference.attribution


def test_debug_case_id_needs_prefix(tmp_path, monkeypatch):
    setup_debug(tmp_path, monkeypatch, case_id="sneaky")
    with pytest.raises(ValueError):
        cases.load_case("sneaky")
