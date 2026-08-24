import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

import os
import sys
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.redis import RedisSaver

# LLM output can contain characters outside Windows' default console
# codepage (cp1252) - reconfigure stdout to UTF-8 so printing doesn't crash.
sys.stdout.reconfigure(encoding="utf-8")

# =====================================================================
# RedisSaver checkpointer - the production-scale alternative to
# SqliteSaver (see sqlite_checkpointing_crash_recovery.py). A .sqlite
# file is local to one process/disk, so it doesn't work once a
# pipeline is horizontally scaled across multiple app instances -
# Redis is a shared network service, so every instance points at the
# SAME checkpoint store and any of them can resume any thread. It also
# supports a TTL, so stale checkpoints expire on their own instead of
# accumulating forever - a real concern once every transfer is a
# permanent row otherwise.
#
# .setup() creates the RediSearch indices RedisSaver queries against
# AND initializes this connection's local key registry - the index
# creation is idempotent server-side, but every process/connection
# still has to call it, unlike SqliteSaver's from_conn_string, which
# is immediately ready to use.
# =====================================================================

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")
THREAD_ID = "transfer-1"
# Auto-expire a thread's checkpoints an hour after the last read, so a
# high-volume production deployment doesn't retain every transfer forever.
TTL = {"default_ttl": 60, "refresh_on_read": True}


class TransferState(TypedDict):
    amount: float
    completed_steps: list[str]


def debit_account(state: TransferState) -> TransferState:
    print(f"[debit_account] debited ${state['amount']:.2f}")
    return {"completed_steps": state["completed_steps"] + ["debit_account"]}


_credit_attempts = 0


def credit_account(state: TransferState) -> TransferState:
    global _credit_attempts
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
    config = {"configurable": {"thread_id": THREAD_ID}}
    initial: TransferState = {"amount": 250.00, "completed_steps": []}

    print("--- Run 1: crashes partway through the transfer ---")
    with RedisSaver.from_conn_string(REDIS_URL, ttl=TTL) as checkpointer:
        checkpointer.setup()
        checkpointer.delete_thread(THREAD_ID)  # start this demo thread clean
        app = graph.compile(checkpointer=checkpointer)
        try:
            app.invoke(initial, config, durability="sync")
        except RuntimeError as exc:
            print(f"Transfer failed: {exc}")

    print("\n--- Run 2: fresh RedisSaver connection (as another app instance would open), resume ---")
    with RedisSaver.from_conn_string(REDIS_URL, ttl=TTL) as checkpointer:
        checkpointer.setup()
        app = graph.compile(checkpointer=checkpointer)
        result = app.invoke(None, config)
        print(f"Completed steps: {result['completed_steps']}")
