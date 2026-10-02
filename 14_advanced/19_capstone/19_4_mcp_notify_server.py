# pip install mcp requests
import warnings
warnings.filterwarnings("ignore")   # MCP servers must keep stdout/stderr clean

import asyncio
import json
import os
import sys
from datetime import datetime

import requests
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.server.fastmcp import FastMCP

from capstone_common import APPROVAL_LOG

load_dotenv(override=True)

# =====================================================================
# STEP 4 of the capstone: the Notify MCP server.
#
# The one ACTION the agent is allowed to take on its own: tell a human
# that a ticket is waiting for approval. It exposes a single tool:
#     send_approval_request(ticket_id, decision, amount, reason)
#
# Every request is appended to data/approval_requests.log. If NTFY_TOPIC
# is set in .env, the same message is also pushed to https://ntfy.sh/<topic>
# so it pops up on the approver's phone (same service the banking chatbot
# demo in 3_langgraph uses). Without NTFY_TOPIC it still works - log only.
# Set CAPSTONE_NO_PUSH=1 to keep it log-only even when NTFY_TOPIC is set
# (19_9_run_test_tickets.py does this so 20 test tickets do not page anyone).
#
# Note what this server does NOT do: it cannot approve anything and it
# cannot move money. It only sends a message.
#
# Run it:
#   python 19_4_mcp_notify_server.py --test   call the tool once and show the log
#   python 19_4_mcp_notify_server.py          run as a stdio MCP server
# =====================================================================

mcp = FastMCP("capstone-notify", log_level="WARNING")   # keep stderr quiet during demos


@mcp.tool()
def send_approval_request(ticket_id: str, decision: str, amount: float, reason: str) -> str:
    """Ask a human support approver to approve or reject a proposed decision.

    Args:
        ticket_id: The ticket waiting for approval
        decision: The proposed decision (refund, replacement, repair or reject)
        amount: Refund amount in rupees (0 if no refund)
        reason: One line explaining why approval is needed
    """
    message = f"Ticket {ticket_id}: approve '{decision}'" + (f" of Rs. {amount:,.0f}" if amount else "") + f"? {reason}"
    with open(APPROVAL_LOG, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat(timespec='seconds')} | {message}\n")

    pushed = False
    topic = os.getenv("NTFY_TOPIC")
    if topic and not os.getenv("CAPSTONE_NO_PUSH"):     # test runs set CAPSTONE_NO_PUSH=1
        try:
            requests.post(f"https://ntfy.sh/{topic}", data=message.encode("utf-8"),
                          headers={"Title": "Approval needed"}, timeout=5)
            pushed = True
        except requests.RequestException:
            pass    # the log entry above is the source of truth; a failed push must not fail the ticket
    return json.dumps({"sent": True, "logged": True, "pushed_to_phone": pushed, "message": message})


async def _self_test():
    # env=: stdio servers get a minimal environment by default; pass ours through
    params = StdioServerParameters(command=sys.executable, args=[os.path.abspath(__file__)], env=dict(os.environ))
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print("=" * 70)
            print("NOTIFY MCP SERVER - tools discovered by the client")
            print("=" * 70)
            for tool in tools.tools:
                print(f"  {tool.name:<24} {tool.description.splitlines()[0]}")
            args = {"ticket_id": "DEMO-1", "decision": "refund", "amount": 65000,
                    "reason": "Refund is above the Rs. 5,000 approval limit."}
            result = await session.call_tool("send_approval_request", args)
            print(f"\nsend_approval_request({args})")
            print(f"  -> {result.content[0].text}")
    print(f"\nLast line of {APPROVAL_LOG}:")
    with open(APPROVAL_LOG, encoding="utf-8") as f:
        print("  " + f.readlines()[-1].strip())


if __name__ == "__main__":
    if "--test" in sys.argv:
        sys.stdout.reconfigure(encoding="utf-8")
        asyncio.run(_self_test())
    else:
        mcp.run()
