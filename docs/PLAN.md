# PinStyle — Plan

Status (2026-10-05): **the demo scope is approved.**

- **Part A** is the current plan.
- **Part B** is the full research plan written earlier the same day. It is kept as **future work**: paused, not deleted.

Related docs:

- [ARCHITECTURE.md](ARCHITECTURE.md) — §0 describes the demo subset; the rest is the full design (future work).
- [THIRD_PARTY.md](THIRD_PARTY.md) — §0 lists the demo components; the rest is the full verification.
- [decisions/](decisions/) — [ADR-0006](decisions/0006-demo-scope.md) (demo scope) and [ADR-0007](decisions/0007-demo-image-policy.md) (demo image policy).

---

# Part A — Demo scope (current)

## Goal

A minimal working demo plus a comparison with existing services, for the research proposal:

1. **Global path:** IP-Adapter / InstantStyle on SDXL with a structure ControlNet. CSGO is used only if it is cheap to integrate (an optional spike).
2. **Engine A only** (training-free): point pairs → SAM 2 masks → masked IP-Adapter correction, with per-region strength and feathered blending.
3. **Gradio app:** upload a reference and a draft, click point pairs, set strength, run, compare before and after, and see a simple version list.
4. **A detail case, end to end:** a small accessory (earrings, hairpin, ribbon, brooch, necklace, …) that fails under global transfer and is recovered with one or two point pairs. A failure means the accessory is either **lost** or **misrendered** (wrong colour or material, garbled shape). The line-art ControlNet often keeps outlines, so a surviving outline alone does not count as success.
5. **Comparison runner:** the same inputs run through:
   - two Chinese image APIs: Tencent TokenHub `hy-image-v3` and Alibaba Cloud Model Studio `qwen-image-edit-plus-2025-12-15` ([ADR-0009](decisions/0009-domestic-image-providers.md); these replace OpenAI and Gemini);
   - Midjourney: skipped;
   - our global-only path;
   - PinStyle.

   It outputs a comparison grid, a failure-taxonomy table (lost detail, misplaced detail, style drift, structure change, not controllable) and the number of attempts until an acceptable result. CSD/DINOv2 scores are added only if cheap.
6. **Governance as static mock screens** (registration, provenance label), clearly marked as a concept.
7. **A README and a 2-minute demo script.**

**Dropped for now** (they stay in Part B): Engine B training and OmniStyle, benchmarks B1–B3, the annotation tool, the full governance implementation, PSD/ORA export, the probe builder, study logging, and the React frontend.

**Constraints (unchanged):**

- SDXL base only.
- No per-artist fine-tuning.
- Rights-cleared images only ([ADR-0007](decisions/0007-demo-image-policy.md)).
- Exact model versions recorded for every external service call.
- Never fabricate results: every number has a run ID.

## Where the work happens

See [ADR-0008](decisions/0008-execution-topology.md).

- **Claude Code runs on the owner's Windows laptop.** The AutoDL server (RTX 4090 D, 24 GB) is a remote GPU executor, reached with key-based SSH.
- **Code is edited only on the laptop** and pushed to GitHub. The server runs `git pull --ff-only` before every run.
- **On the server's 150 GB data disk** (`/root/autodl-tmp/PinStyle`):
  - the clone;
  - the conda env `pinstyle` (Python 3.11, every version pinned in `environment.yml`);
  - `models/` and the HF cache;
  - `runs/`.
- **GPU jobs** run in `tmux` or `nohup` and are polled. Small artifacts are copied back to the laptop's `local_runs/`.
- **Gradio** runs on the server, bound to 127.0.0.1. Open it with `ssh -L 7860:127.0.0.1:7860 -p 39283 root@connect.westb.seetacloud.com`.
- **Autonomy:** D0–D6 run without milestone approvals; the operating rules are in `CLAUDE.md`. The server is shut down whenever work is done or blocked.
- **D1 approval** is delegated to Claude (ADR-0007).

## Status

| # | Milestone | Status | Eng. days (est.) | GPU-h (est.) | Needs from the owner |
|---|---|---|---|---|---|
| H | Docs updated for the demo scope; repo initialized | ✅ 2026-10-05 (laptop) | – | – | git remote URL, to push |
| D0 | Environment + CUDA smoke test | ✅ 2026-10-08: smoke_cuda and smoke_models pass (`20261008T092942Z_smoke_models`; 11.98 GiB peak); models verified (ADR-0009); env frozen in `requirements.lock.txt` | 0.5–1 | < 1 | the persistent path on the box |
| D1 | CC image shortlist (approval gate) | ✅ 2026-10-06: 8 Pepper&Carrot works by David Revoy (CC BY 4.0), 3 characters, approved under delegation. Source files have no line-art layers (only paint layers; checked ep35 pages and the 2019 Shichimi artwork), so all drafts are `simulated` | 0.5–1 | 0 | approve the shortlist |
| D2 | Global path | ✅ 2026-10-08: txt2img + MistoLine + IP-Adapter (InstantStyle), 4–7 s at 1024 px. Detail case: Pepper's red hair ribbon, misrendered or lost in 6/6 runs (EXPERIMENTS D2). Coriander line art too sparse (follow-up) | 1–1.5 | 1–2 | – |
| D3 | Engine A + detail case end to end (CLI) | ⬜ | 2–3 | 2–4 | – |
| D4 | Gradio app + concept screens | ⬜ | 1.5–2.5 | ~1 | UI feedback |
| D5 | Comparison runner + report | ⬜ | 2–3 | 1–2 | Keys in `.env` (done 2026-10-07); budget CNY 5 per provider, spend ≤ 80%; reviews (~1–2 h) |
| D6 | README + 2-minute demo script | ⬜ | 0.5–1 | < 1 | a dry run |
| **Total** | | | **8–13 (~2–3 weeks)** | **≈ 5–10** | API cost, rough estimate: ≈ $5–30 |

Legend: ⬜ not started · 🔄 in progress · ✅ done · ⛔ blocked.

- **Estimates** are planning numbers. They are replaced by measured values as the milestones run.
- **Ordering:** D1 (web research) can start right after D0. While the shortlist waits for approval, D2 may debug on AI-generated images (debugging only, per ADR-0007).
- **End of every milestone:**
  1. run the tests;
  2. update this table;
  3. append results with run IDs to `docs/EXPERIMENTS.md`;
  4. commit as `D<n>: …`;
  5. push.

