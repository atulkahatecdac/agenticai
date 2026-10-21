"""
Birthday Gift Hunt - game engine and agent tools.

No LLM code lives here. This module holds:
  * the 15-page "house" (loaded from pages.json): each page is a room or hiding spot
  * HuntState: everything the agent has done so far (visited pages, evidence, tool calls)
  * the three tools the agent may use: read_page, list_links, submit_answer

The tools receive the HuntState through the Agents SDK's RunContextWrapper,
so each run gets its own fresh state (no globals).

Rules the engine enforces (so the LLM cannot cheat):
  1. The agent may only open pages it has already discovered a link to.
  2. submit_answer checks the answer AND that the cited evidence pages were
     actually visited and include the decisive evidence.
  3. A hard budget of MAX_TOOL_CALLS tool calls.
"""

import json
import os
from dataclasses import dataclass, field

from agents import RunContextWrapper, Tool, function_tool

PAGES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pages.json")
MAX_TOOL_CALLS = 20

with open(PAGES_FILE, encoding="utf-8") as f:
    HUNT = json.load(f)

PAGES = HUNT["pages"]


@dataclass
class HuntState:
    max_tool_calls: int = MAX_TOOL_CALLS
    reachable: set = field(default_factory=lambda: {HUNT["start_page"]})
    visited: list = field(default_factory=list)       # page ids, in visit order
    current_page: str | None = None
    tool_calls: list = field(default_factory=list)    # one dict per tool call
    status: str = "playing"                            # playing | solved | out_of_steps
    final_answer: str | None = None
    final_evidence: list = field(default_factory=list)

    def budget_left(self) -> int:
        return self.max_tool_calls - len(self.tool_calls)

    def log(self, tool: str, args: dict, reason: str, result: str) -> None:
        self.tool_calls.append(
            {"step": len(self.tool_calls) + 1, "tool": tool, "args": args,
             "reason": reason, "result": result}
        )


def _out_of_budget(state: HuntState) -> str | None:
    if state.budget_left() <= 0:
        state.status = "out_of_steps"
        return "BUDGET EXHAUSTED: no tool calls left. Stop and report what you found."
    return None


def _link_list(page_id: str) -> str:
    return "\n".join(f"  - {pid}: {PAGES[pid]['title']}" for pid in PAGES[page_id]["links"])


@function_tool
def read_page(ctx: RunContextWrapper[HuntState], page_id: str, reason: str) -> str:
    """Open a page and read its full content and outgoing links.

    Args:
        page_id: The id of the page to open, e.g. "p01". It must be a page you have
            already seen a link to (or the start page).
        reason: One short sentence explaining why this page is the most useful next step.
    """
    state = ctx.context
    if (msg := _out_of_budget(state)):
        return msg

    page_id = page_id.strip().lower()
    if page_id not in PAGES:
        result = f"ERROR: no page called '{page_id}'."
    elif page_id not in state.reachable:
        result = f"ERROR: you have not found a link to '{page_id}' yet. Only open pages linked from pages you have read."
    else:
        page = PAGES[page_id]
        state.current_page = page_id
        if page_id not in state.visited:
            state.visited.append(page_id)
        state.reachable.update(page["links"])
        result = (f"PAGE {page_id}: {page['title']}\n\n{page['content']}\n\n"
                  f"FROM HERE YOU CAN GO TO:\n{_link_list(page_id)}")

    state.log("read_page", {"page_id": page_id}, reason, result)
    return result + f"\n\n(Tool calls left: {state.budget_left()})"


@function_tool
def list_links(ctx: RunContextWrapper[HuntState], page_id: str, reason: str) -> str:
    """Peek at the titles of the links on a page without reading its content.
    Cheaper than read_page; useful for deciding which branch looks promising.

    Args:
        page_id: The id of a page you have already found a link to.
        reason: One short sentence explaining why you want to peek at this page.
    """
    state = ctx.context
    if (msg := _out_of_budget(state)):
        return msg

    page_id = page_id.strip().lower()
    if page_id not in PAGES or page_id not in state.reachable:
        result = f"ERROR: '{page_id}' is not a page you have found a link to."
    else:
        state.reachable.update(PAGES[page_id]["links"])
        result = f"Links on {page_id} ({PAGES[page_id]['title']}):\n{_link_list(page_id)}"

    state.log("list_links", {"page_id": page_id}, reason, result)
    return result + f"\n\n(Tool calls left: {state.budget_left()})"


@function_tool
def submit_answer(ctx: RunContextWrapper[HuntState], answer: str,
                  evidence_page_ids: list[str], reason: str) -> str:
    """Submit exactly where Mom's birthday gift is hidden.

    Args:
        answer: The exact hiding place, e.g. "inside the ... in the ...".
        evidence_page_ids: Ids of the pages you READ that prove the answer.
        reason: A short summary of the evidence chain that supports the answer.
    """
    state = ctx.context
    if (msg := _out_of_budget(state)):
        return msg

    evidence = [p.strip().lower() for p in evidence_page_ids]
    unvisited = [p for p in evidence if p not in state.visited]
    missing = [p for p in HUNT["required_evidence"] if p not in evidence]
    correct = any(k in answer.lower() for k in HUNT["answer_keywords"])

    if unvisited:
        result = f"REJECTED: you cited pages you never read: {unvisited}. Only cite pages you actually read."
    elif not correct:
        result = "REJECTED: the gift is not there. Re-read Dad's notes carefully and keep searching."
    elif missing:
        result = ("REJECTED: insufficient evidence. You may be on the right track, but you have not "
                  "actually opened that hiding place and seen the gift yet. Keep exploring.")
    else:
        state.status = "solved"
        state.final_answer = HUNT["answer"]
        state.final_evidence = evidence
        result = f"ACCEPTED! Found it: {HUNT['answer']}. Mom's birthday is saved. Stop now and summarise."

    state.log("submit_answer", {"answer": answer, "evidence_page_ids": evidence}, reason, result)
    return result


TOOLS: list[Tool] = [read_page, list_links, submit_answer]


def replay(tool_calls: list[dict]) -> HuntState:
    """Rebuild the HuntState a recorded run had after these tool calls (no LLM, no tools run).
    Used by the app's replay mode, which steps through a run saved with `hunt_agent.py --save`."""
    state = HuntState()
    for call in tool_calls:
        state.tool_calls.append(call)
        result = call["result"]
        if result.startswith("BUDGET"):
            state.status = "out_of_steps"
        elif call["tool"] == "read_page" and result.startswith("PAGE"):
            pid = call["args"]["page_id"]
            state.current_page = pid
            if pid not in state.visited:
                state.visited.append(pid)
            state.reachable.update(PAGES[pid]["links"])
        elif call["tool"] == "list_links" and result.startswith("Links"):
            state.reachable.update(PAGES[call["args"]["page_id"]]["links"])
        elif call["tool"] == "submit_answer" and result.startswith("ACCEPTED"):
            state.status = "solved"
            state.final_answer = HUNT["answer"]
            state.final_evidence = call["args"]["evidence_page_ids"]
    return state
