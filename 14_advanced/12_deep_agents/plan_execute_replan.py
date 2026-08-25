import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

import sys
from typing import TypedDict, Union
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langchain_tavily import TavilySearch
from langgraph.graph import StateGraph, START, END

load_dotenv(override=True)
sys.stdout.reconfigure(encoding="utf-8")

# =====================================================================
# Plan-and-Execute + replanning: plan_step commits to a full ordered
# plan up front (unlike ReAct's one-step-at-a-time thinking), but
# UNLIKE a fixed plan, replan_step re-examines that plan after every
# single step against what was actually found - it can shorten, extend,
# or reorder the remaining steps, or decide enough is known and end.
# Real web search on every step via Tavily - no mocked findings.
# =====================================================================

planner_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
replanner_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
search_tool = TavilySearch(max_results=3)
executor_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0).bind_tools([search_tool])


class PlanExecuteState(TypedDict):
    task: str
    plan: list[str]
    past_steps: list[tuple[str, str]]
    response: str


class Plan(BaseModel):
    steps: list[str] = Field(description="Ordered list of concrete research/calculation steps still needed. At most 5.")


class Response(BaseModel):
    response: str = Field(description="Final answer to the task, once enough information has been gathered.")


class Act(BaseModel):
    action: Union[Plan, Response] = Field(
        description="Plan if more steps are still needed, Response if the task is now fully answered."
    )


def plan_step(state: PlanExecuteState) -> PlanExecuteState:
    plan = planner_llm.with_structured_output(Plan).invoke(
        f"Break this task into a short ordered list of concrete steps:\n\n{state['task']}"
    )
    print("PLAN:")
    for i, step in enumerate(plan.steps, 1):
        print(f"  {i}. {step}")
    return {"plan": plan.steps}


def execute_step(state: PlanExecuteState) -> PlanExecuteState:
    step = state["plan"][0]
    prompt = (
        f"Overall task: {state['task']}\n"
        f"Findings so far: {state['past_steps']}\n\n"
        f"Your ONLY job right now is this single step: {step}"
    )
    print(f"\nEXECUTING: {step}")
    ai_message = executor_llm.invoke(prompt)
    if ai_message.tool_calls:
        call = ai_message.tool_calls[0]
        tool_result = search_tool.invoke(call["args"])
        follow_up = executor_llm.invoke([
            HumanMessage(prompt), ai_message, ToolMessage(content=str(tool_result), tool_call_id=call["id"]),
        ])
        result_text = follow_up.content
    else:
        result_text = ai_message.content
    print(f"RESULT: {result_text}")
    return {"past_steps": state["past_steps"] + [(step, result_text)]}


def replan_step(state: PlanExecuteState) -> PlanExecuteState:
    prompt = (
        f"Task: {state['task']}\n\n"
        f"Original plan: {state['plan']}\n"
        f"Steps completed so far and their results: {state['past_steps']}\n\n"
        "If the task is now fully answered, return a Response. Otherwise return an updated "
        "Plan with ONLY the remaining steps still needed - do not repeat steps already done."
    )
    act = replanner_llm.with_structured_output(Act).invoke(prompt)
    if isinstance(act.action, Response):
        print(f"\nREPLAN: enough information gathered, finalizing answer.")
        return {"response": act.action.response}
    print(f"\nREPLAN: {len(act.action.steps)} step(s) remaining")
    return {"plan": act.action.steps}


def should_end(state: PlanExecuteState) -> str:
    return "done" if state.get("response") else "continue"


graph = StateGraph(PlanExecuteState)
graph.add_node("plan_step", plan_step)
graph.add_node("execute_step", execute_step)
graph.add_node("replan_step", replan_step)
graph.add_edge(START, "plan_step")
graph.add_edge("plan_step", "execute_step")
graph.add_edge("execute_step", "replan_step")
graph.add_conditional_edges("replan_step", should_end, {"continue": "execute_step", "done": END})

app = graph.compile()

if __name__ == "__main__":
    task = (
        "Find who won the most recent Formula 1 World Drivers' Championship, then find how many "
        "races they won that season, and state whether that's more or less than half the season's races."
    )
    result = app.invoke({"task": task, "plan": [], "past_steps": [], "response": ""})

    print("\n" + "=" * 70)
    print("FINAL ANSWER")
    print("=" * 70)
    print(result["response"])
