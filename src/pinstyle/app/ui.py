"""Gradio demo app: a single Finish page plus a Governance (concept) tab.

Run:  python -m pinstyle.app.ui   (http://127.0.0.1:7860; on the server, tunnel with
ssh -L 7860:127.0.0.1:7860). The main page shows only what the demo flow uses; experiment
settings and the version history sit in collapsed sections (owner feedback, 2026-10-08).
"""

from __future__ import annotations

import os

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("GRADIO_ANALYTICS_ENABLED", "False")

import logging  # noqa: E402
import time  # noqa: E402

import gradio as gr  # noqa: E402
from PIL import Image  # noqa: E402

from pinstyle.app import pairs as P  # noqa: E402
from pinstyle.cases import case_ids, load_case  # noqa: E402
from pinstyle.global_path import GlobalSettings, run_global  # noqa: E402
from pinstyle.runs import new_run_dir, write_record  # noqa: E402

log = logging.getLogger("pinstyle.app")

# "Keep draft content" starts from the (flat) draft, so content and colours stay aligned with
# it and the colour control blends cleanly; "Free re-render" generates from noise under the
# line art (more of the reference's rendering, but it can drop draft content). Colour
# experiment, 2026-10-08 (EXPERIMENTS).
GEN_MODES = {"Keep draft content (img2img)": "img2img", "Free re-render (txt2img)": "txt2img"}
DEFAULT_CASE = "shichimi_flat"
MODE_LABEL = {"global": "Generate", "global_local": "Generate + fix", "local_on_current": "Fix"}


def _stack():
    from pinstyle.models import sdxl_stack

    return sdxl_stack()


def _engine():
    from pinstyle.engine_a import EngineA

    return EngineA(_stack())


def _outside_change(a, b, masks):
    from pinstyle.cli import outside_change

    return outside_change(a, b, masks)


# ---------------------------------------------------------------- handlers


def load_case_ui(case_id: str):
    case = load_case(case_id)
    ref, draft = case.reference_image(), case.draft.convert("RGB")
    state = P.PairState(default_tags=", ".join(case.accessories[:1]))
    sess = {
        "case": case_id,
        "ref": ref,
        "draft": draft,
        "source": case.source.id,
        "reference": case.reference.id,
        "draft_source": case.draft_source,
    }
    return (
        sess,
        state,
        P.draw_markers(ref, state, "ref"),
        P.draw_markers(draft, state, "tgt"),
        [],
        case.prompt,
        None,
        (
            "⚠️ **Debug case:** unverified images, for local testing only (not for the demo). "
            if case_id.startswith("debug_")
            else ""
        )
        + "**Step 1:** click **Generate**. **Step 2:** click a detail on the reference, then the "
        "same detail on the draft. **Step 3:** click **Fix pinned details**.",
    )


def _redraw(sess, state):
    return (
        P.draw_markers(sess["ref"], state, "ref"),
        P.draw_markers(sess["draft"], state, "tgt"),
        P.to_compact(state),
    )


def on_ref_click(sess, state, evt: gr.SelectData):
    if not sess:
        return gr.skip(), gr.skip(), gr.skip(), state, "Choose a case first."
    state = P.click_ref(state, P.normalize(evt.index, sess["ref"].size))
    return *_redraw(sess, state), state, "Now click the same detail on the **draft**."


def on_draft_click(sess, state, evt: gr.SelectData):
    if not sess:
        return gr.skip(), gr.skip(), gr.skip(), state, "Choose a case first."
    if state.pending_ref is None:
        return *_redraw(sess, state), state, "Click the **reference** first."
    state = P.click_tgt(state, P.normalize(evt.index, sess["draft"].size))
    msg = f"Pinned **{state.pairs[-1].id}**. Add more, or click **Fix pinned details**."
    return *_redraw(sess, state), state, msg


def on_table_edit(sess, state, rows):
    if not sess:
        return state
    rows = rows.values.tolist() if hasattr(rows, "values") else rows
    return P.from_compact(state, rows)


def on_undo(sess, state):
    state = P.undo(state)
    if not sess:
        return gr.skip(), gr.skip(), [], state
    return *_redraw(sess, state), state


def on_clear(sess, state):
    state = P.clear(state)
    if not sess:
        return gr.skip(), gr.skip(), [], state
    return *_redraw(sess, state), state


