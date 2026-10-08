# Experiments

Every number here comes from a run record under `runs/<run_id>/` on the server (config, seed, commit hash). Small copies are in the gitignored `local_runs/`.

## D0 — environment (2026-10-08)

| Run ID | What | Result |
|---|---|---|
| `20261005T170219Z_smoke_cuda` | `scripts/smoke_cuda.py` | OK. torch 2.14.1+cu130, CUDA 13.0, cuDNN 92400, RTX 4090 D (sm 8.9, 23.52 GiB). Matmul: fp16 41.4 TFLOPS, bf16 45.8 TFLOPS. SDPA flash and mem-efficient backends on. A 20 GiB allocation succeeded. |
| `20261008T092942Z_smoke_models` | `scripts/smoke_models.py` | OK. Resident VRAM in GiB: UNet 5.572, text encoders 1.523, VAE 0.156, MistoLine 2.330, ViT-H image encoder + IP-Adapter Plus 1.177, SAM 2.1-L 0.409, DINOv2-L/reg 0.567; total 11.967. Peak 11.98 GiB. Load of the SDXL stack 17.3 s; 512², 4-step ControlNet + IP-Adapter generation 1.91 s; SAM 2 load + one mask 2.2 s. |

Notes:
- transformers warns that the SAM 2.1 checkpoint's config type is `sam2_video` while it loads as `Sam2Model`. The image-mask path ran and produced a mask; D3 checks mask quality.
- Model download (`runs/download/log.txt`): ModelScope ~12–14 MB/s, hf-mirror ~0.8–4 MB/s; all files verified against pinned HF hashes (ADR-0009).

## D2 — global path (2026-10-08, commit a8f9fb4)

Settings are the `GlobalSettings` defaults: style 1.0 on the InstantStyle block, structure 0.7, 30 steps, CFG 6.0, 1024 px long side. Each run record stores the full settings.

| Case | Mode | Run IDs (seed) | Latency (s) | Peak VRAM (GiB) |
|---|---|---|---|---|
| pepper_bergen | txt2img | `20261008T093631Z` (0), `…093638Z` (1), `…093644Z` (2) | 6.47 / 6.01 / 6.06 | 13.43 |
| pepper_bergen | img2img 0.8 | `20261008T093706Z` (0) | 5.62 | 13.43 |
| pepper_bergen_ref2021 | txt2img | `20261008T093730Z` (0), `…093737Z` (1), `…093744Z` (2) | 6.74 / 6.05 / 6.07 | 13.43 |
| pepper_bergen_ref2021 | img2img 0.8 | `20261008T093807Z` (0) | 5.78 | 13.43 |
| shichimi | txt2img | `20261008T093828Z` (0), `…093832Z` (1), `…093837Z` (2) | 4.70 / 4.15 / 4.14 | 12.66 |
| shichimi | img2img 0.8 | `20261008T093859Z` (0) | 3.96 | 12.65 |
| coriander | txt2img | `20261008T093919Z` (0), `…093925Z` (1), `…093930Z` (2) | 5.59 / 4.83 / 4.85 | 12.81 |
| coriander | img2img 0.8 | `20261008T093952Z` (0) | 4.79 | 12.81 |

The first attempt ran out of memory at 1024 px: `from_pipe` cast the shared modules to fp32 (21.8 GiB resident). Fixed in `models.py`.

**Mode choice: txt2img + ControlNet.** img2img at strength 0.8 keeps the draft's white paper look and transfers little style, in all 4 cases.

**Detail case (visual inspection by the developer, not staged): the red hair ribbon in `pepper_bergen`.**

- In the source, Pepper wears a small red ribbon tied at the back of her head, and the prompt names "red ribbon in her hair".
- In all 6 txt2img runs (2 references × seeds 0–2), the ribbon is misrendered or lost:
  - ref 2017: a brown bead ornament (s0), a purple ribbon (s1), a black bow (s2);
  - ref 2021: a small dark tie or nothing.
- The ribbon's outline partly survives in the line art, which matches the PLAN's warning that an outline alone is not success.
- A secondary detail is the silver bodice clasp. It is rendered red in 4 of 6 runs and grey or silver in 2 (s2 with both references), so it is less consistent.
- Crops: `local_runs/d2/pepper_crops.jpg`, rebuilt from the runs above.

**Other observations:**

- `coriander`: the simulated line art is almost empty (the source is a light, soft painting), so the structure is not kept. That case is unusable until the line extraction is tuned (follow-up item).
- `shichimi`: the white hair ornament is drawn differently in every seed, and the hair colour drifts (blonde or brown instead of white). This is a possible second case, but it is confounded by the drift.

## D3 — Engine A on the detail case (2026-10-08)

**Setup**

- Case `pepper_bergen_flat`. The draft is line art over mean-shift flat colours, so the red ribbon is in the draft, as the necklace is in the brief's case.
- k-means flats (k = 8–32) merged the ribbon into the hair colour, so drafts now use mean-shift flats (`lineart.py`).
- Reference: `pc_pepper_portrait_2017`. **None of the Pepper references contain a red ribbon**, so the single point pair maps the ribbon to the reference's red vest fabric, as the rendering style for red cloth (`configs/pairs/pepper_ribbon.json`).
- Region tag: "red hair ribbon". Strength 0.6, giving IP scale 0.76 and denoise 0.72.
- `init_from_draft`: the region is first filled with the draft's own colours, only inside the undilated SAM mask.

**Results:** commit after `D3: keep IP-Adapter region masks on the GPU`; seeds 0–2; 1 point pair.

| Run ID | Global-only ribbon | PinStyle ribbon | Local latency (s) | MAD outside the region | SSIM outside the region |
|---|---|---|---|---|---|
| `20261008T095710Z_pinstyle_pepper_bergen_flat_s0` | gold ornament (misrendered) | red ribbon restored | 7.01 | 0.003 | 0.9999 |
| `20261008T095723Z_pinstyle_pepper_bergen_flat_s1` | purple bow (misrendered) | partly restored: reddish pink, with purple left over | 5.11 | 0.004 | 0.9999 |
| `20261008T095737Z_pinstyle_pepper_bergen_flat_s2` | black bow (misrendered) | red ribbon restored | 5.28 | 0.004 | 0.9999 |

- The global-only result in each run is that run's `global.png` (same seed and settings as D2), so the ribbon failure reproduces 3/3 on the flat draft too.
- Judgements are visual, by the developer.
- MAD is the mean absolute difference on a 0–255 scale.
- Local latency includes SAM 2 on the draft and the reference, plus one 1024² ControlNet-inpaint pass with 30 steps.

**Fixes found on the way** (the earlier runs are kept on the server):

- Run 1 (`20261008T094438Z…`–`094717Z…`): a pale halo of the draft's sky colour around the ribbon, because the draft colours were pasted into the dilated mask.
- Runs 1–2: about 70 s per region, of which about 43 s was IP-Adapter mask resizing on the CPU at every attention call. Keeping the masks on the GPU brought it to 5–7 s.

**Figure:** `local_runs/d3/figure_d3_s0.png`, rebuilt with `python scripts/make_figure_d3.py <run dir> <out>`.

**Limits, stated plainly:**

- The draft is simulated, and its flats come from the finished work.
- The ribbon's appearance comes from the draft plus a region tag. The reference supplies only rendering style, because no reference contains the ribbon.
- 1 of 3 seeds is only a partial fix.
