# pip install mcp
import warnings
warnings.filterwarnings("ignore")   # an MCP stdio server must keep stdout clean

import asyncio
import json
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.server.fastmcp import FastMCP

from common import load_step

# =====================================================================
# STEP 7a: the same tools, behind an MCP SERVER.
#
# Until now the tools were Python functions inside the agent's file. With
# MCP (Model Context Protocol) they live in a separate process that any
# MCP-capable agent can connect to and DISCOVER: no tool code in the agent.
# The insurer's IT team could own this server; the chat team only connects.
#
# Tools (the functions are reused from steps 3, 4 and 5b):
#     get_my_policies()                          SQL
#     search_policy_docs(query)                  RAG
#     get_policy_details(policy_id, request_type) Insurance API
#     submit_claim(...)                          Insurance API - the only WRITE.
#                                                Step 7b leaves it out; step 10
#                                                uses it behind a human approval.
#
# WHOSE data? The server is started FOR one logged-in customer: the client
# passes CUSTOMER_ID as an environment variable when it launches the
# server. No tool takes a customer id, so a prompt cannot change it.
#
# Run it:
#   python 7a_mcp_insurance_server.py --test   launch the server as a subprocess,
#                                              discover its tools and call each read tool
#   (step 7b and step 10 launch it themselves - you never start it by hand)
# =====================================================================

mcp = FastMCP("securelife-insurance", log_level="WARNING")
CUSTOMER_ID = os.environ.get("CUSTOMER_ID", "")

sql = load_step("3_tool_sql.py")
rag = load_step("4_rag_policy_docs.py")
api = load_step("5b_structured_request.py")


@mcp.tool()
def get_my_policies() -> str:
    """List the insurance policies held by the logged-in customer (policy id, type, plan name,
    members covered, purchase date). Does NOT include coverage amount or status."""
    return json.dumps(sql.fetch_customer_policies(CUSTOMER_ID))


@mcp.tool()
def search_policy_docs(query: str) -> str:
    """Search the SecureLife HEALTH policy wording and FAQs: what is covered or excluded, waiting
    periods, limits, claim procedures, renewal, bonuses. Each result starts with its citation,
    e.g. [Health_Policy_Wording clause 3.4]."""
    return rag.format_hits(rag.search_docs(query, policy_type="health"))


@mcp.tool()
def get_policy_details(policy_id: str, request_type: str) -> str:
    """Ask the Insurance API about one of the customer's policies.
    request_type: get_coverage (sum insured, claimed, available, room rent limit, co-payment, no claim
    bonus, status, valid till) | get_status (status, valid till) | get_claims (past claims).
    policy_id: e.g. P12345 - get it from get_my_policies first."""
    return json.dumps(api.policy_details(CUSTOMER_ID, policy_id, request_type))


@mcp.tool()
def submit_claim(policy_id: str, amount: int, reason: str, hospital: str, admission_date: str) -> str:
    """File a health insurance claim for the logged-in customer. This is a WRITE: it creates a claim.
    amount: claimed amount in rupees; reason: illness or injury and treatment;
    hospital: hospital name and city; admission_date: YYYY-MM-DD."""
    return json.dumps(api.file_claim(CUSTOMER_ID, policy_id, amount, reason, hospital, admission_date))


async def run_test() -> None:
    params = StdioServerParameters(command=sys.executable, args=[os.path.abspath(__file__)],
                                   env={**os.environ, "CUSTOMER_ID": "C67890"})  # "log in" as Rahul
    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        tools = (await session.list_tools()).tools
        print(f"Connected to MCP server, logged in as C67890. It offers {len(tools)} tools:")
        for t in tools:
            print(f"  - {t.name}({', '.join(t.inputSchema.get('properties', {}))})")

        async def call(name: str, args: dict) -> None:
            res = await session.call_tool(name, args)
            text = " ".join(res.content[0].text.split())
            print(f"\n{name}({args})\n  -> {text[:300]}{'...' if len(text) > 300 else ''}")

        await call("get_my_policies", {})
        await call("search_policy_docs", {"query": "maternity waiting period"})
        await call("get_policy_details", {"policy_id": "P12345", "request_type": "get_coverage"})
        await call("get_policy_details", {"policy_id": "P99999", "request_type": "get_coverage"})
        print("\n(The last call asked for someone else's policy: the Insurance API refused it.)")


if __name__ == "__main__":
    if "--test" in sys.argv:
        sys.stdout.reconfigure(encoding="utf-8")
        asyncio.run(run_test())
    else:
        mcp.run()          # stdio transport