def run(
    mode,
    sess,
    state,
    versions,
    prompt,
    gen_mode,
    style,
    colour,
    structure,
    steps,
    seed,
    resolution,
    progress,
):
    if not sess:
        raise gr.Error("Choose a case first.")
    if mode != "global" and not state.pairs:
        raise gr.Error("Pin at least one detail: click the reference, then the draft.")
    stack = _stack()
    settings = GlobalSettings(
        prompt=prompt,
        mode=GEN_MODES[gen_mode],
        img2img_strength=0.75,
        style_strength=float(style),
        colour_strength=float(colour),
        structure_strength=float(structure),
        steps=int(steps),
        seed=int(seed),
        resolution=int(resolution),
    )
    t0 = time.perf_counter()
    if mode == "local_on_current":
        cur = next((v for v in reversed(versions) if v["case"] == sess["case"]), None)
        if cur is None:
            raise gr.Error("Nothing to fix yet: click Generate first.")
        glob_out, ginfo = Image.open(cur["output"]).convert("RGB"), {"from_version": cur["id"]}
    else:
        progress(0.1, desc="generating")
        glob_out, ginfo, _ = run_global(stack, sess["draft"], sess["ref"], settings)
    out, einfo, masks = glob_out, None, {}
    if mode != "global":
        progress(0.6, desc="fixing pinned details")
        pairs, regions = P.to_engine(state)
        out, einfo = _engine().apply(
            glob_out, sess["draft"], [sess["ref"]], pairs, regions, seed=int(seed)
        )
        einfo.pop("layers")
        masks = einfo.pop("masks")
    run_dir = new_run_dir(f"app_{mode}_{sess['case']}_s{int(seed)}")
    glob_out.save(run_dir / "before.png")
    out.save(run_dir / "output.png")
    rec = dict(
        kind=f"app_{mode}",
        case=sess["case"],
        seed=int(seed),
        source=sess["source"],
        reference=sess["reference"],
        draft_source=sess["draft_source"],
        models=stack.revisions,
        global_info=ginfo,
        engine_info=einfo,
        pairs=[vars(p) for p in state.pairs],
        latency_s=round(time.perf_counter() - t0, 2),
    )
    if masks:
        rec["change_vs_before"] = _outside_change(glob_out, out, masks.values())
    write_record(run_dir, **rec)
    v = {
        "id": run_dir.name,
        "time": time.strftime("%H:%M:%S"),
        "case": sess["case"],
        "mode": mode,
        "seed": int(seed),
        "pairs": len(state.pairs),
        "output": str(run_dir / "output.png"),
    }
    versions = [*versions, v]
    msg = (
        f"{MODE_LABEL[mode]} done in {rec['latency_s']:.0f} s. The result is the right side of "
        f"the slider, saved as `{run_dir.name}/output.png`."
    )
    return (glob_out, out), versions, version_rows(versions), version_choices(versions), msg


def version_rows(versions):
    return [[v["time"], MODE_LABEL[v["mode"]], v["pairs"], v["id"]] for v in versions]


def version_choices(versions):
    ids = [v["id"] for v in versions]
    return gr.update(choices=ids), gr.update(choices=ids)


def compare(versions, a, b):
    by = {v["id"]: v for v in versions}
    if a not in by or b not in by:
        raise gr.Error("Pick two versions.")
    return (Image.open(by[a]["output"]), Image.open(by[b]["output"]))


# ---------------------------------------------------------------- layout

GOV_MD = """
> **Concept, not implemented.** These are the governance functions of the full system
> (ARCHITECTURE §12–§13). Nothing on this tab is enforced in the demo.

**Registry.** The artist registers their own finished works (upload, authorship declaration,
optional portfolio URL). Only registered works can be used as references.

**Provenance label on export.**

| Field | Example |
|---|---|
| Label | AI-assisted finishing (PinStyle demo) |
| References | registered work IDs + sha256 |
| Engine | global path + Engine A v0.1, settings, seed |
| Usage log | append-only, hash-chained |
"""

CSS = """
.gradio-container {max-width: 1180px !important; margin: auto;}
#title h1 {margin-bottom: 0;}
#title p {margin-top: 4px; color: var(--body-text-color-subdued);}
#status {min-height: 2.2em;}
.pin-img img {object-fit: contain;}
"""

BUTTON_HELP = (
    "**Generate**: finish the whole draft in the reference's style. "
    "**Fix pinned details**: redo only the pinned regions of the latest result (repeat to "
    "keep refining). **Generate + fix**: both in one click."
)


