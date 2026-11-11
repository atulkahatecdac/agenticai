import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

import asyncio
import os
import sys
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, ToolMessage
from langchain_mcp_adapters.client import MultiServerMCPClient

load_dotenv(override=True)

# Tool output can contain characters outside Windows' default console
# codepage (cp1252) - reconfigure stdout to UTF-8 so printing doesn't crash.
sys.stdout.reconfigure(encoding="utf-8")

# =====================================================================
# MCP servers as LangChain agent tools. MultiServerMCPClient.get_tools()
# converts each MCP server's tools into ordinary LangChain BaseTool
# objects - from here on, the agent loop below (the same bind_tools loop
# as 14_advanced/06_langchain_agents/06_3_sql_database_toolkit_agent.py,
# just async) can't tell them apart from a local @tool function.
# Each call to an MCP-backed tool spins up its own short-lived stdio
# subprocess session under the hood, so no persistent connection needs
# to be managed for the lifetime of the agent run.
# =====================================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

client = MultiServerMCPClient({
    "crypto": {
        "transport": "stdio",
        "command": sys.executable,
        "args": [os.path.join(BASE_DIR, "crypto_mcp_server.py")],
    },
    "forex": {
        "transport": "stdio",
        "command": sys.executable,
        "args": [os.path.join(BASE_DIR, "forex_mcp_server.py")],
    },
})

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

SYSTEM_PROMPT = "You are a helpful assistant with access to tools."


# The agent loop: the LLM asks for tools, our code runs them and feeds the
# results back, until the LLM answers without asking for a tool. MCP tools
# are async, so they are called with ainvoke().
async def run_agent(question: str, tools: list, max_steps: int = 6, verbose: bool = True) -> str:
    llm_with_tools = llm.bind_tools(tools)
    tools_by_name = {t.name: t for t in tools}
    messages: list[BaseMessage] = [SystemMessage(SYSTEM_PROMPT), HumanMessage(question)]

    for _ in range(max_steps):
        ai_message = await llm_with_tools.ainvoke(messages)
        messages.append(ai_message)

        if not ai_message.tool_calls:
            return ai_message.content

        for tool_call in ai_message.tool_calls:
            if verbose:
                print(f"Calling tool: {tool_call['name']}({tool_call['args']})")
            try:
                result = await tools_by_name[tool_call["name"]].ainvoke(tool_call["args"])
            except Exception as e:
                result = f"Tool failed: {e}"
            if verbose:
                print(f"Tool result: {str(result)[:300]}\n")
            messages.append(ToolMessage(content=str(result), tool_call_id=tool_call["id"]))

    return f"Stopped: no final answer after {max_steps} steps."


async def main():
    tools = await client.get_tools()
    print(f"Loaded {len(tools)} tool(s) from MCP servers: {[t.name for t in tools]}")

    # Deliberately needs both MCP servers: a crypto price lookup, then a
    # currency conversion chained off that price. The printed tool calls
    # ARE the point of the demo: watch the agent pick between the crypto
    # and forex MCP servers depending on what the question needs.
    question = "What is the current price of ethereum in USD, and how much is that in INR?"
    answer = await run_agent(question, tools)

    print("\n" + "=" * 70)
    print("FINAL ANSWER")
    print("=" * 70)
    print(answer)


if __name__ == "__main__":
    asyncio.run(main())
