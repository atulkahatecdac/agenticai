import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

import os
import sys
import time
from typing import Annotated, TypedDict
from dotenv import load_dotenv

load_dotenv(override=True)

# .env's LANGSMITH_PROJECT is shared with another exercise (a CrewAI
# demo) - use a dedicated project so this script's traces don't mix in.
os.environ["LANGSMITH_PROJECT"] = "agenticai-09-langsmith-demo"

# LLM output can contain characters outside Windows' default console
# codepage (cp1252) - reconfigure stdout to UTF-8 so printing doesn't crash.
sys.stdout.reconfigure(encoding="utf-8")

from langchain_core.messages import HumanMessage
from langchain_core.tracers.context import tracing_v2_enabled
from langchain_openai import ChatOpenAI
from langchain_tavily import TavilySearch
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langsmith import Client

# =====================================================================
# Tracing a LangGraph agent end-to-end: run a standard tool-calling
# agent, then pull the FULL nested trace (every node/LLM/tool span, not
# just "it got traced") back from LangSmith programmatically.
# =====================================================================

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
tools = [TavilySearch(max_results=3)]
llm_with_tools = llm.bind_tools(tools)


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


def call_model(state: AgentState) -> AgentState:
    return {"messages": [llm_with_tools.invoke(state["messages"])]}


def should_continue(state: AgentState) -> str:
    return "tools" if state["messages"][-1].tool_calls else "end"


graph = StateGraph(AgentState)
graph.add_node("agent", call_model)
graph.add_node("tools", ToolNode(tools))
graph.add_edge(START, "agent")
graph.add_conditional_edges("agent", should_continue, {"tools": "tools", "end": END})
graph.add_edge("tools", "agent")
app = graph.compile()

if __name__ == "__main__":
    question = "Search for the current population of Japan and of France, then tell me which is bigger and by how much."

    # 1. Run the agent - LANGSMITH_TRACING (set in .env) traces every
    # node/LLM/tool call automatically. tracing_v2_enabled just lets us
    # grab the resulting run's id/URL afterward.
    with tracing_v2_enabled(project_name=os.environ["LANGSMITH_PROJECT"]) as tracer:
        result = app.invoke({"messages": [HumanMessage(content=question)]})
        print(f"Answer: {result['messages'][-1].content}")
        print(f"View trace: {tracer.get_run_url()}")
        run_id = tracer.latest_run.id
        tracer.wait_for_futures()  # runs upload asynchronously - avoids a 404 below

    # 2. Pull the full trace tree back from LangSmith. dotted_order
    # encodes execution order AND nesting depth (one "." per level), so
    # sorting by it and counting separators reproduces the call tree
    # without manually walking parent_run_id links.
    client = Client()
    run = None
    for _ in range(10):
        run = client.read_run(run_id)
        if run.end_time is not None:
            break
        time.sleep(2)

    print("\nFull trace tree:")
    child_runs = sorted(
        client.list_runs(project_name=os.environ["LANGSMITH_PROJECT"], trace_id=run.trace_id),
        key=lambda r: r.dotted_order,
    )
    for r in child_runs:
        depth = r.dotted_order.count(".") - 1
        latency = (r.end_time - r.start_time).total_seconds() if r.end_time else 0.0
        print(f"{'  ' * depth}- [{r.run_type}] {r.name} ({latency:.2f}s)")
