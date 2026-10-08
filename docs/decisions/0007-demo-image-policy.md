# 0007 — Demo image policy: CC0 / CC BY works by their actual authors

- Status: **Accepted** (2026-10-05, owner decision).
- Applies to: `assets/demo/`, the detail case and the comparison runner. For the demo, it narrows brief §7.1.

## Context

The demo and the service comparison need illustrations with clear rights. For now, the owner chose openly licensed works over their own or commissioned works.

## Decision

- **License:** only **CC0** or **CC BY** works (any version), with no NC or ND variants. A CC BY work keeps its attribution (author, title, source URL, license) everywhere it appears: the manifest, figures, report captions and the README.
- **Authorship:** the uploader must be the **actual author**; reposts are skipped. Evidence of authorship is recorded, for example a link to the artist's own site or profile.
- **Grouping:** prefer several works by the same artist, ideally of the same character, so a draft can be simulated from one work and another used as the reference.
- **Detail case:** any small accessory that is lost or misrendered under global transfer qualifies: earrings, hairpin, ribbon, brooch, necklace and so on.
- **Drafts:** where the artist's own line art exists (for example, line-art layers in Pepper&Carrot source files), it is preferred over a simulated draft. Each case records `draft_source` as `artist_lineart` or `simulated`.
- **Manifest:** every image is listed in `assets/demo/MANIFEST.csv` with:
  - source URL, author, license and attribution;
  - authorship evidence;
  - approval status.

  The owner approves the shortlist before any image is used. *Updated 2026-10-05:* the owner delegated this approval to Claude. Claude chooses and approves the shortlist under these rules and marks entries `approved_by: claude (delegated by owner)`.
- **AI-generated images are for debugging only.** They live in `assets/debug/`, are flagged in the manifest, and never appear in the demo or the comparison.
- **Enforcement:** a manifest checker applies these rules in the CLI, the Gradio app and the comparison runner, and refuses to send unapproved images to external services.

## Consequences

- **External services.** The licenses allow sending CC0 and CC BY works to OpenAI, Gemini and Midjourney, and we keep CC BY attribution in our records and outputs. For Midjourney, prefer Stealth mode: posting a CC BY work publicly without attribution would conflict with the license.
- **Sourcing time.** Finding several works of the same character that include a small accessory may take time (D1). The fallback is same-artist, different-character pairs, documented as such.
- **A stand-in scenario.** These works stand in for the brief's "artist's own registered work" scenario, and the demo narrative says so.

## Update 2026-10-08 — approval delegated

The owner delegated image approval to Claude Code: new CC0 / CC BY images may be used without asking, after Claude Code has checked them. The checks are the same as before:

- the license is verified at the source;
- the work is by the actual author (no reposts);
- it is listed in `MANIFEST.csv`;
- no NC or ND licenses.

Each approval is recorded in the manifest and in EXPERIMENTS.
