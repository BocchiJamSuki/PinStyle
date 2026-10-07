# Third-party components: availability, licenses, VRAM fit

Verification required by brief §0 and §10. Done on **2026-10-05**, before any code was written. Every fact below was checked at its source on that date (GitHub REST API, Hugging Face Hub API, PyPI, official docs and terms pages); links are in §11.

How to read this document:

- **License** is what the source declares (GitHub license field, Hugging Face `license` tag, README or terms text). Where sources disagree, both are listed.
- **VRAM (est.)** is an *estimate*: checkpoint file size, or parameter count × 2 bytes for fp16/bf16. Activations come on top. **These are not measurements.** The M0 smoke test on the RTX 4090 fills the *Measured* column in §9; run IDs go to `docs/EXPERIMENTS.md`.
- Verdict: ✅ use · ⚠️ use with restrictions · ❌ unavailable or not adopted.

---

## 0. Demo scope (2026-10-05)

The project is in demo scope ([ADR-0006](decisions/0006-demo-scope.md)). The demo uses only the components below; everything else in this file still applies to the full plan, which is now future work. Facts in this section were checked on 2026-10-05. VRAM figures are estimates until D0 measures them.

### 0.1 Models

`scripts/download_models.py` downloads these, and all of them stay resident in fp16.

| Component | Source | License | VRAM est. (fp16, GB) |
|---|---|---|---|
| SDXL base 1.0 (UNet + text encoders) | `stabilityai/stable-diffusion-xl-base-1.0` | CreativeML Open RAIL++-M | 5.1 + 1.6 |
| VAE, fp16 fix | `madebyollin/sdxl-vae-fp16-fix` | MIT | 0.2 |
| Structure ControlNet | `TheMistoAI/MistoLine` (fallback: `diffusers/controlnet-canny-sdxl-1.0`) | OpenRAIL++ | 2.5 |
| IP-Adapter Plus SDXL ViT-H + ViT-H image encoder | `h94/IP-Adapter` | Apache-2.0 | 0.85 + 1.3 |
| SAM 2.1 hiera-large (transformers format) | `facebook/sam2.1-hiera-large` | Apache-2.0 | ≈ 0.45 |
| DINOv2 ViT-L/14 with registers (optional score) | `facebook/dinov2-with-registers-large` | Apache-2.0 | 0.6 |
| CSD ViT-L (optional score, at most 2 h of work) | `tomg-group-umd/CSD-ViT-L` (code MIT) | CC-BY-4.0 | ≤ 1.2 |
| **Resident total** | | | **≈ 12** (+ 0.6–1.8 with the optional scores), plus 4–6 GB of activations at 1024² |

- **Disk:** about 15–20 GB of weights plus about 10 GB for the env, so at least 50 GB of persistent disk.
- **CSGO** is only an optional spike of up to 4 hours. Its official code is unlicensed, so it stays in the gitignored `third_party/`, for local use only, and is never committed (§2.1; ADR-0002, deferred).

### 0.2 Python packages

These are the latest versions on 2026-10-05. Exact pins go in `environment.yml` during D0.

| Package | Version | Notes |
|---|---|---|
| Python | 3.11 (conda) | |
| torch / torchvision | 2.14.1 / 0.29.1 | PyTorch 2.14 ships cu130 wheels by default and cu126 for older drivers; cu128 was dropped. This comes from a web-search summary of the release, and D0 confirms it on the box. |
| diffusers | 0.40.0 | `StableDiffusionXLControlNetInpaintPipeline` supports `load_ip_adapter`, `cross_attention_kwargs` (which carries `ip_adapter_masks`) and `callback_on_step_end`, per the diffusers API docs. |
| transformers | 5.18.0 | Native SAM 2 (`Sam2Model`, `Sam2Processor`): several points per object, negative points, several objects, and embedding reuse. |
| accelerate / huggingface_hub | 1.15.0 / 2.1.1 | |
| gradio | 6.29.1 (Apache-2.0) | `gr.ImageSlider` is built in (before/after). `gr.Image.select` returns click coordinates (`evt.index` = [x, y]). Set `GRADIO_ANALYTICS_ENABLED=False`; `GRADIO_SERVER_NAME` defaults to 127.0.0.1. |
| requests | 2.34.2 (Apache-2.0) | The D5 providers call the REST APIs directly, with no vendor SDK (ADR-0009). |
| pytest-socket | 0.8.1 (MIT) | |

The newest major versions (transformers 5.x, huggingface_hub 2.x) may not work with diffusers 0.40. If so, D0 picks the newest compatible set and records why.

### 0.3 External services for the comparison (D5)

| Service | Default model → alternatives | Notes |
|---|---|---|
| ~~OpenAI Images API~~ (dropped 2026-10-07, ADR-0009) | `gpt-image-2.5-sunburst` → `gpt-image-2.5-flare`, `gpt-image-2` (snapshot `gpt-image-2-2026-04-21`) | Third-party reviews say Sunburst targets edit precision and detail and Flare is faster, at the same price. Inputs are not used for training by default (§7). |
| ~~Google Gemini API, paid tier~~ (dropped 2026-10-07) | `gemini-3-pro-image` → `gemini-3.1-flash-image` (up to 3 style-reference images) | The unpaid tier allows training and human review, so it is not allowed (§7). Outputs carry SynthID. |
| Midjourney | – | Skipped (owner, 2026-10-07). |
| **Tencent Cloud TokenHub** (checked 2026-10-07) | **`hy-image-v3`** (Hy-Image-3.0) → `hy-image-v3.5-preview` | `POST https://tokenhub.tencentmaas.com/v1/wand/hunyuan-image/v3-generation`, Bearer key, synchronous. Takes 0–3 reference images (URL or base64, PNG/JPEG, ≤ 10 MB). Output sides are 512–2048 px with an area ≤ 1024², one image per call. Seed range [1, 2³²−1]. The result URL is in `data[n].url` and expires after 12 h. Price: 20,000 output tokens per image at CNY 10 per million tokens, so **CNY 0.2 per image**. The 3.5 preview takes up to 20 inputs at CNY 0.15–0.2 per image, but it is a preview whose behaviour may change, so it is only the alternative. The key was validated with the free `GET /v1/models`, which lists both models. |
| **Alibaba Cloud Model Studio (百炼), Beijing** (checked 2026-10-07) | **`qwen-image-edit-plus-2025-12-15`** (dated snapshot) → `qwen-image-edit-max-2026-01-16`, `qwen-image-2.0-pro-2026-06-22`, `wan2.7-image` | `POST https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation`, Bearer key. Takes 1–3 input images (≤ 10 MB, 384–3072 px). `n` is 1–6 (we use 1) and `size` is "W*H" with sides of 512–2048 px. Result URLs expire after 24 h. Price: **CNY 0.2 per image** (Beijing). Instruction editing over several images matches the draft + style-reference task exactly. The key was validated with the free `GET /compatible-mode/v1/models`. The international endpoint rejects it, so the key belongs to the Beijing region. Prices for 2.0-pro and edit-max were not found on the public pages, so those models stay alternatives. |

