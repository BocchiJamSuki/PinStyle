import json
import socket

import pytest

from pinstyle.runs import new_run_dir, write_record


def test_run_record_roundtrip(tmp_path):
    d = new_run_dir("unit", root=tmp_path)
    p = write_record(d, seed=1, config={"a": 1})
    rec = json.loads(p.read_text())
    assert rec["run_id"] == d.name
    assert rec["seed"] == 1
    assert "commit" in rec["git"]


def test_sockets_are_blocked():
    with pytest.raises(Exception):
        socket.create_connection(("example.com", 80), timeout=2)
