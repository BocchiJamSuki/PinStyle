# PinStyle — Architecture

> **Scope note (2026-10-05).** The project is in **demo scope** ([ADR-0006](decisions/0006-demo-scope.md); PLAN.md Part A).
>
> - **§0** describes what the demo builds.
> - **§1–§18** are the full design. They are kept as **future work** and are not being built now.

Status of §1–§18: **proposed, pre-M0** (2026-10-05), written before any code. Items marked *decide in Mx* are still open and get an ADR when they are decided.

Related docs: third-party facts and VRAM estimates in [THIRD_PARTY.md](THIRD_PARTY.md), milestones in [PLAN.md](PLAN.md), decisions in [decisions/](decisions/).

---

## 0. Demo architecture (current)

### 0.1 What the demo builds, against the full design

| Part | Demo (PLAN.md Part A) | Full design (future work) |
|---|---|---|
| Global path | SDXL base + MistoLine ControlNet on the draft's line art + IP-Adapter Plus (InstantStyle style-block scales) on the reference; CSGO only as an optional spike | CSGO via our own attention processors (§7.2, §7.4) |
| Local engine | Engine A: SAM 2 masks → one crop pass per region with `StableDiffusionXLControlNetInpaintPipeline` and `ip_adapter_masks` → feathered blend | Engine A variants A1/A2 and Engine B (§7.5, §7.6) |
| Point pairs | clicked by hand in the app | automatic suggestion (§8) |
| UI | Gradio app | FastAPI + React (§10, §11) |
| Governance | static concept screens | registry, gate, provenance, usage log (§12) |
| Evaluation | comparison runner: Tencent hy-image-v3, Alibaba qwen-image-edit-plus (ADR-0009), global-only, PinStyle | benchmarks B1–B3, baselines, metrics (§14) |
| Models | all resident in fp16 (≈ 12 GB of weights, estimated) | tiered residency (§9) |
| Export | PNG + run record | PNG / ORA / PSD with C2PA (§12.4, §13) |

### 0.2 Modules

```
PinStyle/
├── environment.yml             conda env "pinstyle": Python 3.11, every version pinned
├── pyproject.toml              src layout, editable install; ruff and pytest config
├── configs/demo.yaml           model IDs + pinned revisions; defaults (strengths, steps, resolution)
├── src/pinstyle/
│   ├── config.py               OmegaConf loading
│   ├── types.py                PointPair, RegionSettings, EngineInfo (subset of §4.2)
│   ├── manifest.py             MANIFEST.csv checker (ADR-0007)
│   ├── runs.py                 run records (config, seed, model revisions, git commit, timings, peak VRAM), version list
│   ├── models.py               load every model once and keep it resident (fp16)
│   ├── lineart.py              draft simulation and ControlNet conditioning (line extraction, flat colours)
│   ├── global_path.py          SDXL + ControlNet + IP-Adapter / InstantStyle
│   ├── segmentation.py         SAM 2.1 via transformers + mask ops (dilate, feather)
│   ├── engine_a.py             LocalEngine implementation (§5.1)
│   ├── pipeline.py             global → local → run record
│   ├── cli.py                  `pinstyle global …`, `pinstyle run …`
│   └── compare/                generic ImageProvider, Tencent/Alibaba providers, response cache, cost ledger, attempt log, report
├── app/                        Gradio app: Finish, Versions, Review and Governance-concept tabs
├── scripts/                    smoke_cuda · download_models · smoke_models · make_report
├── tests/                      unit tests (sockets blocked) + gpu-marked smoke tests
├── assets/demo/                approved CC0 / CC BY images + MANIFEST.csv
└── (gitignored) models/ · runs/ · assets/debug/ (AI-generated debug images) · third_party/
```

Reports are written under `runs/`. Figures meant for the proposal are copied to `docs/figures/`, with their attributions.

### 0.3 Data flow

