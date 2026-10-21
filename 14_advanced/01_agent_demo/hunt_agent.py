"""
Birthday Gift Hunt - the agent.

A single OpenAI Agents SDK agent, running on a LOCAL model (qwen3:8b via Ollama),
that finds Mom's hidden birthday gift by calling the tools in hunt_engine.py.
Nothing about the route is hard-coded: the LLM decides which room to search
next, when to ignore a misleading note, and when it has enough evidence.

Prerequisites:  ollama pull qwen3:8b   (and the Ollama app/server running)

Run from the console:   python hunt_agent.py
Save the run for the app's replay mode:   python hunt_agent.py --save
Run with the web UI:    streamlit run app.py
"""

import asyncio
import datetime
import json
import os
import re
import sys

from openai import AsyncOpenAI
from agents import Agent, OpenAIChatCompletionsModel, Runner, set_tracing_disabled
from agents.exceptions import MaxTurnsExceeded

from hunt_engine import HUNT, MAX_TOOL_CALLS, TOOLS, HuntState

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
MODEL = "qwen3:8b"
MAX_TURNS = MAX_TOOL_CALLS + 5   # SDK-level backstop on top of the engine's tool budget
RECORDED_RUN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "recorded_run.json")

# Tracing uploads to OpenAI's servers by default; there is no OpenAI key in a local-only setup.
set_tracing_disabled(True)

INSTRUCTIONS = f"""You are a helpful kid searching the family house for a hidden birthday gift.

Your goal: {HUNT['mission']}

How the house works:
- Each page is a room or a hiding spot. Reading a page tells you what you see there and where you can go next.
- Start by reading the start page "{HUNT['start_page']}". You can only go to pages listed as "FROM HERE YOU CAN GO TO".

Rules:
- You know NOTHING about this house except what the pages say. Never guess from general knowledge.
- Follow Dad's numbered sticky notes - they are the reliable clues.
- Be careful: some notes are pranks, some are left over from LAST year, and some wrapped boxes are NOT Mom's gift.
  Check the wrapping colour and the tag before deciding.
- Before each tool call, put your reason in the tool's `reason` argument (one short sentence).
- Do not re-read pages you have already read. If you reach a dead end, go back and try another room.
- You have a budget of {MAX_TOOL_CALLS} tool calls in total.
- Only call submit_answer after you have actually SEEN Mom's gift. Give the exact hiding place and
  the ids of the pages that prove it. If it is rejected, read the feedback and keep searching.
- After the answer is accepted (or the budget runs out), stop calling tools and write a short
  summary of how you found the gift, citing page ids.
"""


def build_agent(model: str = MODEL) -> Agent[HuntState]:
    client = AsyncOpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")   # Ollama ignores the key
    return Agent[HuntState](
        name="Birthday Gift Hunter",
        instructions=INSTRUCTIONS,
        tools=TOOLS,
        model=OpenAIChatCompletionsModel(model=model, openai_client=client),
    )


def strip_thinking(text: str) -> str:
    """qwen3 may wrap its private reasoning in <think>...</think>; keep only the final reply."""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


async def run_hunt(state: HuntState, model: str = MODEL, on_event=None) -> str:
    """Run the agent to completion. `on_event(event, state)` is called for every stream event
    (the Streamlit app uses it to redraw its panels live). Returns the agent's final message."""
    agent = build_agent(model)
    result = Runner.run_streamed(agent, input="Start the hunt.", context=state, max_turns=MAX_TURNS)
    try:
        async for event in result.stream_events():
            if on_event:
                on_event(event, state)
    except MaxTurnsExceeded:
        state.status = "out_of_steps"
        return "Stopped: the maximum number of turns was reached."
    if state.status == "playing":
        state.status = "out_of_steps"   # agent gave up without a correct answer
    return strip_thinking(str(result.final_output or ""))


def save_run(state: HuntState, summary: str, model: str = MODEL, path: str = RECORDED_RUN) -> None:
    """Write a finished run to JSON so the app can replay it without Ollama."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"model": model, "recorded": datetime.date.today().isoformat(), "status": state.status,
                   "tool_calls": state.tool_calls, "summary": summary}, f, indent=2, ensure_ascii=False)


def _console_printer(event, state: HuntState) -> None:
    if event.type != "run_item_stream_event":
        return
    if event.item.type == "tool_call_output_item":
        call = state.tool_calls[-1]
        print(f"\n[Step {call['step']}] {call['tool']}({call['args']})")
        print(f"  Why: {call['reason']}")
        print(f"  Result: {call['result'].splitlines()[0]}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")   # Windows consoles choke on emoji in model output
    print("MISSION:", HUNT["mission"])
    print(f"MODEL: {MODEL} via {OLLAMA_BASE_URL}")
    state = HuntState()
    summary = asyncio.run(run_hunt(state, on_event=_console_printer))
    print("\n" + "=" * 70)
    print("STATUS:", state.status, "| tool calls used:", len(state.tool_calls))
    print("VISITED:", " -> ".join(state.visited))
    print("\nAGENT SUMMARY:\n" + summary)
    if "--save" in sys.argv:
        save_run(state, summary)
        print(f"\nSaved for replay: {RECORDED_RUN}")
