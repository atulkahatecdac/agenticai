import json
import os
# from mcp.server import MCPServer
from mcp.server import FastMCP

# server = MCPServer("shopassist")
server = FastMCP("shopassist")

ORDERS = {
    "ORD-12345678": {
        "item": "jacket",
        "status": "delivered",
        "delivered_days_ago": 20,
    },
    "ORD-87654321": {
        "item": "lamp",
        "status": "delivered",
        "delivered_days_ago": 45,
    },
}


# The trace file sits next to this script, wherever the server is started from.
TRACE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".trace")


def log(tool, order_id):
    os.makedirs(TRACE_DIR, exist_ok=True)
    with open(os.path.join(TRACE_DIR, "trace.jsonl"), "a") as f:
        f.write(json.dumps({"event": "tool", "tool": tool,
                            "order_id": order_id}) + "\n")


@server.tool()
def lookup_order(order_id: str) -> dict:
    """Look up an order by its ID. Returns the item, the status
    and how many days ago it was delivered."""
    log("lookup_order", order_id)
    order = ORDERS.get(order_id)
    if order is None:
        return {"found": False, "message": "No order with this ID."}
    return {"found": True, "order": order}


@server.tool()
def start_return(order_id: str) -> dict:
    """Start a return for a delivered order inside the 30-day
    window. Returns the return label number."""
    log("start_return", order_id)
    order = ORDERS.get(order_id)
    if order is None:
        return {
            "isError": True,
            "errorCategory": "validation",
            "isRetryable": False,
            "customerMessage": "We couldn't find an order with this ID.",
            "developerMessage": f"unknown order_id={order_id}",
        }
    if order["delivered_days_ago"] > 30:
        return {
            "isError": True,
            "errorCategory": "business",
            "isRetryable": False,
            "customerMessage": "This order is past the 30-day "
                               "return window.",
            "developerMessage": "delivered_days_ago="
                                f"{order['delivered_days_ago']} > 30",
        }
    return {"return_label": "RET-2048", "order_id": order_id}


if __name__ == "__main__":
    server.run(transport="stdio")