## D0 — Environment and CUDA smoke test (first step, on the 4090)

**Tasks**

- [x] **D0.1 Machine check and CUDA smoke test.**
  - Inspect `nvidia-smi` (RTX 4090, driver, CUDA), find out which path is persistent and how much space is free, and check whether conda is present.
  - If conda is missing, install Miniforge on the persistent disk, after asking the owner.
  - Write `environment.yml`: `python=3.11` plus exact pip pins, starting from these versions (latest on 2026-10-05):
    - torch 2.14.1 + torchvision 0.29.1, from the PyTorch **cu130** index (needs a recent driver) or **cu126** for older drivers;
    - diffusers 0.40.0, transformers 5.18.0, accelerate 1.15.0, huggingface_hub 2.1.1;
    - gradio 6.29.1;
    - requests 2.34.2, for the D5 REST providers (ADR-0009);
    - pytest-socket 0.8.1;
    - plus opencv-python-headless, pillow, numpy, omegaconf, pytest and ruff.

    If these conflict, pick the newest compatible set and record why.
  - Run `conda env create -f environment.yml`, then `scripts/smoke_cuda.py`, which checks:
    - torch, CUDA and cuDNN versions;
    - the device name and compute capability 8.9;
    - fp16 and bf16 matmul, and the SDPA backends;
    - a ~20 GiB allocation and a small timing test.

    It writes a JSON report under `runs/` and exits non-zero on failure.
- [x] **D0.2 Repo scaffold:**
  - `pyproject.toml` (src layout, editable install), ruff, and pytest with sockets blocked;
  - a `pinstyle` package skeleton (`config`, `types`, `runs`) and `configs/demo.yaml`;
  - `HF_HOME`, `models/` and `runs/` placed on the persistent disk.
- [x] **D0.3 `scripts/download_models.py`.** Pins Hugging Face revisions, records sha256, and writes `models/MANIFEST.json`. About 15–20 GB in total:
  - SDXL base (fp16 variant) and the fp16-fix VAE;
  - the MistoLine ControlNet (canny as fallback);
  - IP-Adapter Plus SDXL ViT-H with the ViT-H image encoder;
  - SAM 2.1-L in transformers format;
  - optionally, DINOv2-L with registers.
- [x] **D0.4 `scripts/smoke_models.py`:**
  - load everything;
  - run one 512² ControlNet + IP-Adapter generation (4 steps) and one SAM 2 mask;
  - measure VRAM per component and at peak, into a run record;
  - fill the *Measured* column in THIRD_PARTY.md.
- [x] **D0.5 Freeze and wrap up:**
  - re-export the working env so that `environment.yml` pins *every* package, transitive ones included;
  - start `docs/EXPERIMENTS.md` and update the status;
  - commit and push.

**Done when:**

- `smoke_cuda.py` and `smoke_models.py` pass in `conda activate pinstyle`;
- the measured VRAM table is recorded with a run ID;
- `environment.yml` is fully pinned;
- `pytest` passes with sockets blocked;
- the work is pushed.

## D1 — CC image shortlist (owner approval gate)

**Rules** ([ADR-0007](decisions/0007-demo-image-policy.md)):

- **License:** CC0 or CC BY only (no NC, no ND). Record the attribution for CC BY works.
- **Authorship:** the uploader must be the actual author; skip reposts.
- **Grouping:** prefer several works by the same artist, ideally of the same character, so a draft can be simulated from one work and another used as the reference.
- **Detail case:** any small accessory that gets lost under global transfer.
- **Logging:** every image goes in `assets/demo/MANIFEST.csv` with its source URL, author, license and attribution. The owner sees the shortlist before anything is used.
- **AI-generated images** are for debugging only (`assets/debug/`, flagged in the manifest) and never appear in the demo or the comparison.

**Tasks**

- [ ] Search candidate sources and verify each work's license and authorship:
  - **Pepper&Carrot** by David Revoy (CC BY 4.0, license page verified). Check whether the source files contain line-art layers; if they do, the artist's real line art is preferred as the draft over a simulated one;
  - Blender Studio open-movie concept art (CC BY);
  - Wikimedia Commons "own work" uploads;
  - OpenGameArt character art;
  - Openverse.
- [ ] Build `MANIFEST.csv` (status `pending`) and a contact sheet showing visible accessories and same-character groups. Each case records `draft_source`: `artist_lineart` or `simulated`.
- [ ] Write a manifest checker that enforces CC0/CC BY only, a verified author, owner approval, and no AI images. The CLI, the app and the comparison runner all use it.

**Done when** the owner approves a shortlist of at least 4 works, ideally at least 2 of the same character, including candidates with small accessories.

## D2 — Global path

**Tasks**

- [x] Get the draft:
  - use the artist's real line art where it exists (`draft_source = artist_lineart`);
  - otherwise simulate it from a finished work (`simulated`): line art (TEED/MTEED, or XDoG/Canny) plus optional flat-colour quantization.
- [x] Global path:
  - SDXL + MistoLine ControlNet on the draft's line art;
  - IP-Adapter on the reference, using InstantStyle's style-block scales;
  - choose txt2img + ControlNet or img2img from the draft, by a quick check.
- [x] CLI `pinstyle global --case <id>`, writing run records.
- [x] **Find the detail case.** Run strong global transfer on the approved pairs with at least 3 seeds, and identify a small accessory that is lost or misrendered (wrong colour or material, garbled shape). Document it with run IDs and never stage it.

**Done when** global-only outputs and latency are logged for every approved case, and one detail-loss case is documented across at least 3 seeds. If no such case is found, report that honestly, with next steps.

## D3 — Engine A and the detail case end to end (CLI)

**Tasks**

- [ ] **Masks:** SAM 2.1 via transformers (`Sam2Model`; several points and negative points per region; image embeddings reused).
  - The target mask comes from the **draft**, where the accessory is still drawn (optionally from the output).
  - The reference mask comes from the reference.
  - Masks are dilated and feathered.
- [ ] **Engine A**, implementing the `LocalEngine` interface (ARCHITECTURE §5.1). For each region:
  1. crop the region and upscale it to ~1 MP;
  2. run `StableDiffusionXLControlNetInpaintPipeline` (modules shared via `from_pipe`) with `ip_adapter_masks`: the reference's region crop on the region mask, and the global reference on the complement;
  3. add the line-art ControlNet;
  4. paste the result back with a feathered pixel-space blend, keeping one layer per region.

  Region strength sets the IP scale and the denoising strength.
