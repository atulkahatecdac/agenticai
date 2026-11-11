import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

async def main():
    server_params = StdioServerParameters(
        command="python",
        args=[os.path.join(BASE_DIR, "10_1_weather_mcp_server.py")]
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Get forecast
            result = await session.call_tool("get_weather", {
                "location": "San Francisco",
            })
            print(result.content[0].text)

if __name__ == "__main__":
    asyncio.run(main())