# =====================================================================
# STEP 4: The Identity & Access MCP server.
#
# Tools that CHANGE things - account unlocks, password reset links,
# access requests, notifications - live in their own server. Splitting
# servers by responsibility means each agent can be handed only the
# tools it needs (least privilege for agents, not just for people).
#
# Tools:
#   unlock_account(employee_id)
#   send_password_reset_link(employee_id)    never returns a password!
#   check_access(employee_id, system)
#   request_access(employee_id, system, reason)
#   notify(recipient, message)
#   decide_access_request(request_id, approver_id, decision)
#        ^ called by the GRAPH after a human approves - it is never handed
#          to an LLM agent (see 7_helpdesk_graph.py)
#
# Defence in depth: the agent READS POL-201 (RAG) to explain the access
# rules to the employee, but the hard rules are also ENFORCED here, in
# plain code. A confused or manipulated LLM still cannot grant a
# contractor AWS Production.
#
# Run it:
#   python 4_mcp_identity_server.py --test
# =====================================================================
import warnings
warnings.filterwarnings("ignore")   # MCP servers must keep stdout/stderr clean

import json
import os
import sqlite3
import sys
from datetime import date, datetime

from mcp.server.fastmcp import FastMCP

# MCP servers are standalone processes - keep them light and self-contained
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
HELPDESK_DB = os.path.join(DATA_DIR, "helpdesk.db")
NOTIFY_LOG = os.path.join(DATA_DIR, "notifications.log")

mcp = FastMCP("identity", log_level="WARNING")

# The same tiers POL-201 describes in words
TIERS = {
    "standard": ["Slack", "Zoom", "Confluence", "Microsoft 365"],
    "restricted": ["GitHub", "Jira", "Salesforce", "Tableau", "SAP Finance"],
    "highly_restricted": ["AWS Production", "Payroll System", "Customer Database"],
}
DEPARTMENT_ONLY = {
    "SAP Finance": ["Finance", "HR"],
    "Payroll System": ["Finance", "HR"],
    "Salesforce": ["Sales", "Customer Support"],
}


def db():
    conn = sqlite3.connect(HELPDESK_DB)
    conn.row_factory = sqlite3.Row
    return conn


def get_employee(employee_id: str):
    with db() as conn:
        row = conn.execute("SELECT * FROM employees WHERE employee_id = ?", (employee_id,)).fetchone()
    return dict(row) if row else None


def now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


@mcp.tool()
def unlock_account(employee_id: str) -> str:
    """Unlock a locked account. Only for the employee who is asking - never for someone else.

    Args:
        employee_id: Employee id such as E1001
    """
    emp = get_employee(employee_id)
    if not emp:
        return json.dumps({"error": f"No employee {employee_id}"})
    if emp["account_status"] != "locked":
        return json.dumps({"result": "Account is not locked - nothing to do."})
    with db() as conn:
        conn.execute("UPDATE employees SET account_status = 'active' WHERE employee_id = ?", (employee_id,))
    return json.dumps({"result": f"Account {employee_id} unlocked."})


@mcp.tool()
def send_password_reset_link(employee_id: str) -> str:
    """Send a password reset link (valid 15 minutes) to the employee's company email
    and registered mobile. This tool never returns or reveals a password.

    Args:
        employee_id: Employee id such as E1001
    """
    emp = get_employee(employee_id)
    if not emp:
        return json.dumps({"error": f"No employee {employee_id}"})
    log(emp["email"], "Your BrightPath password reset link (valid 15 minutes): https://reset.brightpath.example/...")
    return json.dumps({"result": f"Reset link sent to {emp['email']} and registered mobile. Valid 15 minutes."})


@mcp.tool()
def check_access(employee_id: str, system: str) -> str:
    """Check whether an employee already has access to a system, and list any
    access requests they already raised for it.

    Args:
        employee_id: Employee id such as E1001
        system: System name such as GitHub, Tableau, AWS Production
    """
    with db() as conn:
        granted = conn.execute("SELECT * FROM entitlements WHERE employee_id = ? AND lower(system) = lower(?)",
                               (employee_id, system)).fetchone()
        requests = conn.execute("SELECT * FROM access_requests WHERE employee_id = ? AND lower(system) = lower(?)",
                                (employee_id, system)).fetchall()
    return json.dumps({"has_access": bool(granted), "requests": [dict(r) for r in requests]})


