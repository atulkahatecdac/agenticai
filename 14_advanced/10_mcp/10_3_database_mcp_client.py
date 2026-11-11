import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


async def main():
    """Connect to the database MCP server, discover its tools, then call them."""

    server_params = StdioServerParameters(
        command="python",
        args=[os.path.join(BASE_DIR, "10_3_database_mcp_server.py")],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # 1. Discovery: ask the server what it offers (name, description, input schema)
            tools_list = await session.list_tools()

            print("Available MCP Tools:")
            print("=" * 60)

            for tool in tools_list.tools:
                print(f"\nTool Name: {tool.name}")
                print(f"Description: {tool.description}")

                if tool.inputSchema:
                    print("Parameters:")
                    properties = tool.inputSchema.get("properties", {})
                    required = tool.inputSchema.get("required", [])

                    for param_name, param_info in properties.items():
                        req_marker = " (required)" if param_name in required else " (optional)"
                        param_type = param_info.get("type", "unknown")
                        param_desc = param_info.get("description", "No description")
                        print(f"  - {param_name} ({param_type}){req_marker}: {param_desc}")

                print("-" * 60)

            print(f"\nTotal tools found: {len(tools_list.tools)}")

            # 2. Use the tools we just discovered
            print("\n=== call_tool ===")
            for name, email in [("Alice", "alice@example.com"), ("Bob", "bob@example.com")]:
                result = await session.call_tool("add_user", {"name": name, "email": email})
                print(result.content[0].text)

            result = await session.call_tool("list_users", {})
            print(result.content[0].text)


if __name__ == "__main__":
    asyncio.run(main())