- [ ] Orchestrator (global → local → run record) and CLI `pinstyle run --case <id> --pairs pairs.json`.
- [ ] Figure: draft | reference | global-only | PinStyle | zoomed crops.

**Done when:**

- the accessory is restored with 1–2 point pairs;
- the change outside the regions stays small (mean absolute difference and SSIM against global-only, logged);
- the figure is saved;
- latency per correction at 1024 px is logged (target: about 20 s or less).

## D4 — Gradio app

**Tasks**

- [ ] **Finish tab:**
  - upload a case or load one; a prompt field; global settings (style strength, structure strength, steps, seed, resolution);
  - **pair clicking** (`gr.Image.select`): click the reference, then the draft; numbered markers drawn on both; a pair table with strength and an optional region group; delete and clear;
  - run buttons: global only / global + PinStyle / PinStyle on the current output; a progress bar;
  - **before/after** with the built-in `gr.ImageSlider`;
  - a "mark acceptable" button, which feeds the attempt counting.
- [ ] **Versions:** a simple list of runs (time, mode, seed, number of pairs, acceptable flag); pick two to compare in the slider.
- [ ] **Governance tab (CONCEPT):** static mock screens for registration and a provenance label, with a "Concept — not implemented" banner.
- [ ] **Launch** bound to 127.0.0.1, with `GRADIO_ANALYTICS_ENABLED=False` and `HF_HUB_OFFLINE=1`.

**Done when** the detail case works end to end in the browser (a manual run with screenshots) and unit tests cover the pair-state logic.

## D5 — Comparison runner and report

**Methods**

- ours, global-only;
- PinStyle (global + Engine A);
- **Tencent TokenHub** `hy-image-v3` (Hy-Image-3.0): takes 0–3 reference images, so the draft and the style reference go in one call; CNY 0.2 per image;
- **Alibaba Cloud Model Studio** (Beijing) `qwen-image-edit-plus-2025-12-15` (a dated snapshot): takes 1–3 input images; CNY 0.2 per image;
- **Midjourney:** skipped.

Both run behind one generic `ImageProvider` interface in `src/pinstyle/compare/` (name, model ID, `estimate_cost`, `generate`), so other services can be added later. Use dated snapshots where offered. On the day of the run, check the model list and the price, and log them. The choice and the alternatives are in [ADR-0009](decisions/0009-domestic-image-providers.md).

**Budget (owner, 2026-10-07):** each provider has a balance of CNY 5, and total spend per provider stays at or below 80% of it (CNY 4).

- Before any paid call, compute the cost per call and the total estimate from the official price. If the estimate is over the cap, stop and ask the owner.
- Request one output image per call, at the lowest resolution that serves the comparison: the 1024² area limit for `hy-image-v3`, and a long side of about 1024 px for Qwen.
- Make exactly one trial call per provider before the real run, to confirm the response format.
- Cache every response by (provider, model, input hashes, prompt, parameters). Never send a cached input again.
- Keep a ledger at `runs/d5/ledger.jsonl`: time, provider, model, request hash, number of images, unit price and running total. It never contains keys.
- At CNY 0.2 per image, 1 trial plus 3 attempts × 6 cases is 19 images, or CNY 3.8 per provider. If fewer cases fit the budget, drop cases and say so in the report.
- Make no paid calls before D5. Free endpoints, such as the model list, may be used to validate the keys.

**Protocol**

- **Same inputs:** every method gets the same draft and reference, and the text-driven methods share one prompt template.
- **Attempts per case:** at most 3 for each external service (owner, 2026-10-07), and at most 5 for our own methods:
  - attempt 1 uses the template;
  - later attempts may refine the prompt (services), the points/strength (PinStyle) or the seed/strength (global-only).
- **Fairness rule (fixed):** from attempt 2 on, prompts to external services may name the accessory and where it is (e.g. "keep the red brooch on the collar"). This mirrors how PinStyle users indicate it with points.
- **Blind review:** the review tab shuffles the outputs and hides method names. Names are revealed only after the labels are saved.
- **Labels:** acceptable or not, plus the taxonomy: lost detail, misplaced detail, style drift, structure change, not controllable. A misrendered accessory (wrong colour or material, garbled shape) counts as a detail failure.
- **Reviewer:** the report states that the reviewer is the developer.
- **Objective accessory score:** where the draft comes from a finished work, each method's accessory region is scored against that original (SSIM plus DINOv2 cosine on the region crop), logged per attempt with run IDs.

**Records**

- **What each call logs (JSONL):**
  - provider;
  - requested model ID and the model field from the response;
  - SDK version;
  - UTC time, prompt and parameters;
  - input and output hashes;
  - usage and latency.
- **Upload gate:** the manifest checker gates every upload.

**Report.** `scripts/make_report.py` rebuilds everything from the logs alone:

- a comparison grid (PNG);
- a taxonomy table;
- an attempts-until-acceptable table (a count, or "> 5");
- Markdown and CSV versions, with CC BY attributions in the captions.

A CSD score is added only if it loads within 2 hours of work.

**Done when:**

- one command regenerates the report from logs alone;
- every external call has its exact model ID and date;
- all approved cases have been run through every method (or the gaps are documented).

## D6 — README and 2-minute demo script

**Tasks**

- [ ] **README:**
  - setup on the box: Miniforge → `conda env create` → model download → smoke tests → app via SSH tunnel → comparison;
  - CC BY attributions;
  - limitations;
  - a link to Part B (future work).
- [ ] **`docs/DEMO.md`:** a 2-minute demo script, with precomputed fallbacks in case live generation runs slow.

**Done when** a fresh clone on the box can be set up by following the README, and a dry run of the script fits in 2 minutes.

## Optional, time-boxed (only if cheap)

- **CSGO** as an extra global path:
  - a spike of at most 4 hours, after D4;
  - it uses the official code from the gitignored `third_party/`, which has no license, so it is for local use only and is never committed;
  - drop it if it needs patching.
- **CSD score:** at most 2 hours.

## Demo architecture

The demo builds a subset of the full design; see [ARCHITECTURE.md §0](ARCHITECTURE.md). In short:

