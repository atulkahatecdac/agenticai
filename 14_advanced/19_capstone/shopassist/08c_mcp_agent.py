import asyncio
import os
import sys
from dotenv import load_dotenv
from anthropic import Anthropic
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

load_dotenv()
client = Anthropic()

MODEL = "claude-sonnet-5-5"
SYSTEM = (
    "You are ShopAssist, an online store's support assistant. "
    "Returns are accepted within 30 days of delivery. "
    "Use the tools to look up orders and to start returns. "
    "Answer in one or two sentences."
)

# Same agentic loop as 07a, but the tools now come from the MCP server
# (08a) instead of being written in this file.
SERVER = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "08a_mcp_server.py")
server_params = StdioServerParameters(command=sys.executable, args=[SERVER])


async def main():
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # 1. Ask the server for its tools and convert them to
            #    Claude's format (inputSchema -> input_schema).
            mcp_tools = await session.list_tools()
            tools = [{"name": t.name,
                      "description": t.description,
                      "input_schema": t.inputSchema}
                     for t in mcp_tools.tools]
            print("tools from MCP server:", [t["name"] for t in tools])

            messages = [{"role": "user", "content":
                         "I want to return the jacket from order ORD-12345678."}]

            # 2. The agentic loop from 07a.
            turn = 0
            while True:
                turn += 1
                response = client.messages.create(
                    model=MODEL,
                    max_tokens=1000,
                    output_config={"effort": "low"},
                    system=SYSTEM,
                    tools=tools,
                    messages=messages,
                )
                print(f"turn {turn}: stop_reason = {response.stop_reason}")
                if response.stop_reason != "tool_use":
                    break
                messages.append({"role": "assistant", "content": response.content})
                results = []
                for block in response.content:
                    if block.type == "tool_use":
                        print(f"  run {block.name}({block.input}) on the MCP server")
                        # 3. The only real change from 07a: the MCP server runs the tool.
                        output = await session.call_tool(block.name, block.input)
                        results.append({"type": "tool_result",
                                        "tool_use_id": block.id,
                                        "content": output.content[0].text,
                                        "is_error": output.isError})
                messages.append({"role": "user", "content": results})

            for block in response.content:
                if block.type == "text":
                    print(block.text)


asyncio.run(main())
