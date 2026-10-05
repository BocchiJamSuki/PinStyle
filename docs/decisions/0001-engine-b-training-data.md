# 0001 — Engine B training data: OmniStyle-150K plus self-supervised pairs (IMAGStyle unavailable)

- Status: **Deferred — future work** (2026-10-05). Engine B is outside the demo scope ([ADR-0006](0006-demo-scope.md)). The proposal below stands for when Engine B resumes.
- Affects: brief §4.3 (Engine B), §7.2 (benchmark B1), PLAN M6.2 and M7.1.

## Context

- **IMAGStyle is unavailable.** Brief §4.3 trains Engine B on IMAGStyle triplets (content, style, stylized). As of 2026-10-05 IMAGStyle has not been released publicly (THIRD_PARTY.md F1):
  - no Hugging Face dataset exists;
  - the CSGO README lists it as planned;
  - release requests #10 (2024-09-18) and #18 (2025-01-11) have no maintainer reply.
- **The point supervision is weak.** In style-transfer triplets the style image and the stylized target usually show *different content*. So point pairs extracted between them are sparse and mostly texture-level. They are not the semantic detail correspondences (a necklace, an eye highlight) that Engine B must learn.

## Decision (proposed)

1. **D1: OmniStyle-150K replaces IMAGStyle.**
   - Source: HF `StyleXX/OmniStyle-150k`, 150K content/style/stylized triplets at 1024², 200.6 GB.
   - License: the dataset card says Apache-2.0 and the paper says CC BY 4.0, so we give attribution.
   - Use: extract style↔stylized point pairs with the §3.3 matchers, keep the high-confidence ones, and prefer triplets where style and stylized images share content.
2. **D2: self-supervised exact-correspondence pairs**, built from the same images:
   - target: a finished image;
   - draft: its synthesized line art and flat colours;
   - reference: a geometrically warped copy (TPS warp, crop, flip; no colour jitter, because palette is a style feature), progressively patch-shuffled as a curriculum;
   - point pairs: known exactly from the warp.
3. **Mixing and benchmark.** The D1:D2 mixing ratio is an ablation (M7.8). Benchmark B1 uses a held-out OmniStyle subset with manually checked correspondences.

## Alternatives considered

- **Wait for IMAGStyle.** There is no timeline and no response from the maintainers.
- **Generate triplets with CSGO on CC0 images.** Feasible (estimated ~8 s per image, so ~20K triplets in about 45 GPU-h), but the targets would inherit CSGO's own local errors, the very errors Engine B is meant to fix. Kept as a fallback.
- **Use frames from anime videos** (as MangaNinja does). Rejected: the content is copyrighted, which conflicts with this project's ethics.

## Consequences

- Engine B stays "trained once on general data": no artist's data is used.
- Needs at least 500 GB of persistent disk on the rented machine (PLAN M7).
- Provenance caveats are documented in THIRD_PARTY.md §4: the content images are FLUX-generated, the Style30K style images have unverified provenance, and CSGO outputs are part of the data.
- B1 is defined on OmniStyle instead of IMAGStyle.
