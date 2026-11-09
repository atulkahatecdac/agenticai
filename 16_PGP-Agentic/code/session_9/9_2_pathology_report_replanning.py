import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

import sys
from typing import TypedDict, Union

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel, Field

load_dotenv(override=True)
sys.stdout.reconfigure(encoding="utf-8")

# =====================================================================
# Replanning, isolated as its own concept - distinct from Planning
# (plain plan-and-execute) and Reflection (9_1_meal_plan_reflection.py)
# in this folder. Same plan_step -> execute_step -> replan_step shape,
# but the scenario is specifically engineered so replan_step has real
# work to do: a corrected re-read of the patient's original marker
# (recheck_marker_a, scripted to ALWAYS reverse the finding) arrives
# partway through executing a plan that was built on the original,
# since-superseded result - forcing the plan to actually change rather
# than just being confirmed step by step, the way the deleted
# plan_execute_replan.py's F1 task never really did.
#
# All patient data, marker names, and test results below are entirely
# synthetic/fictional (recommend_followups is a fixed lookup table, not
# the LLM inventing clinical judgment) - this demonstrates REPLANNING
# MECHANICS, not real diagnostic or treatment logic. Not medical
# software; nothing here should inform an actual health decision.
# =====================================================================

PATIENT_ID = "PT-2044"

FOLLOWUP_TESTS = {
    "Borderline": ["Marker A Confirmatory Imaging", "Marker D Screening", "Follow-up Consultation"],
}

FOLLOWUP_RESULTS = {
    "Marker A Confirmatory Imaging": "No abnormal findings on imaging; consistent with a normal result.",
    "Marker D Screening": "Marker D: Normal (3.2 - reference range < 5).",
    "Follow-up Consultation": "Consultation completed; no acute concerns noted pending final marker status.",
}


@tool
def get_pathology_report(patient_id: str) -> str:
    """Retrieve a patient's pathology report, including all marker results."""
    return (
        f"Pathology report for patient {patient_id}:\n"
        "- Marker A: Borderline (12.4; reference: Normal <10, Borderline 10-15, High >15)\n"
        "- Marker B: Normal (4.1; reference: <6)\n"
        "- Marker C: Normal (7.8; reference: <9)"
    )


@tool
def recommend_followups(marker_status: str) -> str:
    """Look up the standard recommended follow-up tests for a given Marker A status
    (e.g. 'Borderline')."""
    tests = FOLLOWUP_TESTS.get(marker_status)
    if not tests:
        return f"No follow-up tests are recommended for Marker A status '{marker_status}'."
    return f"Recommended follow-ups for Marker A status '{marker_status}': " + ", ".join(tests)


@tool
def run_followup_test(test_name: str) -> str:
    """Run one specific follow-up test by its exact name (as returned by
    recommend_followups) and get its result."""
    result = FOLLOWUP_RESULTS.get(test_name)
    if result is None:
        return f"No result available for test '{test_name}' - check the exact test name and retry."
    return f"{test_name}: {result}"


@tool
def recheck_marker_a(patient_id: str) -> str:
    """Request a corrected/confirmatory re-read of the patient's original Marker A result,
    e.g. to rule out a lab error before finalizing follow-up actions."""
    return (
        f"CORRECTED RESULT for patient {patient_id}: Marker A re-read as Normal (9.1; reference "
        "<10). The original 'Borderline' reading (12.4) was caused by a sample handling error at "
        "the lab. This corrected result supersedes the original report."
    )


tools = [get_pathology_report, recommend_followups, run_followup_test, recheck_marker_a]

planner_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
replanner_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
executor_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0).bind_tools(tools)
TOOLS_BY_NAME = {t.name: t for t in tools}


class PlanExecuteState(TypedDict):
    task: str
    plan: list[str]
    past_steps: list[tuple[str, str]]
    response: str


class Plan(BaseModel):
    steps: list[str] = Field(description="Ordered list of concrete steps still needed. At most 6.")


class Response(BaseModel):
    response: str = Field(description="Final summary of the patient's status and any outstanding follow-ups.")


class Act(BaseModel):
    action: Union[Plan, Response] = Field(
        description="Plan if more steps are still needed, Response once the case is fully resolved."
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
        f"Your ONLY job right now is this single step: {step}\n\n"
        "If this step needs a tool call, make it. If it doesn't (e.g. it's a check/decision step "
        "that can be answered from the findings above), answer directly with your conclusion - "
        "never return an empty response either way."
    )
    print(f"\nEXECUTING: {step}")
    messages: list = [HumanMessage(prompt)]
    ai_message = executor_llm.invoke(messages)
    messages.append(ai_message)
    # Follow every tool call the executor makes for this step, not just one -
    # a step can legitimately need more than one tool call (e.g. running two
    # follow-up tests back to back).
    max_tool_rounds = 3
    for _ in range(max_tool_rounds):
        if not ai_message.tool_calls:
            break
        for call in ai_message.tool_calls:
            tool_result = TOOLS_BY_NAME[call["name"]].invoke(call["args"])
            messages.append(ToolMessage(content=str(tool_result), tool_call_id=call["id"]))
        ai_message = executor_llm.invoke(messages)
        messages.append(ai_message)
    result_text = ai_message.content or "(no result found for this step)"
    print(f"RESULT: {result_text}")
    return {"past_steps": state["past_steps"] + [(step, result_text)]}


def replan_step(state: PlanExecuteState) -> PlanExecuteState:
    prompt = (
        f"Task: {state['task']}\n\n"
        f"Original plan: {state['plan']}\n"
        f"Steps completed so far and their results: {state['past_steps']}\n\n"
        "If the case is now fully resolved, return a Response with a final summary. Otherwise "
        "return an updated Plan with ONLY the remaining steps still needed. Pay close attention "
        "to whether any earlier finding has since been corrected or reversed by a later step - if "
        "so, the remaining plan should reflect the CORRECTED information, not the original "
        "assumption, and any already-planned follow-up that's no longer necessary should be "
        "dropped rather than executed anyway."
    )
    act = replanner_llm.with_structured_output(Act).invoke(prompt)
    if isinstance(act.action, Response):
        print("\nREPLAN: case resolved, finalizing.")
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
    print("(All data below is synthetic/fictional - a mechanics demo, not medical software.)\n")

    task = (
        f"Review the pathology report for patient {PATIENT_ID}. If Marker A is borderline, get "
        "the recommended follow-up tests and run them one by one. Partway through, also request "
        "a corrected re-read of Marker A - if it changes the original finding, reconsider which "
        "already-planned follow-ups are still actually needed given the corrected result, and "
        "state a final summary of the patient's status and any follow-ups still outstanding."
    )
    result = app.invoke({"task": task, "plan": [], "past_steps": [], "response": ""})

    print("\n" + "=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)
    print(result["response"])
