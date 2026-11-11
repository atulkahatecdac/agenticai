import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Payload 1: authentication-bypass style injection. The unsafe query becomes:
#   SELECT id, name, email FROM users WHERE name = 'nobody' OR '1'='1'
# `'1'='1'` is always true, so instead of matching zero rows for a
# made-up name, every row in the table matches.
AUTH_BYPASS_PAYLOAD = "nobody' OR '1'='1"

# Payload 2: UNION-based exfiltration. The unsafe query becomes:
#   SELECT id, name, email FROM users WHERE name = 'nobody'
#   UNION SELECT id, api_key, 'stolen' FROM secrets --'
# The tool only ever intended to return user names/emails, but this pulls
# rows out of a completely different table (`secrets`) it was never
# supposed to expose. Column count (3) has to match the original SELECT.
UNION_EXFIL_PAYLOAD = "nobody' UNION SELECT id, api_key, 'stolen' FROM secrets --"


async def try_query(session: ClientSession, tool_name: str, label: str, name: str):
    result = await session.call_tool(tool_name, {"name": name})
    print(f"\n[{tool_name}] {label}")
    print(f"  input: {name}")
    print(f"  result: {result.content[0].text}")


async def main():
    server_params = StdioServerParameters(
        command="python",
        args=[os.path.join(BASE_DIR, "6_4_sql_injection_mcp_server.py")],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            print("=" * 70)
            print("ATTACKING search_users_unsafe (no validation, string-built SQL)")
            print("=" * 70)
            await try_query(session, "search_users_unsafe", "normal, legitimate search", "Alice")
            await try_query(session, "search_users_unsafe", "auth-bypass injection", AUTH_BYPASS_PAYLOAD)
            await try_query(session, "search_users_unsafe", "UNION-based data exfiltration", UNION_EXFIL_PAYLOAD)

            print("\n" + "=" * 70)
            print("SAME ATTACKS against search_users_safe (validated + parameterized)")
            print("=" * 70)
            await try_query(session, "search_users_safe", "normal, legitimate search", "Alice")
            await try_query(session, "search_users_safe", "auth-bypass injection", AUTH_BYPASS_PAYLOAD)
            await try_query(session, "search_users_safe", "UNION-based data exfiltration", UNION_EXFIL_PAYLOAD)


if __name__ == "__main__":
    asyncio.run(main())