- **Resident models:** everything is loaded once and kept in VRAM in fp16. That is an estimated ~12 GB of weights plus 4–6 GB of activations at 1024², which fits in 24 GB without tiering (measured in D0).
- **Disk:** at least 50 GB persistent.
- **Network:** generation code makes no network calls. Only the comparison providers and the model download script use the network, and only when run explicitly.

## Risks → fallbacks

- **Newest package majors** (transformers 5.x, huggingface_hub 2.x) don't work with diffusers 0.40 → pin the newest compatible set in D0.
- **Driver too old for CUDA 13** → use the cu126 wheels.
- **No accessory loss with the CC pairs** → try other pairs and stronger style settings, and report honestly.
- **SAM 2 is weak on line art** → more points and negative points, segment on the output, dilate.
- **Too few same-character sets** → same artist, different characters (documented).
- **External model IDs or terms change** → re-check them on the day of the run and record what was used.

## Open items for the owner

- The **git remote URL**, for the first push (or push it yourself).
- **D5 keys:** provided on 2026-10-07 (Tencent TokenHub and Alibaba Model Studio) and stored in `.env`. Both were validated with the free model-list endpoints.
- **Midjourney:** skipped.

---

# Part B — Future work: full research plan (paused 2026-10-05)

> Written before the scope change and kept for later; nothing below is scheduled. Of its open questions:
>
> - answered by the demo decisions: 1, 3, 4, 5 and 6 (see the notes at the end);
> - moot for the demo: 2 and 7;
> - smaller for the demo: 9 (about 50 GB is enough);
> - still open: 8.

## How to read the estimates

- **Engineering days** are focused implementation days, assuming Claude Code does most of the implementation and the owner reviews at milestone boundaries. They exclude time spent waiting for data, approvals or GPU access.
- **GPU-hours** are hours on the rented RTX 4090.
- **Every number here is a planning estimate, not a measurement.** M0 (VRAM), M1–M2 (latency) and M7.0 (training throughput) would produce measured values.

## Status

| Milestone | Status | Eng. days (est.) | GPU-h (est.) | Needs from the owner |
|---|---|---|---|---|
| Pre-M0: verification and design docs | ✅ written and approved 2026-10-05 | – | – | – |
| M0 Setup | ⏸ future work | 2–3 | 1–2 | access to the 4090 box, ≥ 500 GB persistent disk, git remote |
| M1 Global path | ⏸ future work | 3–5 | 2–4 | ≥ 5 rights-cleared (draft, reference) pairs |
| M2 Engine A | ⏸ future work | 4–6 | 4–8 | necklace-case images (rights-cleared) |
| M3 App v1 | ⏸ future work | 6–9 | 1–2 | UI feedback |
| M4 Suggestion and confidence | ⏸ future work | 4–6 | 2–4 | about 20 annotated region pairs, or annotation time |
| M5 Governance and export | ⏸ future work | 4–6 | < 1 | a PSD check in Photoshop / Clip Studio Paint |
| M6 Evaluation | ⏸ future work | 6–9 | 10–20 | B2 works, annotation time, API keys and budget, provider decisions |
| M7 Engine B | ⏸ future work | 10–15 | 33–50 (≤ 75 with contingency) | approval of ADR-0001; a window of ~2 days of continuous GPU time |
| M8 Tooling and polish | ⏸ future work | 4–6 | 1–2 | demo assets, questionnaire URL |
| **Total** | | **43–65** | **≈ 55–95** (≤ ~120 with contingency) | |

Legend: ⏸ paused (future work) · ⬜ not started · 🔄 in progress · ✅ done · ⛔ blocked.

**Calendar.** Roughly 9–13 working weeks of implementation, provided data and GPU access arrive when needed. The owner's annotation and data work (B1 check, B2 collection, B3) would be on the critical path.

## Working rules (from the brief)

- **One milestone at a time.** Each starts only after approval.
- **End of every milestone:**
  1. run the tests (`pytest`, plus `pytest -m gpu` on the 4090);
  2. update the status here;
  3. append results with run IDs to `docs/EXPERIMENTS.md`;
  4. commit as `M<n>: …`.
- **Never fabricate results.** Every number comes from a logged run with its config, seed and commit hash. Estimates are labelled as estimates.
- **Decisions** become ADRs in `docs/decisions/`.
- **Where work happens.** Code is edited and run on the rented Linux 4090, where Claude Code runs (decided 2026-10-05).

---

## M0 — Setup

**Goal:** a reproducible environment where every component loads on the 4090, with the test harness and logging in place.

Tasks

- [ ] M0.1 `git init` and `.gitignore` (`models/`, `data/`, `runs/`, `third_party/`, secrets, caches). First commit includes these docs. Set up the remote.
- [ ] M0.2 Python project:
  - `pyproject.toml` with a src layout and extras `server`, `train`, `eval`, `external`, `dev`;
  - `.python-version` 3.11 and `uv.lock`;
  - CUDA wheels on Linux, CPU wheels on Windows.

  (The demo uses a conda env instead.)
- [ ] M0.3 Tooling:
  - ruff, and mypy (strict for `src/`);
  - pytest with markers `gpu`, `bench`, `slow`, `network`, and pytest-socket on by default;
  - an import-linter contract: core code must not import `pinstyle.external`.
- [ ] M0.4 `pinstyle.config`, `configs/app.yaml` (`offline: true`, paths, VRAM budget) and `configs/models.yaml`. The latter lists every component with repo, pinned revision, files, sha256, dtype, tier, license and loader.
- [ ] M0.5 `pinstyle.tracking`: structlog setup, run IDs, and run records (git commit and dirty flag, environment, resolved config).
- [ ] M0.6 Offline guard (`pinstyle.governance.offline`) with tests. A basic version now; it is completed in M5.
- [ ] M0.7 `scripts/download_models.py`:
  - pinned revisions, `allow_patterns`, sha256 checks;
  - renames (TTPlanet file → diffusers name) and conversion of the CSD pickle to safetensors;
  - writes `models/MANIFEST.json`.
- [ ] M0.8 `pinstyle.runtime`: a skeleton `ModelManager` (specs, lazy local loading, tiers, `on_gpu`, `report`) and the GPU lock.
- [ ] M0.9 `scripts/smoke_test.py` (GPU):
  - Load every component, tier by tier, and run one tiny forward pass each: SDXL for 1 step at 512², the ControlNets, the CSGO weights, IP-Adapter Plus, a SAM 2.1 mask, DINOv2 features, a CSD embedding, DISK + LightGlue.
  - Measure VRAM per component and at peak, and write a run record.
  - Fill the *Measured* column in THIRD_PARTY.md §9 and resolve the M0 items in THIRD_PARTY.md §10.
