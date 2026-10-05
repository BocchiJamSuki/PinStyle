# 0008 — Execution topology: Claude Code on the laptop, AutoDL server as remote GPU executor

- Status: **Accepted** (2026-10-05, owner decision). Supersedes the "Claude Code runs on the box" topology in ADR-0006.

## Context

The owner runs Claude Code on a Windows laptop. The GPU is an AutoDL instance (RTX 4090 D, 24 GB) reached over SSH. The repo is public.

## Decision

- **Source of truth:** `git@github.com:BocchiJamSuki/PinStyle.git`.
  - Code is edited **only on the laptop**, then committed and pushed.
  - Before every run, the server runs `git pull --ff-only`. Code is never edited on the server.
- **Server layout:** everything lives on the 150 GB data disk `/root/autodl-tmp`:
  - the clone at `/root/autodl-tmp/PinStyle`;
  - conda env `pinstyle`;
  - the HF cache, `models/` and `runs/`.

  Other folders on that disk are not ours and are left untouched.
- **Access:** key-based SSH only. The server password is never written to any file, script, commit, log or output.
- **GPU jobs:** started over SSH inside `tmux` or `nohup`, logging to `runs/<run_id>/`. The laptop polls the logs instead of holding long SSH sessions.
- **Artifacts:** only small ones (figures, JSON run records, thumbnails) are copied back, to the gitignored `local_runs/` on the laptop. Large files stay on the server.
- **Gradio** runs on the server, bound to 127.0.0.1. The owner opens it with `ssh -L 7860:127.0.0.1:7860 -p <port> root@<host>`.
- **Slow downloads:** if GitHub, PyPI or Hugging Face are slow on the server, run `source /etc/network_turbo` (AutoDL academic acceleration).
- **External-service calls** (D5) may run from the laptop, subject to each provider's regional availability. Never work around geographic restrictions.
- **Cost:** the server runs only while GPU work is happening. When work is done or blocked:
  1. make sure no job is running;
  2. commit and push;
  3. update `docs/STATUS.md`;
  4. shut the instance down from inside with `shutdown`.

  Never shut down mid-job or mid-push, and never release the instance.

## Consequences

- Every run is pinned to a pushed commit, so run records always reference a public commit hash.
- Secrets live only in the laptop's `.env` (gitignored). A secret check runs before every commit.
