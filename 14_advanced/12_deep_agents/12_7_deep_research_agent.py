import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

import json
import os
import sys
from typing import Literal
from dotenv import load_dotenv
from pydantic import BaseModel
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain_tavily import TavilySearch

load_dotenv(override=True)
sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# =====================================================================
# A "deep agent" (the 2025 meaning of the term, popularised by Claude
# Code, Deep Research and LangChain's `deepagents` package) is a plain
# tool-calling loop with four extra parts that let it work on a long,
# open-ended task without losing the plot:
#
#   1. A PLANNING tool   - write_todos keeps a to-do list the agent
#                          re-reads and updates as it works
#   2. SUB-AGENTS        - task() hands one sub-question to a fresh
#                          agent with its own empty context; only a
#                          short answer comes back
#   3. A FILE SYSTEM     - write_file / read_file / ls let it park long
#                          notes outside the context window
#   4. A DETAILED PROMPT - says how to use the three tools above
#
# `deepagents` needs LangChain 1.x and this course is pinned to 0.3, so
# the four parts are built by hand here - about 100 lines.
# (12_2/12_3 plan-and-execute: the PLAN is fixed code. Here the agent
#  writes and revises its own plan with a tool.)
# =====================================================================

TODOS: list[dict] = []          # the agent's plan
FILES: dict[str, str] = {}      # a virtual file system (a dict, saved to disk at the end)
search = TavilySearch(max_results=4)


# ---------------------------------------------------------------------
# 1. Planning
# ---------------------------------------------------------------------
class Todo(BaseModel):
    task: str
    status: Literal["pending", "in_progress", "completed"]


@tool
def write_todos(todos: list[Todo]) -> str:
    """Replace the whole to-do list (send every item each time, with its status).
    Call it first to make the plan, and again after each step to update it."""
    TODOS[:] = [t.model_dump() if isinstance(t, BaseModel) else dict(t) for t in todos]
    mark = {"pending": "[ ]", "in_progress": "[>]", "completed": "[x]"}
    print("   PLAN: " + " | ".join(f"{mark[t['status']]} {t['task']}" for t in TODOS))
    return "To-do list saved."


# ---------------------------------------------------------------------
# 3. File system - long notes live here, not in the context window
# ---------------------------------------------------------------------
@tool
def write_file(path: str, content: str) -> str:
    """Save text to a file in your workspace (overwrites)."""
    FILES[path] = content
    print(f"   FILE: wrote {path} ({len(content)} chars)")
    return f"Saved {path}."


@tool
def read_file(path: str) -> str:
    """Read a file from your workspace."""
    return FILES.get(path, f"No file named {path}. Use ls().")


@tool
def ls() -> str:
    """List the files in your workspace."""
    return "\n".join(f"{p} ({len(c)} chars)" for p, c in FILES.items()) or "(empty)"


# ---------------------------------------------------------------------
# 2. Sub-agents - a fresh, isolated context per sub-question
# ---------------------------------------------------------------------
@tool
def web_search(query: str) -> str:
    """Search the web. Returns titles, URLs and snippets."""
    hits = search.invoke(query).get("results", [])
    return "\n\n".join(f"{h['title']} ({h['url']})\n{h['content'][:500]}" for h in hits) or "No results."


RESEARCHER_PROMPT = (
    "You are a research sub-agent. Answer ONE question from the search results you are given; "
    "call web_search once or twice more only if something important is missing. Reply with 4-6 "
    "bullet points of facts, each with the source URL it came from - use only URLs that appear "
    "in the search results. No introduction."
)


def run_loop(system: str, user: str, tools: list, max_steps: int, label: str) -> str:
    """The same tool-calling loop as 06_3 - used by the main agent and every sub-agent."""
    model = llm.bind_tools(tools)
    by_name = {t.name: t for t in tools}
    messages: list[BaseMessage] = [SystemMessage(system), HumanMessage(user)]
    for _ in range(max_steps):
        ai = model.invoke(messages)
        messages.append(ai)
        if not ai.tool_calls:
            return ai.content
        for call in ai.tool_calls:
            if call["name"] not in ("write_todos", "write_file"):
                print(f"{label}{call['name']}({json.dumps(call['args'])[:90]})")
            try:
                result = by_name[call["name"]].invoke(call["args"])
            except Exception as e:
                result = f"Error: {e}"
                print(f"{label}{call['name']} failed: {str(e)[:150]}")
            messages.append(ToolMessage(str(result), tool_call_id=call["id"]))
    return "Stopped: step limit reached."


@tool
def task(question: str) -> str:
    """Delegate ONE focused research question to a sub-agent with its own fresh context.
    It searches the web and returns a short list of sourced facts."""
    print(f"\n   SUB-AGENT starts: {question}")
    # Search first, so the facts come from the web and not from the model's
    # memory; the sub-agent can still search again for anything missing.
    print("      sub-agent -> web_search (the question itself)")
    first_results = web_search.invoke({"query": question})
    brief = f"Question: {question}\n\nFirst search results:\n{first_results}"
    answer = run_loop(RESEARCHER_PROMPT, brief, [web_search], max_steps=5, label="      sub-agent -> ")
    # The full answer goes to a file; the main agent gets a short pointer,
    # so its own context stays small however much research piles up.
    path = f"notes/{len([p for p in FILES if p.startswith('notes/')]) + 1}.md"
    write_file.invoke({"path": path, "content": f"# {question}\n\n{answer}"})
    pointer = f"Done. Full findings saved to {path} ({len(answer)} chars). First line: {answer.strip().splitlines()[0][:150]}"
    print(f"   SUB-AGENT done -> main agent gets {len(pointer)} chars, not {len(answer)}")
    return pointer


# ---------------------------------------------------------------------
# 4. The main agent's prompt - how to use planning, sub-agents and files
# ---------------------------------------------------------------------
MAIN_PROMPT = """You are a deep research agent for a streaming-media analytics team.
Work like this:
1. Call write_todos with a plan of 3-4 sub-questions, then a final 'write report' item.
2. For each sub-question call task() - never search yourself. A sub-agent saves its
   findings to a notes/ file and tells you which one.
3. After each step call write_todos again with the updated statuses.
4. Finally ls() and read_file every note, then write the report with write_file('report.md', ...):
   a title, a 3-sentence executive summary, one section per sub-question, and sources.
   Then reply with just: DONE."""

if __name__ == "__main__":
    question = (
        "What is driving the rise of particular genres on video streaming platforms this year, "
        "and what should a content team do about it?"
    )
    print("QUESTION:", question, "\n")
    status = run_loop(MAIN_PROMPT, question, [write_todos, task, write_file, read_file, ls],
                      max_steps=20, label="   main -> ")

    out_dir = os.path.join(BASE_DIR, "deep_research_output")
    os.makedirs(out_dir, exist_ok=True)
    for path, content in FILES.items():
        full = os.path.join(out_dir, *path.split("/"))
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as f:
            f.write(content)

    print("\n" + "=" * 70)
    print(f"Agent says: {status}   |   files: {', '.join(FILES) or 'none'}")
    print(f"Saved to: {out_dir}")
    print("=" * 70)
    print(FILES.get("report.md", "(no report.md written)")[:2500])
