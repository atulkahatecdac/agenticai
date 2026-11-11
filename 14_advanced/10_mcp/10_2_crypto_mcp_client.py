import asyncio
import json
import os

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from pydantic import AnyUrl

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


async def main():
    server_params = StdioServerParameters(
        command="python",
        args=[os.path.join(BASE_DIR, "10_2_crypto_mcp_server.py")],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # 1. Resources: discover the URI template, then read it for two coins
            templates = await session.list_resource_templates()
            for t in templates.resourceTemplates:
                print(f"Resource template: {t.uriTemplate}  ({t.description})")

            for coin in ["bitcoin", "ethereum"]:
                result = await session.read_resource(AnyUrl(f"crypto://price/{coin}"))
                data = json.loads(result.contents[0].text)
                print(f"  read crypto://price/{coin} -> {data}")

            # 2. Tools: the same live API, but as an action an LLM would call
            result = await session.call_tool("get_cryptocurrency_price", {"crypto": "tether"})
            print(f"\nTool call get_cryptocurrency_price(tether) -> {result.content[0].text}")


if __name__ == "__main__":
    asyncio.run(main())
