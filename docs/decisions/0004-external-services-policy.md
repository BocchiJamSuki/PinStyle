# 0004 — External image services: provider selection and data policy

- Status: **Accepted for the demo** (2026-10-05, owner decision). The **provider choice is superseded by [ADR-0009](0009-domestic-image-providers.md)** (2026-10-07): OpenAI and Gemini are no longer used. The data rules and per-call records below still apply.
- Affects: brief §7.6; PLAN Part A, D5 (the full-plan M6.7 and M8.1 are future work).

## Demo decision (2026-10-05)

- **Providers:**
  - **OpenAI** Images API: `gpt-image-2.5-sunburst` by default (the edit-precision variant; configurable, e.g. to `gpt-image-2`).
  - **Google Gemini** API, **paid tier only**: `gemini-3-pro-image`, and optionally `gemini-3.1-flash-image`.
  - **Midjourney** is optional, by manual import only, and skipped unless the owner confirms a plan with Stealth mode.
- **Dated snapshots:** where a provider offers dated model snapshots (e.g. `gpt-image-2.5-sunburst-2026-09-08`), use them, verify them on the day of the run, and log them.
- **Fairness rule:** from attempt 2 on, prompts may name the accessory and where it is (e.g. "keep the red brooch on the collar"), mirroring how PinStyle users indicate it with points.
  - Stability AI and Black Forest Labs are **not** used in the demo.
- **What may be sent:** only the approved CC0 / CC BY demo images ([ADR-0007](0007-demo-image-policy.md)). Their licenses permit this use. CC BY attribution is kept in our records and outputs, and for Midjourney Stealth mode is preferred.
- **Unchanged:**
  - every call records the provider, the exact model ID and the response's model field, the SDK version, the UTC date, the prompt, the parameters, the input and output hashes, and usage;
  - outputs are used for evaluation only, never for training;
  - the terms are re-checked on the day of each run.

The original proposal for the full plan follows, as background.

## Context

Brief §7.6 compares PinStyle with general-purpose generation services and allows only rights-cleared images to be sent. The services' data terms differ sharply (checked 2026-10-05; details and links in THIRD_PARTY.md §7):

| Provider | Data terms |
|---|---|
| **OpenAI API** | Inputs are not used for training unless you opt in; abuse-monitoring logs are kept for 30 days. |
| **Google Gemini API** (terms modified 2026-04-28) | Paid tier: not used to improve products. Unpaid tier: used to improve and develop products, and human reviewers may read inputs and outputs. |
| **Stability AI** (ToS effective 2026-09-30) | May use inputs and outputs to train its models unless you opt out. |
| **Black Forest Labs** (FLUX API Service Terms, revised 2026-08-04) | You grant a perpetual, irrevocable, sublicensable license to inputs and outputs, for improving and developing products. That document offers no opt-out. |
| **Midjourney** | No public API. The official ToS could not be fetched automatically (HTTP 403). Third-party summaries report a perpetual license to inputs and outputs, with images public by default. |

## Original proposal (full plan, future work)

- **API runners:**
  - OpenAI (`gpt-image-2`, `gpt-image-2.5-*`);
  - Google Gemini (`gemini-3.1-flash-image`, `gemini-3-pro-image`), **paid tier only**;
  - Stability Style Transfer, **only after the training opt-out is set**.
- **Black Forest Labs** is **disabled** unless the owner gives explicit consent for specific images, or an enterprise zero-retention agreement exists.
- **Midjourney:** manual import only, with the owner's own works only, in Stealth mode, and only after the owner has read the official ToS.
- **Every call records:** provider, exact model ID or snapshot, UTC date, prompt, parameters, input hashes, consent reference, outputs, cost and latency.
- **Use of outputs:** for evaluation only, never for training.
- **Terms are re-checked** on the day of each comparison run.

## Consequences

- `pinstyle.external` stays isolated. It needs `offline: false` plus `--allow-network`, and core code never imports it.
- The benchmark manifests carry a consent field per image *per provider*.
- Results reflect the model versions available on the day of each run; this is reported with them.
