# =====================================================================
# STEP 3: The Helpdesk MCP server.
#
# The LLM cannot know who the employee is, what laptop they have, or
# whether the VPN is down right now - those are LIVE facts in the helpdesk
# database. An MCP server exposes them as tools that ANY MCP-capable agent
# (LangChain, Claude Desktop, VS Code ...) can discover and call.
#
# Tools:
#   get_employee(employee_id)        who they are, manager, account status
#   get_assets(employee_id)          laptops / phones and purchase dates
#   get_service_status(service)      live status: VPN, Email, Jira ...
#   get_open_tickets(employee_id)    so the agent doesn't raise duplicates
#   create_ticket(...)               the one tool that WRITES
#
# Notice: the docstrings ARE the prompt. The model picks a tool by reading
# its name, description and argument names - write them carefully.
#
# Run it:
#   python 3_mcp_helpdesk_server.py --test   list the tools and call a few
#   python 3_mcp_helpdesk_server.py          stdio server (launched by the agents)
# =====================================================================
import warnings
warnings.filterwarnings("ignore")   # MCP servers must keep stdout/stderr clean

import json
import os
import sqlite3
import sys
from datetime import datetime

from mcp.server.fastmcp import FastMCP

# MCP servers are standalone processes - keep them light and self-contained
HELPDESK_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "helpdesk.db")

mcp = FastMCP("helpdesk", log_level="WARNING")

ASSIGNED_GROUP = {"P1": "IT Security", "P2": "Service Desk L2", "P3": "Service Desk L1", "P4": "Service Desk L1"}


def query(sql: str, params: tuple = ()) -> list[dict]:
    conn = sqlite3.connect(HELPDESK_DB)
    conn.row_factory = sqlite3.Row
    rows = [dict(r) for r in conn.execute(sql, params)]
    conn.close()
    return rows


@mcp.tool()
def get_employee(employee_id: str) -> str:
    """Get an employee's profile: name, email, department, role, employment type
    (Employee or Contractor), manager and account status (active or locked).

    Args:
        employee_id: Employee id such as E1001
    """
    rows = query("SELECT * FROM employees WHERE employee_id = ?", (employee_id,))
    return json.dumps(rows[0] if rows else {"error": f"No employee {employee_id}"})


@mcp.tool()
def get_assets(employee_id: str) -> str:
    """List the laptops and phones assigned to an employee, with model, OS and purchase date.

    Args:
        employee_id: Employee id such as E1001
    """
    return json.dumps(query("SELECT * FROM assets WHERE employee_id = ?", (employee_id,)))


@mcp.tool()
def get_service_status(service: str) -> str:
    """Get the LIVE status of an IT service (operational, degraded or down) and the
    status message. Known services: VPN, Email, Wi-Fi, Printing, GitHub, Jira, Salesforce.
    Use 'all' to list every service.

    Args:
        service: Service name, or 'all'
    """
    if service.lower() == "all":
        return json.dumps(query("SELECT * FROM service_status"))
    rows = query("SELECT * FROM service_status WHERE lower(service) = lower(?)", (service,))
    return json.dumps(rows[0] if rows else {"error": f"Unknown service '{service}'"})


@mcp.tool()
def get_open_tickets(employee_id: str) -> str:
    """List an employee's tickets that are not yet resolved. Check this before
    creating a new ticket, to avoid duplicates.

    Args:
        employee_id: Employee id such as E1001
    """
    return json.dumps(query(
        "SELECT * FROM tickets WHERE employee_id = ? AND status != 'resolved'", (employee_id,)))


@mcp.tool()
def create_ticket(employee_id: str, category: str, priority: str, summary: str) -> str:
    """Create a helpdesk ticket. Only do this when self-help did not or cannot fix
    the problem, or for hardware refresh requests and security incidents.

    Args:
        employee_id: Employee id such as E1001
        category: One of troubleshooting, hardware, security_incident
        priority: P1, P2, P3 or P4 (see SLA-301)
        summary: One line naming the system and the symptom
    """
    if priority not in ASSIGNED_GROUP:
        return json.dumps({"error": "priority must be P1, P2, P3 or P4"})
    group = ASSIGNED_GROUP[priority]
    conn = sqlite3.connect(HELPDESK_DB)
    cur = conn.execute(
        "INSERT INTO tickets (employee_id, category, priority, summary, status, assigned_group, created_at)"
        " VALUES (?, ?, ?, ?, 'open', ?, ?)",
        (employee_id, category, priority, summary, group, datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()
    conn.close()
    return json.dumps({"ticket_id": cur.lastrowid, "priority": priority, "assigned_group": group})


# ---------------------------------------------------------------- self-test
async def self_test():
    """Act as an MCP CLIENT: start this file as a server and call its tools."""
    from langchain_mcp_adapters.client import MultiServerMCPClient
    from common import MCP_SERVERS

    client = MultiServerMCPClient({"helpdesk": MCP_SERVERS["helpdesk"]})
    tools = {t.name: t for t in await client.get_tools()}
    print("Tools discovered over MCP:")
    for t in tools.values():
        print(f"  - {t.name}: {t.description.splitlines()[0]}")
    print("\nget_employee(E1002) ->", await tools["get_employee"].ainvoke({"employee_id": "E1002"}))
    print("\nget_service_status(VPN) ->", await tools["get_service_status"].ainvoke({"service": "VPN"}))


if __name__ == "__main__":
    if "--test" in sys.argv:
        import asyncio
        asyncio.run(self_test())
    else:
        mcp.run()