- [ ] M0.10 `web/` scaffold: Vite + React + strict TypeScript, ESLint/Prettier, Vitest; it builds.
- [ ] M0.11 License report (`pip-licenses`, `license-checker`), appended to THIRD_PARTY.md; flag anything not permissive.
- [ ] M0.12 Create `docs/EXPERIMENTS.md` (template and first entries), update status, commit.

**Done when** (brief, refined)

- All components load on the 4090 and `smoke_test.py` passes; the measured VRAM table is recorded with a run ID.
- `uv run pytest` passes with sockets blocked, and `uv run pytest -m gpu` (smoke test) passes on the 4090.
- `web/` builds, and the license report shows no unexpected restrictive licenses.

**Risks → fallbacks**

- **Version conflicts** between torch, diffusers, sam2 and 2024-era CSGO code: our code uses current versions, and the official CSGO code gets its own environment (M1 parity only).
- **Disk or bandwidth limits** on the box: download the models first (~30 GB core, ~25 GB baselines) and the datasets later (M7.1).

## M1 — Global path

**Goal:** turn a draft and a registered reference into a globally stylized output, via CSGO (primary) and IP-Adapter/InstantStyle + ControlNet (alternative), with an exposed structure scale.

Tasks

- [ ] M1.1 Shared SDXL core (`sdxl_core.py`):
  - modules come from `ModelManager`;
  - pipelines are assembled with `from_pipe`;
  - scheduler config (DPM-Solver++ 2M Karras by default), SDPA, VAE tiling.
- [ ] M1.2 Attention-processor bank v1 (token layout, groups, block targeting), plus a loader for `csgo_4_32.bin` covering the UNet and the ControlNet.
- [ ] M1.3 Minimal registry stub (exact-hash registration of demo assets), so engines take `RegisteredReference` from the first day. The full registry comes in M5.
- [ ] M1.4 CSGO parity:
  - clone the official repo at a pinned commit into `third_party/csgo_official` (own environment if needed);
  - run ≥ 3 pairs with the same seeds and settings, and record LPIPS and PSNR;
  - settle which TTPlanet file (v1 or v2) the authors used.
- [ ] M1.5 `GlobalPath` implementations:
  - `csgo`: style, content and structure scales; steps, guidance, resolution, seed, optional prompt;
  - `ipa`: IP-Adapter Plus with InstantStyle blocks and a structure ControlNet.
- [ ] M1.6 Choose the structure ControlNet (union vs MistoLine vs canny) on 3 pairs → planned ADR.
- [ ] M1.7 CLI `pinstyle global …` that writes run records and outputs.
- [ ] M1.8 Rights-cleared sample set (≥ 5 pairs) in `assets/demo/`, with `MANIFEST.csv`.
- [ ] M1.9 Profiling: latency and peak VRAM at 768 and 1024 px for both paths.

**Done when**

- The parity result is recorded (target: LPIPS < 0.02 against official CSGO at the same seed), and any remaining difference is explained.
- Global results and latency are logged with run IDs for ≥ 5 sample pairs on both paths, and structure preservation (edge agreement with the draft) is measured.

**Risks → fallbacks**

- **Parity fails under current diffusers:** debug side by side with the official environment. Worst case, run the official code unmodified (still not vendored) for the CSGO path until it is fixed (the alternative in ADR-0002).
- **CSGO is weak on illustration/manga:** the IP-Adapter/InstantStyle path becomes the default global path for the necklace demo, which the brief allows.
- **Sample data arrives late:** start with CC-licensed images listed in the manifest.

## M2 — Engine A (training-free local correction)

**Goal:** points become SAM 2 masks, which drive a masked regional correction of the global output. The necklace case is reproduced and fixed.

Tasks

- [ ] M2.1 SAM 2.1 masker (package vs transformers decided in M0):
  - per-image embedding cache;
  - prompts with several points, including negatives;
  - mask ops (dilate, erode, feather, union, hole filling) with tests.
- [ ] M2.2 Region pipeline: reference crops from masks, the strength → (IP scale, denoise) mapping, and crop mode for small regions.
- [ ] M2.3 Per-pixel strength sampling (latent re-noising in a step callback), feathered blending in pixel space, and one layer per region.
- [ ] M2.4 Variants A1 (inside CSGO: masked regional style groups) and A2 (separate pass: regional IP-Adapter Plus groups plus the structure ControlNet).
- [ ] M2.5 Orchestrator v1 (gate → global → local → lock composite → run record), and CLI `pinstyle run --pairs pairs.json …`.
- [ ] M2.6 Necklace case:
  - **Reproduce:** show the detail is lost under global transfer, across ≥ 3 seeds.
  - **Fix:** recover it with 1–2 pairs.
  - **Measure:**
    - DINOv2/CSD agreement in the necklace region goes up;
    - global CSD (CSLS) stays within tolerance of global-only (target ≥ 95 %);
    - changes outside the regions stay small (masked LPIPS).
- [ ] M2.7 Compare A1 and A2 on the necklace case and ≥ 10 B2-style cases (if data is available), on quality and latency → planned ADR.
- [ ] M2.8 `scripts/make_figures.py necklace`: the before/after sequence (global loss → points → recovery).
- [ ] M2.9 Latency per correction at 1024 px (target: about 20 s or less).

**Done when** the necklace case is reproduced and fixed, the before/after figure is saved, metrics and latency are logged with run IDs (brief), and the planned ADR is written.

**Risks → fallbacks**

- **SAM 2 struggles on line art and flat colours:** segment on the global output, add more points and negative points, use the mask brush override.
- **Seams:** wider feathering, pixel-space blending, a low-strength harmonization pass.
- **The available images don't lose the necklace under global transfer:** try other seeds, strengths and references. If the loss can't be reproduced honestly, report that and pick another real detail case. Never stage results.
- **Latency over target:** fewer steps, crop mode only where needed, several regions in one pass.

## M3 — App v1

**Goal:** the full interaction loop works in the browser.

Tasks

- [ ] M3.1 FastAPI app factory, settings, SQLite models (projects, versions, jobs, blobs), content-addressed blob store, `/api/health`.
- [ ] M3.2 GPU worker, priority queue, SSE and cancel; fake-GPU mode.
- [ ] M3.3 Endpoints:
  - projects, draft, references (via the registry stub);
  - saving points, masks;
  - runs, jobs;
  - versions (tree, HEAD, diff), files.
