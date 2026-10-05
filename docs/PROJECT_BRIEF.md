# PinStyle — Project Brief

> **Scope note (2026-10-05):** the current scope is the demo ([ADR-0006](decisions/0006-demo-scope.md), PLAN.md Part A). The full plan described in this brief is future work.

Research prototype for the proposal *"Keeping Creators in Control: An Artist-Owned, Region-Controllable Generative Finishing System for Illustration and Manga Production"*.

PinStyle lets an illustrator "pin" their own style onto specific regions of a new draft with a few point correspondences, instead of handing the whole image to an end-to-end generator.

---

## 0. Working agreement for Claude Code

- Read this whole brief before planning. Do not write application code until `docs/PLAN.md` and `docs/ARCHITECTURE.md` exist and the owner has approved them.
- **Verify before you build.** Check every third-party repo or model listed here for availability, license and VRAM fit on one RTX 4090 (24 GB). Record findings in `docs/THIRD_PARTY.md`. If something is unavailable or unsuitable, propose an alternative and explain why.
- Work milestone by milestone (Section 9). At the end of each milestone: run the tests, update the status in `docs/PLAN.md`, append results to `docs/EXPERIMENTS.md`, and commit.
- **Never fabricate results.** Every number in a report must come from a logged run with its config, seed and commit hash.
- Code style: Python 3.10+, type hints, pytest, YAML configs (OmegaConf or Hydra), structured logging. Frontend in TypeScript.
- Hardware: a rented Linux machine with one RTX 4090 (24 GB). Manage VRAM explicitly (bf16/fp16, keep hot models resident, offload cold ones, one GPU job at a time).
- Record significant design decisions as short notes in `docs/decisions/`.

---

## 1. Research context (why this project exists)

**Problem.** Most generative image tools work end to end: a prompt or reference goes in, a finished image comes out. Professional illustrators lose the decisions that define their work: which details must survive, how a region is rendered, and whose style is reproduced. In Japan, AI illustration tools have been withdrawn shortly after announcement because creators objected to how their work was used.