Use dated snapshot IDs where providers offer them (e.g. `gpt-image-2.5-sunburst-2026-09-08`). The exact IDs are verified on the day of the run.

Stability AI and Black Forest Labs are not used in the demo ([ADR-0004](decisions/0004-external-services-policy.md)).

### 0.4 Demo image sources (candidates for D1)

The rules are in [ADR-0007](decisions/0007-demo-image-policy.md): CC0 or CC BY only, the actual author only, a manifest entry for every image, owner approval, and AI-generated images for debugging only.

| Candidate | License (as checked) | Notes |
|---|---|---|
| Pepper&Carrot, by David Revoy | CC BY 4.0 (license page checked 2026-10-05). Attribution: "Copyright © David Revoy <year>, www.peppercarrot.com" | Many works featuring the same characters. Check whether the source files include line-art layers. |
| Blender Studio open-movie concept art | to verify in D1, per asset | |
| Wikimedia Commons "own work" uploads | CC0 / CC BY, per file | Verify that the uploader is the author. |
| OpenGameArt character art | CC0 / CC BY, per asset | Verify authorship; reposts are common. |
| Openverse | aggregator | Verify at the original source. |

---

## 1. Findings that change the brief

| # | Finding | Consequence | Decision |
|---|---|---|---|
| F1 | **IMAGStyle is not released.** No dataset on Hugging Face; the CSGO README lists it as planned; release requests #10 (2024-09-18) and #18 (2025-01-11) have no maintainer reply; #9 was closed without a link. | Engine B training (§4.3) and benchmark B1 (§7.2) need other data. | **OmniStyle-150K** plus self-supervised pairs → [ADR-0001](decisions/0001-engine-b-training-data.md) (Proposed) |
| F2 | **CSGO's official code has no license** (GitHub `license: null`). The weights on Hugging Face are Apache-2.0. | The code cannot be vendored or redistributed. | Own attention processors that load the Apache-2.0 weights; official code used only for a parity test → [ADR-0002](decisions/0002-csgo-integration.md) (Proposed) |
| F3 | CSGO replaces the attention processors with its own (no spatial masks), so diffusers' `ip_adapter_masks` does not work inside it. A ControlNet is already part of CSGO. | Region masking inside CSGO needs our own processor; a separate SDXL pass with diffusers' masking also works. | Build both as Engine A variants, choose in M2 by quality and latency (planned ADR; future work). The demo uses the separate-pass variant only. |
| F4 | **SuperPoint has a restrictive license**; DISK (Apache-2.0) and ALIKED (BSD-3) do not. | The geometric matcher must avoid SuperPoint. | DISK default, ALIKED as ablation → [ADR-0003](decisions/0003-keypoint-extractor.md) |
| F5 | **The data terms of image services differ sharply.** BFL takes a perpetual, sublicensable license to inputs and outputs with no opt-out in its terms; Stability trains on inputs unless you opt out; Gemini's unpaid tier trains on inputs and allows human review. | Sending an artist's work to a service can grant that service training rights. | Provider policy → [ADR-0004](decisions/0004-external-services-policy.md) (Proposed, needs owner decision) |
| F6 | **Stability AI removed SD 2.1 from Hugging Face** (HTTP 401). CoCoDiff needs it. This also shows hosted weights can disappear. | One baseline depends on a community mirror. All weights must be pinned and archived privately. | Use the `sd2-community/stable-diffusion-2-1` mirror; pin revisions and sha256 in M0 |
| F7 | **Raw CSD cosine is not a calibrated absolute style score** (arXiv 2605.09030, May 2026). | Affects metrics, the confidence map and Engine B's style loss. | Report paired/relative comparisons, add a CSLS-normalized CSD, plus human spot checks |
| F8 | **InstantStyle's official repo has no license either.** The technique is built into diffusers (Apache-2.0). | Use diffusers' implementation, not the repo. | — |

---

## 2. Generation stack

### 2.1 CSGO — primary global path (brief §4.1, §10)