- [ ] M3.4 Script that generates TypeScript types from the OpenAPI spec.
- [ ] M3.5 UI:
  - split view with zoom/pan and overlay toggles;
  - pairs: create (click reference → click draft), drag, delete, with IDs and colours;
  - regions: merge pairs; strength, tag presets plus free text, lock;
  - global settings; run modes (global / global + local / local only); progress and cancel;
  - version history with undo/redo; a before/after slider between any two versions.
- [ ] M3.6 Tests: API tests with fakes, Vitest, and a Playwright end-to-end test of the necklace flow in fake mode.
- [ ] M3.7 A manual end-to-end run on the 4090 with real engines; screenshots saved under `runs/`.

**Done when** the full necklace flow works in the browser: the Playwright test passes in fake mode, and a manual run with real engines on the 4090 is recorded.

**Risks → fallbacks**

- **UI scope creep:** stick to the MVP list above and move everything else to M8.
- **Large images slow the canvas:** show previews in the browser and process full resolution on the server.

## M4 — Suggestion and confidence

**Goal:** pairs auto-suggested by both matchers, with the matchers compared; a confidence heatmap with hints.

Tasks

- [ ] M4.1 Dense-feature service (DINOv2-L/14 with registers; optionally SDXL UNet features), with caching.
- [ ] M4.2 Geometric matcher: DISK + LightGlue → DINOv2 filter → clustering → top K.
- [ ] M4.3 Semantic matcher: DINOv2 mutual nearest neighbours (optionally fused with SDXL features) → saliency filter → clustering → sub-patch refinement → top K.
- [ ] M4.4 Matcher comparison:
  - metrics: PCK@α and precision@K;
  - data: the B1 validation subset and owner-annotated pairs;
  - candidates: LightGlue alone, the geometric pipeline, the semantic pipeline;
  - result → planned ADR.
- [ ] M4.5 Confidence estimator:
  - signals: DINOv2 regional agreement, CSLS-normalized CSD, optional seed variance;
  - normalization, and a threshold calibrated on a small labelled set;
  - "suggest a point here".
- [ ] M4.6 API and UI: a suggest button; suggested pairs shown dashed with their confidence and accept/reject; heatmap overlay; hints on flagged regions.
- [ ] M4.7 Measure suggestion latency (< 2 s) and SAM mask latency (< 0.5 s), and optimize if needed.

**Done when** suggestions and the heatmap are visible in the UI, the matcher comparison is logged, and latency is measured against the targets.

**Risks → fallbacks**

- **LightGlue is weak across poses** (the brief expects this): make the semantic matcher the default.
- **CSD is unreliable on small crops:** enforce a minimum crop size, interpolate positional embeddings (THIRD_PARTY F7).

## M5 — Governance and export

**Goal:** own-work registry with a gate, offline enforcement, provenance, usage log and layered export.

Tasks

- [ ] M5.1 Registry:
  - upload with an authorship declaration and an optional portfolio URL (stored, never fetched);
  - fingerprints: file/pixel sha256, pHash, dHash, DINOv2;
  - an embedding precompute job and a registry UI.
- [ ] M5.2 Gate:
  - exact and near-duplicate rules;
  - `scripts/calibrate_gate.py` runs augmented positives against negatives (including unregistered works by the same artist) to set the thresholds, and logs the results;
  - a clear rejection message;
  - replaces the M1 stub.
- [ ] M5.3 Full offline enforcement:
  - the guard runs at server and CLI start;
  - pytest-socket and import-linter;
  - test: a full run with `offline: true` makes zero non-loopback connections.
- [ ] M5.4 Usage log:
  - hash-chained JSONL with append and verify;
  - events from the registry, gate, runs and exports;
  - a viewer with a verification badge;
  - a tamper test.
- [ ] M5.5 Provenance:
  - `scripts/make_test_cert.py`: a test CA and an ES256 leaf with the claimSigning EKU;
  - C2PA manifest builder; sign PNGs without a TSA; read them back (expect valid but untrusted);
  - JSON sidecar and PNG iTXt;
  - spike: sign ORA's `mergedimage.png`.
- [ ] M5.6 Export PNG, ORA (own writer) and PSD (psd-tools) with the layer structure in ARCHITECTURE §13; flatten PSDs on import.
- [ ] M5.7 Interop: ORA in Krita and GIMP, PSD in Krita (the owner checks Photoshop and Clip Studio Paint). Record the results.
- [ ] M5.8 Document the governance limits: authorship is self-declared, and perceptual hashes can be evaded.

**Done when:**

- an unregistered reference is rejected with a clear message (API and UI, tested);
- exports carry provenance (readable C2PA, sidecar and PNG text);
- tampering with the usage log is detected;
- ORA files open in Krita and GIMP;
- the offline tests pass.

**Risks → fallbacks**

- **`ta_url=None` is rejected, or the c2pa API changes:** pin the version and adapt. If offline C2PA signing turns out to be infeasible, ship the sidecar and PNG text only and document it (the brief says "if feasible").
- **PSD quirks:** ORA is the primary format; PSD is best-effort.

## M6 — Evaluation

**Goal:** benchmarks, metrics, baselines and the external comparison; one command reproduces the report.

Tasks

- [ ] M6.1 Manifests and rights checks (`benchmarks/manifests/*.csv`), plus a checker that refuses unlisted images.
- [ ] M6.2 B1: a held-out OmniStyle subset (~300 triplets) with manually checked correspondences (annotation mode), split into validation and test.
- [ ] M6.3 B2 (own-style propagation), from the owner's or consenting artists' works (≥ 10 cases ideal):
  - draft: synthesized with TEED line art plus flat-colour quantization;
  - reference: another work by the same artist;
  - ground truth: the original.
- [ ] M6.4 B3: annotated region pairs, and an operational definition of regional accuracy.
- [ ] M6.5 Metrics module (ARCHITECTURE §14), including CSLS-normalized CSD.
- [ ] M6.6 Baselines:
  - in-process: CSGO alone; IP-Adapter/InstantStyle + ControlNet;
  - subprocess adapters in their own environments: CoCoDiff, MangaNinja.
- [ ] M6.7 External comparison:
  - providers as decided in ADR-0004, plus manual import;
  - consent checks and call records;
  - the same prompt protocol for every service.
