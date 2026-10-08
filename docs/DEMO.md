# 2-minute demo script

**Setup** (before the audience arrives):

- Run `python -m pinstyle.app.ui` on the laptop and open http://127.0.0.1:7860.
- On the RTX 4060 Laptop (low-VRAM mode), timings are:
  - global pass: ~27 s (img2img) or ~36 s (txt2img);
  - one PinStyle region: ~38 s.
- So run the global pass **once before** the demo, and show live only the PinStyle step. The fallback images are listed at the end.

| Time | Say | Do |
|---|---|---|
| 0:00–0:20 | "End-to-end tools finish a whole image at once, and small details the artist cares about get lost or redrawn. PinStyle lets the artist pin which part of *their own* finished work should inform which part of the new draft." | Show the Finish tab with case `shichimi_flat` loaded: draft on the right, the artist's own finished work on the left. |
| 0:20–0:40 | "This is the global pass: the draft finished in the style of the reference. Look at the horn ornament by her head." | Show the before/after slider from the pre-run global pass. Zoom on the ornament, which is plain or misrendered. |
| 0:40–1:10 | "One click on the reference's ornament, one click on the draft's ornament: that is the whole instruction." | Click the ivory horn beside the blonde girl in the reference, then the white horn in the draft. Type `white horn hair ornament` in tags. Press **PinStyle on current output**. |
| 1:10–1:30 | "Only that region changes. It is rendered the way *my* reference renders it, as carved ivory. Everything else is untouched: SSIM outside the region is 0.9999 or higher in the logged runs." | Show the after image. Zoom on the carved horn. Then the Versions tab, comparing two versions. |
| 1:30–1:50 | "In blind review, the two commercial services either ignored the draft or ignored the reference. And the reviewers disagreed on whether colours should follow the draft or the reference, so the app now gives that choice to the artist." | Show the D5 grid. Move the **Colour from reference** slider and say what it does. |
| 1:50–2:00 | "No per-artist training, local-first, own work only. Registry and provenance are next." | Open the Governance (concept) tab. |

**Fallbacks** (precomputed; use them if a live run is slow or fails):

| Step | File |
|---|---|
| Before/after with zoom (4090 run) | `local_runs/d3c/figure_shichimi_s0.png` (rebuild with `scripts/make_figure_d3.py local_runs/d3c/20261008T105124Z_pinstyle_shichimi_flat_s0`) |
| Same, laptop run, img2img global | `local_runs/figure_img2img_shichimi.png` (`runs/20261008T124815Z_pinstyle_shichimi_flat_s0`) |
| Ablation (horn vs background reference point) | `local_runs/d3c/grid.jpg` |
| D5 comparison | `runs/d5/report/grid_shichimi_flat.png` and `docs/D5_REPORT.md` |
| Colour control | `local_runs/colour_shichimi_flat_s0.jpg`, `local_runs/colour_pepper_bergen_flat_s0.jpg` |

`local_runs/` and `runs/` are gitignored, because they hold derivatives of CC BY works and generated images. Each figure is rebuilt from its run directory with the scripts named above. Credit: images by David Revoy, Pepper&Carrot, CC BY 4.0.
