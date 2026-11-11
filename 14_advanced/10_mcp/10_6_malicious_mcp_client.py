import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

async def test_sneaky_server():
    server_params = StdioServerParameters(
        command="python",
        args=[os.path.join(BASE_DIR, "10_6_malicious_mcp_server.py")],
        env=None
    )
    
    print("Connecting to MCP server...")
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("Connected\n")
            
            tools_list = await session.list_tools()
            print(f"Available tools: {[t.name for t in tools_list.tools]}\n")
            
            print("Testing multiply_numbers(7, 6)...")
            result = await session.call_tool("multiply_numbers", arguments={"a": 7, "b": 6})
            print(f"{result.content[0].text}\n")
            
            print("Testing add_numbers(10, 5)...")
            result = await session.call_tool("add_numbers", arguments={"a": 10, "b": 5})
            print(f"{result.content[0].text}\n")
            
            print("Tests complete")

if __name__ == "__main__":
    asyncio.run(test_sneaky_server())