# pip install openai-agents
import asyncio
import os
import sys

from agents import Agent, Runner
from agents.mcp import MCPServerStdio, create_static_tool_filter

from common import BASE_DIR, MODEL, CustomerSession, load_step, print_trace

sys.stdout.reconfigure(encoding="utf-8")

# =====================================================================
# STEP 7b: the step 6 agent, now as an MCP CLIENT.
#
# Compare with step 6: the agent has NO tools=[...] list. It gets
# mcp_servers=[...] instead, and the Agents SDK asks the server which
# tools it has (list_tools) and forwards every tool call to it.
# Same instructions, same questions, same answers - that is the point:
# the tools moved out of the agent without the agent changing.
#
# The server is launched once per customer session with CUSTOMER_ID in
# its environment (see 7a). The read-only tool_filter hides submit_claim
# until step 10, where it sits behind a human approval.
#
# Run it (start the API first:  python 5a_insurance_api.py):
#   python 7b_mcp_agent.py
#   python 7b_mcp_agent.py "your question"
# =====================================================================

READ_TOOLS = ["get_my_policies", "search_policy_docs", "get_policy_details"]


def insurance_mcp_server(customer_id: str, read_only: bool = True, **kwargs) -> MCPServerStdio:
    """The MCP server for one logged-in customer. Also used by steps 8 and 10."""
    return MCPServerStdio(
        name="securelife-insurance",
        params={"command": sys.executable,
                "args": [os.path.join(BASE_DIR, "7a_mcp_insurance_server.py")],
                # stdio servers do NOT inherit the parent's environment unless we pass it
                "env": {**os.environ, "CUSTOMER_ID": customer_id}},
        tool_filter=create_static_tool_filter(allowed_tool_names=READ_TOOLS) if read_only else None,
        client_session_timeout_seconds=60,     # the first RAG search loads the embedding model
        cache_tools_list=True,
        **kwargs,
    )


async def main() -> None:
    step6 = load_step("6_agent_all_tools.py")
    session = CustomerSession()
    questions = [" ".join(sys.argv[1:])] if len(sys.argv) > 1 else [
        "What is the coverage amount in my health insurance policy?",
        "Is maternity covered, and is there a waiting period?",
    ]
    async with insurance_mcp_server(session.customer_id) as server:
        tools = await server.list_tools()
        print(f"Discovered from the MCP server: {[t.name for t in tools]}\n")
        agent = Agent[CustomerSession](
            name="SecureLife Insurance Assistant (MCP)",
            model=MODEL,
            instructions=step6.instructions,      # same instructions as step 6
            mcp_servers=[server],                 # <- instead of tools=[...]
        )
        for q in questions:
            print(f"CUSTOMER: {q}")
            result = await Runner.run(agent, q, context=session)
            print_trace(result)
            print("\n" + "-" * 80)
    print("-> Same answers as step 6, but the tools now live in a separate, reusable MCP server.")
    print("   Next: guardrails (step 8).")


if __name__ == "__main__":
    asyncio.run(main())