**Technical symptom (the "necklace case").** In reference-based style transfer, pushing for global style erases small but meaningful details (a character's diamond necklace disappeared). Protecting the details keeps the necklace and earrings but weakens the style. An end-to-end model cannot know which details the artist cares about.

**Target scenario: own-style propagation.** An illustrator uses their *own* finished works as references to finish their *own* new drafts (colouring, shading, rendering).

**Key terms.**
- *Signature features*: characteristics an artist considers essential to their style (eye highlights, hair shading, accessories, palette, line weight).
- *Region-level intent*: the artist's choice of which part of a reference should inform which part of a new drawing.
- *Control granularity*: the level at which the creator directs the AI, from fully automatic, through region-level guidance, to manual editing.

**Research questions.**
- **RQ1 (Boundaries):** At what granularity of control, and within what boundaries, are professional illustrators willing to accept AI in their work? Which decisions must stay with them, and which can be delegated?
- **RQ2 (Design):** Can lightweight interaction, such as a few point correspondences, achieve precise transfer of local features without retraining the model for each artist?
- **RQ3 (Value):** Compared with an end-to-end general-purpose service, does this design balance task efficiency, style fidelity and the creator's subjective sense of ownership?

**Hard constraints.**
- No per-artist fine-tuning. Never train LoRA, DreamBooth or similar on an artist's work. Any trained component is trained once on general data.
- References must be the artist's own registered work.
- Local-first: core processing runs on the local machine with no network calls.

**What the prototype must demonstrate.**
1. The full interaction concept working end to end in a browser.
2. The necklace case: a detail lost under global transfer is recovered with one or two point pairs while the global style is kept.
3. A quantitative comparison with research baselines and with general-purpose generation services.
4. Working governance functions (registry gate, provenance, usage log).
5. Tooling for the planned interview probe (RQ1) and user study (RQ3).

---

## 2. System overview

Three subsystems plus research tooling:

| Part | Responsibility |
| --- | --- |
| Interaction | Web UI and API: point editing, signature-feature tags, strength, versions, confidence display |
| Generation | Global stylization plus local correction, with two interchangeable local engines (A: training-free, B: trained point-guided branch) |
| Governance | Own-work registry and reference gate, offline enforcement, provenance, tamper-evident usage log |
| Research tooling | Benchmarks, metrics, baselines, external-service comparison, interview probe builder, study logging, figure scripts |

**Main flow.** Register own works → choose reference(s) and a draft → auto-suggest point pairs → artist edits points, tags and strength → global pass → local correction per point/region → confidence map → artist iterates → export with provenance. Every step is logged.

---

## 3. Interaction subsystem

### 3.1 Frontend (React + TypeScript + Vite; canvas via react-konva)
- Side-by-side view: reference on the left, draft/output on the right; zoom and pan; overlay toggles for masks, points and the confidence heatmap.
- Point pairs: auto-suggested pairs shown with their confidence; the artist can accept, drag, delete or add pairs (click on the reference, then on the draft). Each pair has an ID and colour.
- Per-pair/region settings: strength slider; signature-feature tags (presets such as "eye highlight", "hair shading", "accessory", "palette", "line weight", plus free text); "lock region" to keep the draft unchanged there.
- Global settings: global style strength, structure strength, seed, steps, resolution.
- Run modes: global only; global + local; local only on the current output.
- Version history: every run is a node storing inputs, points, settings and outputs; undo/redo; a before/after comparison slider between any two versions.
- Confidence map overlay; low-confidence regions highlighted with a "suggest a point here" hint.
- Annotation mode for building benchmarks (Section 7.2).
- Probe mode for RQ1 (Section 7.7) and study logging for RQ3 (Section 7.8).

### 3.2 Backend (FastAPI)
- Endpoints for projects, uploads, registry, point suggestion, point-to-mask segmentation, generation jobs, confidence maps, export and logs.
- A single-GPU job queue; progress pushed to the UI via WebSocket or SSE; models warmed up at start.

### 3.3 Point suggestion
Implement two matchers behind one interface and compare them on the benchmarks:
- **Geometric:** SuperPoint or DISK features + LightGlue, then filter by DINOv2 patch-feature similarity.
- **Semantic:** mutual nearest neighbours on DINOv2 patch features (optionally fused with diffusion features), clustered into a small number of salient pairs.

LightGlue alone is likely weak across different poses and characters; measure this rather than assume it.

---

## 4. Generation subsystem

Define a common interface so the two local engines are interchangeable in the app and in experiments:

```python
class LocalEngine(Protocol):
    def apply(self, global_output, draft, references, point_pairs, region_settings) -> tuple[Image, dict]: ...
```

### 4.1 Global path
- **Primary:** CSGO (official code and weights, SDXL-based). The draft is the content image; the reference is the style image.
- **Alternative for comparison:** IP-Adapter or InstantStyle on SDXL with a structure ControlNet (canny or line art) on the draft.
- Expose the structure-control scale so line art in the draft is preserved.

### 4.2 Local engine A: training-free
This is also the fallback described in the research proposal.
1. **Points to masks:** SAM 2 with point prompts on both the draft/output and the reference; allow several points per region; dilate and feather masks.
2. **Reference region conditioning:** crop or mask the matched reference region and encode it for IP-Adapter (Plus variant).
3. **Region-masked injection:** use diffusers IP-Adapter masking (`IPAdapterMaskProcessor`, passed through `cross_attention_kwargs={"ip_adapter_masks": masks}`): one IP-Adapter image and binary mask per region, plus a global reference for the remaining area.
4. **Masked regeneration:** inpaint/img2img on the global output with per-region denoising strength and the structure ControlNet; blend with feathered masks to avoid seams.
5. Region strength maps to IP-Adapter scale × denoising strength.

Investigate whether masked injection can run inside CSGO's own pipeline or needs a separate SDXL inpainting pass; choose by quality and latency, and document the decision.

### 4.3 Local engine B: trained point-guided local correspondence branch
This is the research method in the proposal.
- **Architecture:** a lightweight branch on top of frozen CSGO/SDXL. For each point pair, build point-conditioned local tokens from (a) reference features in a window around the reference point (image-encoder patch tokens and/or DINOv2 features) and (b) a positional encoding of the target location. Inject them through additional decoupled cross-attention, spatially weighted around the target point (soft Gaussian or SAM mask). Trainable parts: the token encoder and the new cross-attention projections, with optional gating. The backbone stays frozen.
- **Training data:** IMAGStyle triplets (content, style, stylized). Extract candidate point pairs between the style image and the stylized target with the matchers from 3.3; drop low-confidence pairs; cache them. Hold out a manually checked subset for validation and testing.
- **Supervision issue:** IMAGStyle provides image-level targets only, and a stylized crop may contain the very local errors the branch should correct. Treat points as weak correspondence signals and combine:
  - the standard diffusion denoising loss;
  - a CSD-based style loss on matched regions, computed on the predicted clean image at low-noise timesteps on small crops to limit VRAM;
  - a DINOv2-based content/structure constraint;
  - a contrastive (InfoNCE) term pulling each output region toward its matched reference region and away from unmatched regions, which discourages copying reference patches;
  - optional progressive patch shuffling of the reference as a curriculum.
- **Fitting on one 4090:** bf16, gradient checkpointing, 8-bit AdamW, batch size 1 with gradient accumulation, precomputed VAE latents and encoder features; start at 768 px and move to 1024 px if feasible. Profile first and put time estimates in `docs/PLAN.md`.
- **Deliverables:** data preparation and point-extraction scripts, training script and configs, checkpoints, ablation runner, integration as a selectable engine in the app.

### 4.4 Confidence map
After generation, compute per-region agreement between each output region and its matched reference region (DINOv2 patch similarity and CSD style similarity), optionally combined with variance across 2–3 low-resolution seeds. Normalize into a heatmap, flag regions below a threshold, and suggest adding a point there.

### 4.5 Initial performance targets (revise after profiling)
- Point suggestion under 2 s; SAM 2 mask under 0.5 s.
- One local correction at 1024 px in about 20 s or less on the 4090, with models kept resident.

---

## 5. Governance subsystem

- **Artist profile and registry:** the artist registers their own works (upload, authorship declaration, optional public portfolio URL). Store perceptual hashes (pHash/dHash) and embedding fingerprints (DINOv2 or CLIP).
- **Reference gate:** a reference is accepted only if it matches a registered work (exact hash or near-duplicate within thresholds); otherwise it is rejected with a clear message. Log every decision. Real-world authorship verification is out of scope: implement the mechanism and document its limits.
- **Local-first enforcement:** no network calls in core paths; an `offline: true` config that tests enforce (for example by blocking sockets in test mode). The external-service comparison lives in a separate, clearly marked module.
- **Provenance:** every export carries (a) a C2PA manifest via the c2pa-python library with a local test certificate, if feasible, recording ingredients (reference hashes), actions ("AI-assisted finishing"), engine and settings; and (b) a fallback JSON sidecar plus PNG text metadata. Outputs are labelled as AI-assisted.
- **Usage log:** append-only JSONL with hash chaining (tamper-evident), recording which registered works were used, when, and for which export; viewable in the UI.

---

## 6. File exchange with paint software

- **Import:** PNG/JPG; PSD flattened via psd-tools.
- **Export:** PNG; layered OpenRaster (.ora) containing the global result, one layer per region correction and the masks (opens in Krita and GIMP); layered PSD if a reliable writer exists (evaluate and document).

---

## 7. Research tooling

### 7.1 Data and rights
Benchmarks and demos use only the owner's own illustrations, works shared with explicit permission, or CC-licensed works. Keep a manifest with source and license for every image. No scraping. Demo assets in `assets/demo/` must be rights-cleared.

### 7.2 Benchmarks
- **B1:** held-out IMAGStyle subset with manually checked correspondences.
- **B2 (own-style propagation, self-supervised):** from an artist's finished illustration, synthesize a draft (line extraction + flat-colour quantization or segmentation); use a *different* finished work by the same artist as the reference; the original finished illustration serves as ground truth.
- **B3:** annotated region pairs (built with the annotation mode) for regional accuracy.

### 7.3 Metrics
- Regional accuracy on annotated region pairs (define operationally, e.g. DINOv2/CSD agreement thresholds plus human spot checks).
- DINOv2 regional consistency; CSD style similarity, global and per region.
- LPIPS/SSIM against ground truth (B2); structure preservation (line-art/edge agreement with the draft).
- Latency; number of corrections until an acceptable result.

### 7.4 Ablations
Number of point pairs (0–10); strength; patch shuffling on/off; matcher (geometric vs semantic); engine A vs engine B.

### 7.5 Research baselines
CSGO alone; IP-Adapter/InstantStyle with ControlNet; CoCoDiff (official code); MangaNinja (official code, line-art colourization setting, where applicable). Check code availability and licenses first.

### 7.6 Comparison with general-purpose services
- A runner for services that offer official image APIs; record the exact model name, version, date and prompt for every call.
- Manual import for services without an API (e.g. Midjourney).
- Only rights-cleared images may be sent to external services.
- Evaluate outputs with the same metrics plus a failure taxonomy: lost detail, misplaced detail, style drift, structure change, not controllable.

### 7.7 RQ1 probe builder
For a given draft, produce the same task at three control levels (fully automatic end-to-end, point-guided PinStyle, manual editing without AI) and export a side-by-side sheet for interviews.

### 7.8 Study logging (RQ3)
Session logs with task time, edits, corrections and the accepted result; CSV export; a hook to link an external ownership questionnaire.

### 7.9 Figures
Scripts that produce comparison grids, the necklace-case sequence (global loss → points → recovery) and ablation plots for slides and the proposal.

---

## 8. Repository layout (proposal; refine in ARCHITECTURE.md)

```
pinstyle/
  CLAUDE.md
  docs/            PROJECT_BRIEF.md  PLAN.md  ARCHITECTURE.md  THIRD_PARTY.md  EXPERIMENTS.md  decisions/
  configs/
  src/pinstyle/
    correspondence/   segmentation/   generation/{global_path,engine_a,engine_b}/
    confidence/       governance/     io/            evaluation/   external/   logging/
  server/          FastAPI app
  web/             React + TypeScript app
  scripts/         download_models  prepare_data  extract_points  train_branch  run_eval  make_figures
  tests/
  assets/demo/     rights-cleared images only
```

---

## 9. Milestones and acceptance criteria

| Milestone | Scope | Done when |
| --- | --- | --- |
| M0 Setup | Repo, environment, model download scripts, THIRD_PARTY.md, test harness | All components load on the 4090 and a smoke test passes |
| M1 Global path | CSGO CLI; IP-Adapter/InstantStyle + ControlNet alternative | Global results and latency logged for sample pairs |
| M2 Engine A | Points → SAM 2 masks → masked IP-Adapter correction (CLI) | Necklace case reproduced and fixed; before/after figure saved |
| M3 App v1 | FastAPI + React UI: point editing, strength, run, history, compare | Full necklace flow works in the browser |
| M4 Suggestion and confidence | Both matchers; confidence heatmap in the UI | Suggestions and heatmap visible; matcher comparison logged |
| M5 Governance and export | Registry gate, offline enforcement, provenance, usage log, ORA export | Unregistered reference rejected; exports carry provenance |
| M6 Evaluation | Benchmarks B1–B3, metrics, baselines, external comparison, figures | One command reproduces the full report |
| M7 Engine B | Point extraction on IMAGStyle, training, integration, ablations vs engine A | Checkpoint, ablation table, engine switchable in the UI |
| M8 Research tooling and polish | Probe builder, study logging, demo mode, README, 2-minute demo script | Demo runs from a clean clone |

---

## 10. Verify first (before writing M0 code)

- CSGO: code and weight availability, license, SDXL base, VRAM, and whether IP-Adapter masking and ControlNet can be combined with its pipeline.
- Choice of SAM 2 checkpoint, LightGlue feature extractor, DINOv2 variant and CSD weights.
- CoCoDiff and MangaNinja: official code status and licenses.
- c2pa-python: feasibility of signing with a local test certificate.
- Layered export: OpenRaster writer; PSD writer options.
- Image APIs for the external comparison, and their terms of use.

Write findings and decisions to `docs/THIRD_PARTY.md` and `docs/decisions/`.

---

## 11. Out of scope for now

- Running the actual interviews and user study (only the tooling is built).
- Commercial deployment, user accounts, cloud hosting.
- Any per-artist fine-tuning.
