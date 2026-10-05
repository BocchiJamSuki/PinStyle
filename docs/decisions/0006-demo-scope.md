# 0006 — Demo scope: a minimal working demo plus a service comparison

- Status: **Accepted** (2026-10-05, owner decision).
- Effect: the M0–M8 plan (PLAN.md Part B) becomes future work. ADRs [0001](0001-engine-b-training-data.md), [0002](0002-csgo-integration.md), [0003](0003-keypoint-extractor.md) and [0005](0005-model-residency.md) are deferred, and [0004](0004-external-services-policy.md) is updated for the demo.

## Context

The full plan (verification, architecture, M0–M8) was written on 2026-10-05. The owner judged it closer to a paper than to a proposal prototype, and asked for a minimal working demo plus a comparison with existing services.

## Decision

**Build only these seven things:**

1. **A global path:** IP-Adapter / InstantStyle on SDXL base with a structure ControlNet. CSGO is at most an optional, time-boxed spike.
2. **Engine A** (training-free): point pairs → SAM 2 masks → masked IP-Adapter correction, with per-region strength and feathered blending.
3. **A Gradio app:** upload, click point pairs, set strength, run, compare before and after, and a simple version list.
4. **One detail case end to end:** a small accessory that fails under global transfer and is recovered with point pairs. A failure means the accessory is lost or misrendered (wrong colour or material, garbled shape).
5. **A comparison runner** covering:
   - OpenAI and Gemini (paid tier), via their APIs;
   - Midjourney, by manual import (optional: only if the owner confirms Stealth mode);
   - global-only;
   - PinStyle.

   It outputs a comparison grid, a failure-taxonomy table and the number of attempts until an acceptable result. Similarity scores are added only if cheap.
6. **Governance** as static concept screens only.
7. **A README and a 2-minute demo script.**

**Not built now:** Engine B and OmniStyle, benchmarks B1–B3, the annotation tool, the full governance implementation, PSD/ORA export, the probe builder, study logging, the React frontend.

**Environment:**

- *Superseded by [ADR-0008](0008-execution-topology.md):* Claude Code runs on the owner's laptop, and the AutoDL RTX 4090 D server is a remote GPU executor.
- The repo, the conda env `pinstyle` (Python 3.11, every version pinned in `environment.yml`), weights and outputs live on its persistent disk, and work is pushed to the git remote.
- The first step is a CUDA smoke test.

**Constraints, unchanged:**

- SDXL base only.
- No per-artist fine-tuning.
- Rights-cleared images only ([ADR-0007](0007-demo-image-policy.md)).
- Exact model versions recorded for every external service call.
- Never fabricate results.

## Consequences

- **Effort:** an estimated 8–13 engineering days instead of 43–65.
- **No custom attention code.** diffusers' SDXL ControlNet inpaint pipeline supports IP-Adapter masks natively, and SAM 2 runs through transformers.
- **No tiering.** All models stay resident (estimated ~12 GB of weights), so ADR-0005's residency tiers are not needed.
- **Room for Engine B later.** The `LocalEngine` interface (ARCHITECTURE §5.1) is kept, so Engine B can be added without changing the app or the comparison runner.
- **Limited claims.** The demo claims only what it shows: one detail case and a small comparison, with every number traceable to a run ID.
