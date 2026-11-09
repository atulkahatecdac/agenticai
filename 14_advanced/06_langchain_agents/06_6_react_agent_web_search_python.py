import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

import contextlib
import io
import sys
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, ToolMessage
from langchain_tavily import TavilySearch

load_dotenv(override=True)

# Tool output can contain characters outside Windows' default console
# codepage (cp1252) - reconfigure stdout to UTF-8 so printing doesn't crash.
sys.stdout.reconfigure(encoding="utf-8")

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# -----------------------------
# Tools
# A ReAct agent has no fixed capability of its own beyond reasoning in a
# loop - everything it can actually DO comes from its tools. Two very
# different kinds here on purpose: one reaches out to the real world
# (web search), one computes (running Python).
# -----------------------------
web_search = TavilySearch(max_results=3)

@tool
def run_python(code: str) -> str:
    """Run Python code and return whatever it prints.
    Use print() to show results. Use this for any arithmetic."""
    # DEMO ONLY: exec() runs whatever code the LLM writes, on this machine.
    # A real agent would run it in a sandbox (a container, or a service
    # such as E2B), never in the same process as the app.
    output = io.StringIO()
    try:
        with contextlib.redirect_stdout(output):
            exec(code, {})
    except Exception as e:
        return f"Error: {e!r}"
    return output.getvalue() or "(the code printed nothing - use print())"

tools = [web_search, run_python]
llm_with_tools = llm.bind_tools(tools)
tools_by_name = {t.name: t for t in tools}

# -----------------------------
# ReAct = Reason + Act. The classic version made the LLM write
# "Thought: / Action: / Observation:" text that the framework then parsed.
# With native tool calling the Action is a structured tool call instead,
# so nothing needs parsing - we only ask the LLM to say its Thought out
# loud before acting, so we can watch it reason.
# -----------------------------
SYSTEM_PROMPT = (
    "You solve problems step by step. Before every tool call, write one "
    "short sentence saying what you are thinking and why you need the tool. "
    "Never do arithmetic in your head - use run_python. When you know the "
    "answer, reply without calling a tool."
)

# -----------------------------
# The ReAct loop: Thought -> Action (tool call) -> Observation (tool
# result), repeated until the LLM answers without asking for a tool.
# This is the same loop as 06_3_sql_database_toolkit_agent.py, with the
# three ReAct stages printed so they are easy to follow.
# -----------------------------
def run_react_agent(question: str, max_steps: int = 6, verbose: bool = True) -> str:
    messages: list[BaseMessage] = [SystemMessage(SYSTEM_PROMPT), HumanMessage(question)]

    for step in range(1, max_steps + 1):
        ai_message = llm_with_tools.invoke(messages)
        messages.append(ai_message)

        if not ai_message.tool_calls:
            return ai_message.content

        if verbose and ai_message.content:
            print(f"\n[step {step}] Thought: {ai_message.content}")

        for tool_call in ai_message.tool_calls:
            if verbose:
                print(f"[step {step}] Action: {tool_call['name']}({tool_call['args']})")
            try:
                result = tools_by_name[tool_call["name"]].invoke(tool_call["args"])
            except Exception as e:
                result = f"Tool failed: {e}"
            if verbose:
                print(f"[step {step}] Observation: {str(result)[:300]}")
            messages.append(ToolMessage(content=str(result), tool_call_id=tool_call["id"]))

    return f"Stopped: no final answer after {max_steps} steps."

if __name__ == "__main__":
    # Deliberately needs BOTH tools in sequence: a live fact from search,
    # then arithmetic on that fact that the LLM shouldn't just guess at.
    question = (
        "Search the web for Japan's current population. Then use Python to divide "
        "that number by 47 (Japan's number of prefectures) and tell me the average "
        "population per prefecture, rounded to the nearest whole number."
    )

    answer = run_react_agent(question)

    print("\n" + "=" * 70)
    print("FINAL ANSWER")
    print("=" * 70)
    print(answer)
