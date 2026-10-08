"""External image services for the D5 comparison (ADR-0004, ADR-0009). Network access.

Each provider implements `ImageProvider`: one output image per call from the draft, the style
reference and a prompt. Keys come from environment variables and are never logged; use
`mask_secret` for anything printed or stored.
"""

from __future__ import annotations

import base64
import io
import os
import time
from dataclasses import dataclass
from typing import Any, Protocol

from PIL import Image


def mask_secret(s: str | None) -> str:
    if not s:
        return "<unset>"
    return f"{s[:5]}…{s[-4:]}" if len(s) > 12 else "***"


def scrub(text: str, secrets: list[str]) -> str:
    for s in secrets:
        if s:
            text = text.replace(s, mask_secret(s))
    return text


def png_data_uri(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def fit_size(img: Image.Image, long_side: int, max_area: int | None, step: int = 16):
    w, h = img.size
    s = long_side / max(w, h)
    if max_area and (w * s) * (h * s) > max_area:
        s = (max_area / (w * h)) ** 0.5
    return max(512, int(w * s) // step * step), max(512, int(h * s) // step * step)


@dataclass
class Result:
    image: Image.Image
    meta: dict[str, Any]  # response model field, request id, usage, latency, endpoint


class ImageProvider(Protocol):
    name: str
    model: str
    endpoint: str
    price_cny: float  # per output image, from the official price page (THIRD_PARTY §0.3)
    key_env: str

    def request_body(
        self, draft: Image.Image, reference: Image.Image, prompt: str, seed: int
    ) -> dict: ...

    def parse(self, resp: dict) -> tuple[str, dict]: ...  # (image url, meta)


def call(provider: ImageProvider, body: dict, timeout: int = 300) -> Result:
    import requests

    key = os.environ.get(provider.key_env)
    if not key:
        raise RuntimeError(f"{provider.key_env} is not set (.env)")
    t0 = time.perf_counter()
    r = requests.post(
        provider.endpoint,
        json=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        timeout=timeout,
    )
    latency = round(time.perf_counter() - t0, 2)
    if r.status_code != 200:
        raise RuntimeError(f"{provider.name} HTTP {r.status_code}: {scrub(r.text[:800], [key])}")
    resp = r.json()
    url, meta = provider.parse(resp)
    img = Image.open(io.BytesIO(requests.get(url, timeout=120).content)).convert("RGB")
    meta.update(
        latency_s=latency,
        endpoint=provider.endpoint,
        sdk=f"requests {requests.__version__}",
        response=_redact_urls(resp),
    )
    return Result(img, meta)


def _redact_urls(obj):
    """Drop signed result URLs (they carry access tokens) from the stored response."""
    if isinstance(obj, dict):
        return {
            k: ("<url>" if k in ("url", "image") and isinstance(v, str) else _redact_urls(v))
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [_redact_urls(v) for v in obj]
    return obj


class TencentHunyuan:
    """Tencent Cloud TokenHub, Hy-Image-3.0 (0-3 reference images; area <= 1024^2)."""

    name = "tencent"
    model = "hy-image-v3"
    endpoint = "https://tokenhub.tencentmaas.com/v1/wand/hunyuan-image/v3-generation"
    price_cny = 0.2
    key_env = "TENCENT_HUNYUAN_API_KEY"

    def request_body(self, draft, reference, prompt, seed):
        w, h = fit_size(draft, 1024, 1024 * 1024)
        return {
            "model": self.model,
            "prompt": prompt,
            "images": [png_data_uri(draft), png_data_uri(reference)],
            "size": f"{w}x{h}",
            "seed": max(1, seed),
            "revise": False,
        }

    def parse(self, resp):
        return resp["data"][0]["url"], {
            "response_model": resp.get("model"),
            "request_id": resp.get("request_id") or resp.get("id"),
            "usage": resp.get("tokenhub_usage"),
        }


class AlibabaQwenEdit:
    """Alibaba Cloud Model Studio (Beijing), Qwen-Image-Edit-Plus dated snapshot.
    The output aspect ratio follows the last input image, so the draft goes last."""

    name = "alibaba"
    model = "qwen-image-edit-plus-2025-12-15"
    endpoint = (
        "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
    )
    price_cny = 0.2
    key_env = "DASHSCOPE_API_KEY"
    draft_last = True

    def request_body(self, draft, reference, prompt, seed):
        w, h = fit_size(draft, 1024, None)
        return {
            "model": self.model,
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"image": png_data_uri(reference)},
                            {"image": png_data_uri(draft)},
                            {"text": prompt},
                        ],
                    }
                ]
            },
            "parameters": {
                "n": 1,
                "size": f"{w}*{h}",
                "seed": seed,
                "watermark": False,
                "prompt_extend": False,
                "negative_prompt": " ",
            },
        }

    def parse(self, resp):
        content = resp["output"]["choices"][0]["message"]["content"]
        url = next(c["image"] for c in content if "image" in c)
        return url, {
            "response_model": resp.get("model"),
            "request_id": resp.get("request_id"),
            "usage": resp.get("usage"),
        }


PROVIDERS: dict[str, ImageProvider] = {p.name: p for p in (TencentHunyuan(), AlibabaQwenEdit())}
