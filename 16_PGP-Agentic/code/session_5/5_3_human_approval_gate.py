import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

import sys
from typing import Literal, TypedDict
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command, interrupt

load_dotenv(override=True)

# LLM output can contain characters outside Windows' default console
# codepage (cp1252) - reconfigure stdout to UTF-8 so printing doesn't crash.
sys.stdout.reconfigure(encoding="utf-8")

# =====================================================================
# Human-approval gate via LangGraph's interrupt()/Command(resume=...).
#
# evaluate_expense now makes the call with an LLM instead of a fixed
# amount threshold - it reads the expense description and decides
# approved/rejected/needs_review the way a policy-aware reviewer would.
# Anything the LLM itself flags as needs_review routes to
# human_approval, which calls interrupt(...) - this PAUSES the graph
# and returns control to whoever called .invoke(), along with the exact
# payload passed to interrupt(). The graph's state at that point is
# durably checkpointed (via MemorySaver here; a real app would use a
# database-backed checkpointer), so the process can exit entirely and
# the pending expense will still be there whenever a human resumes it
# with app.invoke(Command(resume=<their decision>), config) -
# re-entering human_approval as if interrupt() had just returned that
# value. This demo asks for that decision via real console input()
# rather than simulating one, so the pause is genuine, not illustrated.
# =====================================================================

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)


class ExpenseState(TypedDict):
    amount: float
    description: str
    status: str
    notes: str


# ---------------------------------------------------------------------
# Node 1: evaluate_expense - an LLM applies company policy instead of a
# hardcoded threshold. Constrained via with_structured_output so the
# conditional edge downstream never has to guard against an unexpected
# decision string coming back.
# ---------------------------------------------------------------------
class ExpenseEvaluation(BaseModel):
    decision: Literal["approved", "rejected", "needs_review"] = Field(
        description="approved/rejected for clear-cut cases, needs_review if genuinely borderline."
    )
    reason: str = Field(description="One-sentence justification for the decision.")


evaluation_prompt = ChatPromptTemplate.from_template("""\
You are an expense-approval assistant applying this company policy:
- Approve routine, reasonably priced business expenses (meals, supplies, \
software, standard equipment).
- Reject expenses that are clearly personal, extravagant, or policy-violating \
(alcohol, gifts, entertainment, anything with no plausible business purpose).
- If it's genuinely ambiguous whether policy allows it, mark needs_review so \
a human decides instead of guessing.

Expense description: {description}
Amount: ${amount:.2f}""")

evaluation_chain = evaluation_prompt | llm.with_structured_output(ExpenseEvaluation)


def evaluate_expense(state: ExpenseState) -> ExpenseState:
    result = evaluation_chain.invoke({"description": state["description"], "amount": state["amount"]})
    print(f"[evaluate_expense] LLM decision: {result.decision} - {result.reason}")
    return {"status": result.decision, "notes": result.reason}


def route_after_evaluation(state: ExpenseState) -> str:
    return "review" if state["status"] == "needs_review" else "done"


# ---------------------------------------------------------------------
# Node 2: human_approval - the interrupt point. Only reached when the
# LLM itself decided the expense needs a human.
# ---------------------------------------------------------------------
def human_approval(state: ExpenseState) -> ExpenseState:
    decision = interrupt({
        "message": "Manual review required for this expense.",
        "description": state["description"],
        "amount": state["amount"],
        "llm_reason": state["notes"],
    })
    return {"status": decision["status"], "notes": decision.get("notes", "")}


# ---------------------------------------------------------------------
# Graph: START -> evaluate_expense --needs_review--> human_approval -> END
#                        \_______________auto-decided_______________/^
# ---------------------------------------------------------------------
graph = StateGraph(ExpenseState)
graph.add_node("evaluate_expense", evaluate_expense)
graph.add_node("human_approval", human_approval)

graph.add_edge(START, "evaluate_expense")
graph.add_conditional_edges(
    "evaluate_expense",
    route_after_evaluation,
    {"review": "human_approval", "done": END},
)
graph.add_edge("human_approval", END)

# A checkpointer is REQUIRED for interrupt()/Command(resume=...) to work -
# it's what lets the graph "remember" where it paused. MemorySaver only
# persists in this process's memory; a real app would use a Postgres/
# SQLite checkpointer so a pending approval survives a restart.
checkpointer = MemorySaver()
app = graph.compile(checkpointer=checkpointer)


def ask_human_for_decision(pending: dict) -> dict:
    print("PAUSED - waiting for human approval:")
    for key, value in pending.items():
        print(f"  {key}: {value}")

    while True:
        raw = input("Approve or reject this expense? [approve/reject]: ").strip().lower()
        if raw in ("approve", "reject", "approved", "rejected"):
            break
        print("Please type 'approve' or 'reject'.")

    notes = input("Notes (optional): ").strip()
    status = "approved" if raw.startswith("approve") else "rejected"
    return {"status": status, "notes": notes}


def run_expense(thread_id: str, amount: float, description: str):
    config = {"configurable": {"thread_id": thread_id}}
    initial: ExpenseState = {"amount": amount, "description": description, "status": "", "notes": ""}

    result = app.invoke(initial, config)

    if "__interrupt__" in result:
        pending = result["__interrupt__"][0].value
        human_response = ask_human_for_decision(pending)
        result = app.invoke(Command(resume=human_response), config)

    return result


if __name__ == "__main__":
    expenses = [
        ("expense-1", 45.00, "Team lunch after a sprint review"),
        ("expense-2", 250.00, "Bottle of whiskey as a client gift"),
        ("expense-3", 650.00, "Ergonomic monitor arm for home office setup"),
    ]

    for thread_id, amount, description in expenses:
        print("=" * 70)
        print(f"Processing {thread_id}: {description} (${amount:,.2f})")
        result = run_expense(thread_id, amount, description)
        print(f"Final status: {result['status'].upper()} - {result['notes']}")
        print()
