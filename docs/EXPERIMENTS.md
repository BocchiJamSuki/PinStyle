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

## D4 — Gradio app (2026-10-08)

- Unit tests: `tests/test_pairs.py` (10 tests on the pair-state logic). Full suite: 23 passed with sockets blocked.
- End-to-end handler test on the server, in the app's process with simulated clicks at the D3 coordinates: load case → pair p1 (tag "red hair ribbon") → global only (7.67 s, `20261008T100211Z_app_global_pepper_bergen_flat_s0`) → PinStyle on the current output (7.66 s, `20261008T100218Z_app_local_on_current_pepper_bergen_flat_s0`) → global + PinStyle (12.45 s, `20261008T100231Z_app_global_local_pepper_bergen_flat_s0`) → mark acceptable → compare two versions. All steps passed.
- **Not yet done:** a manual click-through in a real browser, with screenshots. It needs the owner's SSH tunnel and is folded into the D6 dry run.

## D3 ablation — where does the ribbon's red come from? (2026-10-08)

The owner pointed out that the reference vest and the draft ribbon are both red, so the D3 case cannot show what the reference contributes. Ablation on `pepper_bergen_flat`, seeds 0–2, 1 pair, strength 0.6, everything else as in D3:

| Condition | Run IDs | Ribbon red? (visual, developer) |
|---|---|---|
| A: reference point on the red vest, with draft init (the D3 setting) | `20261008T095710Z`/`095723Z`/`095737Z` | s0 and s2 red, s1 partly |
| B: reference point on dark hair, with draft init | `20261008T101607Z`/`101620Z`/`101634Z` | no: brown or dark purple |
| C: reference point on the blue background, with draft init | `20261008T101713Z`/`101727Z`/`101741Z` | s0 and s2 red, s1 partly |
| D: reference point on the red vest, no draft init | `20261008T101818Z`/`101831Z`/`101845Z` | no: dark or greenish |
| E: reference point on the blue background, no draft init | `20261008T101922Z`/`101936Z`/`101949Z` | no |

Grid: `local_runs/d3abl/grid.jpg`.

A crude automatic score, `local_runs/d3abl/red_fraction.json`: the share of the draft's red ribbon pixels that are red in the output (R > G + 50 and R > B + 50).

| Condition | s0 | s1 | s2 |
|---|---|---|---|
| global-only | 0.000 | 0.000 | 0.003 |
| A | 0.017 | 0.000 | 0.131 |
| B | 0.000 | 0.000 | 0.004 |
| C | 0.124 | 0.000 | 0.112 |
| D | 0.000 | 0.000 | 0.005 |
| E | 0.000 | 0.000 | 0.001 |

The score under-counts, because the re-rendered ribbon does not sit exactly on the draft's pixels (A s0 looks red but scores 0.017), so it is only indicative.

**Conclusion:**

- The red comes from the **draft init** (with the region tag). The reference region does **not** carry the colour: C, with a blue reference region, is as red as A.
- A dark reference region (B) suppresses it.
- So D3 shows *detail protection* (keeping what the artist drew in a region that global transfer loses). It does **not** show *regional style transfer from a chosen reference region*.
- That needs a case where the same accessory appears in both the reference and the draft (next step).

## D3b — the main detail case: Shichimi's horn ornament (2026-10-08)

**Why this case:** the same accessory, Shichimi's white horn hair ornament, is in both the draft (`pc_shichimi_concept_2015`, plain white) and the reference (`pc_shichimi_torreya_2025`, carved ivory with engraved swirls). Both images were already approved. So this case can test what the reference region contributes, which the Pepper case could not.

**Setup**

- Case `shichimi_flat` (flat draft). One pair: `configs/pairs/shichimi_ornament.json`.
  - Target: the horn, at (0.582, 0.175).
  - Negative points: the hair and the paper crane.
  - Reference: the 2025 horn, at (0.725, 0.495).
- Ablation `shichimi_ornament_refbg.json`: the same, but with the reference point on the plain paper background (0.88, 0.2).
- Both use draft init, strength 0.6, tag "white horn hair ornament".
- Global structure strength 0.7 (default) and 1.0. Seeds 0–2.
- An earlier batch (`20261008T104507Z`–`104814Z`) put the target point on the background just below the horn, so SAM masked the hand and hair. It is excluded and kept on the server.

**Results** (visual, by the developer; grid `local_runs/d3c/grid.jpg`; figure `local_runs/d3c/figure_shichimi_s0.png`)