def build() -> gr.Blocks:
    with gr.Blocks(title="PinStyle") as demo:
        sess = gr.State(None)
        state = gr.State(P.PairState())
        versions = gr.State([])
        gr.Markdown(
            "# PinStyle\nFinish a draft in the style of your own work, and pin the details "
            "that matter.",
            elem_id="title",
        )
        with gr.Tab("Finish"):
            with gr.Row(equal_height=True):
                case_dd = gr.Dropdown(case_ids(), value=DEFAULT_CASE, label="Case", scale=1)
                status = gr.Markdown(elem_id="status")
            with gr.Row():
                ref_img = gr.Image(
                    label="① Your finished work (reference): click a detail",
                    type="pil",
                    interactive=False,
                    height=420,
                    elem_classes="pin-img",
                )
                draft_img = gr.Image(
                    label="② Your draft: click the same detail",
                    type="pil",
                    interactive=False,
                    height=420,
                    elem_classes="pin-img",
                )
            with gr.Row(equal_height=True):
                table = gr.Dataframe(
                    headers=P.COMPACT_HEADERS,
                    label="Pinned details",
                    interactive=True,
                    wrap=True,
                    scale=3,
                )
                with gr.Column(scale=1, min_width=160):
                    undo_btn = gr.Button("Undo last pin", size="sm")
                    clear_btn = gr.Button("Clear pins", size="sm")
            with gr.Row():
                b_global = gr.Button("Generate")
                b_local = gr.Button("Fix pinned details", variant="primary")
                b_both = gr.Button("Generate + fix")
            gr.Markdown(BUTTON_HELP)
            colour = gr.Slider(
                0,
                1,
                1.0,
                step=0.05,
                label="Colour from reference (0 = keep the draft's colours)",
            )
            slider = gr.ImageSlider(label="Before / after", type="pil", height=640)
            with gr.Accordion("Advanced settings", open=False):
                prompt = gr.Textbox(label="Prompt", lines=2)
                with gr.Row():
                    gen_mode = gr.Dropdown(
                        list(GEN_MODES), value=next(iter(GEN_MODES)), label="Generation"
                    )
                    seed = gr.Number(0, precision=0, label="Seed")
                    resolution = gr.Dropdown([768, 1024], value=1024, label="Resolution")
                with gr.Row():
                    style = gr.Slider(0, 1.5, 1.0, step=0.05, label="Rendering from reference")
                    structure = gr.Slider(0, 1.5, 1.0, step=0.05, label="Structure strength")
                    steps = gr.Slider(4, 50, 30, step=1, label="Steps")
            with gr.Accordion("History", open=False):
                vtable = gr.Dataframe(
                    headers=["time", "action", "pins", "run"], interactive=False, wrap=True
                )
                with gr.Row():
                    va = gr.Dropdown([], label="Version A")
                    vb = gr.Dropdown([], label="Version B")
                    cmp_btn = gr.Button("Compare", size="sm")
                vslider = gr.ImageSlider(label="A / B", type="pil")
        with gr.Tab("Governance (concept)"):
            gr.Markdown(GOV_MD)

        load_outs = [sess, state, ref_img, draft_img, table, prompt, slider, status]
        demo.load(load_case_ui, case_dd, load_outs)
        case_dd.change(load_case_ui, case_dd, load_outs)
        ref_img.select(on_ref_click, [sess, state], [ref_img, draft_img, table, state, status])
        draft_img.select(on_draft_click, [sess, state], [ref_img, draft_img, table, state, status])
        table.input(on_table_edit, [sess, state, table], state)
        undo_btn.click(on_undo, [sess, state], [ref_img, draft_img, table, state])
        clear_btn.click(on_clear, [sess, state], [ref_img, draft_img, table, state])
        settings = [prompt, gen_mode, style, colour, structure, steps, seed, resolution]
        outs = [slider, versions, vtable, va, vb, status]
        for btn, mode in (
            (b_global, "global"),
            (b_both, "global_local"),
            (b_local, "local_on_current"),
        ):
            btn.click(make_runner(mode), [sess, state, versions, *settings], outs)
        cmp_btn.click(compare, [versions, va, vb], vslider)
    return demo


def make_runner(mode: str):
    # a named function with an explicit progress parameter, so Gradio injects the tracker
    def runner(
        sess,
        state,
        versions,
        prompt,
        gen_mode,
        style,
        colour,
        structure,
        steps,
        seed,
        resolution,
        progress=gr.Progress(),  # noqa: B008 (Gradio injects the tracker by default value)
    ):
        return _unpack(
            run(
                mode,
                sess,
                state,
                versions,
                prompt,
                gen_mode,
                style,
                colour,
                structure,
                steps,
                seed,
                resolution,
                progress,
            )
        )

    return runner


def _unpack(res):
    images, versions, rows, (ua, ub), msg = res
    return images, versions, rows, ua, ub, msg


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    _stack()  # warm up: models load once and stay resident
    build().queue(default_concurrency_limit=1).launch(
        server_name="127.0.0.1",
        server_port=7860,
        theme=gr.themes.Soft(primary_hue="rose", neutral_hue="slate"),
        css=CSS,
    )


if __name__ == "__main__":
    main()
