# 0003 — Geometric matcher keypoints: DISK (ALIKED as ablation), not SuperPoint

- Status: **Deferred — future work** (2026-10-05). The demo has no automatic point suggestion; pairs are clicked by hand ([ADR-0006](0006-demo-scope.md)).
- Affects: brief §3.3; PLAN M4, M7.1.

## Context

Brief §3.3 allows "SuperPoint or DISK features + LightGlue". The LightGlue README (checked 2026-10-05) gives these licenses:

- LightGlue code and weights: Apache-2.0.
- DISK: the same license (Apache-2.0).
- ALIKED: BSD-3-Clause.
- SuperPoint: "a different, restrictive license", covering both its weights and its inference file.

## Decision

- DISK + LightGlue is the default.
- ALIKED + LightGlue is an ablation.
- SuperPoint is neither installed nor used.

## Consequences

- The whole matching stack is permissively licensed.
- As the brief asks, we still *measure* whether LightGlue is weak across different poses and characters. We expect the semantic (DINOv2) matcher to become the default; that is decided in M4 (planned ADR).
