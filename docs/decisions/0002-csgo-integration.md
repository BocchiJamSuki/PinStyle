# 0002 — CSGO integration: our own attention processors around the Apache-2.0 weights

- Status: **Deferred — future work** (2026-10-05). The demo uses IP-Adapter / InstantStyle. CSGO is at most an optional spike of up to 4 h, using the official code from the gitignored `third_party/`: local use only, never committed, and dropped if it needs patching ([ADR-0006](0006-demo-scope.md)).
- Affects: brief §4.1, §4.2 ("can masked injection run inside CSGO"), §4.3 (branch on top of CSGO); PLAN M1, M2, M7.

## Context

- **The official code has no license** (github.com/instantX-research/CSGO; GitHub API `license: null`; last push 2024-09-05), so it cannot be vendored or redistributed.
- **The weights are Apache-2.0** (HF `InstantX/CSGO`).
- **How CSGO works** (read from its code):
  - it installs custom `IP_CS_AttnProcessor2_0` processors on the SDXL UNet and on its Tile ControlNet;
  - it concatenates 4 content and 32 style tokens onto `prompt_embeds`;
  - it applies no spatial mask (`attn_mask=None` on the image branches).
- **What we need on the same UNet:** per-region masks (Engine A) and extra token groups (Engine B).
- **Age:** the code targets 2024-era diffusers; diffusers is now at 0.40.

## Decision (proposed)

- **Our own processor bank.** Implement an attention-processor bank: a token layout with N groups, each with its own K/V projections, scale, block targeting and optional spatial mask (ARCHITECTURE §7.2). Add a loader that maps `csgo_4_32.bin` into it.
- **Official code for parity only.**
  - Clone the official repo only into the gitignored `third_party/` (pinned commit, separate environment if needed).
  - Use it only for a parity test: same seed and settings, target LPIPS < 0.02.
  - It is never committed or redistributed.
- **License request.** The owner decides whether to ask the authors to add a license (GitHub issue).

## Alternatives considered

- **Vendor and modify the official code.** License risk.
- **Use the official code unmodified, plus a separate diffusers inpainting pass for local edits.** This needs either two UNets in VRAM or swapping processors between calls, and gives no regional masks inside CSGO. It stays as a fallback for the CSGO path if parity cannot be reached (it is still not vendored).

## Consequences

- More work in M1, in exchange for one shared UNet serving the global path, Engine A and Engine B ([ADR-0005](0005-model-residency.md)).
- The parity test guards fidelity to CSGO, and any remaining difference is documented in EXPERIMENTS.md.
- Engine A variant A1 (masked regional CSGO style groups) becomes possible; whether A1 or A2 (separate pass) is used is decided in M2 (planned ADR).
