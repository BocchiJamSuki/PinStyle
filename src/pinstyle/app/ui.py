"""Gradio demo app: Finish, Versions and Governance (concept) tabs.

Run on the GPU server:  python -m pinstyle.app.ui
Bound to 127.0.0.1:7860; the owner tunnels with ssh -L 7860:127.0.0.1:7860.
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
    return (
        {
            "case": case_id,
            "ref": ref,
            "draft": draft,
            "source": case.source.id,
            "reference": case.reference.id,
            "draft_source": case.draft_source,
        },
        state,
        P.draw_markers(ref, state, "ref"),
        P.draw_markers(draft, state, "tgt"),
        [],
        case.prompt,
        None,
        f"Loaded {case_id}: click the reference, then the draft, to make a pair.",
    )


def _redraw(sess, state):
    return (
        P.draw_markers(sess["ref"], state, "ref"),
        P.draw_markers(sess["draft"], state, "tgt"),
        P.to_table(state),
    )


def on_ref_click(sess, state, evt: gr.SelectData):
    if not sess:
        return gr.skip(), gr.skip(), gr.skip(), state, "Load a case first."
    state = P.click_ref(state, P.normalize(evt.index, sess["ref"].size))
    return *_redraw(sess, state), state, "Reference point set: now click the draft."


def on_draft_click(sess, state, evt: gr.SelectData):
    if not sess:
        return gr.skip(), gr.skip(), gr.skip(), state, "Load a case first."
    if state.pending_ref is None:
        return *_redraw(sess, state), state, "Click the reference first."
    state = P.click_tgt(state, P.normalize(evt.index, sess["draft"].size))
    return *_redraw(sess, state), state, f"Pair {state.pairs[-1].id} added."


def on_table_edit(sess, state, rows):
    if not sess:
        return state
    rows = rows.values.tolist() if hasattr(rows, "values") else rows
    return P.from_table(state, rows)


def on_delete(sess, state, pair_id):
    state = P.delete(state, (pair_id or "").strip())
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
    style,
    structure,
    steps,
    seed,
    resolution,
    progress,
):
    if not sess:
        raise gr.Error("Load a case first.")
    if mode != "global" and not state.pairs:
        raise gr.Error("Add at least one point pair.")
    stack = _stack()
    settings = GlobalSettings(
        prompt=prompt,
        style_strength=float(style),
        structure_strength=float(structure),
        steps=int(steps),
        seed=int(seed),
        resolution=int(resolution),
    )
    t0 = time.perf_counter()
    if mode == "local_on_current":
        cur = next((v for v in reversed(versions) if v["case"] == sess["case"]), None)
        if cur is None:
            raise gr.Error("No current output for this case: run global first.")
        glob_out, ginfo = Image.open(cur["output"]).convert("RGB"), {"from_version": cur["id"]}
    else:
        progress(0.1, desc="global pass")
        glob_out, ginfo, _ = run_global(stack, sess["draft"], sess["ref"], settings)
    out, einfo, masks = glob_out, None, {}
    if mode != "global":
        progress(0.6, desc="local correction")
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
        "acceptable": False,
        "before": str(run_dir / "before.png"),
        "output": str(run_dir / "output.png"),
        "dir": str(run_dir),
    }
    versions = [*versions, v]
    msg = f"{mode} done in {rec['latency_s']} s -> {run_dir.name}"
    return (glob_out, out), versions, version_rows(versions), version_choices(versions), msg


def version_rows(versions):
    return [
        [
            v["id"],
            v["time"],
            v["case"],
            v["mode"],
            v["seed"],
            v["pairs"],
            "yes" if v["acceptable"] else "",
        ]
        for v in versions
    ]


def version_choices(versions):
    ids = [v["id"] for v in versions]
    return gr.update(choices=ids), gr.update(choices=ids)


def mark_acceptable(versions):
    if not versions:
        raise gr.Error("No run yet.")
    v = versions[-1]
    versions = [*versions[:-1], {**v, "acceptable": True}]
    import json
    from pathlib import Path

    (Path(v["dir"]) / "acceptable.json").write_text(
        json.dumps(
            {"acceptable": True, "marked_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        )
    )
    return versions, version_rows(versions), f"Marked {v['id']} acceptable."


def compare(versions, a, b):
    by = {v["id"]: v for v in versions}
    if a not in by or b not in by:
        raise gr.Error("Pick two versions.")
    return (Image.open(by[a]["output"]), Image.open(by[b]["output"]))


# ---------------------------------------------------------------- layout

GOV_MD = """
> **Concept — not implemented.** These screens show where governance goes in the full system
> (ARCHITECTURE §12–§13). Nothing on this tab is enforced in the demo.

