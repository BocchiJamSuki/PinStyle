# 0009 — D5 external providers: Tencent TokenHub and Alibaba Model Studio; model download sources

- Status: **Accepted** (2026-10-07, owner decision; model choice by Claude Code)
- Supersedes the provider choice in [ADR-0004](0004-external-services-policy.md). Its data rules still apply.

## Context

The owner dropped OpenAI and Gemini. They provided one key for Tencent and one for Alibaba Cloud, each with a CNY 5 balance. Separately, model downloads through AutoDL's academic proxy ran at 1–2 MB/s.

## Decision

**Which product each key belongs to** (checked 2026-10-07 with free model-list calls only, no paid calls):

- The Tencent key is a **Tencent Cloud TokenHub** key (`tokenhub.tencentmaas.com`). The legacy Hunyuan endpoint rejects it.
- The Alibaba key is an **Alibaba Cloud Model Studio (百炼), Beijing region** key (`dashscope.aliyuncs.com`). The Singapore endpoint rejects it.

**Models.** The owner preferred, first, an editing model that takes the draft and the style reference as two images, and second, image-to-image with a reference.

| Provider | Model | Why | Price |
|---|---|---|---|
| Tencent | `hy-image-v3` (Hy-Image-3.0) | Tencent's own model. Takes 0–3 reference images, so draft + style reference fit in one call. A stable release, not a preview. | CNY 0.2 per image |
| Alibaba | `qwen-image-edit-plus-2025-12-15` | Instruction editing over 1–3 images. It is a **dated snapshot**, which keeps the run reproducible. | CNY 0.2 per image (Beijing) |

- **Alternatives** (not used unless re-decided): `hy-image-v3.5-preview` (a preview, so its behaviour may change); `qwen-image-edit-max-2026-01-16` and `qwen-image-2.0-pro-2026-06-22` (no public price found); `wan2.7-image`.
- **Generic interface.** Providers implement one generic `ImageProvider` interface (name, model ID, `estimate_cost`, `generate`) and call the REST APIs with `requests`, with no vendor SDK. Adding a service means adding one class. The "SDK version" field in the call record holds the `requests` version and the endpoint URL.
- **Midjourney** stays skipped.

**Budget and protocol** (owner, 2026-10-07):

- Spend at most 80% of the CNY 5 balance per provider, and estimate the cost before any paid call.
- One image per call (`n=1`), at the lowest resolution that serves the comparison.
- One trial call per provider before the real run.
- Cache every response, and never send the same input twice.
- At most 3 attempts per case for each external service; drop cases if the budget requires it, and say so in the report.
- Keep a key-free ledger at `runs/d5/ledger.jsonl`.
- No paid calls before D5.
- Unchanged: the shared prompt template, naming the accessory from attempt 2 on, blind review, and logging model versions.

**Keys** live only in `.env` as `TENCENT_HUNYUAN_API_KEY` and `DASHSCOPE_API_KEY`. Any printed or stored form is masked (first 5 and last 4 characters at most).

**Model downloads.** Measured on the server on 2026-10-07 (single stream, then `aria2c` with 16 connections):

| Source | Single stream | 16 connections |
|---|---|---|
| Direct HF | unreachable | – |
| HF + `network_turbo` | ~0.7 MB/s | – |
| hf-mirror | ~2.4 MB/s | ~3–5 MB/s |
| ModelScope | ~6 MB/s | ~12–13 MB/s; up to ~47 MB/s observed on a resumed large file |

`scripts/download_models.py` works as follows:

- It probes the candidate sources for each model (8 s of `aria2c`) and downloads each file from the fastest source, with resume (`aria2c -c`), in tmux.
- Integrity is always anchored to Hugging Face. The pinned revision and the expected hash of each file (LFS sha256, or the git blob sha1 for small files) come from the HF API, read through hf-mirror.
- A file whose bytes do not match is discarded and fetched from the next source.
- `models/MANIFEST.json` records the HF revision and hashes, and the source and URL actually used for each file.
- MistoLine has no ModelScope copy, so it comes from hf-mirror.
- Only public mirrors are used; no self-hosted proxy.

## Consequences

- The `openai` and `google-genai` pins are replaced by `requests` in `requirements.txt`.
- If ModelScope ever serves different bytes, verification fails and that file falls back to hf-mirror at the pinned revision. A mismatched file is never accepted.
- At CNY 0.2 per image, 19 calls (1 trial plus 3 × 6 cases) cost CNY 3.8 per provider, inside the CNY 4 cap. Prices are re-checked on the day of the run.
