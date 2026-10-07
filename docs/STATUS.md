# Status

Last updated: 2026-10-07

## Done
- Docs: verification, full plan (future work), demo scope (ADR-0006), image policy (ADR-0007), topology (ADR-0008).
- Laptop ↔ GitHub and laptop ↔ AutoDL key-based SSH working. Server: RTX 4090 D 24 GB, driver 595.71.05, /root/autodl-tmp 150 GB (112 GB free), conda 24.4.0.

- D1 — shortlist approved (delegated): 8 Pepper&Carrot works by David Revoy, CC BY 4.0, in `assets/demo/` with `MANIFEST.csv`. Groups: Pepper (4), Shichimi (2), Coriander (2). No artist line-art layers exist in the sources, so drafts will be simulated.

## In progress
- D0.3 done 2026-10-07: all 6 models (15 GB) downloaded and verified against pinned HF revisions (`models/MANIFEST.json` on the server). Sources: ModelScope at ~12–14 MB/s (server egress appears capped there); MistoLine from hf-mirror (no ModelScope copy, ~0.8 MB/s).
- D0 — environment and CUDA smoke test on the server (huggingface_hub pin relaxed to <2 for diffusers 0.40).

## Needed from the owner
- **Restart the AutoDL instance in GPU mode** (it was in no-GPU mode, and has been shut down). D0.1/D0.4 smoke tests need the GPU.
- D5 keys received 2026-10-07 (Tencent TokenHub, Alibaba Model Studio), validated free; nothing else needed until the D5 blind review.
- Midjourney: skipped.

## How to resume
- Start the AutoDL instance if it is off, then tell Claude Code to continue from this file and `docs/PLAN.md` Part A.
