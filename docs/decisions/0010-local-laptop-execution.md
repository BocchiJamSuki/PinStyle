# 0010 — Finish the demo on the owner's laptop (RTX 4060 Laptop, 8 GB)

- Status: **Accepted** (2026-10-08, owner request)
- Amends [ADR-0008](0008-execution-topology.md). The AutoDL server stays available but optional.

## Context

The AutoDL platform had no GPUs free, so the owner asked to move the remaining steps to the laptop:

- the colour-vs-rendering experiment;
- D6 (README, demo script, dry run).

The laptop has:

- an NVIDIA RTX 4060 Laptop GPU with 8 GB (driver 617.42, CUDA 13.4 UMD);
- a Ryzen 9 7945HX and 32 GB RAM;
- Windows 11, with 413 GB free on D:.

The demo stack needs about 12 GiB resident and 13.4 GiB at peak at 1024 px (D0/D2, measured on the 4090). That does not fit in 8 GB.

## Decision

- **Environment:** a conda env `pinstyle` (Python 3.11) on the laptop.
  - The packages are the same pinned versions as on the server.
  - torch 2.14.1 + cu130 comes from the PyTorch index, because the default Windows wheel on PyPI is CPU-only.
  - The Linux lockfile is not reused on Windows. The Windows freeze goes in `requirements.lock.win.txt`.
- **Models** are downloaded on the laptop into `models/`, with the same pinned HF revisions, now written into `configs/demo.yaml`.
  - These are the commits the server downloaded on 2026-10-07. Full SHAs were read from huggingface.co and match the server log's prefixes.
  - Every file is verified against the HF hashes.
  - Byte sources: ModelScope, huggingface.co (the laptop reaches it directly) and hf-mirror. The fastest one, by probe, is used.
- **aria2c** for Windows (1.37.0, from the official GitHub release; zip sha256 `67d01530…b288`) sits in the gitignored `third_party/tools/`.
- **Low-VRAM mode** (`Stack.low_vram`):
  - It turns on automatically below 16 GiB, or is forced with `PINSTYLE_LOW_VRAM=1/0`.
  - The modules stay in CPU RAM, and diffusers model-CPU-offload hooks are attached to the pipeline about to run (`Stack.use(name)`).
  - Results are the same models and settings. Only memory placement differs.
- **Measurements made on the laptop** (latency, VRAM) are labelled "laptop, RTX 4060 8 GB, low-VRAM". They are never compared with the 4090 numbers as if they were like for like.
- **Gradio** runs locally on 127.0.0.1:7860, so no SSH tunnel is needed.
- Git stays the sync path. The server, if used again, pulls as before.

## Consequences

- Generation is slower on the laptop, because of offload transfers and the smaller GPU. The demo script will show precomputed results where a live run would be too slow.
- The local-first rule is unchanged. Network access happens only for model downloads and the D5 providers.
