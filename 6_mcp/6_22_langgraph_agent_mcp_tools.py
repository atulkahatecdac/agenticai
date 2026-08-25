import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

import asyncio
import os
import sys
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langchain_mcp_adapters.client import MultiServerMCPClient

load_dotenv(override=True)

# Tool output can contain characters outside Windows' default console
# codepage (cp1252) - reconfigure stdout to UTF-8 so printing doesn't crash.
sys.stdout.reconfigure(encoding="utf-8")

# =====================================================================
# MCP servers as LangGraph agent tools - the LangGraph counterpart to
# 6_21_langchain_agent_mcp_tools.py. The same MultiServerMCPClient.
# get_tools() call converts each MCP server's tools into ordinary
# LangChain BaseTool objects; here they're handed to langgraph.prebuilt.
# create_react_agent instead of an AgentExecutor. The prebuilt ReAct
# agent loops calling tools and reasoning until it has a final answer,
# with no separate prompt template or agent_scratchpad to wire up.
# =====================================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

client = MultiServerMCPClient({
    "crypto": {
        "transport": "stdio",
        "command": sys.executable,
        "args": [os.path.join(BASE_DIR, "6_3_crypto_mcp_server.py")],
    },
    "forex": {
        "transport": "stdio",
        "command": sys.executable,
        "args": [os.path.join(BASE_DIR, "6_5_forex_mcp_server.py")],
    },
})

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)


async def main():
    tools = await client.get_tools()
    print(f"Loaded {len(tools)} tool(s) from MCP servers: {[t.name for t in tools]}")

    agent = create_react_agent(model=llm, tools=tools)

    # Deliberately needs both MCP servers: a crypto price lookup, then a
    # currency conversion chained off that price.
    question = "What is the current price of ethereum in USD, and how much is that in INR?"

    final_state = None
    async for state in agent.astream({"messages": [{"role": "user", "content": question}]}, stream_mode="values"):
        final_state = state
        last = state["messages"][-1]
        for call in getattr(last, "tool_calls", None) or []:
            print(f"  -> calling {call['name']}({call['args']})")
        if getattr(last, "type", None) == "tool":
            print(f"     result: {last.content}")

    print("\n" + "=" * 70)
    print("FINAL ANSWER")
    print("=" * 70)
    print(final_state["messages"][-1].content)


if __name__ == "__main__":
    asyncio.run(main())