**Registry.** The artist registers their own finished works (upload, authorship declaration,
optional portfolio URL). Only registered works can be used as references; others are rejected.

**Provenance label on export.**

| Field | Example |
|---|---|
| Label | AI-assisted finishing (PinStyle demo) |
| References | registered work IDs + sha256 |
| Engine | global path + Engine A v0.1, settings, seed |
| Usage log | append-only, hash-chained |
"""


def build() -> gr.Blocks:
    with gr.Blocks(title="PinStyle demo") as demo:
        sess = gr.State(None)
        state = gr.State(P.PairState())
        versions = gr.State([])
        gr.Markdown("# PinStyle — pin your own style onto regions of a draft")
        with gr.Tab("Finish"):
            with gr.Row():
                case_dd = gr.Dropdown(case_ids(), label="Case", value="shichimi_flat")
                load_btn = gr.Button("Load case")
            status = gr.Markdown()
            with gr.Row():
                ref_img = gr.Image(label="Reference (click 1st)", type="pil", interactive=False)
                draft_img = gr.Image(label="Draft (click 2nd)", type="pil", interactive=False)
            table = gr.Dataframe(
                headers=P.TABLE_HEADERS,
                label="Point pairs (edit strength, group, tags)",
                interactive=True,
                wrap=True,
            )
            with gr.Row():
                del_id = gr.Textbox(label="Pair id to delete", scale=1)
                del_btn = gr.Button("Delete pair")
                clear_btn = gr.Button("Clear pairs")
            prompt = gr.Textbox(label="Prompt")
            with gr.Row():
                style = gr.Slider(0, 1.5, 1.0, step=0.05, label="Style strength")
                structure = gr.Slider(0, 1.5, 0.7, step=0.05, label="Structure strength")
                steps = gr.Slider(4, 50, 30, step=1, label="Steps")
                seed = gr.Number(0, precision=0, label="Seed")
                resolution = gr.Dropdown([768, 1024], value=1024, label="Resolution")
            with gr.Row():
                b_global = gr.Button("Global only")
                b_both = gr.Button("Global + PinStyle", variant="primary")
                b_local = gr.Button("PinStyle on current output")
                b_ok = gr.Button("Mark acceptable")
            slider = gr.ImageSlider(label="Before / after", type="pil")
        with gr.Tab("Versions"):
            vtable = gr.Dataframe(
                headers=["id", "time", "case", "mode", "seed", "pairs", "acceptable"],
                interactive=False,
            )
            with gr.Row():
                va = gr.Dropdown([], label="Version A")
                vb = gr.Dropdown([], label="Version B")
                cmp_btn = gr.Button("Compare")
            vslider = gr.ImageSlider(label="A / B", type="pil")
        with gr.Tab("Governance (concept)"):
            gr.Markdown(GOV_MD)

        load_btn.click(
            load_case_ui, case_dd, [sess, state, ref_img, draft_img, table, prompt, slider, status]
        )
        ref_img.select(on_ref_click, [sess, state], [ref_img, draft_img, table, state, status])
        draft_img.select(on_draft_click, [sess, state], [ref_img, draft_img, table, state, status])
        table.input(on_table_edit, [sess, state, table], state)
        del_btn.click(on_delete, [sess, state, del_id], [ref_img, draft_img, table, state])
        clear_btn.click(on_clear, [sess, state], [ref_img, draft_img, table, state])
        settings = [prompt, style, structure, steps, seed, resolution]
        outs = [slider, versions, vtable, va, vb, status]
        for btn, mode in (
            (b_global, "global"),
            (b_both, "global_local"),
            (b_local, "local_on_current"),
        ):
            btn.click(make_runner(mode), [sess, state, versions, *settings], outs)
        b_ok.click(mark_acceptable, versions, [versions, vtable, status])
        cmp_btn.click(compare, [versions, va, vb], vslider)
    return demo


def make_runner(mode: str):
    # a named function with an explicit progress parameter, so Gradio injects the tracker
    def runner(
        sess,
        state,
        versions,
        prompt,
        style,
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
                style,
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
    build().queue(default_concurrency_limit=1).launch(server_name="127.0.0.1", server_port=7860)


if __name__ == "__main__":
    main()
