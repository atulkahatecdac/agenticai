# Needs Node.js/npm (npx) - no `pip install`. First run downloads the
# Playwright browser binaries via npx, which can take a minute.
#
# Microsoft's OFFICIAL Playwright MCP server (`@playwright/mcp`) drives a
# real headless browser - unlike 6_12_crypto_mcp_server.py / 6_13_forex_mcp_server.py
# elsewhere in this folder, which call a clean JSON API directly, this demo
# fetches data that only exists as rendered page content: the live gold
# spot price on goldprice.org, which has no public API of its own. That's
# the actual point of a browser-automation MCP server - reaching pages a
# plain HTTP request can't meaningfully parse (JS-rendered numbers, no
# stable JSON endpoint).
import asyncio
import re
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

sys.stdout.reconfigure(encoding="utf-8")

URL = "https://goldprice.org/"
# The live price renders as e.g. "4,052.9" next to a currency/unit picker
# already set to "USD"/"oz" - no dollar sign in the text itself.
PRICE_PATTERN = r"[0-9]{1,3},[0-9]{3}\.[0-9]{1,2}"


async def main():
    server_params = StdioServerParameters(
        command="npx",
        args=["-y", "@playwright/mcp@latest"],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            print(f"Tools exposed by the official Playwright MCP server ({len(tools.tools)} total):")
            for t in tools.tools:
                print(f"  - {t.name}")

            print(f"\n=== browser_navigate ({URL}) ===")
            result = await session.call_tool("browser_navigate", {"url": URL})
            print(result.content[0].text[:300])

            # Give the page's live ticker a moment to populate after load.
            await session.call_tool("browser_wait_for", {"time": 3})

            print(f"\n=== browser_find (regex: {PRICE_PATTERN}) ===")
            result = await session.call_tool("browser_find", {"regex": PRICE_PATTERN})
            match_text = result.content[0].text
            print(match_text[:500])

            price = re.search(PRICE_PATTERN, match_text)
            if price:
                print(f"\nCurrent gold spot price: ${price.group()} USD per troy ounce")
            else:
                print("\nCould not extract a price from the page - site layout may have changed.")

            input("\nPress Enter to close the browser...")
            await session.call_tool("browser_close", {})


if __name__ == "__main__":
    asyncio.run(main())
