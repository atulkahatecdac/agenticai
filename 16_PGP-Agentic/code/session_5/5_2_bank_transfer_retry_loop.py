from typing import TypedDict, List, cast
from pydantic import BaseModel
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI

from dotenv import load_dotenv
load_dotenv(override=True)

# =====================================================================
# A banking assistant turns a customer's chat message into a fund
# transfer - a retry loop you will find in almost every production agent:
#
#   extract_transfer  : the LLM reads the message and returns structured JSON
#   validate_transfer : plain code checks it against the saved payees
#   invalid?          : send the exact errors back to the LLM and retry
#   still invalid after MAX_ATTEMPTS : hand the request to a human
#
# The loop is just a conditional edge that points back at extract_transfer.
# =====================================================================

MAX_ATTEMPTS = 3

# The customer's saved payees (beneficiaries). The first attempt goes
# without this list; the validator's error message shows the valid payee
# IDs when the LLM gets one wrong.
PAYEES = {
    "PAY-RAHUL":    "Rahul Sharma (brother), HDFC ****4521",
    "PAY-LANDLORD": "Mr. Kulkarni (landlord), SBI ****7788",
    "PAY-ELEC":     "MSEDCL electricity bill",
    "PAY-SIP":      "Mutual fund SIP",
}


class Transfer(BaseModel):
    payee_id: str
    amount: float
    purpose: str


llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
extractor = llm.with_structured_output(Transfer)


class TransferState(TypedDict):
    message: str
    transfer: dict
    errors: List[str]
    attempts: int
    status: str


def extract_transfer(state: TransferState) -> dict:
    prompt = f"Extract the fund transfer (payee ID, amount in rupees, purpose) from this customer message:\n\n{state['message']}"
    if state["errors"]:
        prompt += (
            f"\n\nYour previous answer was {state['transfer']}, but it was rejected:\n- "
            + "\n- ".join(state["errors"])
            + "\nFix these problems. If the payee is not in the list, keep the name the customer used."
        )

    transfer = cast(Transfer, extractor.invoke(prompt))
    print(f"  [extract_transfer] attempt {state['attempts'] + 1}: {transfer.model_dump()}")
    return {"transfer": transfer.model_dump(), "attempts": state["attempts"] + 1}


def validate_transfer(state: TransferState) -> dict:
    errors = []
    transfer = state["transfer"]
    if transfer["payee_id"] not in PAYEES:
        valid = ", ".join(f"{pid} ({name})" for pid, name in PAYEES.items())
        errors.append(f"Unknown payee '{transfer['payee_id']}'. Saved payees: {valid}.")
    if transfer["amount"] <= 0:
        errors.append("Amount must be greater than zero.")

    print(f"  [validate_transfer] {'OK' if not errors else errors}")
    return {"errors": errors}


def route_after_validation(state: TransferState) -> str:
    if not state["errors"]:
        return "valid"
    if state["attempts"] >= MAX_ATTEMPTS:
        return "give_up"
    return "retry"


def make_transfer(state: TransferState) -> dict:
    t = state["transfer"]
    print(f"  [make_transfer] Rs {t['amount']:,.2f} to {PAYEES[t['payee_id']]} ({t['purpose']})")
    return {"status": "transferred"}


def human_review(state: TransferState) -> dict:
    print(f"  [human_review] could not set up this transfer after {state['attempts']} attempts")
    return {"status": "needs_human"}


# START -> extract_transfer -> validate_transfer --valid--> make_transfer -> END
#              ^                     |
#              +-------retry---------+--give_up--> human_review -> END
graph = StateGraph(TransferState)
graph.add_node("extract_transfer", extract_transfer)
graph.add_node("validate_transfer", validate_transfer)
graph.add_node("make_transfer", make_transfer)
graph.add_node("human_review", human_review)

graph.add_edge(START, "extract_transfer")
graph.add_edge("extract_transfer", "validate_transfer")
graph.add_conditional_edges(
    "validate_transfer",      # source node
    route_after_validation,   # routing function
    {
        "valid":   "make_transfer",
        "retry":   "extract_transfer",   # loop
        "give_up": "human_review",
    },
)
graph.add_edge("make_transfer", END)
graph.add_edge("human_review", END)

app = graph.compile()

if __name__ == "__main__":
    messages = [
        "Send 5000 to my brother Rahul for his college books.",
        "Please pay this month's rent of 18,000 to my landlord.",
        "Transfer 2000 to Anita for the dinner last night.",   # not a saved payee
    ]

    for message in messages:
        print(f"CUSTOMER: {message}")
        result = app.invoke({"message": message, "transfer": {}, "errors": [], "attempts": 0, "status": ""})
        print(f"  Final status: {result['status']}\n")
