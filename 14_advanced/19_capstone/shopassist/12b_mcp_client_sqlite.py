import asyncio
import os
import sqlite3
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import TextContent

# Same as 08b, but against the SQLite server (12a).
HERE = os.path.dirname(os.path.abspath(__file__))
SERVER = os.path.join(HERE, "12a_mcp_server_sqlite.py")
server_params = StdioServerParameters(command=sys.executable, args=[SERVER])


async def main():
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            calls = [
                ("start_return", "ORD-11112222"),  # new label
                ("start_return", "ORD-11112222"),  # again: already returned
                ("start_return", "ORD-12345678"),  # another new label
            ]
            for name, order_id in calls:
                result = await session.call_tool(name, {"order_id": order_id})
                print(f"\n{name}({order_id}):")
                for item in result.content:
                    if isinstance(item, TextContent):
                        print(item.text)

    # The returns are saved in shop.db, so they are still there after
    # the server has stopped. Run this script twice to see that.
    db = sqlite3.connect(os.path.join(HERE, "shop.db"))
    print("\nreturns table:", db.execute("SELECT * FROM returns").fetchall())
    db.close()


asyncio.run(main())