| Structure | Seed | Run ID (reference on the horn) | Run ID (reference on the background) | Global-only horn | PinStyle, reference on the horn | PinStyle, reference on the background |
|---|---|---|---|---|---|---|
| 0.7 | 0 | `20261008T105124Z` | `20261008T105218Z` | dark red horn (misrendered) | carved ivory horn with swirls | blonde hair-like blob |
| 0.7 | 1 | `20261008T105134Z` | `20261008T105229Z` | grey striped frame (misrendered) | carved ivory horn with swirls | blonde hair-like blob |
| 0.7 | 2 | `20261008T105145Z` | `20261008T105240Z` | none (lost) | carved ivory horn with swirls | blob with a small face |
| 1.0 | 0 | `20261008T105313Z` | `20261008T105408Z` | dark red horn (misrendered) | carved ivory horn with swirls | hair-like blob |
| 1.0 | 1 | `20261008T105323Z` | `20261008T105419Z` | purple striped shape (misrendered) | carved ivory horn with swirls | blonde blob |
| 1.0 | 2 | `20261008T105335Z` | `20261008T105430Z` | plain pale grey horn (shape kept, no carving) | carved ivory horn with swirls | blob with a small face |

- Change outside the region against global-only: MAD 0.003–0.006, SSIM 0.9998–1.0, in all 12 runs.
- Local latency: 5.06–7.26 s.

**Conclusion**

- With one point pair on the reference's horn, the horn is rendered as the reference's carved ivory ornament in 6/6 runs.
- With the reference point moved to the background, and everything else identical (including draft init), it is not rendered in 6/6 runs.
- So the reference region, not the draft init, determines how the accessory is rendered. This is the regional-transfer half that the Pepper ablation could not show.
- Global-only loses or misrenders the horn in 5/6 runs. In the 6th, the shape survives but without the carving.

**Limits**

- The draft is simulated.
- The judgements are by the developer.
- The global pass also drifts the hair colour from white to blonde, under the reference's global style. That is a separate global-style issue and is not corrected here.

## D5 — external services, first results (2026-10-08)

**Ledger** (`runs/d5/ledger.jsonl` on the laptop, copied here, no keys; prices from THIRD_PARTY §0.3):

| UTC | Provider | Model | Case | Attempt | Request ID | CNY | Running total |
|---|---|---|---|---|---|---|---|
| 2026-10-08T10:59:51Z | alibaba | qwen-image-edit-plus-2025-12-15 | shichimi_flat | 0 | 9b2fdad7-a85a-9356-a953-45a567c5859f | 0.2 | 0.2 |
| 2026-10-08T11:00:52Z | alibaba | qwen-image-edit-plus-2025-12-15 | shichimi_flat | 1 | d7963f83-2ce5-9a64-8196-6d29e13503a8 | 0.2 | 0.4 |
| 2026-10-08T11:01:09Z | alibaba | qwen-image-edit-plus-2025-12-15 | shichimi_flat | 2 | 10d3cba8-a8a8-981f-bb7b-dd0167b5cb3d | 0.2 | 0.6 |
| 2026-10-08T11:01:23Z | alibaba | qwen-image-edit-plus-2025-12-15 | shichimi_flat | 3 | a181e762-6078-9b0c-acdf-02dc5168a580 | 0.2 | 0.8 |
| 2026-10-08T11:01:39Z | alibaba | qwen-image-edit-plus-2025-12-15 | pepper_bergen_flat | 1 | 87b83682-59e3-914d-909c-e30fb5321488 | 0.2 | 1.0 |
| 2026-10-08T11:01:56Z | alibaba | qwen-image-edit-plus-2025-12-15 | pepper_bergen_flat | 2 | 86b104e1-9dd9-9858-813d-759eafe70190 | 0.2 | 1.2 |
| 2026-10-08T11:02:13Z | alibaba | qwen-image-edit-plus-2025-12-15 | pepper_bergen_flat | 3 | b89234be-5a88-9603-b753-54406639801a | 0.2 | 1.4 |

**Tencent `hy-image-v3`:** the first trial returned HTTP 402 (postpaid billing not enabled; nothing charged). The owner enabled it, and the run went ahead.

**Alibaba `qwen-image-edit-plus-2025-12-15`**

- 1 trial plus 2 cases × 3 attempts, one image per call:
  - `shichimi_flat`: 720×1024;
  - `pepper_bergen_flat`: 1024×1024.
- Inputs: the reference first, then the draft, because the output follows the last image's aspect ratio. Both cases use the same template (`configs/compare.yaml`); attempts 2–3 name the accessory and where it is.
- The response has no `model` field. `usage` reports image_count, width and height.
- Template history: the trial (attempt 0) used the wording "the first image / the second image" and re-rendered the reference. The template was then changed, identically for every provider, to the documented "Image 1 / Image 2" naming, with an explicit draft/reference role and "Do not copy the content of Image 2/1".

