# pip install mcp
import warnings
warnings.filterwarnings("ignore")   # MCP servers must keep stdout/stderr clean

import asyncio
import json
import os
import re
import sqlite3
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.server.fastmcp import FastMCP

from capstone_common import ORDERS_DB

# =====================================================================
# STEP 3 of the capstone: the Orders MCP server.
#
# The LLM cannot know a customer's order - so the agent gets that fact
# from a TOOL. This server exposes three small, specific, READ-ONLY tools
# over data/orders.db:
#     get_order(order_id)            one order + the customer's name
#     get_customer_orders(order_id)  the customer's other orders
#     get_past_claims(order_id)      earlier claims on that order
#
# Two deliberate safety choices (the MCP slide's last bullet):
#   - inputs are validated on the SERVER (order ids must look like ORD-1234)
#   - there is no "run any SQL" tool, and the database is opened read-only,
#     so even a confused agent cannot change or dump data
#
# Run it:
#   python 19_3_mcp_orders_server.py --test   start the server as a subprocess,
#                                             list its tools and call each one
#   python 19_3_mcp_orders_server.py          run as a stdio MCP server (this is
#                                             how 19_6_agent_graph.py launches it)
# =====================================================================

mcp = FastMCP("capstone-orders", log_level="WARNING")   # keep stderr quiet during demos
ORDER_ID = re.compile(r"^ORD-\d{4}$")


def _query(sql: str, params: tuple) -> list[dict]:
    # mode=ro: SQLite itself refuses writes on this connection
    conn = sqlite3.connect(f"file:{ORDERS_DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    rows = [dict(r) for r in conn.execute(sql, params)]
    conn.close()
    return rows


def _check(order_id: str) -> str | None:
    if not ORDER_ID.match(order_id or ""):
        return json.dumps({"error": f"Invalid order id '{order_id}'. Expected format ORD-1234."})
    return None


@mcp.tool()
def get_order(order_id: str) -> str:
    """Get one order: product, category, price, delivery date and customer name.

    Args:
        order_id: Order id in the format ORD-1234
    """
    if err := _check(order_id):
        return err
    rows = _query("""SELECT o.order_id, o.product_name, o.category, o.price, o.order_date,
                            o.delivery_date, o.status, c.name AS customer_name
                     FROM orders o JOIN customers c ON c.customer_id = o.customer_id
                     WHERE o.order_id = ?""", (order_id,))
    return json.dumps(rows[0] if rows else {"error": f"Order {order_id} not found."})


@mcp.tool()
def get_customer_orders(order_id: str) -> str:
    """List all orders placed by the customer who placed the given order.

    Args:
        order_id: Any order id of that customer, in the format ORD-1234
    """
    if err := _check(order_id):
        return err
    rows = _query("""SELECT order_id, product_name, category, price, delivery_date FROM orders
                     WHERE customer_id = (SELECT customer_id FROM orders WHERE order_id = ?)
                     ORDER BY delivery_date DESC""", (order_id,))
    return json.dumps(rows)


@mcp.tool()
def get_past_claims(order_id: str) -> str:
    """List earlier warranty claims or returns made on an order.

    Args:
        order_id: Order id in the format ORD-1234
    """
    if err := _check(order_id):
        return err
    rows = _query("SELECT claim_date, claim_type, outcome FROM claims WHERE order_id = ? ORDER BY claim_date",
                  (order_id,))
    return json.dumps(rows)


async def _self_test():
    """Launch this same file as an MCP server and talk to it like the agent does."""
    # env=: stdio servers get a minimal environment by default; pass ours through
    params = StdioServerParameters(command=sys.executable, args=[os.path.abspath(__file__)], env=dict(os.environ))
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print("=" * 70)
            print("ORDERS MCP SERVER - tools discovered by the client")
            print("=" * 70)
            for tool in tools.tools:
                print(f"  {tool.name:<22} {tool.description.splitlines()[0]}")

            calls = [
                ("get_order", {"order_id": "ORD-1001"}, "a normal lookup"),
                ("get_past_claims", {"order_id": "ORD-1013"}, "the repeat claimant"),
                ("get_customer_orders", {"order_id": "ORD-1001"}, "same customer's other orders"),
                ("get_order", {"order_id": "ORD-9999"}, "an order that does not exist"),
                ("get_order", {"order_id": "1; DROP TABLE orders"}, "an injection attempt - rejected by validation"),
            ]
            for name, args, why in calls:
                result = await session.call_tool(name, args)
                print(f"\n{name}({args})   # {why}")
                print(f"  -> {result.content[0].text}")


if __name__ == "__main__":
    if "--test" in sys.argv:
        sys.stdout.reconfigure(encoding="utf-8")
        asyncio.run(_self_test())
    else:
        mcp.run()
