import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

import asyncio
import os
import sys
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_mcp_adapters.client import MultiServerMCPClient

load_dotenv(override=True)

# Tool output can contain characters outside Windows' default console
# codepage (cp1252) - reconfigure stdout to UTF-8 so printing doesn't crash.
sys.stdout.reconfigure(encoding="utf-8")

# =====================================================================
# MCP servers as LangChain agent tools. MultiServerMCPClient.get_tools()
# converts each MCP server's tools into ordinary LangChain BaseTool
# objects - from here on, the standard create_tool_calling_agent /
# AgentExecutor loop can't tell them apart from a local @tool function.
# Each call to an MCP-backed tool spins up its own short-lived stdio
# subprocess session under the hood, so no persistent connection needs
# to be managed for the lifetime of the agent run.
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

prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant with access to tools."),
    ("human", "{input}"),
    MessagesPlaceholder("agent_scratchpad"),
])


async def main():
    tools = await client.get_tools()
    print(f"Loaded {len(tools)} tool(s) from MCP servers: {[t.name for t in tools]}")

    agent = create_tool_calling_agent(llm, tools, prompt)
    # verbose=True prints every tool call/result as it happens - this IS the
    # point of the demo: watching the agent pick between the crypto and
    # forex MCP servers depending on what the question needs.
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True, max_iterations=6)

    # Deliberately needs both MCP servers: a crypto price lookup, then a
    # currency conversion chained off that price.
    question = "What is the current price of ethereum in USD, and how much is that in INR?"
    result = await agent_executor.ainvoke({"input": question})

    print("\n" + "=" * 70)
    print("FINAL ANSWER")
    print("=" * 70)
    print(result["output"])


if __name__ == "__main__":
    asyncio.run(main())