**Outcome (visual, developer; blind review pending)**

- In 6/6 attempts, the output **re-renders the reference's content** (characters, pose, costume, composition) and ignores the draft.
  - Shichimi: Torreya and Shichimi as in the reference. Attempt 2 changes the blonde girl's hair to white, and attempt 3 adds a small white horn.
  - Pepper: the 2017 portrait's hat and vest. Attempt 1 shows two copies of her, and attempt 3 has a checkerboard ("transparent") background.
- Taxonomy: structure change and not controllable, in 6/6.
- Grid: `local_runs/d5_alibaba.jpg`.
- **Limit:** image order may matter. The draft-last order follows the documentation, and no further attempts were made, per the 3-attempt cap.

## D5 — Tencent `hy-image-v3` (2026-10-08)

**Ledger rows:**

| UTC | Provider | Model | Case | Attempt | Request ID | CNY | Running total |
|---|---|---|---|---|---|---|---|
| 2026-10-08T11:04:37Z | tencent | hy-image-v3 | shichimi_flat | 0 | b18adad1-f5f1-4b54-9b73-0a7372a3d2f2 | 0.2 | 0.2 |
| 2026-10-08T11:05:28Z | tencent | hy-image-v3 | shichimi_flat | 2 | ede8518e-99aa-4b8d-84b1-93b81becd637 | 0.2 | 0.4 |
| 2026-10-08T11:05:48Z | tencent | hy-image-v3 | shichimi_flat | 3 | e0a6f56c-31c6-444e-b2d7-d717762b86b2 | 0.2 | 0.6 |
| 2026-10-08T11:06:10Z | tencent | hy-image-v3 | pepper_bergen_flat | 1 | cd397a18-10d1-4f16-8643-5af704e347aa | 0.2 | 0.8 |
| 2026-10-08T11:06:32Z | tencent | hy-image-v3 | pepper_bergen_flat | 2 | f6bd83ad-6edf-436a-bf11-bf57c71c8373 | 0.2 | 1.0 |
| 2026-10-08T11:06:54Z | tencent | hy-image-v3 | pepper_bergen_flat | 3 | e17f27f8-cdbc-47ec-b17d-adbdebd0d986 | 0.2 | 1.2 |

- The trial (attempt 0) used the final template, with seed 1. That is exactly attempt 1 of `shichimi_flat` (Tencent's minimum seed is 1), so attempt 1 was served from the cache and not sent again.
- Inputs: the draft first, then the reference. One image per call: 720×1024 (Shichimi), 1024×1024 (Pepper).
- The response has no `model` field. `tokenhub_usage.total_tokens` = 20000 per image, which is CNY 0.2 at the listed price.
- **Spend:** Tencent CNY 1.20, Alibaba CNY 1.40, both within the CNY 4.00 cap.

**Outcome (visual, developer; blind review pending; grid `local_runs/d5_tencent.jpg`)**

- In 6/6 attempts, the output keeps the draft's composition, characters and details, including the horn ornament and the red ribbon. The hair stays white for Shichimi.
- Shichimi's horn is always a plain white horn. In attempts 2–3 it gains a gold band. It is never the reference's carved ivory with engraved swirls, even though attempts 2–3 ask for it to be "rendered like the same ornament" in the reference.
- How much of the reference's overall style is adopted is left to the blind review. The Pepper outputs look closer to the source painting than to the 2017 portrait.
- **Validity note:** the flat draft is derived from the finished work, so it already carries the original colours. A service that re-renders the draft faithfully therefore "keeps" details easily. This favours draft-faithful methods and is stated in the report.

**Blind review set:** `python scripts/make_review.py` builds `local_runs/review/index.html` from `configs/review.yaml`.

- 24 items: 2 cases × 4 methods × 3 attempts, shuffled with seed 20261008 and with the method names hidden.
- The key is in `runs/d5/review_key.json`.
- `--reveal` joins the labels after the review.

## D5 — blind review and report (2026-10-08)

- The owner labelled all 24 items (`local_runs/review/review_labels.json`). Its extra keys `sl`, `tl`, `query`, `gtrans` and `vote` come from a browser translation extension and are ignored.
- Revealed with `python scripts/make_review.py --reveal …`, giving `runs/d5/review_revealed.csv`.
- Report: `python scripts/make_report.py` writes `runs/d5/report/` (`report.md`, `summary.csv`, grids). It is copied, with interpretation, to `docs/D5_REPORT.md`.