- [ ] M6.8 UI for labelling failures by taxonomy.
- [ ] M6.9 `scripts/run_eval.py` and `scripts/make_figures.py`, which build tables and figures from run records only.

GPU time scales with benchmark size × methods × seeds. For example, 100 cases × 5 methods × 3 seeds at ~20 s each is about 8 h.

**Done when** one command reproduces the full report from an empty `runs/` directory, and every number traces to a run ID.

**Risks → fallbacks**

- **Little rights-cleared data:** use a smaller B2 and report it as such.
- **API cost or terms:** run a subset and document it.
- **Baseline environments break:** pin them, and record failures as results.

## M7 — Engine B (trained point-guided branch)

**Goal:** train the branch once on general data, integrate it, and compare it with Engine A.

Tasks

- [ ] M7.0 Profiling:
  - measure s/iter and peak VRAM across:
    - resolution: 768 or 1024 px;
    - perceptual losses: every step or every 4 steps;
    - ControlNet: in the training loop or out;
    - frozen modules: bf16 or fp8 weight-only;
  - record the results in EXPERIMENTS.md and update the estimates below.
- [ ] M7.1 Data ([ADR-0001](decisions/0001-engine-b-training-data.md)):
  - download OmniStyle-150K to persistent disk and verify it;
  - select ~40–50K training and 1K validation triplets, keeping B1 held out;
  - extract style↔stylized pairs with both matchers, filter by confidence and content overlap, and cache them;
  - build self-supervised warped pairs;
  - precompute VAE latents and frozen-encoder outputs where storage allows;
  - manually check the held-out pairs (shared with M6.2).
- [ ] M7.2 Model:
  - token encoder, Engine B token groups in the processor bank, spatial weights, zero-init gates;
  - unit test: an untrained branch reproduces CSGO.
- [ ] M7.3 Training loop:
  - accelerate (bf16), gradient checkpointing, 8-bit AdamW, gradient accumulation;
  - checkpoint and resume;
  - logging of losses, gradients and VRAM;
  - periodic validation on B1-val;
  - configs `configs/train/engine_b_{pilot,768,1024}.yaml`.
- [ ] M7.4 Losses:
  - diffusion loss;
  - CSD style loss on matched regions (on the predicted x0, at low-noise steps, on small crops);
  - a DINOv2 structure constraint;
  - regional InfoNCE;
  - a progressive patch-shuffle curriculum.
- [ ] M7.5 Pilot: overfit 64 samples. Loss should fall, the gates should open, and regional agreement should rise.
- [ ] M7.6 Main run at 768 px.
- [ ] M7.7 Fine-tune at 1024 px if M7.0 shows it fits in time and VRAM.
- [ ] M7.8 Ablations:
  - number of pairs (0–10);
  - strength;
  - patch shuffling on/off;
  - which matcher extracted the training pairs;
  - data mix (OmniStyle only vs plus self-supervised pairs);
  - loss terms;
  - Engine A vs Engine B on B1–B3.
- [ ] M7.9 Integration: `EngineB` implements `LocalEngine` and is selectable in the API and UI; its checkpoint is registered in `models.yaml` with a sha256.

**Done when** (brief) there is a checkpoint with its config, seed and commit, an ablation table, and the engine can be switched in the UI.

### Engine B time and VRAM model (estimates; would be replaced by M7.0 measurements)

**Assumptions**

- Training setup:
  - batch 1 with gradient accumulation 8;
  - bf16, gradient checkpointing, 8-bit AdamW;
  - the frozen CSGO stack (UNet, Tile ControlNet, adapters) in the loop;
  - the CSD, DINOv2 and InfoNCE losses computed on half of the steps (low-noise timesteps, small crops).
- Throughput: 0.7–1.0 s/iter at 768 px and 1.3–1.8 s/iter at 1024 px. These come from:
  - rough community figures for SDXL LoRA training on a 4090 (on the order of 1 s per step at 1024 px, batch 1);
  - plus 30–50 % for the frozen ControlNet forward pass and the perceptual losses;
  - scaled by pixel count for 768 px.

| Phase | Work | Basis | GPU-h |
|---|---|---|---|
| M7.0 profiling | about 8 short configs | – | ≈ 1 |
| M7.1 download | 200.6 GB plus extraction | network and disk bound (1–4 h wall clock) | 0 |
| M7.1 point extraction | ~50K triplets, both matchers | 0.1–0.2 s per pair | 2–3 |
| M7.1 latents | ~100K images at 768 and 1024 px | 20–40 ms per image | 1–2 |
| M7.1 encoder outputs | ~100K images | 20–30 ms per image | ≈ 1 |
| M7.1 manual check | ~300 held-out pairs | owner or annotator time | (3–5 h of human time) |
| M7.5 pilot | 2K iterations at 768 px | 0.7–1.0 s/iter | 0.4–0.6 |
| M7.6 main run | 40K iterations at 768 px (5K optimizer steps) | 0.7–1.0 s/iter | 7.8–11.1 |
| M7.7 fine-tune | 12K iterations at 1024 px | 1.3–1.8 s/iter | 4.3–6.0 |
| M7.8 ablations | 6 runs × 10K iterations at 768 px | 0.7–1.0 s/iter | 11.7–16.7 |
| Evaluation | checkpoints and ablations on B1–B3 | ~6–10 s per case | 4–8 |
| **Total** | | | **≈ 33–50** (× 1.5 contingency → 50–75) |

- **Iterations.** Nobody knows how many are enough before the pilot runs. The learning curves in M7.5–M7.6 would show whether 40K is too few or too many.
- **VRAM** (THIRD_PARTY.md §9.3): about 19–25 GB at 768 px, which is tight. 1024 px needs mitigations:
  - fp8 weight-only frozen modules;
  - perceptual losses every k steps;
  - precomputed embeddings;
  - no ControlNet in the training loop.
- **Storage:** OmniStyle is 200.6 GB, plus the extracted subset (delete the archives after verification), 30–60 GB of latents and caches, and 10–20 GB of checkpoints. With models and runs, plan for at least 500 GB of persistent disk.

**Risks → fallbacks:** see R1, R2, R5 and R6 in the register below. If Engine B is not better than Engine A, report that honestly: Engine A is the proposal's fallback and stays the default.

## M8 — Research tooling and polish

