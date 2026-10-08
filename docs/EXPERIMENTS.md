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
