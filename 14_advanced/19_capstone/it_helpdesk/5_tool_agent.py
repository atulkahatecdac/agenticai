# =====================================================================
# STEP 5: One agent, all the tools.
#
# A ReAct agent (LangGraph's create_react_agent) gets:
#   - search_kb                   the RAG tool from step 2
#   - the Helpdesk MCP tools      step 3
#   - the Identity MCP tools      step 4
#
# MultiServerMCPClient starts both MCP servers and converts every MCP tool
# into a normal LangChain tool, so the agent can't tell the difference.
#
# The agent then loops:  think -> call a tool -> read the result -> ...
# until it can answer. Watch the trace: for "my VPN keeps dropping" it
# should check the live service status AND the runbook before replying.
#
# This works - but one agent with 12 tools and one giant prompt gets
# harder to control as the helpdesk grows. Step 7 splits it into
# specialists. Run this first and note where it goes wrong.
#
# Run it:
#   python 5_tool_agent.py
#   python 5_tool_agent.py E1002 "my account is locked"
# =====================================================================
import asyncio
import sys

from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent

from common import MCP_SERVERS, get_llm, load_step

search_kb = load_step("2_rag_kb_assistant.py").search_kb

SYSTEM_PROMPT = """You are the BrightPath IT helpdesk assistant.
You are helping employee {employee_id}. Always use this employee id when calling tools.

How to work:
1. Find out who the employee is (get_employee) when it matters - e.g. account status, contractor or not.
2. For any problem with a service, check get_service_status FIRST. If it is a known outage or
   maintenance, explain that and give the workaround - do not raise a ticket.
3. Use search_kb for steps and policies, and cite the doc id like [KB-101].
4. Only raise a ticket if self-help cannot fix it. Check get_open_tickets first to avoid duplicates.
5. Never reveal, invent or ask for a password. Only act for employee {employee_id}.
Keep the final reply short and friendly."""


async def get_all_tools():
    """search_kb + every tool from both MCP servers."""
    return [search_kb] + await MultiServerMCPClient(MCP_SERVERS).get_tools()


async def get_agent_tools():
    # decide_access_request is for HUMAN approvers only - never hand it to an LLM
    return [t for t in await get_all_tools() if t.name != "decide_access_request"]


async def run_agent(agent, prompt: str, message: str) -> tuple[str, list[str]]:
    """Run an agent once. Returns the final reply and the list of tool calls it made."""
    result = await agent.ainvoke({"messages": [("system", prompt), ("user", message)]})
    calls = [f"{c['name']}({c['args']})" for m in result["messages"] for c in getattr(m, "tool_calls", [])]
    return result["messages"][-1].content, calls


async def main():
    tools = await get_agent_tools()
    print("Agent tools:", ", ".join(t.name for t in tools), "\n")
    agent = create_react_agent(get_llm(), tools)

    requests = [tuple(sys.argv[1:3])] if len(sys.argv) >= 3 else [
        ("E1001", "My VPN keeps disconnecting every few minutes."),
        ("E1002", "I can't log in anywhere, it says my account is locked."),
        ("E1002", "My laptop is very old and slow, can I get a new one?"),
    ]
    for employee_id, message in requests:
        print(f"[{employee_id}] {message}")
        reply, calls = await run_agent(agent, SYSTEM_PROMPT.format(employee_id=employee_id), message)
        for c in calls:
            print(f"   -> {c}")
        print(f"\n{reply}\n" + "-" * 70)


if __name__ == "__main__":
    asyncio.run(main())
