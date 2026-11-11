# MCP servers as CrewAI tools - the CrewAI counterpart of
# 6_14_langchain_agent_mcp_tools.py (LangChain) and 6_15 (LangGraph).
#
# CrewAI's own MCP bridge (MCPServerAdapter) lives in the separate
# `crewai-tools[mcp]` package, which this repo doesn't install. The bridge
# is small enough to write by hand, which also shows what any adapter does:
#
#   1. connect to each MCP server and list_tools()
#   2. turn every MCP tool into a CrewAI BaseTool: same name and description,
#      and an args_schema built from the tool's JSON input schema
#   3. the BaseTool's _run() forwards the call to the MCP server (call_tool)
#
# Same two servers as 6_14/6_15: 6_12 crypto prices and 6_13 exchange rates.
# Needs OPENAI_API_KEY and EXCHANGE_RATE_API_KEY in the repo root .env.
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

import asyncio
import os
import sys
from typing import Any, Type

from crewai import Agent, Crew, Task
from crewai.tools import BaseTool
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from pydantic import BaseModel, Field, create_model

load_dotenv(override=True)
sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SERVERS = {
    "crypto": os.path.join(BASE_DIR, "6_12_crypto_mcp_server.py"),
    "forex": os.path.join(BASE_DIR, "6_13_forex_mcp_server.py"),
}

JSON_TO_PY = {"string": str, "number": float, "integer": int, "boolean": bool}


def server_params(script: str) -> StdioServerParameters:
    return StdioServerParameters(command=sys.executable, args=[script])


async def list_mcp_tools(script: str):
    async with stdio_client(server_params(script)) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            return (await session.list_tools()).tools


async def call_mcp_tool(script: str, name: str, args: dict) -> str:
    # One short-lived stdio session per call, like MultiServerMCPClient does
    async with stdio_client(server_params(script)) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(name, args)
            return "\n".join(c.text for c in result.content if hasattr(c, "text"))


def schema_to_model(tool_name: str, schema: dict) -> Type[BaseModel]:
    """Build a pydantic model from an MCP tool's JSON input schema."""
    required = set(schema.get("required", []))
    fields: dict[str, Any] = {}
    for prop, info in schema.get("properties", {}).items():
        py_type = JSON_TO_PY.get(info.get("type"), str)
        default = ... if prop in required else info.get("default")
        fields[prop] = (py_type, Field(default, description=info.get("description", prop)))
    return create_model(f"{tool_name}_args", **fields)


def mcp_tool_to_crewai(script: str, mcp_tool) -> BaseTool:
    """Wrap one MCP tool as a CrewAI BaseTool."""

    class MCPTool(BaseTool):
        name: str = mcp_tool.name
        description: str = mcp_tool.description or mcp_tool.name
        args_schema: Type[BaseModel] = schema_to_model(mcp_tool.name, mcp_tool.inputSchema)

        def _run(self, **kwargs) -> str:
            # CrewAI calls tools synchronously; the MCP client is async
            return asyncio.run(call_mcp_tool(script, mcp_tool.name, kwargs))

    return MCPTool()


def load_tools() -> list[BaseTool]:
    tools = []
    for server, script in SERVERS.items():
        for t in asyncio.run(list_mcp_tools(script)):
            tools.append(mcp_tool_to_crewai(script, t))
            print(f"[{server}] loaded MCP tool: {t.name}")
    return tools


def main():
    tools = load_tools()

    analyst = Agent(
        role="Crypto Price Analyst",
        goal="Report cryptocurrency prices in the currency the user asks for",
        backstory="You look up live prices and convert currencies with the tools you are given; you never guess numbers.",
        tools=tools,
        llm="gpt-4o-mini",
        verbose=True,
    )

    task = Task(
        description="What is the current price of ethereum in USD, and how much is that in INR?",
        expected_output="The ETH price in USD and in INR, with the exchange rate used.",
        agent=analyst,
    )

    result = Crew(agents=[analyst], tasks=[task], verbose=False).kickoff()

    print("\n" + "=" * 70)
    print("FINAL ANSWER")
    print("=" * 70)
    print(result.raw)


if __name__ == "__main__":
    main()
