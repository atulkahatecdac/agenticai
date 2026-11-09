import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

import importlib
import json
import os
import sys
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv(override=True)

# Tool output can contain characters outside Windows' default console
# codepage (cp1252) - reconfigure stdout to UTF-8 so printing doesn't crash.
sys.stdout.reconfigure(encoding="utf-8")

# -----------------------------
# Executor: the ReAct agent (web search + Python) from
# 06_6_react_agent_web_search_python.py. Plan-and-Execute doesn't replace
# ReAct - it wraps it. Each planned step below is carried out by a small
# ReAct loop that can call those tools as needed.
# -----------------------------
_react = importlib.import_module("06_6_react_agent_web_search_python")  # file names start with a digit
run_react_agent = _react.run_react_agent

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# =====================================================================
# PLAN-AND-EXECUTE
# ReAct decides what to do ONE step at a time, re-thinking after every
# observation, with no commitment to what comes next. Plan-and-Execute
# instead commits to a full ordered list of steps UP FRONT, then works
# through that list - closer to writing a to-do list before starting,
# rather than deciding the next move only after seeing the last result.
# This trades ReAct's ability to course-correct mid-task for a plan
# that's visible and auditable before any tool ever gets called.
# =====================================================================

# The planner returns a Pydantic object, not free text, so there is no
# JSON to parse by hand and no "the model added markdown fences" to handle.
class Plan(BaseModel):
    steps: list[str] = Field(description="Short, concrete steps, in order")

planner = llm.with_structured_output(Plan)

def make_plan(question: str) -> list[str]:
    prompt = (
        "Break the following question down into a short ordered list of concrete "
        "steps needed to answer it (at most 4). Some steps may need a web search, "
        "some may need a calculation.\n\n"
        f"Question: {question}"
    )
    return planner.invoke([HumanMessage(content=prompt)]).steps

def run_plan_and_execute(question: str) -> str:
    plan = make_plan(question)

    print("=" * 70)
    print("PLAN")
    print("=" * 70)
    for i, step in enumerate(plan, start=1):
        print(f"{i}. {step}")

    findings = []
    for i, step in enumerate(plan, start=1):
        print(f"\n{'=' * 70}")
        print(f"EXECUTING STEP {i}: {step}")
        print("=" * 70)

        step_input = (
            f"Overall question: {question}\n"
            f"Full plan: {plan}\n"
            f"Findings so far: {findings}\n"
            f"Your ONLY job right now is this single step: {step}\n"
            "Do not attempt any other step."
        )
        result = run_react_agent(step_input)
        print(f"\nStep {i} result: {result}")
        findings.append({"step": step, "result": result})

    print(f"\n{'=' * 70}")
    print("SYNTHESIZING FINAL ANSWER FROM ALL FINDINGS")
    print("=" * 70)

    synthesis_prompt = (
        f"Question: {question}\n"
        f"Findings from executing each planned step:\n{json.dumps(findings, indent=2)}\n\n"
        "Using ONLY these findings, give the final answer."
    )
    final = llm.invoke([HumanMessage(content=synthesis_prompt)])
    return final.content

if __name__ == "__main__":
    question = (
        "Find Japan's current total population and its number of prefectures, "
        "calculate the average population per prefecture, and state whether that "
        "average is higher or lower than 2 million."
    )

    answer = run_plan_and_execute(question)

    print("\n" + "=" * 70)
    print("FINAL ANSWER")
    print("=" * 70)
    print(answer)