**Goal:** tooling for the RQ1 probe and the RQ3 study, and a demo that runs from a clean clone.

Tasks

- [ ] M8.1 Probe builder (RQ1): three control levels for one draft, exported as a side-by-side sheet (PNG/PDF) with captions and process statistics.
- [ ] M8.2 Study logging (RQ3): sessions, the UI event stream, task time, edits, corrections and the accepted result; CSV export; questionnaire link template.
- [ ] M8.3 Demo mode: a preloaded rights-cleared project, and a 2-minute demo script in `docs/DEMO.md`.
- [ ] M8.4 README: setup on a fresh 4090 box, offline guarantees, limitations, licenses.
- [ ] M8.5 Clean-clone test on the box: clone → environment → download → smoke test → demo, recorded.

**Done when** (brief) the demo runs from a clean clone.

---

## Schedule and parallel work

The order follows the brief (M0 → M8), with two overlaps:

- **GPU work.** M7.0 and M7.1 (profiling, dataset download, point extraction) can run overnight on the GPU during M5–M6. M7.1 needs the M4 matchers.
- **Owner work** should start early:
  - rights-cleared samples (M1);
  - the necklace case (M2);
  - B2 works and annotations (M6);
  - decisions and API keys for the external services (M6).

**Critical path:** data availability (necklace case, B2) and Engine B training time.

## Risk register

L/I = likelihood / impact (H, M, L); "–" means the risk is already confirmed.

| ID | Risk | L | I | Mitigation | Fallback | When |
|---|---|---|---|---|---|---|
| R1 | IMAGStyle is unavailable (confirmed) | – | H | OmniStyle-150K + self-supervised pairs (ADR-0001) | CSGO-generated triplets on CC0 images | M7 |
| R2 | Style and stylized images rarely share semantic details, so point supervision is weak | H | H | filter by content overlap; self-supervised warped pairs with exact correspondences; patch-shuffle curriculum | train on self-supervised pairs only | M7 |
| R3 | CSGO's code is unlicensed (confirmed) | – | M | own processors + parity test (ADR-0002) | IP-Adapter/InstantStyle global path | M1 |
| R4 | CSGO incompatible with current diffusers | M | M | own processors; pinned versions | official environment for parity only | M1 |
| R5 | VRAM pressure (est. 20–21 GB peak at inference; training at 768 px tight) | M | H | tiering, cached embeddings, VAE tiling, fp8 weight-only | 768 px interactive; training without ControlNet in the loop | M0, M7 |
| R6 | Engine B does not beat Engine A | M | M | ablations, pilot sanity checks | report honestly; A stays the default | M7 |
| R7 | LightGlue weak on illustrations | H | L | semantic matcher | manual pairs | M4 |
| R8 | SAM 2 weak on line art and flat colours | M | M | segment on the global output; more points and negative points | mask brush | M2 |
| R9 | Seams or blending artefacts | M | M | feathered pixel-space blend | harmonization pass | M2 |
| R10 | Latency over target | M | L | fewer steps, crop mode, caching | 768 px interactive | M2, M4 |
| R11 | c2pa-python API churn or offline signing problem | M | L | pin the version | sidecar + PNG text only | M5 |
| R12 | Hosted weights removed (SD 2.1 precedent) | L | H | pin revisions + sha256; private archive on persistent disk | community mirrors | M0 |
| R13 | The rented machine is ephemeral | M | H | persistent volume; checkpoint and resume; push run summaries | re-run from manifests | all |
| R14 | Too little rights-cleared data (necklace case, B2) | M | H | ask early; CC-licensed sources | smaller benchmarks, reported as such | M1, M2, M6 |
| R15 | CSD miscalibration (THIRD_PARTY F7) | H | M | CSLS, paired comparisons, human checks | DINOv2 + human ratings | M4, M6 |
| R16 | External terms grant training rights over what we send | – | H | provider policy and consent records (ADR-0004) | exclude the provider | M6 |
| R17 | Base models were trained on scraped data (ethical limitation) | – | M | stay on SDXL base; no Danbooru-trained fine-tunes; document it | – | all |

## Inputs needed from the owner

| When | What |
|---|---|
| Before M0 | access to the 4090 box, ≥ 500 GB persistent disk, a git remote |
| M1 | ≥ 5 rights-cleared (draft, reference) pairs, with source and license |
| M2 | the necklace case: a draft and a finished reference (the same character with the necklace), rights-cleared |
| M4 | about 20 annotated region pairs, or annotation time |
| M5 | wording for the authorship declaration; a PSD check in Photoshop / Clip Studio Paint |
| M6 | B2 works (≥ 10 cases, own or from consenting artists), annotation time, ADR-0004 decisions, API keys and budget, manual Midjourney runs if wanted |
| M7 | approval of ADR-0001; a ~2-day GPU window |
| M8 | demo assets; questionnaire URL |

## Open questions (status as of 2026-10-05)

1. **Access to the 4090:** will Claude Code run on the box (over SSH or in a session there), or will you run the GPU commands? Which git remote should we use?
   - *Answered:* Claude Code runs on the box; work is pushed to the git remote.
2. **Training data:** do you approve OmniStyle-150K plus self-supervised pairs instead of IMAGStyle (ADR-0001)?
   - *Moot for the demo:* Engine B is deferred.
3. **CSGO:** is it OK to re-implement the processors around the Apache-2.0 weights and keep the unlicensed code out of the repo (ADR-0002)? Should we ask the authors to add a license?
   - *Demo:* CSGO is only an optional spike.
4. **External services:** please confirm the providers and tiers given their data terms (ADR-0004), and the budget and API keys.
   - *Demo:* OpenAI, Gemini (paid tier) and Midjourney (manual).
5. **Data:** do you have a rights-cleared necklace-case pair? How many of your own works, or works from consenting artists, are available for B2?
   - *Demo:* CC0/CC BY works (ADR-0007).
6. **Base model:** should we stay on SDXL base 1.0 and exclude anime fine-tunes trained on Danbooru?
   - *Answered:* SDXL base only.
7. **Paint software:** which do you mainly use? If it's Clip Studio Paint, PSD matters more than ORA.
   - *Moot for the demo:* there is no PSD/ORA export.
8. **Deadlines:** is there a proposal or demo date that should change the milestone order?
   - *Still open.*
9. **Disk:** does the rented machine have ≥ 500 GB of persistent disk?
   - *Demo:* about 50 GB is enough.
