# pip install openai-agents
import asyncio
import json
import sqlite3
import sys

from agents import Agent, RunContextWrapper, Runner, function_tool

from common import CUSTOMER_DB, MODEL, CustomerSession, print_trace

sys.stdout.reconfigure(encoding="utf-8")

# =====================================================================
# STEP 3: the first TOOL - the "SQL Database" box in the diagram.
#
# A tool is just a Python function the LLM may ask us to run. The loop is:
#     LLM -> "please call get_my_policies()"   (a tool call, as JSON)
#     we  -> run the function, send back the result
#     LLM -> answers using that result
# The trace printed below shows each of those steps.
#
# Two safety choices, already at step 3:
#   1. WHOSE data: the tool takes NO customer_id argument. It reads the
#      logged-in customer from the run context (CustomerSession), so the
#      LLM cannot be talked into reading someone else's policies.
#   2. WHAT SQL: one fixed, parameterised, read-only query - there is no
#      "run any SQL" tool.
#
# Run it:
#   python 3_tool_sql.py
#   python 3_tool_sql.py "your own question"
# =====================================================================


def fetch_customer_policies(customer_id: str) -> dict:
    """Plain function: also used by the MCP server in step 7."""
    conn = sqlite3.connect(f"file:{CUSTOMER_DB}?mode=ro", uri=True)   # read-only connection
    conn.row_factory = sqlite3.Row
    customer = conn.execute("SELECT customer_id, name, city FROM customers WHERE customer_id = ?",
                            (customer_id,)).fetchone()
    policies = [dict(r) for r in conn.execute(
        "SELECT policy_id, policy_type, plan_name, members_covered, purchased_on "
        "FROM policies WHERE customer_id = ? ORDER BY purchased_on DESC", (customer_id,))]
    conn.close()
    if customer is None:
        return {"error": f"No customer {customer_id}"}
    return {"customer": dict(customer), "policies": policies}


@function_tool
def get_my_policies(ctx: RunContextWrapper[CustomerSession]) -> str:
    """List the insurance policies held by the logged-in customer (policy id, type, plan name,
    members covered, purchase date). Does NOT include coverage amount or status - use the
    Insurance API tool for those."""
    return json.dumps(fetch_customer_policies(ctx.context.customer_id))


def instructions(ctx: RunContextWrapper[CustomerSession], agent) -> str:
    return (f"You are the SecureLife health insurance assistant. You are talking to "
            f"{ctx.context.customer_name}. Use your tools to look up facts; never guess policy details. "
            f"If a tool cannot give you the answer, say so.")


agent = Agent[CustomerSession](
    name="Insurance Assistant (SQL tool)",
    model=MODEL,
    instructions=instructions,
    tools=[get_my_policies],
)


async def main() -> None:
    session = CustomerSession()       # the demo login: C67890 Rahul Mehta
    questions = [" ".join(sys.argv[1:])] if len(sys.argv) > 1 else [
        "Which policies do I have with you?",
        "What is the coverage amount in my health insurance policy?",
    ]
    for q in questions:
        print(f"CUSTOMER: {q}")
        result = await Runner.run(agent, q, context=session)
        print_trace(result)
        print()
    print("-> The policy list is now real. But the coverage AMOUNT is not in this database:")
    print("   it lives in the Insurance API (step 5). And policy rules live in documents (step 4).")


if __name__ == "__main__":
    asyncio.run(main())