1. **Load a case.** Use approved images from `assets/demo/` (checked by the manifest checker), or upload them. Simulate the draft from a finished work if needed.
2. **Global pass** → global output, plus a run record.
3. **Pairs.** The artist clicks point pairs (reference first, then draft) and sets the strength per pair or region.
4. **Engine A**, for each region:
   - a SAM 2 target mask from the **draft**, where the accessory is still drawn, plus a reference mask;
   - crop the region and upscale it to ~1 MP;
   - an inpaint pass with masked IP-Adapter (the reference's region crop on the region mask, the global reference on the complement) and the line-art ControlNet;
   - a feathered paste back.
5. **Outputs.** The result, per-region layers and a run record, shown in the version list and the before/after slider.
6. **Comparison.** The runner sends the same inputs to the external services and to our two methods. The owner reviews each attempt, and the report is built from the logs alone.

### 0.4 Runtime and local-first

- **One process, one GPU.** Models are loaded once and stay resident in fp16. Estimated at ~12 GB of weights plus 4–6 GB of activations at 1024²; measured in D0.
- **No network calls in generation code.**
  - `HF_HUB_OFFLINE=1` is set when the app and CLI start, and `GRADIO_ANALYTICS_ENABLED=False`.
  - Gradio binds to 127.0.0.1 and is reached through an SSH tunnel.
  - Tests block sockets.
- **Network access** happens only in `scripts/download_models.py` and in the `compare/` providers, and only when they are run explicitly. API keys come from environment variables.

### 0.5 Kept from the full design

- The `LocalEngine` interface (§5.1) and the core types (§4.2), so Engine B can be added later without changing the app or the runner.
- Normalized coordinates, and run records with config, seed and commit (§15). No number without a run ID.

---

## 1. Design drivers

These are the constraints from the brief that shape the structure:

1. **Region-level artist control.** Point pairs, regions, strength, signature-feature tags and locks are first-class data, stored with every run. They are not UI-only state.
2. **No per-artist fine-tuning.** Nothing in the system trains on a user's works. Engine B is trained once, offline, on general data ([ADR-0001](decisions/0001-engine-b-training-data.md)).
3. **Own-work references only.** An engine cannot receive an unregistered reference: it only accepts a `RegisteredReference`, which only the gate can issue.
4. **Local-first.** Core paths make no network calls. Offline mode is enforced at runtime and in tests. Network code lives only in `pinstyle.external` and `scripts/download_models.py`.
5. **One RTX 4090.** One shared SDXL UNet, explicit residency tiers, one GPU job at a time ([ADR-0005](decisions/0005-model-residency.md)).
6. **Research integrity.** Every output and every reported number traces back to a run record (config, seed, commit, model hashes).
7. **Interchangeable engines.** Global paths and local engines share interfaces, so the app, the CLI and experiments can swap them by name.

---

## 2. System overview

```
┌──────────────────────── Browser — web/ (React + TypeScript + react-konva) ─────────────────────────┐
│ split view (reference | draft/output) · point pairs · regions · versions · overlays · modes        │
└──────────────┬──────────────────────────────────────────────────────────────▲──────────────────────┘
               │ REST (JSON, multipart)                                       │ SSE (job events)
┌──────────────▼──────────────────────── server/ (FastAPI, 127.0.0.1 only) ───┴──────────────────────┐
│ routers → services: registry · projects · points · runs/jobs · versions · export · logs           │
│ storage: SQLite (data/app.db) · content-addressed blobs (data/blobs) · embedding caches           │
│ governance: reference gate · usage log (hash chain) · provenance · offline guard                  │
│ orchestrator (pinstyle.pipeline) ──submit──► priority job queue                                   │
└────────────────────────────────────────────────┬──────────────────────────────────────────────────┘
                                                 ▼  the only thread that touches CUDA
┌────────────────────────────────── GPU worker + ModelManager ──────────────────────────────────────┐
│ shared SDXL core: UNet · VAE · ControlNet(s) · attention-processor bank                           │
│   ├─ global path: CSGO  or  IP-Adapter/InstantStyle + ControlNet          (GlobalPath)            │
│   ├─ Engine A: training-free masked correction                            (LocalEngine)           │
│   └─ Engine B: trained point-guided branch                                (LocalEngine)           │
│ SAM 2.1 (masks) · DINOv2 + DISK/LightGlue (matchers) · CSD (confidence, metrics)                  │
│ encoders (ViT-bigG, ViT-H, text) → embedding caches        residency tiers: hot / warm / cold     │
└────────────────────────────────────────────────────────────────────────────────────────────────────┘
CLI and scripts reuse the same library and take the same GPU lock (download_models, smoke_test, run_eval, train_branch, make_figures).
pinstyle.external (network, opt-in, own process) and the baselines in third_party/ (own environments) are never imported by core code.
```

**Process model**

- **Server:** one uvicorn worker. FastAPI handles HTTP on the event loop, and one dedicated GPU worker thread runs all CUDA work. It binds to `127.0.0.1` only.
- **CLI and scripts:** use the same library and the same `ModelManager`. They take the cross-process GPU lock, so they never run while the server holds the GPU.
- **Baselines** (CoCoDiff, MangaNinja, and the official CSGO code for parity): run as subprocesses in their own environments under the gitignored `third_party/`.
- **External comparison:** a separate process with network explicitly enabled.

---

## 3. Repository layout

```
PinStyle/
├── CLAUDE.md
├── README.md                          (M8)
├── pyproject.toml · uv.lock · .python-version (3.11)
├── configs/
│   ├── app.yaml                       offline flag, paths, server, VRAM budget, residency policy
│   ├── models.yaml                    every model: repo, pinned revision, files, sha256, dtype, tier, license, loader
│   ├── global/{csgo,ipa}.yaml         global-path defaults
│   ├── engine/{a,b}.yaml              local-engine defaults (strength mapping, masks, crop mode)
│   ├── matcher/{geometric,semantic}.yaml
│   ├── confidence.yaml · gate.yaml    thresholds (gate thresholds calibrated in M5)
│   ├── train/engine_b_*.yaml          pilot / 768 / 1024
│   ├── eval/*.yaml                    benchmarks × methods × seeds, report definition
│   └── external/*.yaml                provider settings (no keys)
├── docs/                              PROJECT_BRIEF · PLAN · ARCHITECTURE · THIRD_PARTY · EXPERIMENTS · DEMO (M8) · decisions/
├── src/pinstyle/
│   ├── types.py                       PointPair, RegionSettings, GlobalSettings, RegisteredReference, EngineInfo, …
│   ├── geometry.py                    normalized ↔ pixel coordinates, SDXL resolution buckets, crops and their inverses
│   ├── config.py                      OmegaConf structured configs, loading and merging
│   ├── pipeline.py                    orchestrator: gate → global → local → locks → confidence → version → logs
│   ├── runtime/                       model_manager · gpu_worker (queue, priorities, cancel) · gpu_lock · precision · profiling · seeding
│   ├── correspondence/                base (Matcher) · features (dense features + cache) · geometric · semantic · clustering
│   ├── segmentation/                  sam2_masker · ops (dilate, erode, feather, union, hole filling)
│   ├── generation/
│   │   ├── attention/                 processor (PinStyle processor) · layout (token groups) · loaders (CSGO, IP-Adapter, Engine B)
│   │   ├── sdxl_core.py               shared UNet/VAE/ControlNets, pipeline assembly, schedulers
│   │   ├── sampler.py                 img2img with per-pixel strength, step callbacks, cancellation
│   │   ├── global_path/               base (GlobalPath) · csgo · ipa_instantstyle
│   │   ├── local_engine.py            LocalEngine protocol, EngineInfo, engine registry
│   │   ├── engine_a/                  engine · regions (crops, strength mapping, crop mode) · blend
│   │   └── engine_b/                  model (token encoder, injection) · engine · data · losses · train
│   ├── confidence/                    estimator · heatmap · suggest
│   ├── governance/                    registry · fingerprints · gate · offline · provenance · usage_log
│   ├── io/                            imports (PNG/JPG/PSD) · export_png · ora · psd
│   ├── evaluation/                    benchmarks/ (b1, b2, b3) · metrics/ · baselines/ (subprocess adapters) · protocol · report
│   ├── external/                      ⚠ the only network module: providers/ · manual_import · records
│   ├── research/                      probe (RQ1 sheets) · study (RQ3 sessions, CSV)
│   ├── storage/                       db (SQLAlchemy models) · blobs (content-addressed) · caches
│   └── tracking/                      structlog setup, run records, git/environment capture
├── server/                            FastAPI: app (factory) · routers/ · schemas · jobs (SSE) · deps
├── web/                               Vite + React + TS: src/{api,state,canvas,panels,modes} · Vitest · Playwright e2e
├── scripts/                           download_models · smoke_test · make_test_cert · calibrate_gate · prepare_data ·
│                                      extract_points · train_branch · run_eval · make_figures
├── tests/                             unit/ · gpu/ · e2e/ · conftest.py
├── assets/demo/                       rights-cleared images only + MANIFEST.csv (source, license, consent)
├── benchmarks/manifests/              B1–B3 manifests (path, sha256, source, license, consent)
└── (gitignored) models/ · data/ · runs/ · third_party/
```

Changes relative to brief §8:

- **Added** `runtime/` (model residency, GPU queue), `storage/`, `research/`, `pipeline.py`, `generation/attention/`, `benchmarks/manifests/`.
- **Renamed** `logging/` to `tracking/`, so the package can't be confused with the standard library's `logging`.

---

## 4. Core data model

### 4.1 Conventions

- **Images** at interfaces are `PIL.Image.Image`, RGB, 8-bit.
  - On import: EXIF orientation is applied and ICC profiles are converted to sRGB.
  - Transparency is kept, and generation composites the image onto white.
- **Working resolution:** SDXL buckets of about 1 MP (long side 1024 by default, sides multiples of 64). `geometry.py` owns every resize, pad and crop and its inverse. Outputs come back at the original draft size.
- **Coordinates:** normalized `(x, y) ∈ [0, 1]²`, origin top-left, x to the right, y down, relative to the original image. Pixel coordinates exist only inside modules.
- **IDs:**
  - ULIDs (sortable) for works, projects, versions, jobs, runs and exports.
  - Short IDs that stay stable within a project for pairs and regions (`p3`, `r1`).
- **Hashes:** sha256 of the file bytes and of the decoded, normalized pixels. Blobs are content-addressed by sha256.
- **Time:** UTC, ISO-8601.

### 4.2 Types (`pinstyle.types`)

```python
NormXY = tuple[float, float]                    # (x, y) in [0, 1], origin top-left

@dataclass(frozen=True, slots=True)
class PointPair:
    id: str                                     # "p3", stable within a project
    ref_index: int                              # index into the run's references
    ref_xy: NormXY                              # point on the reference
    tgt_xy: NormXY                              # point on the draft / output
    confidence: float | None = None             # matcher score in [0, 1]; None for manual pairs
    source: Literal["geometric", "semantic", "manual"] = "manual"

@dataclass(frozen=True, slots=True)
class RegionSettings:
    region_id: str                              # "r1"
    pair_ids: tuple[str, ...]                   # a region can hold several pairs (several SAM prompts)
    strength: float = 0.6                       # 0..1; each engine maps it (Engine A: IP scale x denoise)
    tags: tuple[str, ...] = ()                  # signature features: "eye highlight", "accessory", free text
    locked: bool = False                        # keep the draft unchanged here
    mask_override: str | None = None            # blob sha256 of an artist-painted target mask

@dataclass(frozen=True, slots=True)
class GlobalSettings:
    path: Literal["csgo", "ipa"] = "csgo"
    style_strength: float = 1.0
    structure_strength: float = 0.6             # ControlNet conditioning scale
    steps: int = 30
    guidance: float = 7.0
    resolution: int = 1024                      # long side
    prompt: str = ""                            # optional

class RegisteredReference:
    """A reference image that passed the gate. Only governance.gate.admit() can construct one
    (the constructor checks a module-private token), so engines cannot receive raw images."""
    work_id: str
    sha256: str
    def image(self) -> Image.Image: ...

@dataclass(frozen=True, slots=True)
class MaskPair:
    target: np.ndarray                          # float32 HxW in [0, 1], feathered, output size
    reference: np.ndarray                       # float32 HxW in [0, 1], reference size

class EngineInfo(TypedDict):
    engine: str                                 # "engine_a" / "engine_b"
    engine_version: str                         # code version + checkpoint hash
    seed: int
    masks: dict[str, MaskPair]                  # region_id -> masks actually used
    layers: dict[str, Image.Image]              # region_id -> RGBA correction layer (for ORA/PSD export)
    params: dict[str, dict[str, float]]         # region_id -> values actually used (e.g. ip_scale, denoise)
    timings_ms: dict[str, float]
    models: dict[str, str]                      # model key -> pinned revision
    warnings: list[str]
```

### 4.3 Persistence

- **SQLite** at `data/app.db`, via SQLAlchemy 2.x. Tables:
  - `works`: fingerprints and authorship declaration;
  - `projects` and `project_references`;
  - `versions`: parent, run ID, mode, engine, inputs (pairs, regions, settings, seed), output and layer blobs, confidence, status;
  - `project_head`: undo/redo pointer;
  - `jobs` and `exports`;
  - `annotations`;
  - `study_sessions` and `study_events`.
- **Blobs** live at `data/blobs/ab/cd/<sha256>.<ext>`: drafts, outputs, masks, layers, heatmaps, previews.
- **Governance events** are recorded in the hash-chained usage log (§12.5), which is their single source of truth.

---

## 5. Interfaces

### 5.1 `LocalEngine`

```python
class ProgressFn(Protocol):
    def __call__(self, stage: str, step: int, total: int) -> None: ...   # raises JobCancelled to stop

@runtime_checkable
class LocalEngine(Protocol):
    name: str                                   # "engine_a" / "engine_b"
    version: str

    def apply(
        self,
        global_output: Image.Image,
        draft: Image.Image,
        references: Sequence[RegisteredReference],
        point_pairs: Sequence[PointPair],
        region_settings: Sequence[RegionSettings],
        *,
        seed: int,
        progress: ProgressFn | None = None,
    ) -> tuple[Image.Image, EngineInfo]: ...
```

Contract:

- **Signature.** The positional parameters are exactly those in the brief. `seed` and `progress` are keyword-only additions. `EngineInfo` is a `TypedDict`, so the brief's `tuple[Image, dict]` still holds.
- **Sizes.** `global_output` and `draft` have the same size, and the returned image has that size too.
- **Pairs and regions.** Each pair used belongs to exactly one region. Pairs that belong to no region are ignored with a warning.
- **Locks.** Locked regions are passed through but need no special handling: the orchestrator applies locks after the engine runs (§7.7).
- **Determinism.** The result is a function of the inputs, the seed and the model revisions, up to GPU nondeterminism.
- **Isolation.**
  - no network;
  - no file I/O outside the caches;
  - models only through `ModelManager`;
  - all CUDA work on the GPU worker thread.
- **Progress.** Call `progress` at least once per denoising step and stop promptly on `JobCancelled`.
- **Reproducibility.** Report the values actually used (after strength mapping) in `EngineInfo.params`, so a version node is enough to reproduce a run.

### 5.2 Other interfaces

```python
class GlobalPath(Protocol):
    name: str                                   # "csgo" / "ipa"
    version: str
    def run(self, draft: Image.Image, references: Sequence[RegisteredReference], settings: GlobalSettings,
            *, seed: int, progress: ProgressFn | None = None) -> tuple[Image.Image, dict[str, Any]]: ...

class Matcher(Protocol):
    name: str                                   # "geometric" / "semantic"
    def suggest(self, reference: RegisteredReference, target: Image.Image, *, ref_index: int,
                max_pairs: int = 8, roi: NormBox | None = None) -> list[PointPair]: ...

class Masker(Protocol):
    def mask(self, image: Image.Image, positive: Sequence[NormXY],
             negative: Sequence[NormXY] = ()) -> np.ndarray: ...          # float32 HxW in [0, 1]

class ConfidenceEstimator(Protocol):
    def compute(self, output: Image.Image, references: Sequence[RegisteredReference],
                point_pairs: Sequence[PointPair], region_settings: Sequence[RegionSettings],
                masks: Mapping[str, MaskPair]) -> ConfidenceResult: ...
    # ConfidenceResult: heatmap (float32 HxW), per-region scores, flagged boxes, suggested PointPairs
```

Implementations are registered by name (for example `ENGINES = {"engine_a": …, "engine_b": …}`). Configs and requests choose them by name, and `/api/health` lists what is available.

---

## 6. Data flow

### 6.1 Main flow (brief §2)

```
register own works ──► pick reference(s) + draft ──► suggest pairs ──► artist edits pairs / regions / tags / strength / locks
  (fingerprints,          (gate.admit)                 (Matcher)          (saved with every run)
   embeddings cached)
        └──────────► run:  global pass ─► SAM 2 masks ─► local engine ─► lock composite ─► confidence map
                                                                                              │
          export PNG / ORA / PSD + provenance  ◄──  artist iterates (each run = new version)  ◄┘
Every step writes structured logs and a run record. Governance events also go to the hash-chained usage log.
```

### 6.2 A "global + local" run, step by step

1. **Submit.** The UI sends `POST /api/projects/{pid}/runs` with the mode, engine, global settings, seed and parent version. The server creates a job and a pending version node, and the job joins the GPU queue.
2. **Resolve inputs.** Load the draft blob. Each reference goes through `gate.admit(work_id)` and comes back as a `RegisteredReference`; a rejection ends the job with `reference_not_registered`.
3. **Global pass.** `global_out = global_path.run(draft, refs, settings, seed)`. In "local only" mode this is skipped and `global_out` is the parent version's output.
4. **Masks.** SAM 2 runs per region, on the target and on the reference. Results are cached by (image hash, prompts).
5. **Local pass.** `out, info = engine.apply(global_out, draft, refs, pairs, regions, seed=…, progress=…)`.
6. **Locks.** `out = M_lock · draft + (1 − M_lock) · out`, computed by the orchestrator only.
7. **Persist.** Write blobs (output, layers, masks), finish the version node, and write the run record.
8. **Log.** Append a `used_in_run` usage-log event (work IDs, version ID). SSE sends `done{version_id, run_id}`.
9. **Confidence.** Optionally, a lower-priority confidence job attaches a heatmap to the version.

### 6.3 Registration

1. The artist uploads a work with an authorship declaration (checkbox plus text) and, optionally, a portfolio URL. The URL is stored but never fetched.
2. The image is imported (PNG/JPG, or a flattened PSD), normalized, and stored as a blob.
3. Fingerprints are computed: file sha256, pixel sha256, pHash and dHash (imagehash), and a DINOv2 global embedding.
4. A background job computes and caches the encoder inputs for CSGO (ViT-bigG) and IP-Adapter (ViT-H), DINOv2 patch features and the CSD embedding.
5. A `registered` usage-log event is appended.

### 6.4 Export

1. Build layers for the selected version: global result, per-region corrections, masks, draft. Write PNG, ORA or PSD (§13).
2. Attach provenance (§12.4): a C2PA manifest where the format allows, a JSON sidecar and PNG text chunks.
3. Append an `exported` usage-log event (work IDs, version, export, file hashes). The log's head hash is embedded in the provenance.

---

## 7. Generation subsystem

### 7.1 Shared SDXL core

- **One instance of each model:** one SDXL UNet and one VAE (fp16 fix); text encoders in the warm tier; the Tile ControlNet (CSGO) and one structure ControlNet; schedulers.
- **Thin pipelines.** They are diffusers SDXL ControlNet img2img/inpaint pipelines assembled from the shared modules (`from_pipe` shares modules without copying them). No pipeline owns its own UNet.
- **Defaults to profile in M1.** DPM-Solver++ 2M with Karras sigmas, 25–30 steps (CSGO's README uses 50); SDPA attention; VAE tiling at 1024 px and above.

### 7.2 Attention-processor bank ([ADR-0002](decisions/0002-csgo-integration.md))

- **Installed once.** A single custom processor class goes on every cross-attention layer of the UNet and of the Tile ControlNet.
- **Token layout:** `encoder_hidden_states = [text (77) | group 1 | group 2 | …]`. Concatenating the image tokens, as CSGO does, means the ControlNet sees them too.
- **`TokenGroup`.** Each group has:
  - a name and a token slice;
  - a K/V projection set: `csgo_content`, `csgo_style`, `ipa_plus` or `engine_b`;
  - a scale: a scalar, or a per-block map such as InstantStyle's `up.block_0`;
  - the blocks it is active in;
  - an optional spatial weight (H×W in [0, 1]), resized to each layer's attention map;
  - an optional gate.
- **Per-layer output:** `h = Attn_text(h) + Σ_g scale_g · m_g ⊙ Attn_g(h)`. `Attn_g` uses the group's own K/V projections, and `m_g` is its resized spatial weight (1 when absent).
- **Switching paths and engines.** The orchestrator sets the layout for each call in a context object that the processors read. The processors stay installed, so switching between the global path, Engine A and Engine B only changes the layout and never reloads the UNet.
- **Weight loaders:**
  - CSGO `csgo_4_32.bin`: content and style resamplers, plus K/V for both UNet and ControlNet;
  - IP-Adapter Plus SDXL: resampler plus K/V;
  - the Engine B checkpoint.
- **Parity requirement (M1).** With layout `[csgo_content, csgo_style]` and no masks, the output must match the official CSGO code (target LPIPS < 0.02 at the same seed and settings).

### 7.3 Sampling with per-pixel strength

- A local correction is img2img from the global output. Each pixel gets a denoising strength from a region map `S(x) ∈ [0, 1]`, which is 0 outside regions.
- **Implementation** (differential-diffusion style): start at the highest strength in `S`. At each step, wherever `S(x)` is below the current progress, reset the latents to the global output's latents noised to the current timestep. In diffusers this runs in `callback_on_step_end`; a small custom loop is the fallback (*decide in M2*).
- **Blending.** Decode once, then blend into the global output in pixel space with the feathered mask. Pixels outside regions stay untouched, so they avoid a VAE round trip.

### 7.4 Global path

- **CSGO.**
  - The draft is the content image: it is the Tile ControlNet condition and the source of the content tokens.
  - The reference is the style image: it supplies the style tokens.
  - Exposed settings: style strength, content scale, structure strength (ControlNet conditioning scale), steps, guidance, resolution, seed, optional prompt.
- **Alternative.** IP-Adapter Plus with InstantStyle block selection, plus a structure ControlNet on the draft's line art.
- **Several references.** Concatenate or average the style tokens (*decide in M1*). A single reference is the default.

### 7.5 Engine A — training-free (brief §4.2)

1. **Masks.** For each region:
   - run SAM 2.1 on the target (the global output by default; the draft optionally), with the region's target points as positive prompts and the other regions' points as negative prompts;
   - run it on the reference with the reference points;
   - dilate (default 8 px at 1024) and feather (Gaussian, default σ = 6 px).
2. **Reference conditioning.** Crop the reference around its mask (bounding box plus 15 % margin) and grey out pixels outside the mask. Encode it into regional tokens with the CSGO style resampler or IP-Adapter Plus.
3. **Masked injection.**
   - One token group per region, using its target mask as the spatial weight.
   - One global-reference group on the complement of all region masks, which keeps the surroundings consistent.
4. **Masked regeneration.**
   - img2img on the global output with the per-pixel strength map (§7.3) and the structure ControlNet on the draft's line art;
   - then a feathered blend in pixel space;
   - one RGBA layer per region is kept for export.
5. **Strength mapping.** A region strength `s` sets:
   - IP scale `a_min + (a_max − a_min)·s`;
   - denoise `d_min + (d_max − d_min)·s`.

   Initial ranges are 0.4–1.0 and 0.3–0.85, tuned in M2. This is the brief's "IP-Adapter scale × denoising strength".
6. **Crop mode for small regions** (the necklace).
   - When: a region's box is smaller than about 35 % of the image side.
   - What: process a context crop upscaled to about 1 MP, then downscale it and paste it back with the feathered mask. This gives a small detail many more latent pixels.
   - Cost: one pass per small region, estimated at 5–8 s each.

**Two variants, compared in M2** (planned ADR). Both run on the same UNet through the processor bank.

- **A1, inside CSGO:** masked regional CSGO style groups, with the Tile ControlNet.
- **A2, separate pass:** regional IP-Adapter Plus groups, masked the way diffusers does it, plus the structure ControlNet.

### 7.6 Engine B — trained branch (brief §4.3; training in PLAN M7)

- **Token encoder** (one set of tokens per pair):
  - sample a k×k window (k ≈ 5–9 patches) of frozen image-encoder patch tokens around the reference point (ViT-H, optionally DINOv2), bilinear and sub-patch accurate;
  - add Fourier features of the target location;
  - a small transformer/Perceiver (2–4 layers) produces about 8 local tokens.
- **Injection.** Each pair gets one extra token group in selected up-block cross-attention layers, with:
  - new K/V projections, initialized from CSGO's style K/V;
  - a spatial weight around the target point (Gaussian in training; SAM mask or Gaussian at inference);
  - a per-layer gate initialized to zero, so an untrained branch reproduces CSGO exactly (unit-tested).
- **What trains.** Trainable: the token encoder, the new K/V projections and the gates. Frozen: SDXL, the CSGO adapters, the ControlNet and the encoders.
- **Integration.** Engine B implements `LocalEngine`, so the app and experiments switch between A and B by name.

### 7.7 Locks and compositing

- **The only place locks are applied.** After the local engine, the orchestrator computes `out = M_lock · draft + (1 − M_lock) · out`, with a hard mask and a 1–2 px anti-aliased edge.
- **Guarantee.** Locks therefore hold for every engine and global path. A unit test checks that locked pixels equal the draft.
- **Neighbouring areas.** The global pass still sees the whole draft, so areas next to a lock stay coherent.

### 7.8 Confidence map (brief §4.4)

- **Per-region signals:**
  - (a) DINOv2 agreement: for each output patch inside the target mask, the maximum cosine similarity to patches inside the reference mask, averaged over patches;
  - (b) CSD similarity between the output crop and the reference crop, CSLS-normalized against a fixed bank of unrelated crops (THIRD_PARTY F7);
  - (c) optionally, variance across 2–3 low-resolution seeds (512 px, few steps).
- **Areas outside regions.** Each patch gets its maximum DINOv2 similarity to any reference patch. Low values mark areas with no counterpart in the reference.
- **Score and suggestions.**
  - Combine `c = w1·dino + w2·csd − w3·var` and normalize per image to [0, 1] using robust percentiles.
  - Apply a threshold τ (calibrated in M4) to flag regions.
  - "Suggest a point here": run the semantic matcher inside each flagged area and propose its best pair.
- **Output:** a single-channel heatmap blob (colour-mapped in the browser), per-region scores and suggested pairs.

---

## 8. Correspondence and segmentation

- **Geometric matcher.**
  1. DISK finds up to 2048 keypoints per image at about 1024 px.
  2. LightGlue matches them (`features="disk"`).
  3. Keep matches with LightGlue confidence ≥ τ_lg and DINOv2 patch cosine ≥ τ_d at both ends.
  4. Cluster in target space (k-means or NMS), take the best match per cluster, and return the top K.

  There is no global RANSAC: poses differ and the deformation is non-rigid.
- **Semantic matcher.**
  1. Extract dense DINOv2-L/14 (registers) features at 448–672 px, giving 32×32 to 48×48 patches. Optionally fuse them with SDXL UNet decoder features at one timestep (L2-normalize each source, then concatenate).
  2. Take mutual nearest neighbours by cosine similarity.
  3. Apply a foreground/saliency filter (*decide in M4*) and keep pairs with similarity ≥ τ.
  4. Run k-means on target coordinates, weighted by similarity, and keep the best pair per cluster.
  5. Refine to sub-patch accuracy with a soft-argmax in a 3×3 window, and return the top K with calibrated confidence.
- **Comparison (M4).** Both matchers sit behind `Matcher`. They are scored with PCK@α and precision@K on the B1 validation set and on owner-annotated pairs, comparing LightGlue alone, the geometric pipeline and the semantic pipeline. The result sets the default matcher (planned ADR).
- **SAM 2.**
  - Use `SAM2ImagePredictor`, or the transformers port (*decide in M0*), under bf16 autocast.
  - The image embedding is cached per image sha256, so each image is encoded once and later clicks only run the decoder.
  - Prompts: several points, with negatives. With `multimask_output=True`, keep the highest-scoring mask. Post-processing lives in `segmentation/ops.py`.
- **Feature caches.** Dense features are cached in memory (LRU) and on disk, keyed by (image sha256, model revision, resolution).

---

## 9. Model loading and VRAM residency ([ADR-0005](decisions/0005-model-residency.md))

### 9.1 Model registry: `configs/models.yaml`

```yaml
sdxl_unet:
  repo: stabilityai/stable-diffusion-xl-base-1.0
  revision: <commit sha, pinned in M0>
  files: [unet/config.json, unet/diffusion_pytorch_model.fp16.safetensors]
  sha256: {unet/diffusion_pytorch_model.fp16.safetensors: <hash>}
  dtype: fp16
  tier: hot
  est_gib: 5.1
  license: CreativeML Open RAIL++-M
  loader: pinstyle.generation.sdxl_core:load_unet
```

- **Downloading.** `scripts/download_models.py` is the only code that downloads anything.
  - It uses `huggingface_hub` with `allow_patterns` and the pinned revision, and verifies sha256.
  - It handles renames (the TTPlanet file becomes `diffusion_pytorch_model.safetensors`) and converts the CSD pickle to safetensors.
  - It writes `models/MANIFEST.json`.
- **At runtime** everything loads from `models/` with `HF_HUB_OFFLINE=1`.

### 9.2 `ModelManager`

```python
class ModelManager:
    def __init__(self, specs: Mapping[str, ModelSpec], *, budget_gib: float, device: str = "cuda") -> None: ...
    def warmup(self) -> None: ...              # load the hot tier, run tiny forwards, record measured VRAM
    def get(self, key: str) -> torch.nn.Module: ...      # lazy load from models/ (never downloads)
    def on_gpu(self, *keys: str) -> ContextManager[tuple[torch.nn.Module, ...]]: ...
        # make keys resident; evict warm models (LRU) if headroom is short; restore tier policy on exit
    def report(self) -> list[ResidencyRow]: ...          # key, tier, device, estimated vs measured bytes
    def release_gpu(self) -> None: ...         # move everything off the GPU (hand over to training / eval)
```

Only the GPU worker thread calls it, and feature code never calls `.to("cuda")` itself.

### 9.3 Tiers (estimates from THIRD_PARTY.md §9; replaced by M0 measurements)

| Tier | Where it lives | Models | Est. GB |
|---|---|---|---|
| hot | on the GPU from warm-up to shutdown | SDXL UNet, VAE, Tile ControlNet, CSGO adapters, structure ControlNet, IP-Adapter Plus, SAM 2.1-L, DINOv2-L/14-reg, DISK + LightGlue; Engine B branch after M7 | ≈ 14.3 (+ ≤ 0.5) |
| warm | pinned CPU RAM; moved to the GPU for a job, evicted LRU | SDXL text encoders, ViT-bigG and ViT-H image encoders, CSD | ≈ 7.8 |
| cold | separate processes and environments | CoCoDiff, MangaNinja, official CSGO (parity), external services | – |

**Budget.** `runtime.vram_budget_gib` defaults to 22.5. Each job type reserves headroom for activations (initial values: 6 GiB for 1024 px generation, 1 GiB for segmentation; measured in M0–M2), and the manager evicts warm models until the reserve fits. If the hot set alone does not fit, startup fails with a clear message. The interactive path never falls back silently to CPU offload.

### 9.4 Embedding caches

- **Key:** (model key, revision, image sha256, parameters).
- **What is cached:**
  - encoder hidden states for references and drafts (CSGO and IP-Adapter inputs);
  - DINOv2 patch features;
  - CSD embeddings;
  - prompt embeddings, keyed by prompt text.
- **When.** They are computed in background jobs at registration and on upload, so generation rarely needs warm models.
- **Region crops** are encoded on demand. The first use moves an encoder to the GPU, estimated at 0.2–0.5 s for 1.3–3.7 GB over PCIe 4.0.

### 9.5 GPU worker, queue and lock

- **One thread owns CUDA.** Jobs run one at a time, as the brief requires.
- **Priorities:** interactive (segment, suggest) > generate and confidence > background (embeddings). Interactive jobs jump the queue but never preempt a running job. A running generation can be cancelled; cancellation is checked at every denoising step.
- **Each job** has an ID, a type, a priority, parameters, a status (queued, running, done, failed, cancelled), progress events, a result reference and a run record.
- **Cross-process lock.** `runs/.gpu.lock` is a file lock. The server takes it at startup, and the training, evaluation and smoke-test scripts take it too.
- **Training while the server is up.** `POST /api/admin/release-gpu` unloads the models and releases the lock. Until `POST /api/admin/acquire-gpu`, GPU requests get a 503 `gpu_released`.

### 9.6 Precision and memory hygiene

- **Precision.**
  - SDXL inference in fp16, with the fp16-fix VAE;
  - SAM 2 under bf16 autocast;
  - DINOv2 and CSD in fp16;
  - Engine B training in bf16, with fp32 master weights for the trainable parameters;
  - TF32 matmul enabled.
- **Memory.**
  - SDPA attention, so xformers is not needed;
  - VAE tiling at 1024 px and above;
  - `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`;
  - `torch.cuda.empty_cache()` after evictions.
- **Measurement.** Peak memory is recorded for every job.

### 9.7 Start-up

1. Enforce offline mode.
2. Take the GPU lock.
3. Load the hot tier.
4. Run tiny warm-up passes: SDXL for 2 steps at 512², a SAM 2 encode, DINOv2 and LightGlue.
5. Measure VRAM.
6. `/api/health` reports ready, with the residency table.

Estimated at 30–60 s, to be measured.

---

## 10. Backend API

### 10.1 Conventions

- **Transport.** JSON over HTTP on `127.0.0.1`. CORS is open only to the Vite dev origin.
- **No accounts:** one local user (brief §11).
- **Schemas.** pydantic schemas produce the OpenAPI spec, which generates the TypeScript types.
- **Errors** are `application/problem+json` with a stable `code`: `reference_not_registered`, `gpu_busy`, `gpu_released`, `offline_violation`, `job_cancelled`.
- **GPU work** runs as jobs with SSE progress (chosen over WebSocket: the stream is one-way and plain HTTP is enough).
- **Images** are served from content-addressed `/api/files/{sha256}`.

### 10.2 Endpoints

| Area | Method and path | Purpose |
|---|---|---|
| System | `GET /api/health` | Readiness, offline flag, GPU, residency table, available engines, paths and matchers |
| | `POST /api/admin/release-gpu` · `POST /api/admin/acquire-gpu` | Hand the GPU to training/eval scripts and take it back |
| Registry | `POST /api/registry/works` | Register an own work: file + authorship declaration (+ optional portfolio URL, stored, never fetched) |
| | `GET /api/registry/works` · `GET/PATCH/DELETE /api/registry/works/{work_id}` | List, inspect, edit metadata, soft-delete (logged) |
| | `POST /api/registry/check` | Run the gate on an image without registering it |
| Projects | `POST /api/projects` · `GET /api/projects` · `GET /api/projects/{pid}` | Create, list, load (including HEAD version, pairs and regions) |
| | `PUT /api/projects/{pid}/draft` | Upload the draft (hashed and logged) |
| | `PUT /api/projects/{pid}/references` | Set references by `work_id`; gate decision per reference; 422 `reference_not_registered` on failure |
| Points | `POST /api/projects/{pid}/points/suggest` | Matcher, `ref_index`, `max_pairs`, optional ROI → suggested pairs (GPU job, awaited; target < 2 s) |
| | `PUT /api/projects/{pid}/points` | Save edited pairs and regions (tags, strength, lock, mask override) |
| Masks | `POST /api/projects/{pid}/masks` | Points (+ negatives) on the draft, output or reference → mask (GPU job, awaited; target < 0.5 s) |
| Runs | `POST /api/projects/{pid}/runs` | Mode `global`, `global_local` or `local`; engine; global settings; seed; parent version → `{job_id, version_id}` |
| Jobs | `GET /api/jobs/{job_id}` · `GET /api/jobs/{job_id}/events` (SSE) · `DELETE /api/jobs/{job_id}` | Status, progress stream, cancel |
| Versions | `GET /api/projects/{pid}/versions` | Version tree + HEAD |
| | `GET /api/versions/{vid}` | Inputs, settings, outputs, metrics, run ID |
| | `PUT /api/projects/{pid}/head` | Undo, redo or jump (moves HEAD) |
| | `GET /api/versions/{a}/diff/{b}` | Differences in settings and pairs (images are compared with the UI slider) |
| Confidence | `POST /api/versions/{vid}/confidence` · `GET /api/versions/{vid}/confidence` | Compute (job) or fetch the heatmap, region scores and suggestions |
| Export | `POST /api/versions/{vid}/exports` · `GET /api/exports/{eid}/download` | PNG, ORA or PSD with provenance options; download |
| Logs | `GET /api/logs/usage` · `GET /api/logs/usage/verify` | Paginated usage log; chain verification |
| Files | `GET /api/files/{sha256}` | Content-addressed images (`?w=` for thumbnails) |
| Benchmarks | `POST /api/annotations` · `GET /api/annotations` | Annotation mode (B3) |
| RQ1 | `POST /api/probe/sheets` · `GET /api/probe/sheets/{id}` | Build and export a three-level probe sheet |
| RQ3 | `POST /api/study/sessions` · `POST /api/study/sessions/{sid}/events` · `POST /api/study/sessions/{sid}/end` · `GET /api/study/sessions/{sid}/export.csv` · `GET /api/study/export.csv` | Study sessions, event logging, CSV export |

### 10.3 SSE events

| Event | Fields / meaning |
|---|---|
| `queued` | `{position}` |
| `started` | the job began running |
| `stage` | `{name}`: gate, global, masks, local, compose, confidence, persist |
| `progress` | `{stage, step, total}` |
| `preview` | `{blob}`: optional low-res preview every N steps |
| `done` | `{version_id, run_id}` |
| `error` | `{code, detail}` |
| `cancelled` | the job was cancelled |

---

## 11. Frontend (`web/`)

- **Stack:**
  - Vite + React + TypeScript (strict), react-konva;
  - Zustand for client state (pair/region edits with local undo, view state);
  - TanStack Query for server state;
  - API types generated with openapi-typescript;
  - `EventSource` for SSE.
- **Layout.** The reference is on the left and the draft or output on the right. Zoom and pan can be synced or independent. Overlay toggles cover masks, points and the heatmap. A version strip offers a before/after slider between any two versions.
- **Canvas layers** (per side, bottom to top):
  1. the image;
  2. the mask overlay;
  3. the heatmap overlay;
  4. point markers, labelled with ID and colour (suggested pairs are dashed and show their confidence until accepted);
  5. the guide line for a pair being created.
- **Interactions:**
  - **Pairs.** Click the reference, then the draft, to add a pair. Drag a point to move it, and press Delete to remove it.
  - **Regions.** Select several pairs and choose "merge into region".
  - **Region panel:** strength slider, tag presets plus free text, lock toggle, and a mask brush as a fallback.
  - **Run controls.** A global settings panel, buttons for the three run modes, and progress with cancel.
- **Modes:**
  - edit (default);
  - annotate (B3 region-pair annotation);
  - probe (the RQ1 sheet builder);
  - study (wraps edit mode and streams UI events to the study log).
- **Images.** The canvas shows downscaled previews (`?w=`); full resolution is used only for processing and export.
- **Tests:** Vitest with React Testing Library; Playwright end-to-end tests against the backend in fake-GPU mode.

---

## 12. Governance

### 12.1 Registry and fingerprints

Each work stores:

- file sha256 and pixel sha256;
- pHash and dHash (64-bit);
- an L2-normalized DINOv2 global embedding;
- the authorship declaration (text and timestamp);
- an optional portfolio URL (stored as text and never fetched);
- a status (active or deleted).

Encoder caches are filled in the background after registration (§6.3).

### 12.2 Reference gate

`gate.admit(image_or_work_id)` returns either a `RegisteredReference` or a `GateRejection`. It applies these rules in order:

1. **Exact match:** the pixel sha256 or the file sha256 equals that of a registered work.
2. **Near-duplicate:** either
   - pHash Hamming distance ≤ T_p **and** dHash Hamming distance ≤ T_d, or
   - DINOv2 cosine ≥ T_e **and** pHash Hamming distance ≤ T_p2.

   Thresholds live in `configs/gate.yaml` and are calibrated in M5. The calibration set has augmented copies of registered works as positives and other works as negatives, including unregistered works by the same artist. The target is zero false accepts on that set.
3. **Otherwise reject**, with the message: "This image doesn't match any of your registered works. Register it first — only your own registered work can be used as a reference."

Further rules:

- **Logging.** Every decision (accept or reject, which rule matched, and the distances) is written as a usage-log event.
- **Only registered works are offered.** The UI lists only registered works as references, and uploading a new reference goes through registration, including the authorship declaration.
- **Limits** (out of scope per the brief; documented):
  - authorship is self-declared;
  - adversarial edits can evade perceptual hashes;
  - a false declaration can register someone else's work.

### 12.3 Local-first enforcement

- **Default.** `offline: true` is the default in `configs/app.yaml`.
- **At process start**, `governance.offline.enforce()`:
  - sets `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1` and `HF_DATASETS_OFFLINE=1`;
  - disables torch.hub downloads;
  - installs a socket guard that patches `socket.socket.connect`, `socket.create_connection` and `socket.getaddrinfo`. Only loopback and Unix sockets are allowed; anything else raises `OfflineViolation`, which is logged.
- **Tests.**
  - pytest-socket blocks every socket except 127.0.0.1 and ::1.
  - One test proves the guard blocks outbound connections.
  - A full run with `offline: true` must make zero non-loopback connection attempts.
- **Static check.** An import-linter contract forbids importing `pinstyle.external` from any other `pinstyle` module or from `server`.
- **Opt-in network.** `pinstyle.external` and `scripts/download_models.py` refuse to run unless `offline: false` is set and `--allow-network` is passed.

### 12.4 Provenance

- **C2PA manifest** (PNG, and ORA's merged image if supported):
  - `claim_generator_info`: PinStyle and its version.
  - `c2pa.actions`:
    - `c2pa.opened`, with the draft as a `parentOf` ingredient;
    - `c2pa.edited`, with `digitalSourceType` = IPTC `compositeWithTrainedAlgorithmicMedia`, `softwareAgent` = PinStyle plus the engine, description "AI-assisted finishing", and a settings summary as parameters.
  - **Ingredients:** each reference work, with its sha256 and work ID. The relationship is `componentOf`, or `inputTo` if the installed c2pa version supports it (*decide in M5*).
  - **Custom assertion `org.pinstyle.run`:** engine and version, model revisions, seed, pairs, regions, settings, and the usage-log head hash.
  - **Optional:** a training-and-mining assertion recording the artist's choice (*decide in M5*).
- **Signing.**
  - Uses the local test certificate (ES256), with no timestamp authority (offline).
  - Expected validation result: valid but untrusted (THIRD_PARTY §6.1).
- **Always written as well:**
  - a JSON sidecar `<name>.provenance.json` (the same content plus the C2PA status);
  - PNG iTXt chunks: `pinstyle:provenance` (compact JSON) and `ai_assisted: true`.

  Exports are labelled AI-assisted in both the UI and the metadata.

### 12.5 Usage log

- **File and format.** `data/logs/usage.jsonl`, append-only.
  - Each record: `{seq, ts, event, work_ids, project_id, version_id, export_id, details, prev_hash, hash}`.
  - `hash = sha256(prev_hash + canonical_json(record without hash))`.
  - The genesis `prev_hash` is 64 zeros.
- **Events:** `registered`, `deleted`, `gate_decision`, `used_in_run`, `exported`, `log_verified`.
- **Appending and verifying.**
  - Appends take a file lock and fsync.
  - `verify()` recomputes the chain and reports the first bad `seq`.
  - Each export embeds the current head hash in its provenance, so a truncated log can be detected against exported files.
- **UI:** a viewer with filters (by work, by export) and a verification badge.
- **Limit (documented).** The log is tamper-evident, not tamper-proof: someone with file access can rewrite the whole chain. Head hashes anchored in exports limit what they can hide.

---

## 13. File exchange (brief §6)

- **Import.**
  - PNG/JPG: through Pillow; EXIF orientation is applied and ICC profiles are converted to sRGB.
  - PSD: through psd-tools. Use the merged image stored in the file if there is one; otherwise use psd-tools compositing and warn that it may differ from Photoshop.
  - Transparency is kept.
- **PNG export:** the final image plus provenance.
- **ORA export** (own writer). The layer stack, top to bottom:
  1. one correction layer per region (RGBA, named with the region ID and tags);
  2. a `masks` group (hidden);
  3. the global result;
  4. the draft (hidden).

  `mergedimage.png` holds the final image, alongside a thumbnail. `pinstyle/provenance.json` is stored inside the archive; readers should ignore unknown entries (verify in M5).
- **PSD export** (psd-tools, best effort): the same structure as groups and pixel layers, with provenance as a sidecar.

---

## 14. Research tooling (brief §7)

- **Benchmarks** (`evaluation/benchmarks/`). All are manifest-driven: each image has a path, sha256, source, license and consent reference, and a checker refuses images not in a manifest.
  - **B1:** a held-out OmniStyle subset with manually checked correspondences.
  - **B2** (own-style propagation):
    - draft: synthesized with TEED line art plus flat-colour quantization;
    - reference: another work by the same artist;
    - ground truth: the original illustration.
  - **B3:** annotated region pairs from annotation mode.
- **Metrics** (`evaluation/metrics/`):
  - regional accuracy (defined as DINOv2 and CSD agreement thresholds on annotated region pairs, plus human spot checks);
  - DINOv2 regional consistency;
  - CSD, global and per region, both raw and CSLS-normalized;
  - LPIPS and SSIM against ground truth (B2);
  - structure preservation (edge F1 or chamfer distance between the draft's line art and the output's);
  - latency;
  - corrections until an acceptable result (from study and run logs).
- **Baselines** (`evaluation/baselines/`):
  - in-process: CSGO alone; IP-Adapter/InstantStyle + ControlNet;
  - subprocess adapters into their own `third_party/` environments, behind a shared I/O contract: CoCoDiff, MangaNinja.
- **External comparison** (`pinstyle.external`):
  - provider adapters, plus manual import (for example Midjourney);
  - consent checks and call records ([ADR-0004](decisions/0004-external-services-policy.md));
  - failure-taxonomy labels: lost detail, misplaced detail, style drift, structure change, not controllable.
- **Report.**
  - `scripts/run_eval.py --config configs/eval/report.yaml` runs benchmarks × methods × seeds and writes run records.
  - `evaluation/report.py` builds tables and figures from run records only.
  - `scripts/make_figures.py` draws comparison grids, the necklace sequence and ablation plots.
- **RQ1 probe builder** (`research/probe.py`): the same draft at three control levels (fully automatic end-to-end, point-guided PinStyle, manual without AI), exported as a side-by-side sheet (PNG/PDF) with captions and process statistics.
- **RQ3 study logging** (`research/study.py`):
  - sessions: pseudonymous participant code, condition, task;
  - recorded: the UI event stream, task time, edits, corrections and the accepted result;
  - outputs: CSV export, and a questionnaire link template that the participant opens (the server never calls it).

---

## 15. Reproducibility and logging

- **Logs.** structlog writes JSON logs (`runs/<run_id>/log.jsonl` for CLI runs and jobs; `data/logs/server.jsonl` for the server), with the run or job ID bound to every line.
- **Run record** (`runs/<run_id>/record.json`):
  - run ID, kind and timestamps;
  - git commit, dirty flag and diff hash;
  - the resolved config;
  - seeds;
  - input hashes;
  - model keys with their revisions and sha256;
  - environment: Python, torch, diffusers, CUDA, driver, GPU;
  - timings, peak VRAM, output hashes and metrics.
- **Report scripts** refuse to run on a dirty tree unless given `--allow-dirty`, in which case the diff hash is recorded. `docs/EXPERIMENTS.md` cites a run ID for every number.
- **Seeds.** Each run has one user-visible seed, and component seeds are derived from it deterministically (the seed plus a stable hash of the region ID). Full GPU determinism is not enforced, for speed; golden tests compare against LPIPS tolerances.

---

## 16. Testing strategy

| Suite | Runs on | Contents |
|---|---|---|
| `tests/unit` (default) | Windows laptop and the 4090 box; CPU; sockets blocked | Types and geometry, mask ops, gate logic (synthetic images), usage-log chain and tamper detection, ORA/PSD round trips, provenance sidecar, offline guard, API with fake engines, matcher post-processing on synthetic features, lock compositing |
| `tests/gpu` (`-m gpu`) | 4090 | Warm-up and residency, VRAM budget assertions, one-step generation per path, SAM 2, DINOv2, CSGO parity (M1), zero-init Engine B equals CSGO |
| `-m bench` | 4090 | Latency targets: suggestion < 2 s, mask < 0.5 s, local correction around 20 s or less at 1024 px |
| `tests/e2e` + Playwright in `web/` | any machine | Browser flows against the server in fake-GPU mode (`PINSTYLE_FAKE_GPU=1`: deterministic stand-in images, no models loaded) |

---

## 17. Configuration

- **How configs merge.** OmegaConf structured configs (dataclasses in `pinstyle.config`) plus YAML files in `configs/`, merged in this order:
  1. defaults;
  2. `configs/app.yaml`;
  3. component files;
  4. CLI `key=value` overrides (Typer CLI `pinstyle …`).

  The resolved config is saved in every run record.
- **No Hydra for now.** Its working-directory and multirun conventions add complexity, and our own ablation runner covers sweeps. This is easy to reverse.

---

## 18. Decisions and open design questions

| ADR | Topic | Status |
|---|---|---|
| [0001](decisions/0001-engine-b-training-data.md) | Engine B training data: OmniStyle-150K + self-supervised pairs | Deferred (future work) |
| [0002](decisions/0002-csgo-integration.md) | CSGO via our own attention processors | Deferred (future work) |
| [0003](decisions/0003-keypoint-extractor.md) | DISK, not SuperPoint, for the geometric matcher | Deferred (future work) |
| [0004](decisions/0004-external-services-policy.md) | External services: providers and data policy | Accepted for the demo (narrowed) |
| [0005](decisions/0005-model-residency.md) | Shared UNet, tiered residency, cached embeddings | Deferred (future work) |
| [0006](decisions/0006-demo-scope.md) | Demo scope | Accepted |
| [0007](decisions/0007-demo-image-policy.md) | Demo image policy: CC0 / CC BY works by their actual authors | Accepted |
| – | Engine A: inside CSGO vs a separate pass | planned (future work, M2) |
| – | Structure ControlNet choice | planned (decided for the demo in D2; full plan M1) |
| – | Default matcher | planned (future work, M4) |

Open design questions:

- Several references in the global pass: concatenate or average the style tokens? (M1)
- SAM 2 on the global output or on the draft? (M2)
- diffusers pipelines with step callbacks, or a custom sampling loop? (M2)
- Which saliency filter for the semantic matcher? (M4)
- C2PA ingredient relationship (`componentOf` or `inputTo`) and the training/mining assertion. (M5)
