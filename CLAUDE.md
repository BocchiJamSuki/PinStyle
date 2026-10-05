# PinStyle — project guide for Claude Code

@docs/PROJECT_BRIEF.md

Research prototype: illustrators "pin" their *own* style onto regions of a new draft with a few point pairs.

**Current scope: the demo** ([ADR-0006](docs/decisions/0006-demo-scope.md); `docs/PLAN.md` Part A, milestones D0–D6). The full research plan (PLAN Part B, and ARCHITECTURE §1–§18) is **future work**. Don't build it unless the owner asks.

Before working, read:

- `docs/PLAN.md` Part A — status and the next milestone;
- `docs/ARCHITECTURE.md` §0 — the demo architecture;
- `docs/THIRD_PARTY.md` §0 — demo components and versions;
- ADRs [0006](docs/decisions/0006-demo-scope.md) and [0007](docs/decisions/0007-demo-image-policy.md).

## Non-negotiables

- **SDXL base only.** No per-artist fine-tuning: never train LoRA, DreamBooth, textual inversion or similar on anyone's work.
- **Images** ([ADR-0007](docs/decisions/0007-demo-image-policy.md)):
  - CC0 or CC BY only (no NC/ND), by the verified actual author (no reposts);
  - each listed in `assets/demo/MANIFEST.csv` (source URL, author, license, attribution);
  - approved by the owner before use.
- **AI-generated images are for debugging only** (`assets/debug/`), never in the demo or the comparison.
- **Local-first.** Generation code makes no network calls. Only `scripts/download_models.py` and the providers in `src/pinstyle/compare/` touch the network, and only when run explicitly. Tests run with sockets blocked.
- **External services.** For every call, record:
  - provider, exact model ID (plus the model field from the response), SDK version;
  - UTC time, prompt and parameters;
  - input and output hashes.

  Outputs are for evaluation only ([ADR-0004](docs/decisions/0004-external-services-policy.md)).
- **Never fabricate results.** Every number comes from a run record (config, seed, commit hash, run ID), and estimates are labelled as estimates. Never stage a "detail lost" case.
- **Communicate with the owner in Chinese.**
- **Never vendor unlicensed or non-commercial code** (official CSGO, CoCoDiff, MangaNinja). Use the gitignored `third_party/`, locally only.

## Environment and topology ([ADR-0008](docs/decisions/0008-execution-topology.md))

- **Claude Code runs on the Windows laptop.** The AutoDL server (RTX 4090 D, 24 GB) is only a remote GPU executor, reached with key-based SSH: `ssh -p 39283 root@connect.westb.seetacloud.com`. The server password is never written anywhere.
- **Git is the only sync path.**
  - Edit code only on the laptop, then commit and push to `git@github.com:BocchiJamSuki/PinStyle.git`.
  - Before every run, the server does `git pull --ff-only`.
  - Never edit code on the server.
- **Server layout** (on the 150 GB data disk, `/root/autodl-tmp`):
  - the clone at `/root/autodl-tmp/PinStyle`;
  - conda env `pinstyle` (`/root/miniconda3`);
  - the HF cache, `models/` and `runs/`.

  Leave the disk's other folders alone. If downloads are slow, run `source /etc/network_turbo`.
- **GPU jobs:** run them in `tmux` or `nohup`, logging to `runs/<run_id>/`, and poll the logs. Copy back only small artifacts (figures, JSON records, thumbnails) to the gitignored `local_runs/`.
- **Conda env `pinstyle`** (Python 3.11) is built from `environment.yml`, which pins every version. Change dependencies only by editing it, then rebuild or re-export.
- **Gradio** runs on the server, bound to 127.0.0.1, with `GRADIO_ANALYTICS_ENABLED=False`. The owner opens it with `ssh -L 7860:127.0.0.1:7860 -p 39283 root@connect.westb.seetacloud.com`.

## Operating rules

- **Autonomy.** Work through D0–D6 without milestone approvals. Record significant decisions as ADRs, and commit and push at the end of each milestone.
- **Stop and ask the owner only for:**
  - missing credentials (OpenAI key, Gemini paid-tier key, budget cap) or the Midjourney decision;
  - human steps (the D5 blind review, the D6 demo dry run);
  - the server being unreachable or powered off (ask the owner to start it in the AutoDL console);
  - hard blockers:
    - an external provider unavailable from the owner's region (never work around geographic restrictions; propose compliant options instead);
    - spending beyond the budget;
    - anything destructive outside the project directory.

  Write every request to the owner in `docs/STATUS.md` as well.
- **External-service calls** may run from the laptop.
- **Public repo:**
  - before every commit, run a secret check (gitleaks if available, otherwise a grep for key and password patterns) and inspect `git status`;
  - keys live only in `.env`, which is gitignored.
- **Cost and shutdown.** The server runs only while GPU work is happening. When all work is done, or when blocked waiting for the owner:
  1. make sure no server job is running;
  2. commit and push everything;
  3. update `docs/STATUS.md` (what is done, what is needed from the owner, how to resume) and push again;
  4. run `shutdown` on the server over SSH.

  Never shut down mid-job or mid-push, and never release the instance.

## Conventions

- **Code:** src layout (`src/pinstyle`), type hints, ruff for lint and format, and logging instead of `print` in library code.
- **Tests:** pytest with markers `gpu`, `slow` and `network`; the default run excludes them, and sockets are blocked.
- **Config:** YAML in `configs/` (OmegaConf). Every run record stores the resolved config.
- **Coordinates:** point pairs are stored as normalized `(x, y)` in [0, 1], origin top-left. Pixel coordinates exist only inside modules.
- **Models** are loaded once and stay resident in fp16. One GPU job at a time.
- **Interfaces:** keep the `LocalEngine` interface (ARCHITECTURE §5.1), so Engine B can be added later.

## Workflow

- **End of each milestone:** run the tests → update the status in `docs/PLAN.md` → append results with run IDs to `docs/EXPERIMENTS.md` → commit as `D<n>: <summary>` → push.
- **Decisions** go in a short ADR in `docs/decisions/` (Status, Context, Decision, Consequences).
- **Third-party facts** (license, availability, versions) are checked at the source and recorded in `docs/THIRD_PARTY.md` with the date checked.

## Commands (available once D0 is done)

- `conda activate pinstyle`
- `python scripts/smoke_cuda.py` and `python scripts/smoke_models.py`
- `pytest`, then `ruff check . && ruff format --check .`
- `python scripts/download_models.py` — needs network
