# PinStyle (demo)

PinStyle is a research prototype for *"Keeping Creators in Control: An Artist-Owned, Region-Controllable Generative Finishing System for Illustration and Manga Production"*.

An illustrator finishes a new draft in the style of one of their **own** finished works. Where a detail matters, they **pin** it: one click on the reference and one click on the draft. That region is then rendered the way the reference renders it.

This repository is the **demo** scope ([ADR-0006](docs/decisions/0006-demo-scope.md)). The full research plan is future work: [PLAN Part B](docs/PLAN.md) and [ARCHITECTURE §1–§18](docs/ARCHITECTURE.md).

- **Models:** SDXL base only, with no per-artist fine-tuning of any kind.
- **Local-first:** generation makes no network calls.
- **Demo images:** CC BY works, listed in [`assets/demo/MANIFEST.csv`](assets/demo/MANIFEST.csv).

## What the demo shows

| | Where |
|---|---|
| Global path: SDXL + MistoLine line-art ControlNet + IP-Adapter Plus (InstantStyle) | `src/pinstyle/global_path.py` |
| Engine A: point pair → SAM 2.1 masks → masked IP-Adapter inpaint of that region | `src/pinstyle/engine_a.py` |
| Detail case: Shichimi's horn ornament, with ablations | [EXPERIMENTS D3, D3b](docs/EXPERIMENTS.md) |
| Comparison with Tencent `hy-image-v3` and Alibaba `qwen-image-edit-plus`, blind-reviewed | [D5 report](docs/D5_REPORT.md) |
| Colour vs rendering as separate controls | `src/pinstyle/colour.py`, EXPERIMENTS |
| Gradio app: pair clicking, before/after, versions, governance concept | `src/pinstyle/app/` |

**Headline result** ([EXPERIMENTS D3b](docs/EXPERIMENTS.md)): Shichimi's horn ornament, 6 runs per condition (two structure strengths × three seeds), 1 point pair each.

| Condition | Result |
|---|---|
| Reference point on the reference's ornament | Rendered as the reference's carved ivory ornament in 6/6 runs |
| Same point moved to the background | 0/6 runs |
| Global-only | Lost or misrendered in 5/6 runs |

**Limits** are in the D5 report: two cases, simulated drafts, and reviewers who disagree.

## Setup

Use **either** the Windows laptop path ([ADR-0010](docs/decisions/0010-local-laptop-execution.md)) **or** the Linux GPU server path ([ADR-0008](docs/decisions/0008-execution-topology.md)).

### Windows laptop (tested: RTX 4060 Laptop 8 GB, 32 GB RAM)

```powershell
conda create -n pinstyle python=3.11 pip -y
conda activate pinstyle
pip install torch==2.14.1 torchvision==0.29.1 --index-url https://download.pytorch.org/whl/cu130
# requirements.txt without its torch lines (torch comes from the CUDA index above)
Get-Content requirements.txt | Where-Object { $_ -notmatch '^torch' } | Set-Content req-win.txt
pip install -r req-win.txt -e .
```

The exact versions used are in `requirements.lock.win.txt`.

**aria2c:** download `aria2-1.37.0-win-64bit-build1.zip` from the [aria2 releases](https://github.com/aria2/aria2/releases) and put `aria2c.exe` in `third_party/tools/` (or anywhere on `PATH`).

**Low-VRAM mode:** GPUs with less than 16 GiB switch it on automatically. The UNet and ControlNet are offloaded at leaf level, giving a 4.6 GiB peak and about 36 s for one 1024 px global pass on the 4060. Force it with `PINSTYLE_LOW_VRAM=1` or `0`.

### Linux GPU server (tested: RTX 4090 D 24 GB)

```bash
bash scripts/remote/setup_env.sh            # conda env + pinned packages
```

### Models (both paths; network, about 15 GB)

```bash
python scripts/download_models.py
```

- The script downloads the revisions pinned in `configs/demo.yaml`.
- For each model, it probes ModelScope, huggingface.co and hf-mirror, and picks the fastest source. Downloads resume after an interruption.
- Every file is checked against the Hugging Face hashes, and the result is recorded in `models/MANIFEST.json`.
- Set `HF_ENDPOINT=https://huggingface.co` where huggingface.co is reachable. The default is hf-mirror.

### Check

```bash
pytest                                      # sockets blocked; no GPU needed
ruff check . && ruff format --check .
python scripts/smoke_cuda.py                # server: also tries a 20 GiB allocation
```

## Run

```bash
# app on http://127.0.0.1:7860 (server: ssh -L 7860:127.0.0.1:7860 ...)
python -m pinstyle.app.ui

# CLI
python -m pinstyle.cli global --case shichimi_flat --seeds 0 1 2
python -m pinstyle.cli run --case shichimi_flat --pairs configs/pairs/shichimi_ornament.json --seeds 0
python scripts/make_figure_d3.py runs/<run dir> figure.png
python scripts/exp_colour.py                # colour vs rendering
```

### In the app (Finish tab)

The case `shichimi_flat` loads automatically.

1. Click **Generate**.
2. Click the ivory horn to the lower right of the blonde girl's head in the **reference**.
3. Click the white horn beside Shichimi's head in the **draft**. The pin's tag is pre-filled from the case.
4. Click **Fix pinned details**. The result is the right side of the before/after slider, saved as `runs/<run>/output.png`.

- **Fix pinned details** redoes only the pinned regions of the latest result. Click it again to keep refining.
- **Generate + fix** does both steps in one click.
- **Colour from reference:** 0 keeps the draft's colours.
- **Advanced settings** (collapsed): prompt, generation mode, rendering, structure, steps, seed and resolution.
- **History** (collapsed): earlier versions, and an A/B comparison.

### Comparison with external services (paid; D5 only)

Keys go in `.env`. That file is gitignored, so they are never committed. The budget rules are in [ADR-0009](docs/decisions/0009-domestic-image-providers.md).

```bash
python scripts/run_compare.py --trial       # 1 call per provider
python scripts/run_compare.py --run
python scripts/make_review.py               # blind review page: local_runs/review/index.html
python scripts/make_review.py --reveal local_runs/review/review_labels.json
python scripts/make_report.py
```

## Attribution (CC BY 4.0)

All demo images are by **David Revoy**, from [www.peppercarrot.com](https://www.peppercarrot.com), under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The source URL of each work is in `assets/demo/MANIFEST.csv`.

| Work | Attribution |
|---|---|
| Shichimi concept art | © David Revoy 2015 |
| Shichimi and Torreya | © David Revoy 2025 |
| Pepper and Carrot in traditional clothing of Bergen | © David Revoy 2024 |
| Portrait of Pepper | © David Revoy 2017 |
| Pepper | © David Revoy 2019 |
| Pepper | © David Revoy 2021 |
| Coriander concept art | © David Revoy 2015 |
| Coriander the queen | © David Revoy 2019 |

Drafts are *simulated* from these works (line art plus flat colours). The project's outputs are derived from them and are labelled AI-assisted.

## Limitations

- **Data:**
  - only two working cases;
  - the drafts are simulated from the finished works, so they already contain the original colours;
  - the authors are not the users.
- **Global pass:** it can change the draft's content: backgrounds, small props such as the paper crane, the fox's tail. PinStyle only fixes the pinned regions.
- **Evaluation:** the owner's blind review and the developer's non-blind review agree on 10 of 24 items. They disagree on whether colours should follow the draft or the reference, which motivated the separate colour control.
- **Reproducibility:** results are not bit-identical across GPUs. The same seed gives a similar but not identical image on the 4090 and the 4060.
- **Governance** (registry, provenance, usage log) is shown as a concept only.
