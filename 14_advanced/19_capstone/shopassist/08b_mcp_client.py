import asyncio
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import TextContent

# The server script sits next to this one.
SERVER = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "08a_mcp_server.py")

# Start the server as a child process, with the same Python as this client.
server_params = StdioServerParameters(command=sys.executable, args=[SERVER])


async def main():
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # 1. Ask the server which tools it has.
            tools = await session.list_tools()
            print("Tools on the server:")
            for tool in tools.tools:
                print(f"  {tool.name}: {tool.description}")

            # 2. Call each tool.
            calls = [
                ("lookup_order", "ORD-12345678"),  # found
                ("start_return", "ORD-12345678"),  # inside the 30 days
                ("start_return", "ORD-87654321"),  # past the 30 days
                ("start_return", "ORD-00000000"),  # unknown order
            ]
            for name, order_id in calls:
                result = await session.call_tool(name, {"order_id": order_id})
                print(f"\n{name}({order_id}):")
                for item in result.content:
                    if isinstance(item, TextContent):  # tools can also return images etc.
                        print(item.text)


asyncio.run(main())
