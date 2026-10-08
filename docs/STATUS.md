# Status

Last updated: 2026-10-08

## Done
- D0 ✅ (2026-10-08): smoke tests pass; 11.98 GiB peak; env frozen.
- D2 ✅: global path; detail case = Pepper's red hair ribbon, misrendered or lost in 6/6 global runs.
- D3 ✅: main case = Shichimi's horn ornament. Reference point on the horn: carved ornament 6/6; on the background: 0/6. Pepper ribbon ablation: its colour came from the draft, not the reference (EXPERIMENTS).
- D5 ✅ (2026-10-08): owner's blind review plus a second, non-blind developer review with its own criteria (they agree on 10/24 items); report in `docs/D5_REPORT.md`. Spend: Tencent CNY 1.20, Alibaba CNY 1.40.
- Moved to the laptop (ADR-0010): RTX 4060 8 GB, low-VRAM leaf offload; global pass ~27–36 s, one region ~38 s. Colour vs rendering control added (EXPERIMENTS).
- D6 🔄: README and DEMO.md written.
- D4 🔄: Gradio app built and tested end to end (handlers); browser click-through pending.
- Docs: verification, full plan (future work), demo scope (ADR-0006), image policy (ADR-0007), topology (ADR-0008).
- Laptop ↔ GitHub and laptop ↔ AutoDL key-based SSH working. Server: RTX 4090 D 24 GB, driver 595.71.05, /root/autodl-tmp 150 GB (112 GB free), conda 24.4.0.

- D1 — shortlist approved (delegated): 8 Pepper&Carrot works by David Revoy, CC BY 4.0, in `assets/demo/` with `MANIFEST.csv`. Groups: Pepper (4), Shichimi (2), Coriander (2). No artist line-art layers exist in the sources, so drafts will be simulated.

## In progress
- D0.3 done 2026-10-07: all 6 models (15 GB) downloaded and verified against pinned HF revisions (`models/MANIFEST.json` on the server). Sources: ModelScope at ~12–14 MB/s (server egress appears capped there); MistoLine from hf-mirror (no ModelScope copy, ~0.8 MB/s).
- D0 — environment and CUDA smoke test on the server (huggingface_hub pin relaxed to <2 for diffusers 0.40).

## Needed from the owner
- **D4 browser check + D6 dry run (on the laptop, no server needed):**
  1. Run `conda activate pinstyle; python -m pinstyle.app.ui`, then open http://127.0.0.1:7860.
  2. Follow `docs/DEMO.md` and time it.
  3. Tell Claude Code what felt wrong.
- D5 keys received 2026-10-07 (Tencent TokenHub, Alibaba Model Studio), validated free; nothing else needed until the D5 blind review.
- Midjourney: skipped.

## How to resume
- Start the AutoDL instance if it is off, then tell Claude Code to continue from this file and `docs/PLAN.md` Part A.
