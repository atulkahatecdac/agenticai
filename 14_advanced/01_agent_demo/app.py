"""
Birthday Gift Hunt - Streamlit front end.

    streamlit run app.py

Made for the first class of the course, so everything is shown in plain language:
  * a floor plan of the house: the robot moves room to room and leaves a numbered trail
  * a thought bubble with the agent's own reason for each step
  * a board of the sticky notes and wrapped boxes it has found
  * "Under the hood" (off by default): the same steps as real tool calls

Two ways to run it:
  * Replay - steps through a hunt recorded earlier (recorded_run.json); no Ollama needed,
    and you set the pace. Record a new one with `python hunt_agent.py --save`.
  * Live   - the agent (local qwen3:8b via Ollama) decides every step right now.
"""

import asyncio
import base64
import json
import os
import time
from html import escape

import streamlit as st

from house_view import describe, friendly, house_svg, notes_html, pending_sentence, verdict
from hunt_agent import MODEL, RECORDED_RUN, run_hunt, save_run
from hunt_engine import HUNT, MAX_TOOL_CALLS, PAGES, HuntState, replay

st.set_page_config(page_title="Birthday Gift Hunt", page_icon="🎁", layout="wide")

NAVY, CORAL, TEAL, SLATE = "#1F2A44", "#EA4B71", "#1A7F8E", "#5B6475"


# ---------------------------------------------------------------- panels
def bubble_html(state: HuntState, pending: tuple[str, dict] | None) -> str:
    """The robot's thought bubble: what it is about to do (or just did), and why."""
    if pending:
        tool, args = pending
        doing, why = pending_sentence(tool, args), args.get("reason", "")
        head = "🤔 Thinking…"
    elif state.tool_calls:
        call = state.tool_calls[-1]
        icon, doing = describe(call)
        doing, why = f"{icon} {doing}", call["reason"]
        head = f"Step {call['step']}"
    else:
        return (f"<div style='font-size:17px;color:{SLATE};padding:18px'>🤖 The agent is standing at the "
                f"front door, ready to start.</div>")
    extra = ""
    if not pending and (v := verdict(state.tool_calls[-1])):
        colour = TEAL if v[0] == "good" else CORAL
        extra = f"<div style='margin-top:10px;font-weight:700;color:{colour}'>{escape(v[1])}</div>"
    return (f"<div style='font-family:Segoe UI,Helvetica,sans-serif'>"
            f"<div style='font-size:12px;font-weight:700;color:{CORAL};letter-spacing:2px'>{escape(head.upper())}</div>"
            f"<div style='font-size:20px;font-weight:700;color:{NAVY};margin:6px 0 10px'>{escape(doing)}</div>"
            f"<div style='position:relative;background:#F4F6FA;border-radius:14px;padding:14px 16px;"
            f"font-size:16px;color:{NAVY}'>💭 <i>“{escape(friendly(why))}”</i></div>{extra}</div>")


def status_html(state: HuntState) -> str:
    steps = len(state.tool_calls)
    word = {"playing": ("🔎 Searching…", NAVY), "solved": ("🎉 Found Mom's gift!", TEAL),
            "out_of_steps": ("⏱️ Ran out of steps", CORAL)}[state.status]
    if state.status == "playing" and not steps:
        word = ("Ready", SLATE)
    pct = min(100, round(100 * steps / state.max_tool_calls))
    return (f"<div style='display:flex;gap:28px;align-items:center;font-family:Segoe UI,Helvetica,sans-serif'>"
            f"<div style='font-size:22px;font-weight:700;color:{word[1]}'>{word[0]}</div>"
            f"<div style='flex:1'><div style='font-size:13px;color:{SLATE}'>Steps used: <b>{steps}</b> of "
            f"{state.max_tool_calls} allowed · places searched: <b>{len(state.visited)}</b> of {len(PAGES)}</div>"
            f"<div style='background:#E9ECF1;border-radius:6px;height:8px;margin-top:6px'>"
            f"<div style='width:{pct}%;background:{CORAL};height:8px;border-radius:6px'></div></div></div></div>")


def journal(state: HuntState) -> None:
    """Every step so far in plain language, newest first."""
    for call in reversed(state.tool_calls):
        icon, doing = describe(call)
        v = verdict(call)
        line = f"**{call['step']}.** {icon} {doing}  \n<span style='color:{SLATE}'>💭 {friendly(call['reason'])}</span>"
        if v:
            line += f"  \n{'✅' if v[0] == 'good' else '❌'} {v[1]}"
        st.markdown(line, unsafe_allow_html=True)


def under_the_hood(state: HuntState) -> None:
    st.caption("The same steps as the agent really made them: each one is a call to a Python function "
               "(a *tool*). The LLM chose the function and its arguments; our code ran it and sent back the result.")
    for call in state.tool_calls:
        args = {k: v for k, v in call["args"].items()}
        with st.container(border=True):
            st.markdown(f"**Step {call['step']}** `{call['tool']}({json.dumps(args)})`  \n"
                        f"`reason`: {call['reason']}")
            st.code(call["result"][:600], language=None)


