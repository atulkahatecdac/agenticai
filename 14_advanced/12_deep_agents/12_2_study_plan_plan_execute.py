import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

import logging
import os
import sys
from typing import TypedDict, Union

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel, Field
from pypdf import PdfReader

load_dotenv(override=True)
sys.stdout.reconfigure(encoding="utf-8")
# The PDF has a harmless stray leading newline before its %PDF- header (still
# a valid, fully readable PDF) that pypdf logs a WARNING about on every
# parse; silenced since it's not actionable.
logging.getLogger("pypdf").setLevel(logging.ERROR)

# =====================================================================
# Plan-and-Execute + replanning, following plan_execute_replan.py in
# this same folder exactly: plan_step commits to a full ordered plan
# up front, execute_step works one step at a time, and replan_step
# re-examines the plan after every step against what's been produced
# so far - shortening, extending, or reordering the remaining steps,
# or deciding the task is done. Applied here to a real document: turns
# the 25-module curriculum in
# "Advanced Certification in Agentic AI Engineering.pdf" (one directory
# up) into a 4-week study plan for a working professional.
#
# Unlike plan_execute_replan.py's research task, no external tool is
# needed per step - the "action" for each planned step (e.g. "draft
# week 1", "estimate weekly time budget") is pure reasoning over the
# curriculum text already sitting in state['task'], so execute_step is
# a plain LLM call with no tool binding.
# =====================================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CURRICULUM_PDF = os.path.join(BASE_DIR, "..", "Advanced Certification in Agentic AI Engineering.pdf")

LEARNER_PROFILE = (
    "A working professional with a full-time job. Available study time: roughly "
    "1-1.5 hours on weekday evenings (Mon-Fri) and 2-3 hours on each weekend day "
    "(Sat-Sun) - about 9-13 hours per week total."
)

planner_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
replanner_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
executor_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)


def extract_curriculum(pdf_path: str) -> str:
    """Strip the per-page marketing footer (repeated on every one of the
    PDF's 29 pages) so the LLM sees just the module/topic content, not
    boilerplate it would otherwise have to read past on every call."""
    reader = PdfReader(pdf_path)
    lines = []
    for page in reader.pages:
        for line in (page.extract_text() or "").splitlines():
            if "edureka" in line.lower() or "brain4ce" in line.lower():
                continue
            if line.strip():
                lines.append(line)
    return "\n".join(lines)


class PlanExecuteState(TypedDict):
    task: str
    plan: list[str]
    past_steps: list[tuple[str, str]]
    response: str


class Plan(BaseModel):
    steps: list[str] = Field(
        description="Ordered list of concrete steps still needed to produce the full 4-week study plan. At most 6."
    )


class Response(BaseModel):
    response: str = Field(
        description="The complete, final 4-week (28-day) study plan, ready to hand to the learner."
    )


class Act(BaseModel):
    action: Union[Plan, Response] = Field(
        description="Plan if more steps are still needed, Response once the full 4-week plan is finished."
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
        f"Work done so far: {state['past_steps']}\n\n"
        f"Your ONLY job right now is this single step: {step}"
    )
    print(f"\nEXECUTING: {step}")
    result_text = executor_llm.invoke(prompt).content
    print(f"RESULT: {result_text[:300]}{'...' if len(result_text) > 300 else ''}")
    return {"past_steps": state["past_steps"] + [(step, result_text)]}


def replan_step(state: PlanExecuteState) -> PlanExecuteState:
    prompt = (
        f"Task: {state['task']}\n\n"
        f"Original plan: {state['plan']}\n"
        f"Steps completed so far and their results: {state['past_steps']}\n\n"
        "If a complete 4-week (28-day) study plan has now been fully drafted, return a "
        "Response with the ENTIRE plan written out in full (week-by-week, day-by-day - not a "
        "summary of what was done). Otherwise return an updated Plan with ONLY the remaining "
        "steps still needed - do not repeat steps already done."
    )
    act = replanner_llm.with_structured_output(Act).invoke(prompt)
    if isinstance(act.action, Response):
        print("\nREPLAN: plan is complete, finalizing.")
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
    curriculum = extract_curriculum(CURRICULUM_PDF)
    print(f"Loaded curriculum: {len(curriculum)} characters from {os.path.basename(CURRICULUM_PDF)}")

    task = (
        "Produce a realistic 4-week (28-day) study plan that takes this learner through the "
        "following course curriculum. For each week, give a clear theme and which modules it "
        "covers. For each day, list specific topics to study (not just 'study module 5') - it's "
        "fine to spread one module across several days or cover more than one short module in a "
        "day. Include explicit rest/lighter days, and keep weekly time commitment within the "
        "learner's stated availability.\n\n"
        f"Learner profile: {LEARNER_PROFILE}\n\n"
        f"Course curriculum:\n{curriculum}"
    )

    result = app.invoke({"task": task, "plan": [], "past_steps": [], "response": ""})

    print("\n" + "=" * 70)
    print("FINAL 4-WEEK STUDY PLAN")
    print("=" * 70)
    print(result["response"])

    out_path = os.path.join(BASE_DIR, "study_plan.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(result["response"])
    print(f"\nSaved to: {out_path}")
