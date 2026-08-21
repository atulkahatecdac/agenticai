#!/usr/bin/env python3
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    server_params = StdioServerParameters(
        command="python",
        args=["c:/code/agenticai/6_mcp/6_20_gutenberg_mcp_server.py"]
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            result = await session.call_tool("search_gutenberg_books", {
                "query": "Jane Austen",
            })
            print(result.content[0].text)

if __name__ == "__main__":
    asyncio.run(main())
