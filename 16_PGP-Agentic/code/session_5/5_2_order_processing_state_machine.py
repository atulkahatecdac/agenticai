import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

import csv
import os
import sys
from typing import TypedDict
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END

load_dotenv(override=True)

# LLM output can contain characters outside Windows' default console
# codepage (cp1252) - reconfigure stdout to UTF-8 so printing doesn't crash.
sys.stdout.reconfigure(encoding="utf-8")

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)

# =====================================================================
# Order-processing state machine with a RETRY state and a FAIL state.
#
# Inventory is a real, one-shot lookup against products.csv - checking
# a static stock number twice can't change the answer, so there's
# nothing to retry there. Payment is the stage that's genuinely
# retryable (a real gateway can fail transiently), so it's the one
# that loops back to itself via a conditional edge up to a max attempt
# count. Either stage routes to the single shared "fail_order" terminal
# state on failure - both patterns are just conditional edges, nothing
# LangGraph special-cases.
# =====================================================================

MAX_PAYMENT_ATTEMPTS = 2

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PRODUCTS_CSV = os.path.join(BASE_DIR, "products.csv")

PRODUCTS = {}
with open(PRODUCTS_CSV, newline="", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        PRODUCTS[row["product_id"]] = {
            "product_name": row["product_name"],
            "stock_quantity": int(row["stock_quantity"]),
            "unit_price": float(row["unit_price"]),
        }

# Simulated payment gateway - scripted per order_id so every run is
# deterministic and reproducible instead of depending on real randomness.
# Each list is read up to its last element, then held there.
PAYMENT_SCRIPT = {
    "ORD-1": ["approved"],
    "ORD-3": ["declined", "approved"],
    "ORD-4": ["declined", "declined"],
}


class OrderState(TypedDict):
    order_id: str
    product_id: str
    quantity: int
    item: str
    payment_attempts: int
    status: str
    failure_reason: str
    customer_message: str


# ---------------------------------------------------------------------
# Node 1: check_inventory - a single real lookup against products.csv,
# no retry (a static number doesn't change between checks).
# ---------------------------------------------------------------------
def check_inventory(state: OrderState) -> OrderState:
    product = PRODUCTS[state["product_id"]]
    in_stock = product["stock_quantity"] >= state["quantity"]
    status = "in_stock" if in_stock else "out_of_stock"
    print(
        f"[check_inventory] {product['product_name']}: need {state['quantity']}, "
        f"have {product['stock_quantity']} -> {status}"
    )
    return {"item": product["product_name"], "status": status}


def route_after_inventory(state: OrderState) -> str:
    return "in_stock" if state["status"] == "in_stock" else "give_up"


# ---------------------------------------------------------------------
# Node 2: process_payment - the RETRY state. Loops back to itself via
# a conditional edge while declined and attempts remain.
# ---------------------------------------------------------------------
def process_payment(state: OrderState) -> OrderState:
    attempt = state["payment_attempts"]
    outcomes = PAYMENT_SCRIPT.get(state["order_id"], ["approved"])
    outcome = outcomes[min(attempt, len(outcomes) - 1)]
    print(f"[process_payment] attempt {attempt + 1}: {outcome}")
    return {"payment_attempts": attempt + 1, "status": outcome}


def route_after_payment(state: OrderState) -> str:
    if state["status"] == "approved":
        return "approved"
    if state["payment_attempts"] >= MAX_PAYMENT_ATTEMPTS:
        return "give_up"
    return "retry"


# ---------------------------------------------------------------------
# Node 3a: ship_order - the SUCCESS terminal state.
# ---------------------------------------------------------------------
def ship_order(state: OrderState) -> OrderState:
    print(f"[ship_order] shipping {state['quantity']}x {state['item']} for {state['order_id']}")
    return {"status": "shipped"}


# ---------------------------------------------------------------------
# Node 3b: fail_order - the single shared FAIL terminal state. Both
# check_inventory and process_payment route here on failure, so
# state["status"] at the moment of arrival tells it which stage gave up.
# ---------------------------------------------------------------------
def fail_order(state: OrderState) -> OrderState:
    if state["status"] == "out_of_stock":
        reason = f"Insufficient inventory for {state['item']} (requested {state['quantity']})."
    else:
        reason = f"Payment declined after {state['payment_attempts']} attempts."
    print(f"[fail_order] {reason}")
    return {"failure_reason": reason}


# ---------------------------------------------------------------------
# Node 4: notify_customer - LLM writes the customer-facing message,
# whichever terminal state the order actually landed in.
# ---------------------------------------------------------------------
def notify_customer(state: OrderState) -> OrderState:
    if state["status"] == "shipped":
        prompt = (
            f"Write a short, friendly order-confirmation message for order {state['order_id']}: "
            f"{state['quantity']}x {state['item']} has shipped."
        )
    else:
        prompt = (
            f"Write a short, apologetic customer message for order {state['order_id']}, "
            f"which failed. Reason: {state['failure_reason']}"
        )
    response = llm.invoke(prompt)
    return {"customer_message": response.content}


# ---------------------------------------------------------------------
# Graph:
#   START -> check_inventory --in_stock--> process_payment --approved--> ship_order -> notify_customer -> END
#                  |                              |  ^retry                              ^
#                  give_up                       give_up                                 |
#                   \_______________________> fail_order _______________________________/
# ---------------------------------------------------------------------
graph = StateGraph(OrderState)
graph.add_node("check_inventory", check_inventory)
graph.add_node("process_payment", process_payment)
graph.add_node("ship_order", ship_order)
graph.add_node("fail_order", fail_order)
graph.add_node("notify_customer", notify_customer)

graph.add_edge(START, "check_inventory")

graph.add_conditional_edges(
    "check_inventory",
    route_after_inventory,
    {"in_stock": "process_payment", "give_up": "fail_order"},
)
graph.add_conditional_edges(
    "process_payment",
    route_after_payment,
    {"approved": "ship_order", "retry": "process_payment", "give_up": "fail_order"},
)

graph.add_edge("ship_order", "notify_customer")
graph.add_edge("fail_order", "notify_customer")
graph.add_edge("notify_customer", END)

app = graph.compile()

if __name__ == "__main__":
    test_orders = [
        ("ORD-1", "P001", 1),  # plenty of stock, payment approved first try -> shipped
        ("ORD-2", "P003", 5),  # only 2 in stock, need 5 -> fails at inventory
        ("ORD-3", "P004", 2),  # in stock, payment declined once then approved -> shipped
        ("ORD-4", "P002", 1),  # in stock, payment declined twice -> exhausts retries, fails
    ]

    for order_id, product_id, quantity in test_orders:
        print("=" * 70)
        print(f"Processing {order_id}: {quantity}x {product_id}")
        initial: OrderState = {
            "order_id": order_id,
            "product_id": product_id,
            "quantity": quantity,
            "item": "",
            "payment_attempts": 0,
            "status": "",
            "failure_reason": "",
            "customer_message": "",
        }
        result = app.invoke(initial)
        print(f"Final status: {result['status']}")
        print(f"Customer message: {result['customer_message']}")
        print()
