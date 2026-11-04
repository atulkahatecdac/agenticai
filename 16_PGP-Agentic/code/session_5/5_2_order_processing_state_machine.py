from typing import TypedDict
from langgraph.graph import StateGraph, START, END

# =====================================================================
# A retry loop in LangGraph: an order's payment is retried until it is
# approved or we run out of attempts. The loop is just a conditional
# edge that points back at the same node. No LLM, no API key needed.
# =====================================================================

MAX_PAYMENT_ATTEMPTS = 3

# Simulated payment gateway: the scripted outcome of each attempt, per
# order, so every run is the same.
PAYMENT_SCRIPT = {
    "ORD-1": ["approved"],
    "ORD-2": ["declined", "approved"],
    "ORD-3": ["declined", "declined", "declined"],
}


class OrderState(TypedDict):
    order_id: str
    payment_attempts: int
    status: str


def process_payment(state: OrderState) -> dict:
    attempt = state["payment_attempts"]
    outcome = PAYMENT_SCRIPT[state["order_id"]][attempt]
    print(f"  [process_payment] attempt {attempt + 1}: {outcome}")
    return {"payment_attempts": attempt + 1, "status": outcome}


def route_after_payment(state: OrderState) -> str:
    if state["status"] == "approved":
        return "approved"
    if state["payment_attempts"] >= MAX_PAYMENT_ATTEMPTS:
        return "give_up"
    return "retry"


def ship_order(state: OrderState) -> dict:
    print(f"  [ship_order] shipping {state['order_id']}")
    return {"status": "shipped"}


def fail_order(state: OrderState) -> dict:
    print(f"  [fail_order] payment declined {state['payment_attempts']} times")
    return {"status": "failed"}


# START -> process_payment --approved--> ship_order -> END
#            |  ^ retry
#            give_up --> fail_order -> END
graph = StateGraph(OrderState)
graph.add_node("process_payment", process_payment)
graph.add_node("ship_order", ship_order)
graph.add_node("fail_order", fail_order)

graph.add_edge(START, "process_payment")
graph.add_conditional_edges(
    "process_payment",        # source node
    route_after_payment,      # routing function
    {
        "approved": "ship_order",
        "retry":    "process_payment",   # loop
        "give_up":  "fail_order",
    },
)
graph.add_edge("ship_order", END)
graph.add_edge("fail_order", END)

app = graph.compile()

if __name__ == "__main__":
    for order_id in PAYMENT_SCRIPT:
        print(f"Processing {order_id}")
        result = app.invoke({"order_id": order_id, "payment_attempts": 0, "status": ""})
        print(f"  Final status: {result['status']}\n")
