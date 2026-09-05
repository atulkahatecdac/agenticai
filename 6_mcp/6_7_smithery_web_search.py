import os
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from urllib.parse import urlencode
from dotenv import load_dotenv
import asyncio

# Load environment variables
load_dotenv(override=True)
smithery_api_key = os.getenv("SMITHERY_API_KEY")

base_url = "https://server.smithery.ai/pinkpixel-dev/web-scout-mcp/mcp"
params = {
    "api_key": smithery_api_key
}
url = f"{base_url}?{urlencode(params)}"

async def main():
    query = "what is the latest news on the mcp protocol?"

    async with streamable_http_client(url) as (read, write, _):
        async with ClientSession(read, write) as session:
            # Initialize the connection
            await session.initialize()

            # List tools
            tools_result = await session.list_tools()
            print(f"Available tools: {', '.join([t.name for t in tools_result.tools])}")

            # Find the DuckDuckGoWebSearch tool
            tool_name = "DuckDuckGoWebSearch"
            if tool_name not in [t.name for t in tools_result.tools]:
                print(f"Tool '{tool_name}' not found.")
                return

            # Call the tool
            print(f"\nCalling tool '{tool_name}' with query: {query}\n")
            result = await session.call_tool(tool_name, {"query": query, "maxResults": 5})

            # Display results
            if hasattr(result, "content"):
                print("Search Results:\n")
                for idx, item in enumerate(result.content, start=1):
                    print(f"{idx}. {item.text if hasattr(item, 'text') else item}\n")
            else:
                print(result)

if __name__ == "__main__":
    asyncio.run(main())
