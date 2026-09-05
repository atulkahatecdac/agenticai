from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

# Construct server URL with authentication
from urllib.parse import urlencode
from dotenv import load_dotenv
import os

load_dotenv(override=True)
smithery_api_key = os.getenv("SMITHERY_API_KEY")

base_url = "https://server.smithery.ai/isdaniel/mcp_weather_server/mcp"
params = {"api_key": smithery_api_key}
url = f"{base_url}?{urlencode(params)}"

async def main():
    # Connect to the server using HTTP client
    async with streamable_http_client(url) as (read, write, _):
        async with ClientSession(read, write) as session:
            # Initialize the connection
            await session.initialize()
            
            # List available tools
            tools_result = await session.list_tools()
            tool_names = [t.name for t in tools_result.tools]
            print(f"Available tools: {', '.join(tool_names)}")

            # ✅ Call the get_current_weather tool if available
            if "get_current_weather" in tool_names:
                city = "Rome"
                print(f"\nCalling get_current_weather for city: {city}\n")

                result = await session.call_tool("get_current_weather", {"city": city})

                # Print results
                print("Weather Result:\n")
                if hasattr(result, "content"):
                    for item in result.content:
                        if hasattr(item, "text"):
                            print(item.text)
                        else:
                            print(item)
                else:
                    print(result)
            else:
                print("\n❌ Tool 'get_weather' not found on this server.")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
