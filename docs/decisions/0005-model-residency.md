# 0005 — One shared SDXL UNet, tiered model residency, cached embeddings

- Status: **Deferred — future work** (2026-10-05). The demo keeps all models resident in one process (an estimated ~12 GB of weights, measured in D0), so no tiering is needed ([ADR-0006](0006-demo-scope.md)). The numbers below are estimates.
- Affects: brief §0 (VRAM management), §3.2 (warm-up), §4; ARCHITECTURE §9.

## Context

There is one RTX 4090 with 24 GB. Estimated fp16 weight sizes (THIRD_PARTY.md §9):

- **CSGO stack:** about 15 GB, including a 3.7 GB ViT-bigG image encoder and 1.6 GB of text encoders.
- **Engine A adds:** IP-Adapter Plus (0.85 GB), a ViT-H encoder (1.3 GB) and a structure ControlNet (2.5 GB).
- **Other models:** SAM 2.1-L 0.45 GB, DINOv2-L 0.6 GB, CSD ≤ 1.2 GB.

Separate SDXL pipelines for the global path and the engines would each carry their own 5.1 GB UNet.

## Decision

1. **One instance.** There is exactly one SDXL UNet and VAE, shared by the global path and both local engines through the attention-processor bank ([ADR-0002](0002-csgo-integration.md)).
2. **`ModelManager` with three tiers:**
   - **hot:** on the GPU from warm-up to shutdown;
   - **warm:** in pinned CPU RAM, moved to the GPU on demand and evicted least-recently-used first;
   - **cold:** separate processes (the baselines).

   The VRAM budget comes from config, each job type reserves headroom for its activations, and the interactive path never falls back silently to CPU offload.
3. **Cached encoder outputs.** Reference and draft embeddings, prompt embeddings and DINOv2 features are computed once and cached by image sha256 and model revision. The large encoders therefore rarely need the GPU.
4. **One GPU job at a time.** A single GPU worker thread runs all CUDA work, and a file lock (`runs/.gpu.lock`) enforces this across processes. Training and evaluation take the GPU only after the server releases it.

## Consequences

- **It should fit.** The hot set is estimated at about 14.3 GB, plus about 5–6 GB of peak activations at 1024², which leaves roughly 3 GB of margin. M0 measures this.
- **Encoder cost.** The first use of a new image or crop pays an encoder transfer, estimated at 0.2–0.5 s.
- **Start-up** takes an estimated 30–60 s for loading and warm-up.
- **Shared-UNet discipline.** Processors are configured per call, never reinstalled, so cross-engine state leakage is covered by tests (Engine B zero-init equals CSGO; lock compositing).
