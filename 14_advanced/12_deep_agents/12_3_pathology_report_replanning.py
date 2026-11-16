# Plan -> execute -> REPLAN. The planner commits to a full plan up front,
# the executor runs one step at a time with tools, and after every step
# the replanner revisits what's left. Halfway through, a re-check of
# Marker A reverses the original "Borderline" finding, so the remaining
# follow-ups must be dropped - the plan has to actually change.
# All data is synthetic - a demo of replanning, not medical software.

import sys
from typing import Union
from dotenv import load_dotenv
from pydantic import BaseModel
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, ToolMessage
from langchain_openai import ChatOpenAI

load_dotenv(override=True)
sys.stdout.reconfigure(encoding="utf-8")


# ---- Tools (fixed, synthetic data) ----
@tool
def get_pathology_report(patient_id: str) -> str:
    """Get a patient's pathology report."""
    return (f"Report for {patient_id}: Marker A Borderline (12.4; normal <10, high >15), "
            "Marker B Normal (4.1), Marker C Normal (7.8)")


@tool
def recommend_followups(marker_status: str) -> str:
    """Get the recommended follow-up tests for a Marker A status, e.g. 'Borderline'."""
    if marker_status.lower() == "borderline":
        return "Recommended: Marker A Confirmatory Imaging, Marker D Screening, Follow-up Consultation"
    return f"No follow-ups needed for Marker A status '{marker_status}'."


@tool
def run_followup_test(test_name: str) -> str:
    """Run one follow-up test by name and return its result."""
    return f"{test_name}: no abnormal findings."


@tool
def recheck_marker_a(patient_id: str) -> str:
    """Request a corrected re-read of the patient's Marker A result."""
    return (f"CORRECTED for {patient_id}: Marker A is Normal (9.1). The Borderline reading was a "
            "lab sample-handling error. This supersedes the original report.")


tools = {t.name: t for t in [get_pathology_report, recommend_followups, run_followup_test, recheck_marker_a]}
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
executor = llm.bind_tools(list(tools.values()))


class Plan(BaseModel):
    steps: list[str]  # ordered steps still needed (at most 6)


class Done(BaseModel):
    summary: str  # final patient status and outstanding follow-ups


class Replan(BaseModel):
    action: Union[Plan, Done]  # Plan if more work remains, Done when resolved


def plan_step(task: str) -> list[str]:
    steps = llm.with_structured_output(Plan).invoke(f"Break this task into short ordered steps:\n{task}").steps
    print("PLAN:\n" + "\n".join(f"  {i}. {s}" for i, s in enumerate(steps, 1)))
    return steps


def execute_step(task: str, step: str, findings: list[str]) -> str:
    print(f"\nEXECUTING: {step}")
    messages = [HumanMessage(f"Task: {task}\nFindings so far: {findings}\n\n"
                             f"Do ONLY this step: {step}\nUse a tool if needed, then state the result.")]
    reply = executor.invoke(messages)
    while reply.tool_calls:  # a step may need several tool calls
        messages.append(reply)
        for call in reply.tool_calls:
            messages.append(ToolMessage(str(tools[call["name"]].invoke(call["args"])), tool_call_id=call["id"]))
        reply = executor.invoke(messages)
    print(f"RESULT: {reply.content}")
    return f"{step} -> {reply.content}"


def replan_step(task: str, plan: list[str], findings: list[str]) -> Replan:
    return llm.with_structured_output(Replan).invoke(
        f"Task: {task}\nRemaining plan: {plan}\nCompleted steps and results: {findings}\n\n"
        "If the case is resolved, return Done with a summary. Otherwise return a Plan with only the "
        "steps still needed. If a later result CORRECTED an earlier finding, plan from the corrected "
        "information and drop follow-ups that are no longer necessary."
    )


task = ("Review the pathology report for patient PT-2044. If Marker A is borderline, get the "
        "recommended follow-up tests and run them one by one. Partway through, request a corrected "
        "re-read of Marker A; if it changes the finding, reconsider which follow-ups are still needed. "
        "Finish with a summary of the patient's status and any outstanding follow-ups.")

plan, findings = plan_step(task), []
for _ in range(10):  # safety limit
    if not plan:
        break
    findings.append(execute_step(task, plan[0], findings))
    decision = replan_step(task, plan[1:], findings).action
    if isinstance(decision, Done):
        print("\n" + "=" * 70 + f"\nFINAL SUMMARY\n{decision.summary}")
        break
    plan = decision.steps
    print(f"REPLAN: {len(plan)} step(s) remaining: {plan}")