@mcp.tool()
def request_access(employee_id: str, system: str, reason: str) -> str:
    """Request access to a system for the employee who is asking. Standard systems
    are granted at once; restricted ones create a request that waits for approval.
    Policy rules (POL-201) are enforced here and a refusal explains which rule applied.

    Args:
        employee_id: Employee id such as E1001
        system: Exact system name, e.g. Slack, Zoom, GitHub, Jira, Tableau, AWS Production
        reason: The business reason the employee gave
    """
    emp = get_employee(employee_id)
    if not emp:
        return json.dumps({"error": f"No employee {employee_id}"})
    tier = next((t for t, systems in TIERS.items() if system in systems), None)
    if tier is None:
        return json.dumps({"error": f"Unknown system '{system}'. Known: {sum(TIERS.values(), [])}"})
    if not reason.strip():
        return json.dumps({"status": "refused", "rule": "POL-201 rule 1: a business reason is required"})
    if tier == "highly_restricted" and emp["employment_type"] == "Contractor":
        return json.dumps({"status": "refused", "rule": "POL-201 rule 2: contractors may never get highly restricted systems"})
    if system in DEPARTMENT_ONLY and emp["department"] not in DEPARTMENT_ONLY[system]:
        return json.dumps({"status": "refused",
                           "rule": f"POL-201: {system} is only for {', '.join(DEPARTMENT_ONLY[system])}"})

    with db() as conn:
        if tier == "standard":
            conn.execute("INSERT OR IGNORE INTO entitlements VALUES (?, ?, ?)",
                         (employee_id, system, date.today().isoformat()))
            return json.dumps({"status": "granted", "tier": tier, "system": system})

        approvers = f"{emp['manager_id']} (manager)"
        if tier == "highly_restricted":
            approvers += " + IT Security"
        cur = conn.execute(
            "INSERT INTO access_requests (employee_id, system, tier, reason, approvers, status, created_at)"
            " VALUES (?, ?, ?, ?, ?, 'pending', ?)", (employee_id, system, tier, reason, approvers, now()))
    return json.dumps({"status": "pending_approval", "request_id": cur.lastrowid,
                       "tier": tier, "system": system, "approvers": approvers})


@mcp.tool()
def notify(recipient: str, message: str) -> str:
    """Send a notification (simulated: written to data/notifications.log).

    Args:
        recipient: An email address, an employee id, or a team such as 'IT Security'
        message: The message text
    """
    log(recipient, message)
    return json.dumps({"result": f"Notified {recipient}"})


@mcp.tool()
def decide_access_request(request_id: int, approver_id: str, decision: str) -> str:
    """Record a human approver's decision on a pending access request.

    Args:
        request_id: The access request id
        approver_id: Employee id of the person deciding
        decision: approved or rejected
    """
    if decision not in ("approved", "rejected"):
        return json.dumps({"error": "decision must be 'approved' or 'rejected'"})
    with db() as conn:
        req = conn.execute("SELECT * FROM access_requests WHERE request_id = ?", (request_id,)).fetchone()
        if not req or req["status"] != "pending":
            return json.dumps({"error": f"No pending request {request_id}"})
        if approver_id == req["employee_id"]:
            return json.dumps({"error": "POL-201 rule 6: you cannot approve your own request"})
        conn.execute("UPDATE access_requests SET status = ?, decided_by = ? WHERE request_id = ?",
                     (decision, approver_id, request_id))
        if decision == "approved":
            conn.execute("INSERT OR IGNORE INTO entitlements VALUES (?, ?, ?)",
                         (req["employee_id"], req["system"], date.today().isoformat()))
    return json.dumps({"request_id": request_id, "status": decision, "system": req["system"]})


def log(recipient: str, message: str):
    with open(NOTIFY_LOG, "a", encoding="utf-8") as f:
        f.write(f"{now()} | to: {recipient} | {message}\n")


# ---------------------------------------------------------------- self-test
async def self_test():
    from langchain_mcp_adapters.client import MultiServerMCPClient
    from common import MCP_SERVERS

    client = MultiServerMCPClient({"identity": MCP_SERVERS["identity"]})
    tools = {t.name: t for t in await client.get_tools()}
    print("Tools discovered over MCP:", ", ".join(tools))
    for args in [{"employee_id": "E1004", "system": "AWS Production", "reason": "debug a deployment"},
                 {"employee_id": "E1001", "system": "Payroll System", "reason": "curious"}]:
        print(f"\nrequest_access({args}) ->\n  ", await tools["request_access"].ainvoke(args))


if __name__ == "__main__":
    if "--test" in sys.argv:
        import asyncio
        asyncio.run(self_test())
    else:
        mcp.run()
