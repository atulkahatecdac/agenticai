import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

import os
import sys
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver

# LLM output can contain characters outside Windows' default console
# codepage (cp1252) - reconfigure stdout to UTF-8 so printing doesn't crash.
sys.stdout.reconfigure(encoding="utf-8")

# =====================================================================
# SqliteSaver checkpointer: unlike MemorySaver (sibling files here),
# checkpoints are written to a .sqlite file, so they survive the
# process ending. credit_account fails on its first attempt below to
# simulate a crash after the debit but before the credit; a fresh
# SqliteSaver connection then resumes with app.invoke(None, config),
# which continues from the last completed step instead of restarting
# (and re-debiting the account).
# =====================================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "bank_transfer_checkpoints.sqlite")
THREAD_ID = "transfer-1"


class TransferState(TypedDict):
    amount: float
    completed_steps: list[str]


def debit_account(state: TransferState) -> TransferState:
    print(f"[debit_account] debited ${state['amount']:.2f}")
    return {"completed_steps": state["completed_steps"] + ["debit_account"]}


_credit_attempts = 0


def credit_account(state: TransferState) -> TransferState:
    global _credit_attempts # Use the _credit_attempts variable that was created outside this function
    _credit_attempts += 1
    if _credit_attempts == 1:
        raise RuntimeError("simulated crash during credit_account")
    print(f"[credit_account] credited ${state['amount']:.2f}")
    return {"completed_steps": state["completed_steps"] + ["credit_account"]}


graph = StateGraph(TransferState)
graph.add_node("debit_account", debit_account)
graph.add_node("credit_account", credit_account)
graph.add_edge(START, "debit_account")
graph.add_edge("debit_account", "credit_account")
graph.add_edge("credit_account", END)


if __name__ == "__main__":
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    config = {"configurable": {"thread_id": THREAD_ID}}
    initial: TransferState = {"amount": 250.00, "completed_steps": []}

    print("--- Run 1: crashes partway through the transfer ---")
    with SqliteSaver.from_conn_string(DB_PATH) as checkpointer:
        app = graph.compile(checkpointer=checkpointer)
        try:
            app.invoke(initial, config, durability="sync")
        except RuntimeError as exc:
            print(f"Transfer failed: {exc}")

    print("\n--- Run 2: fresh SqliteSaver connection, resume from disk ---")
    with SqliteSaver.from_conn_string(DB_PATH) as checkpointer:
        app = graph.compile(checkpointer=checkpointer)
        result = app.invoke(None, config)
        print(f"Completed steps: {result['completed_steps']}")
