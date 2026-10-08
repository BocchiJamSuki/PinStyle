# Status

Last updated: 2026-10-08

## Done

- **D0 ✅** Environment and smoke tests: server 4090, 11.98 GiB peak; env frozen. The laptop env is added in ADR-0010.
- **D1 ✅** 8 Pepper&Carrot works by David Revoy (CC BY 4.0), approved under delegation. Image approval is fully delegated since 2026-10-08 (ADR-0007).
- **D2 ✅** Global path (SDXL + MistoLine + IP-Adapter Plus).
- **D3 ✅** Main case: Shichimi's horn ornament.
  - Reference point on the horn: carved ornament in 6/6 runs.
  - Reference point on the background: 0/6.
  - Pepper ribbon ablation: its colour came from the draft.
- **D5 ✅** Report in `docs/D5_REPORT.md`.
  - Owner's blind review, plus a non-blind developer review with its own criteria. They agree on 10/24 items.
  - Spend: Tencent CNY 1.20, Alibaba CNY 1.40.
- **Colour vs rendering control:** `colour_strength`, plus an app *Generation* mode (img2img keeps draft content). Details in EXPERIMENTS.
- **Moved to the laptop (ADR-0010):** RTX 4060 8 GB, low-VRAM leaf offload. A global pass takes ~27–36 s, and one PinStyle region ~38 s.

## In progress

- **D4 🔄** The app works end to end, tested through its handlers with simulated clicks. The real browser click-through is pending (owner).
- **D6 🔄** `README.md` and `docs/DEMO.md` are written. The dry run is pending (owner).

## Needed from the owner

- **D4 browser check + D6 dry run, on the laptop (no server needed):**
  1. Run `conda activate pinstyle`, then `python -m pinstyle.app.ui`, and open http://127.0.0.1:7860.
  2. Follow `docs/DEMO.md` and time it.
  3. Tell Claude Code what felt wrong.

## How to resume

- **Laptop:** run `conda activate pinstyle` in `D:\Code\PinStyle`. The models are in `models/`, already verified.
- **Server (optional):** start the AutoDL instance, then `git pull --ff-only` (ADR-0008).