def render(state: HuntState, slots: dict, pending=None, reveal=False, show_all=False, hood=False) -> None:
    slots["status"].html(status_html(state))
    # st.html strips inline <svg>, so the floor plan goes in as an image
    svg = base64.b64encode(house_svg(state, show_all=show_all).encode("utf-8")).decode("ascii")
    slots["house"].html(f"<img src='data:image/svg+xml;base64,{svg}' style='width:100%' alt='Floor plan of the house'>")
    slots["bubble"].html(bubble_html(state, pending))
    with slots["notes"].container():
        st.markdown("##### 📌 What it has found")
        st.html(notes_html(state, reveal=reveal or state.status != "playing"))
    with slots["journal"].container():
        if state.tool_calls:
            with st.expander("🗺️ The whole route, step by step", expanded=False):
                journal(state)
    with slots["hood"].container():
        if hood and state.tool_calls:
            st.markdown("#### 🔧 Under the hood: the real tool calls")
            under_the_hood(state)


# ---------------------------------------------------------------- page
st.markdown(f"<h1 style='margin-bottom:0'>🎁 The Birthday Gift Hunt</h1>"
            f"<p style='font-size:18px;color:{SLATE};margin-top:4px'>An AI agent searches the house <b>on its own</b>. "
            f"Nobody tells it where to go: it reads each clue, decides where to look next, and must prove "
            f"where the gift is.</p>", unsafe_allow_html=True)
st.info(f"**The mission:** {HUNT['mission']}", icon="🎂")

recorded = None
if os.path.exists(RECORDED_RUN):
    with open(RECORDED_RUN, encoding="utf-8") as f:
        recorded = json.load(f)

with st.sidebar:
    st.header("How to run it")
    modes = (["▶️ Replay a recorded hunt"] if recorded else []) + ["🔴 Live: the agent decides now"]
    mode = st.radio("Mode", modes, label_visibility="collapsed")
    live = mode.startswith("🔴")
    if live:
        st.caption("Uses a local model through Ollama. Every run takes its own route.")
        model = st.text_input("Local Ollama model", MODEL)
        start = st.button("▶️ Start the hunt", type="primary", width="stretch")
    else:
        st.caption(f"A real run of `{recorded['model']}`, recorded {recorded['recorded']}. "
                   "No Ollama needed; you set the pace.")
        speed = st.slider("Seconds per step", 0.5, 5.0, 2.5, 0.5)
        c1, c2 = st.columns(2)
        play = c1.button("▶️ Play", type="primary", width="stretch")
        step_btn = c2.button("⏭️ Next step", width="stretch")
    if st.button("🔄 Start over", width="stretch"):
        for key in ("state", "summary", "replay_at"):
            st.session_state.pop(key, None)
    st.divider()
    reveal = st.toggle("Show which clues are real (spoiler)", value=False)
    show_all = st.toggle("Show the whole house (spoiler)", value=False)
    hood = st.toggle("🔧 Show what's under the hood", value=False)
    st.caption(f"The agent has 3 tools: walk into a room, peek through a door, and say where the gift is. "
               f"It may use at most {MAX_TOOL_CALLS} steps.")

slots = {"status": st.empty()}
left, right = st.columns([5, 3], gap="medium")
with left:
    slots["house"] = st.empty()
with right:
    slots["bubble"] = st.empty()
    st.write("")
    slots["notes"] = st.empty()
slots["journal"] = st.empty()
summary_slot = st.empty()
slots["hood"] = st.empty()
opts = dict(reveal=reveal, show_all=show_all, hood=hood)

if live and start:
    state = HuntState()
    st.session_state["state"] = state
    st.session_state.pop("summary", None)

    def on_event(event, state):
        # Redraw when the agent picks a tool (before it runs) and when the tool returns.
        if event.type != "run_item_stream_event":
            return
        if event.item.type == "tool_call_item":
            raw = event.item.raw_item
            args = json.loads(getattr(raw, "arguments", "{}") or "{}")
            render(state, slots, pending=(getattr(raw, "name", ""), args), **opts)
        elif event.item.type == "tool_call_output_item":
            render(state, slots, **opts)

    render(state, slots, **opts)
    with st.spinner("The agent is searching the house (a local model can take a minute)…"):
        try:
            st.session_state["summary"] = asyncio.run(run_hunt(state, model=model, on_event=on_event))
        except Exception as e:  # show Ollama/connection errors in the UI instead of a stack trace
            st.session_state["summary"] = f"Run failed: {e}"

elif not live:
    calls = recorded["tool_calls"]
    at = st.session_state.get("replay_at", 0)
    if step_btn and at < len(calls):
        at += 1
    if play:
        for i in range(at, len(calls)):
            render(replay(calls[:i]), slots, pending=(calls[i]["tool"], calls[i]["args"]), **opts)
            time.sleep(speed * 0.5)
            render(replay(calls[:i + 1]), slots, **opts)
            time.sleep(speed * 0.5)
        at = len(calls)
    st.session_state["replay_at"] = at
    st.session_state["state"] = replay(calls[:at])
    if at == len(calls):
        st.session_state["summary"] = recorded["summary"]

state = st.session_state.get("state", HuntState())
render(state, slots, **opts)
if st.session_state.get("summary"):
    with summary_slot.container():
        st.markdown("#### 🧾 The agent's own summary")
        st.write(friendly(st.session_state["summary"]))
        if live and state.tool_calls and st.button("💾 Use this run as the recorded replay"):
            save_run(state, st.session_state["summary"], model=model)
            st.success("Saved. Switch to Replay mode to step through it.")
