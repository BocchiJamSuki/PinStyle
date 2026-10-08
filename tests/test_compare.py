import json

import pytest
from PIL import Image

from pinstyle.compare import runner
from pinstyle.compare.providers import (
    PROVIDERS,
    Result,
    _redact_urls,
    fit_size,
    mask_secret,
    scrub,
)


def imgs():
    return Image.new("RGB", (704, 1024), "white"), Image.new("RGB", (900, 600), "red")


def fake_send(counter):
    def send(provider, body):
        counter.append(provider.name)
        return Result(Image.new("RGB", (64, 64), "blue"), {"request_id": "r1"})

    return send


def test_mask_and_scrub_hide_keys():
    k = "sk-ABCDEFGHIJKLMNOPQRSTUVWXYZ123456"
    assert k not in mask_secret(k)
    assert k not in scrub(f"bad key {k} here", [k])


def test_redact_urls():
    out = _redact_urls({"data": [{"url": "https://x?sig=1"}], "content": [{"image": "https://y"}]})
    assert "sig" not in json.dumps(out) and "https://y" not in json.dumps(out)


def test_sizes_respect_provider_limits():
    w, h = fit_size(Image.new("RGB", (704, 1024)), 1024, 1024 * 1024)
    assert w * h <= 1024 * 1024 and max(w, h) <= 1024
    w, h = fit_size(Image.new("RGB", (2000, 1000)), 1024, 1024 * 1024)
    assert w * h <= 1024 * 1024 and min(w, h) >= 512


def test_alibaba_puts_draft_last():
    d, r = imgs()
    body = PROVIDERS["alibaba"].request_body(d, r, "p", 1)
    content = body["input"]["messages"][0]["content"]
    assert body["parameters"]["n"] == 1 and "text" in content[-1]
    assert content[1]["image"] != content[0]["image"]


def test_cache_prevents_repeat_calls_and_ledger_records(tmp_path):
    d, r = imgs()
    calls = []
    p = PROVIDERS["tencent"]
    _, rec1 = runner.generate(p, d, r, "prompt", 1, tag={"case": "c"}, root=tmp_path,
                              send=fake_send(calls))
    _, rec2 = runner.generate(p, d, r, "prompt", 1, tag={"case": "c"}, root=tmp_path,
                              send=fake_send(calls))
    assert calls == ["tencent"]
    assert rec1["cached"] is False and rec2["cached"] is True
    led = runner.Ledger(tmp_path / "ledger.jsonl")
    assert led.spent("tencent") == pytest.approx(0.2)
    text = (tmp_path / "ledger.jsonl").read_text()
    assert "data:image" not in text and "Bearer" not in text


def test_budget_guard_blocks_before_sending(tmp_path):
    d, r = imgs()
    calls = []
    p = PROVIDERS["alibaba"]
    for i in range(2):
        runner.generate(p, d, r, f"p{i}", 1, tag={}, root=tmp_path, cap=0.4,
                        send=fake_send(calls))
    with pytest.raises(runner.BudgetExceeded):
        runner.generate(p, d, r, "p3", 1, tag={}, root=tmp_path, cap=0.4,
                        send=fake_send(calls))
    assert len(calls) == 2
