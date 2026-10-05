import pytest

from pinstyle.manifest import ManifestError, check_row, load, require

GOOD = {
    "id": "x", "file": "x.jpg", "author": "A", "license": "CC-BY-4.0", "source_url": "u",
    "authorship_evidence": "e", "attribution": "a", "ai_generated": "false",
    "status": "approved", "approved_by": "claude (delegated by owner)",
}


def test_real_manifest_rows_pass():
    for row in load().values():
        check_row(row)


@pytest.mark.parametrize("field,value", [
    ("license", "CC-BY-NC-4.0"), ("ai_generated", "true"), ("status", "pending"), ("author", ""),
])
def test_bad_rows_rejected(field, value):
    with pytest.raises(ManifestError):
        check_row({**GOOD, field: value})


def test_unknown_id_rejected():
    with pytest.raises(ManifestError):
        require("does_not_exist")