| Item | Finding |
|---|---|
| Paper | "CSGO: Content-Style Composition in Text-to-Image Generation", arXiv 2408.16766 (2024-08-30); listed in the NeurIPS 2025 proceedings (mlanthology). |
| Code | github.com/instantX-research/CSGO — **no license** (GitHub API `license: null`; no license section in the README). Last push 2024-09-05; 391 stars; 17 open issues. Inference and Gradio code only, no training code. ⚠️ parity testing only, never vendored (F2). |
| Weights | HF `InstantX/CSGO`, tag **Apache-2.0**, not gated, last modified 2024-09-18. `csgo_4_32.bin` = 3,978,088,779 B (4 content + 32 style tokens; the README's recommended setting). `csgo.bin` = 7,955,769,806 B (4 + 16 tokens). `csgo_4_32_v2.bin` is announced but not present. ✅ |
| Base components (from README) | `stabilityai/stable-diffusion-xl-base-1.0`; VAE `madebyollin/sdxl-vae-fp16-fix`; ControlNet `TTPlanet/TTPLanet_SDXL_Controlnet_Tile_Realistic`; image encoder `h94/IP-Adapter` → `sdxl_models/image_encoder` (OpenCLIP ViT-bigG/14). All are checked below. |
| SDXL base? | Yes, SDXL 1.0 base. |
| How it works (read from `ip_adapter/ip_adapter.py` and `attention_processor.py`) | `CSGO` → `IPAdapterXL_CS` → `IPAdapter_CS`. It installs `IP_CS_AttnProcessor2_0` on UNet cross-attention (content tokens in down blocks, style tokens in up blocks) **and** on the ControlNet (`controlnet_adapter=True`). Image features are the penultimate hidden states of the CLIP vision encoder, fed through a Perceiver `Resampler` (12 heads, depth 4) to produce tokens. The tokens are **concatenated onto `prompt_embeds`**. The processor splits them back into text / content / style and adds `content_scale·attn_content + style_scale·attn_style`. Both image branches call SDPA with `attn_mask=None`. |
| README defaults (image-driven transfer) | `guidance_scale=10`, `num_inference_steps=50`, `content_scale=1.0`, `style_scale=1.0`, `controlnet_conditioning_scale=0.6` (lower values for text-driven synthesis), `pipe.enable_vae_tiling()`. The content image is passed both as the ControlNet condition and as the content-token input. |
| Can IP-Adapter masking be combined with it? | **Not as-is.** diffusers' `ip_adapter_masks` only works with diffusers' own `IPAdapterAttnProcessor2_0`; CSGO replaces those processors and has no mask input. Adding masks is a local change in our own processor: multiply each region's style-attention output by its mask resized to the attention map, as diffusers does. Several regions become several style-token groups, each with its own mask (ADR-0002). |
| Can ControlNet be combined with it? | **It already is.** The Tile ControlNet carries the content image and also receives CSGO tokens. Adding a second (line-art) ControlNet via `MultiControlNetModel` means adapting CSGO's processor setup, which assumes a single ControlNet. Checked in M1. |
| VRAM (est.) | UNet 5.1 + text encoders 1.6 + VAE 0.2 + Tile ControlNet 2.5 + CSGO adapters 2.0 (if the file is fp32; up to 4.0 if fp16) + ViT-bigG encoder 3.7 ≈ **15 GB of weights**. Add ~4–6 GB of activations at 1024² with CFG and a tiled VAE. That fits in 24 GB on its own, but needs tiering when it shares the GPU with Engine A, SAM 2 and DINOv2 (§9). Issue #4 reports GPU memory not being released after an OOM in their Gradio demo. |
| Still to check (M0/M1) | dtype of `csgo_4_32.bin`. Which TTPlanet file the authors used: the repo has `…_v1_fp16` and `…_v2_fp16` (2,502,139,104 B each), and diffusers' `from_pretrained` expects `diffusion_pytorch_model.safetensors`, so the download script renames it. Whether the official code runs on diffusers 0.40 (it was written in 2024). |

### 2.2 SDXL components

| Component | Source | License | Size | VRAM est. | Verdict |
|---|---|---|---|---|---|
| SDXL base 1.0 (UNet 2.6B params; CLIP-L + OpenCLIP-bigG text encoders, 0.82B) | `stabilityai/stable-diffusion-xl-base-1.0` (not gated) | CreativeML Open RAIL++-M | fp16 variant files ≈ 7 GB (exact list pinned in M0) | UNet 5.1, text encoders 1.6 | ✅ RAIL use restrictions apply |
| VAE, fp16 fix | `madebyollin/sdxl-vae-fp16-fix` | MIT | ≈ 0.3 GB | 0.2 | ✅ |
| Tile ControlNet (CSGO content path) | `TTPlanet/TTPLanet_SDXL_Controlnet_Tile_Realistic` (last modified 2024-06-08) | OpenRAIL | 2.50 GB fp16 (v1 and v2), 0.77 GB rank-256 variant | 2.5 | ✅ |

### 2.3 IP-Adapter and InstantStyle — alternative global path and Engine A

| Component | Source | License | Size | VRAM est. | Verdict |
|---|---|---|---|---|---|
| IP-Adapter Plus SDXL (ViT-H) | `h94/IP-Adapter` → `sdxl_models/ip-adapter-plus_sdxl_vit-h.safetensors` | Apache-2.0 | 847,517,512 B | 0.85 | ✅ |
| ViT-H/14 image encoder | `h94/IP-Adapter` → `models/image_encoder` | Apache-2.0 | 2,528,373,448 B (fp32) | 1.3 | ✅ |
| ViT-bigG/14 image encoder (used by CSGO) | `h94/IP-Adapter` → `sdxl_models/image_encoder` | Apache-2.0 | 3,689,912,664 B (fp16) | 3.7 | ✅ warm tier (§9) |
| InstantStyle | diffusers `set_ip_adapter_scale({"up": {"block_0": [0.0, 1.0, 0.0]}})` | Apache-2.0 (diffusers). The original repo `instantX-research/InstantStyle` has **no license** | – | – | ✅ via diffusers |
| IP-Adapter masking | diffusers `IPAdapterMaskProcessor` plus `cross_attention_kwargs={"ip_adapter_masks": masks}`: one image and one binary mask per region (documented in diffusers `main`) | Apache-2.0 | – | – | ✅ |

diffusers also documents `prepare_ip_adapter_image_embeds()` for precomputing image embeddings and loading them back without the encoder (`image_encoder_folder=None`). We use it to cache reference embeddings when a work is registered (ADR-0005).

### 2.4 Structure ControlNets (line-art preservation) — the demo chooses in D2 (MistoLine by default); the full plan chooses in M1 (planned ADR)

| Candidate | Source | License | Size (fp16) | Notes |
|---|---|---|---|---|
| ControlNet Union SDXL | `xinsir/controlnet-union-sdxl-1.0` | Apache-2.0 | 2.51 GB (plus a "promax" variant) | One model covers many modes, including anime line art, line art, canny, tile and inpainting. Needs diffusers' union-ControlNet classes; checked in M1. |
| MistoLine | `TheMistoAI/MistoLine` (last modified 2026-01-06) | OpenRAIL++ | 2.50 GB (plus a 0.77 GB rank-256 variant) | Handles any line type; ships the Anyline/MTEED line extractor. |
| Canny SDXL | `diffusers/controlnet-canny-sdxl-1.0` | OpenRAIL++ | 2.50 GB | The option named in the brief. |

### 2.5 SDXL inpainting

No dedicated inpainting UNet is planned. Masked img2img on the shared base UNet (latent blending with a per-pixel strength map) avoids loading a second 5.1 GB UNet. `diffusers/stable-diffusion-xl-1.0-inpainting-0.1` remains a fallback; it was not checked in detail and would be added to this file before use.

---

## 3. Correspondence, segmentation, features and metrics models

| Component | Choice | Source | License | Size | VRAM est. | Verdict |
|---|---|---|---|---|---|---|
| SAM 2.1 | **`sam2.1_hiera_large`** (224.4M params); fallback `base_plus` (80.8M) | github.com/facebookresearch/sam2; HF `facebook/sam2.1-hiera-large` (original `.pt`, 898 MB, plus transformers-format safetensors) | Apache-2.0 (some files BSD-3) | 0.9 GB fp32 | ≈ 0.45 (bf16) | ✅ Needs Python ≥ 3.10 and torch ≥ 2.5.1; the CUDA extension is optional. |
| LightGlue | `LightGlue(features="disk")` | github.com/cvg/LightGlue | Apache-2.0 (code and LightGlue weights) | small | < 0.1 | ✅ README: 150 FPS at 1024 keypoints on an RTX 3080 |
| Keypoint extractor | **DISK** (default), ALIKED (ablation) | via LightGlue | DISK: Apache-2.0; ALIKED: BSD-3-Clause | small | < 0.1 | ✅ |
| Keypoint extractor | SuperPoint | via LightGlue | "a different, restrictive license" covering its weights and inference file | – | – | ❌ not adopted (ADR-0003) |
| DINOv2 | **ViT-L/14 with registers** (default), ViT-B/14 with registers (ablation) | github.com/facebookresearch/dinov2; HF `facebook/dinov2-with-registers-large` | Apache-2.0 (code and standard weights) | 1.22 GB fp32 | 0.6 | ✅ Registers give cleaner patch features for dense matching. |
| DINOv3 | not the default | Meta (announced 2025-08-14) | Custom "DINOv3 License": not OSI, requires attribution when redistributing, gated on HF | – | – | ⚠️ optional ablation only |
| CSD style descriptor | ViT-L | code github.com/learn2phoenix/CSD; weights HF `tomg-group-umd/CSD-ViT-L` | code MIT; weights CC-BY-4.0 | 2,438,228,893 B (fp32 pickle) | ≤ 1.2 | ✅ Load with `weights_only=True` and convert to safetensors in M0. See F7. |
| Diffusion features (optional, semantic matcher) | SDXL UNet decoder features at a single timestep | the shared UNet | – | – | no extra weights | ✅ |
| Line extraction (B2 drafts, ControlNet input) | TEED (58K params) / MTEED (Anyline) | github.com/xavysp/TEED; `TheMistoAI/MistoLine` → `Anyline/MTEED.pth` | MIT / OpenRAIL++ | < 1 MB | ≈ 0 | ✅ |
| Annotator bundle | only for the MangaNinja baseline (`sk_model.pth`) | `lllyasviel/Annotators` | "other" (a bundle of third-party weights) | – | – | ⚠️ baseline only |

**CSD caveat (F7).** Frochte, "When Style Similarity Scores Fail: Diagnosing Raw CSD Cosine in Artist-Style Evaluation" (arXiv 2605.09030, 2026-05-09). On a 91-artist public-domain corpus, raw CSD cosine produced negative same-vs-different "discrimination gaps" for 15 of 91 artists in aggregated-pool scoring. A CSLS readout cut that to 4 of 91, and interpolating positional embeddings to 336 px raised pair-verification AUC from 0.883 to 0.905. The same pattern appeared with CLIP ViT-L/14, SigLIP-L and DINOv2-L. We therefore never report CSD cosine as an absolute score.

---

## 4. Datasets

| Dataset | Status on 2026-10-05 | License | Size | Verdict |
|---|---|---|---|---|
| IMAGStyle (CSGO; 210K triplets) | **Not released** (F1) | – | – | ❌ |
| OmniStyle-150K | HF `StyleXX/OmniStyle-150k`, released 2025-07-23, not gated. Files: `content.tar`, `style.tar`, `OmniStyle-150K.tar.part_aa` … `part_ae`; stylized images are named `<content>&&<style>.jpg`. | HF card: Apache-2.0. arXiv paper: CC BY 4.0. Comply with both (give attribution). | 200,648,890,880 B | ✅ proposed for Engine B and B1 (ADR-0001) |
| OmniStyle-1M | research use only, not released | – | – | ❌ |

OmniStyle-150K provenance, from the paper (arXiv 2505.14028, CVPR 2025):

- All images are 1024×1024.
- Content images were generated with FLUX from ChatGPT-written prompts (20 categories).
- The 1,000 style images were curated from Style30K.
- Each stylized image is the best of six methods (StyleID, ArtFlow, StyleShot, AesPANet, CSGO, CAST), chosen by OmniFilter (CLIP + DINOv2 for content, a fine-tuned CLIP for style, InternVL2 for aesthetics).

Caveats:

- The original sources of the Style30K images were not verified here, and they include artwork-like images.
- CSGO's own outputs are part of the data.

This is general data, not tied to any artist, and the caveats are documented as a limitation. The OmniStyle model itself needs about 46 GB of VRAM (per its repo), so it cannot serve as a baseline on a 4090.

Rights rules for our own benchmark and demo data (B2, B3, demos) are in brief §7.1: every image gets a manifest entry with its source, license and consent reference.

---

## 5. Research baselines (brief §7.5)

| Baseline | Code | License | Weights and dependencies | VRAM est. | Verdict |
|---|---|---|---|---|---|
| CSGO alone | ours (ADR-0002) | – | §2.1 | – | ✅ |
| IP-Adapter / InstantStyle + ControlNet | ours, via diffusers | Apache-2.0 | §2.3–2.4 | – | ✅ |
| **CoCoDiff** (ICLR 2026, arXiv 2602.14464; training-free, correspondence-consistent style transfer) | github.com/Wenbo-Nie/CoCoDiff (created 2026-02-14, last push 2026-04-07) | **no license** (GitHub `null`) | Original LDM codebase with an SD v1 checkpoint (`models/ldm/stable-diffusion-v1/model.ckpt`), plus SD 2.1 in diffusers format for match precomputation and cycle mode | not stated; SD 1.x/2.x scale, estimated < 12 GB | ⚠️ Run unmodified from the gitignored `third_party/` folder in its own environment; never vendored; outputs used for evaluation only. |
| **MangaNinja** (CVPR 2025; point-guided line-art colorization) | github.com/ali-vilab/MangaNinjia (last push 2025-03-02) | README: **CC BY-NC 4.0** (GitHub field: "Other"). Weights HF `Johanan0528/MangaNinjia`, tagged Apache-2.0. | `denoising_unet.pth` 3.44 GB, `reference_unet.pth` 3.44 GB, `controlnet.pth` 1.45 GB, `point_net.pth` 0.10 GB (all fp32). Also needs SD 1.5, `openai/clip-vit-large-patch14`, `lllyasviel/control_v11p_sd15_lineart` and Annotators `sk_model.pth`. | README mentions 6 GB for the Windows build | ⚠️ Non-commercial research use only; own environment. Points are passed as 512×512 index maps (`--point_ref_paths`, `--point_lineart_paths`). Training code is not released. |
| SD 1.5 (needed by both) | HF `stable-diffusion-v1-5/stable-diffusion-v1-5` (a mirror of the removed runwayml repo; not gated) | CreativeML OpenRAIL-M | – | – | ✅ |
| SD 2.1 (needed by CoCoDiff) | `stabilityai/stable-diffusion-2-1` returns HTTP 401: Stability deprecated and removed it in 2025. Community mirror: `sd2-community/stable-diffusion-2-1` (not affiliated with Stability). | CreativeML OpenRAIL++-M | – | – | ⚠️ Mirror; pin revision and hash. If the mirror disappears, try CoCoDiff's matching step with SD 1.5. |

MangaNinja is the closest published relative of Engine B (it follows a reference via points), so it is the most informative baseline. It is compared only in the line-art colorization setting, where it applies.

---

## 6. Governance and file exchange

### 6.1 c2pa-python — signing with a local test certificate (brief §5, §10)

- **Package.** `c2pa-python` (github.com/contentauth/c2pa-python), license **MIT OR Apache-2.0**. Latest **v0.38.0, released 2026-09-29**; it wraps c2pa-rs 0.90.x. Releases are very frequent, so we pin the exact version. Python ≥ 3.10; wheels include `manylinux_2_28_x86_64` and `win_amd64`.
- **API** (`docs/usage.md`):
  - reading: `Reader(path, context=ctx).json()`;
  - signer: `C2paSignerInfo(alg, sign_cert, private_key, ta_url)` → `Signer.from_info(...)`;
  - signing: `Builder(manifest_json, ctx).sign(signer, mime_type, source, dest)`;
  - configuration: `Context` / `Settings` (for example `verify_cert_anchors`).

  The repo's example signs with the ES256 fixtures `es256_certs.pem` and `es256_private.key`.
- **Signing with a local test certificate is feasible.**
  - C2PA guidance says development certificates (self-signed, or from a private test CA) work, and that conforming validators report them as *untrusted*. That is the expected result for us.
  - Leaf certificate: ECDSA P-256 (ES256), with the C2PA claimSigning EKU `1.3.6.1.4.1.62558.2.1` plus `id-kp-emailProtection` or `id-kp-documentSigning` for older validators. It is signed by a local test CA, not self-signed.
  - `scripts/make_test_cert.py` generates both in M5.
- **Offline caveat.** The example passes `ta_url="http://timestamp.digicert.com"`, which is a network call. For local-first signing we leave out the timestamp authority. *To verify in M5:* that `ta_url=None` is accepted and signing works with sockets blocked.
- **Formats.** c2pa-rs supports PNG and JPEG. ORA and PSD are not expected to be supported, so in M5 we try signing ORA's `mergedimage.png`, and the JSON sidecar is always written.
- **Keys.** The docs warn that keys on local disk are for development only. That is acceptable for a prototype; keys stay in the gitignored `data/secrets/`.

### 6.2 OpenRaster (.ora) writer

- `pyora` 0.3.11 (MIT) was last released on 2021-03-19 and is unmaintained, so it is not adopted.
- **We write our own writer** (about 150 lines, `zipfile` + Pillow). It produces `mimetype` (the first entry, stored uncompressed, containing `image/openraster`), `stack.xml`, `data/*.png`, `Thumbnails/thumbnail.png` and `mergedimage.png`. The spec details are re-checked against openraster.org during implementation (M5).
- Interop check in M5: Krita (native ORA support) and GIMP 3.x. Both are tested by hand and the results recorded.

### 6.3 PSD

- **psd-tools** (MIT), latest **v1.23.0, released 2026-10-01**. It is actively maintained (v1.21–1.23 shipped between 2026-09-28 and 10-01) and needs Python ≥ 3.10.
  - Writing: `PSDImage.new(mode, size, depth)`, `create_group()`, `create_pixel_layer(pil_image, name, top, left, opacity)` and `save()`. The docs mark layer creation as **experimental**, most layer effects are unsupported, and its own compositing can differ from Photoshop's.
  - Reading and flattening (import, brief §6): use the merged image stored in the file when present; otherwise fall back to psd-tools compositing, which may differ, and warn the user.
- Plan: ORA is the primary layered format. PSD is best-effort, using plain pixel layers and groups. Interop is checked in Krita, and by the owner in Photoshop and Clip Studio Paint (M5). Fallback: export ORA and convert it with Krita's command line (optional, not part of the core).

### 6.4 Fingerprints, metrics and other libraries

Except where marked as verified, these licenses come from commonly published package metadata. **M0 generates an automated license report** (`pip-licenses` for Python, `license-checker` for npm) and appends it here.

| Purpose | Package | License |
|---|---|---|
| pHash / dHash | imagehash | BSD-2-Clause (confirm in M0) |
| LPIPS | lpips | BSD-2-Clause (confirm in M0) |
| SSIM and image ops | scikit-image, opencv-python-headless | BSD-3-Clause / Apache-2.0 (confirm in M0) |
| Blocking network access in tests | pytest-socket 0.8.1 (2026-08-19) | MIT (verified) |
| 8-bit AdamW | bitsandbytes | MIT (confirm in M0) |
| Training utilities | accelerate, transformers | Apache-2.0 (confirm in M0) |
| Configs, logging, CLI | omegaconf, structlog, typer | BSD-3 / MIT or Apache-2.0 / MIT (confirm in M0) |
| API server | fastapi, uvicorn, pydantic, SQLAlchemy | MIT / BSD-3 / MIT / MIT (confirm in M0) |
| Frontend | react, vite, konva, react-konva, zustand, @tanstack/react-query, vitest; Playwright | MIT; Playwright Apache-2.0 (confirm in M0) |

---

## 7. External image services (brief §7.6) — for comparison only

Checked on 2026-10-05. Model names change often, so the runner records the exact model ID or snapshot and the date of every call, and the terms are re-checked on the day of each comparison run.

| Provider | Models / endpoint | Reference images | Data use via the API | Proposed status |
|---|---|---|---|---|
| OpenAI Images API | `gpt-image-2` (launched 2026-04-21; snapshot `gpt-image-2-2026-04-21`), `gpt-image-2.5-sunburst` and `gpt-image-2.5-flare` (2026-09-08). Older: `gpt-image-1.5`, `gpt-image-1`, `gpt-image-1-mini`. | The edits endpoint accepts several input images (third-party docs say up to 16; to verify) | Not used for training unless you opt in. Abuse-monitoring logs are kept for 30 days. The Images API stores no application state. Zero data retention is available with approval. Image inputs are scanned for CSAM. | ✅ enable |
| Google Gemini API | `gemini-3.1-flash-image` (Nano Banana 2), `gemini-3-pro-image` (Nano Banana Pro), `gemini-3.1-flash-lite-image`, `gemini-2.5-flash-image`; all generally available | Nano Banana 2: up to 10 object + 4 character + 3 style images. Nano Banana Pro: up to 6 object + 5 character images. | Terms (modified 2026-04-28). **Unpaid tier:** content is used to provide, improve and develop products, including ML, and human reviewers may read inputs and outputs. **Paid tier:** prompts and responses are not used to improve products; logs are kept for abuse detection and legal compliance. Every output carries a SynthID watermark. | ✅ paid tier only |
| Stability AI | Style Transfer, `POST /v2beta/stable-image/control/style-transfer`, with `init_image` (content) and `style_image` (per the API reference and AWS Bedrock docs; to verify in M6) | one content image + one style image | ToS (effective 2026-09-30): Stability may use content to improve and develop its services, and you can **opt out** of training on your inputs and outputs. You warrant that you hold the rights to what you submit. Outputs may not be used to train competing models. | ⚠️ only after opting out |
| Black Forest Labs | FLUX 3 Image (up to 10 references), FLUX.2 [pro]/[flex]/[max]/[klein], FLUX.1 Kontext [pro]/[max] | multi-reference (up to 10, per the docs) | FLUX API Service Terms (revised 2026-08-04): the developer grants BFL a "fully paid, royalty-free, perpetual, irrevocable, worldwide, non-exclusive, and fully sublicensable" license to use Input and Output to operate the service, improve products and develop new ones. **That document offers no opt-out.** Zero data retention is reportedly available for enterprise clients (not verified). | ❌ off unless the owner consents per image |
| Midjourney | no public API, so outputs are imported manually | – | The official ToS could not be fetched automatically (HTTP 403 on docs.midjourney.com and midjourney.com). Third-party summaries from 2026 describe a perpetual, worldwide, sublicensable, irrevocable license to Midjourney over prompts (including image prompts) and outputs, with images public by default unless Stealth mode is on (higher plans). **The owner must read the official ToS before use.** | ⚠️ manual only, owner's own works, Stealth mode |
| **Tencent Cloud TokenHub** (added 2026-10-07; **used in D5**) | `hy-image-v3`, `hy-image-v3.5-preview`; `tokenhub.tencentmaas.com` | 0–3 (v3), ≤ 20 (3.5 preview) | Tencent Cloud's TokenHub service terms: customer data is kept only as long as needed to provide the service; afterwards Tencent stops using it, or returns or deletes it on instruction. No statement that API inputs train models was found; the FAQ "does TokenHub use my data to train models" exists, but its answer could not be fetched (re-check on the day of the run). | **Used** (ADR-0009) |
| **Alibaba Cloud Model Studio** (added 2026-10-07; **used in D5**) | `qwen-image-edit-plus-2025-12-15` and others; `dashscope.aliyuncs.com` (Beijing) | 1–3 | Model Studio's data-use principles: input and output data from API calls are not used for model training or optimization. The Coding Plan is an exception, but we do not use it. Result URLs expire after 24 h. | **Used** (ADR-0009) |

Not checked; candidates if broader coverage is wanted: Adobe Firefly Services, Ideogram, Recraft, Runway, ByteDance Seedream (also on TokenHub as `seedream-image-v5.0-*`).

Rules, enforced by `pinstyle.external` (ADR-0004):

- **Consent.** Send only images whose manifest entry records consent for that specific provider. Never send an artist's work without explicit consent.
- **Logging.** For every call, record:
  - provider, model ID or snapshot, UTC date;
  - prompt and parameters;
  - input hashes and consent reference;
  - output hashes, cost and latency.
- **Use of outputs.** Outputs are used for evaluation only, never for training.
- **Network.** API keys come from environment variables only. The module runs only with `offline: false` plus an explicit `--allow-network` flag.

---

## 8. Runtime versions (latest on 2026-10-05; exact pins are chosen in M0)

| Package | Latest | Note |
|---|---|---|
| Python | 3.11 planned | Broadest wheel coverage for the ML stack; the brief requires ≥ 3.10. The dev laptop has 3.14, so uv will manage a 3.11 interpreter. |
| torch | 2.14.1 (wheels for CPython 3.10–3.14) | CUDA 12.x build for Ada (sm_89) |
| diffusers | 0.40.0 (needs Python ≥ 3.10) | Current docs use `dtype=` where 2024-era code used `torch_dtype=`; the CSGO parity environment may need an older pin. |
| transformers, accelerate | pinned in M0 | |
| c2pa-python | 0.38.0 | pin the exact version |
| psd-tools | 1.23.0 | |
| pytest-socket | 0.8.1 | |

---

## 9. VRAM budget on one RTX 4090 (24 GB) — estimates

### 9.1 Per component

| Component | Basis | Est. (GB) | Measured (M0) |
|---|---|---|---|
| SDXL UNet | 2.6B params × 2 B | 5.1 | — |
| SDXL text encoders | 0.82B params × 2 B | 1.6 | — |
| SDXL VAE (fp16 fix) | 84M params × 2 B | 0.2 | — |
| CSGO adapters (`csgo_4_32.bin`) | 3.98 GB file, dtype unknown | 2.0–4.0 | — |
| Tile ControlNet | fp16 file | 2.5 | — |
| ViT-bigG/14 image encoder | fp16 file | 3.7 | — |
| ViT-H/14 image encoder | fp32 file ÷ 2 | 1.3 | — |
| IP-Adapter Plus SDXL | file size | 0.85 | — |
| Structure ControlNet | fp16 file | 2.5 | — |
| SAM 2.1 hiera-large | 224M params × 2 B | 0.45 | — |
| DINOv2 ViT-L/14 with registers | 304M params × 2 B | 0.6 | — |
| CSD ViT-L | fp32 file ÷ 2 | ≤ 1.2 | — |
| DISK + LightGlue | small | < 0.1 | — |
| Engine B branch | design target | ≤ 0.5 | — |

### 9.2 Interactive app (inference)

- **Hot set (resident on the GPU):** UNet + VAE + Tile ControlNet + CSGO adapters + structure ControlNet + IP-Adapter Plus + SAM 2.1 + DINOv2 + DISK/LightGlue ≈ **14.3 GB** (assuming 2.0 GB for the CSGO adapters).
- **Peak activations:** about 4–6 GB for SDXL at 1024² with CFG, one ControlNet (SDPA) and a tiled VAE decode, plus about 1 GB for the CUDA context and fragmentation. That gives **about 20–21 GB at peak**: it fits, with roughly 3 GB to spare.
- **Warm set (kept in CPU RAM, moved to the GPU on demand):** text encoders 1.6 + ViT-bigG 3.7 + ViT-H 1.3 + CSD 1.2 = 7.8 GB. These *cannot* all sit on the GPU next to the hot set during generation. They are used for embedding jobs whose outputs are cached (ADR-0005).
- **If measurements come out worse:** keep only the active ControlNet on the GPU, quantize the ControlNets to fp8 (weights only), and offer a 768 px interactive mode.

### 9.3 Engine B training (bf16, batch 1, gradient checkpointing, 8-bit AdamW)

| Part | Est. |
|---|---|
| Frozen modules: UNet 5.1 + Tile ControlNet 2.5 + CSGO adapters 2.0 + VAE 0.2 + encoders used on the fly (ViT-H 1.3, DINOv2 0.6) + CSD 1.2 | ≈ 12.9 GB |
| Trainable branch, with gradients and optimizer state | ≈ 1–1.5 GB |
| Activations at 768² | ≈ 4–7 GB |
| Perceptual losses on decoded crops | ≈ 1–3 GB |
| **Total at 768²** | **≈ 19–25 GB (tight)** |

- At 1024², activations grow by about 1.8×, so mitigations are needed. Options:
  - fp8 weight-only quantization of the frozen modules;
  - computing the CSD and DINOv2 losses only every k steps;
  - precomputing embeddings;
  - leaving the ControlNet out of the training loop.
- The M7.0 profiling run measures all of this before any long run.

---

## 10. Open verification items (the milestone that resolves each)

- **M0**
  - measured VRAM for every component;
  - dtype of `csgo_4_32.bin`;
  - `sam2` package vs the transformers port of SAM 2;
  - CSD checkpoint loads with `weights_only=True`;
  - automated license report.
- **M1**
  - TTPlanet v1 vs v2 file;
  - CSGO parity under current diffusers;
  - support for the union ControlNet;
  - a second ControlNet alongside the CSGO adapters.
- **M2:** masked injection inside CSGO vs a separate pass (planned ADR; future work).
- **M5**
  - `ta_url=None` offline signing;
  - C2PA on ORA's `mergedimage.png`;
  - ORA opens in Krita and GIMP;
  - PSD opens in Krita, Photoshop and CSP;
  - gate thresholds.
- **M6**
  - Stability endpoint parameters;
  - OpenAI's maximum number of input images;
  - external terms re-checked on the day of each run.
- **M7**
  - attribution for OmniStyle (Apache-2.0 card vs CC BY 4.0 paper);
  - provenance note for Style30K.

---

## 11. Sources (all accessed 2026-10-05)

- **Demo scope (§0)**
  - Gradio: https://pypi.org/project/gradio/ · https://www.gradio.app/docs/gradio/imageslider · https://www.gradio.app/docs/gradio/image · https://www.gradio.app/guides/environment-variables
  - transformers: https://pypi.org/project/transformers/ · https://huggingface.co/docs/transformers/main/en/model_doc/sam2
  - other packages: https://pypi.org/project/torchvision/ · https://pypi.org/project/accelerate/ · https://pypi.org/project/huggingface-hub/
  - PyTorch CUDA wheels (via a web-search summary): https://github.com/pytorch/pytorch/releases
  - diffusers SDXL ControlNet pipelines: https://huggingface.co/docs/diffusers/main/en/api/pipelines/controlnet_sdxl
  - OpenAI: https://pypi.org/project/openai/ · https://developers.openai.com/api/docs/guides/image-generation
  - GPT Image 2.5 Flare vs Sunburst (third-party): https://www.mindstudio.ai/blog/gpt-image-25-pricing-access
  - Google: https://pypi.org/project/google-genai/
  - Pepper&Carrot: https://www.peppercarrot.com/en/license/index.html
- **CSGO**
  - repo: https://github.com/instantX-research/CSGO · https://api.github.com/repos/instantX-research/CSGO
  - code: https://raw.githubusercontent.com/instantX-research/CSGO/main/ip_adapter/ip_adapter.py · https://raw.githubusercontent.com/instantX-research/CSGO/main/ip_adapter/attention_processor.py
  - issues: https://github.com/instantX-research/CSGO/issues/9 (plus #10 and #18 via the GitHub search API)
  - weights: https://huggingface.co/InstantX/CSGO
  - paper: https://arxiv.org/abs/2408.16766 · https://mlanthology.org/neurips/2025/xing2025neurips-csgo/
- **SDXL and ControlNets**
  - https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0
  - https://huggingface.co/madebyollin/sdxl-vae-fp16-fix
  - https://huggingface.co/TTPlanet/TTPLanet_SDXL_Controlnet_Tile_Realistic
  - https://huggingface.co/xinsir/controlnet-union-sdxl-1.0
  - https://huggingface.co/TheMistoAI/MistoLine
  - https://huggingface.co/diffusers/controlnet-canny-sdxl-1.0
- **IP-Adapter and InstantStyle**
  - https://huggingface.co/h94/IP-Adapter
  - https://huggingface.co/docs/diffusers/main/en/using-diffusers/ip_adapter
  - https://api.github.com/repos/instantX-research/InstantStyle
- **SAM 2:** https://github.com/facebookresearch/sam2 · https://huggingface.co/facebook/sam2.1-hiera-large
- **LightGlue:** https://github.com/cvg/LightGlue
- **DINOv2 / DINOv3**
  - https://github.com/facebookresearch/dinov2 · https://huggingface.co/facebook/dinov2-with-registers-large
  - https://ai.meta.com/resources/models-and-libraries/dinov3-license/
- **CSD**
  - https://github.com/learn2phoenix/CSD · https://api.github.com/repos/learn2phoenix/CSD · https://huggingface.co/tomg-group-umd/CSD-ViT-L
  - caveat paper: https://arxiv.org/abs/2605.09030
- **Line extraction:** https://github.com/xavysp/TEED · https://huggingface.co/lllyasviel/Annotators
- **OmniStyle**
  - https://huggingface.co/datasets/StyleXX/OmniStyle-150k · https://huggingface.co/api/datasets/StyleXX/OmniStyle-150k
  - paper: https://arxiv.org/abs/2505.14028 · https://arxiv.org/html/2505.14028v1
  - repo: https://github.com/StyleX-Research/OmniStyle
- **CoCoDiff:** https://github.com/Wenbo-Nie/CoCoDiff · https://api.github.com/repos/Wenbo-Nie/CoCoDiff · https://arxiv.org/abs/2602.14464
- **MangaNinja:** https://github.com/ali-vilab/MangaNinjia · https://api.github.com/repos/ali-vilab/MangaNinjia · https://huggingface.co/Johanan0528/MangaNinjia
- **SD 1.5 / 2.1**
  - https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-v1-5
  - https://huggingface.co/sd2-community/stable-diffusion-2-1
  - removal discussion: https://discuss.huggingface.co/t/stable-diffusion-2-1/171866
- **c2pa-python**
  - https://github.com/contentauth/c2pa-python · https://api.github.com/repos/contentauth/c2pa-python/releases
  - https://raw.githubusercontent.com/contentauth/c2pa-python/main/docs/usage.md · https://raw.githubusercontent.com/contentauth/c2pa-python/main/examples/sign.py
  - https://pypi.org/project/c2pa-python/
- **C2PA certificates** (via web-search summaries; re-read in M5)
  - https://spec.c2pa.org/specifications/specifications/2.2/guidance/Guidance.html
  - https://github.com/contentauth/c2pa-conformance-tool/blob/main/TEST_CERTIFICATES.md
  - https://provemark.github.io/articles/c2pa-certificates/
- **ORA / PSD**
  - https://pypi.org/project/pyora/
  - https://pypi.org/project/psd-tools/ · https://psd-tools.readthedocs.io/en/latest/usage.html · https://github.com/psd-tools/psd-tools/releases
- **Runtime:** https://pypi.org/project/torch/ · https://pypi.org/project/diffusers/ · https://pypi.org/project/pytest-socket/
- **OpenAI:** https://developers.openai.com/api/docs/changelog · https://developers.openai.com/api/docs/guides/your-data
- **Google:** https://ai.google.dev/gemini-api/docs/image-generation · https://ai.google.dev/gemini-api/terms
- **Stability**
  - https://stability.ai/terms-of-service · https://platform.stability.ai/docs/api-reference
  - https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-stability-ai-stable-image-style-transfer.html
- **Black Forest Labs:** https://docs.bfl.ml/llms.txt · https://bfl.ai/legal/flux-api-service-terms
- **Midjourney**
  - official ToS (HTTP 403 for automated fetch): https://docs.midjourney.com/hc/en-us/articles/32083055291277-Terms-of-Service
  - third-party summary: https://terms.law/ai-output-rights/midjourney/


### 11.1 Sources added 2026-10-07

- Tencent TokenHub: https://cloud.tencent.com/document/product/1823/135745 (Hy image API) · https://cloud.tencent.com/document/product/1823/130055 (prices, page dated 2026-09-24) · https://cloud.tencent.com/document/product/301/129852 (service terms)
- Alibaba Model Studio: https://help.aliyun.com/zh/model-studio/qwen-image-edit-api · https://help.aliyun.com/en/model-studio/qwen-image-edit-plus (price, snapshots) · https://docs.agent.bailian.aliyun.com/en/resources/agreements (data use)
- Model downloads: hf-mirror.com (HF API at pinned revisions; LFS sha256) · modelscope.cn (same-name repos)
