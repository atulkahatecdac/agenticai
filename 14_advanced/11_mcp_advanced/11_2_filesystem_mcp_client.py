# Needs Node.js/npm installed (npx comes bundled with it) - no `pip install`
# for this one.
#
# Same idea as 11_1_sqlite_resource_mcp_client.py, but for Anthropic's
# OFFICIAL reference FILESYSTEM MCP server (`@modelcontextprotocol/server-filesystem`,
# a Node package launched below via `npx`) instead of a hand-rolled one -
# again, no server script to write, just point the official server at a
# directory and drive its tools.
#
# The one argument the server takes is the SANDBOX directory: every tool
# call is restricted to paths inside it, no matter what path a client
# asks for - the last demo below deliberately tries to read a file
# OUTSIDE the sandbox to prove that boundary is actually enforced
# server-side, not just a suggestion.
import asyncio
import os
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SANDBOX_DIR = os.path.join(BASE_DIR, "fs_sandbox")
os.makedirs(SANDBOX_DIR, exist_ok=True)

# A real file OUTSIDE the sandbox, to prove the server refuses to touch it.
OUTSIDE_FILE = os.path.join(BASE_DIR, "11_1_sqlite_resource_mcp_client.py")


async def main():
    server_params = StdioServerParameters(
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", SANDBOX_DIR],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            print("Tools exposed by the official filesystem server:")
            for t in tools.tools:
                print(f"  - {t.name}")

            print("\n=== list_allowed_directories ===")
            result = await session.call_tool("list_allowed_directories", {})
            print(result.content[0].text)

            print("\n=== create_directory (notes) ===")
            result = await session.call_tool("create_directory", {"path": "notes"})
            print(result.content[0].text)

            print("\n=== write_file (notes/todo.txt) ===")
            result = await session.call_tool("write_file", {
                "path": "notes/todo.txt",
                "content": "1. Buy milk\n2. Finish MCP demo\n",
            })
            print(result.content[0].text)

            print("\n=== read_text_file ===")
            result = await session.call_tool("read_text_file", {"path": "notes/todo.txt"})
            print(result.content[0].text)

            print("\n=== edit_file (replace one line) ===")
            result = await session.call_tool("edit_file", {
                "path": "notes/todo.txt",
                "edits": [{"oldText": "2. Finish MCP demo\n", "newText": "2. Finish MCP demo [DONE]\n"}],
            })
            print(result.content[0].text)

            print("\n=== directory_tree ===")
            result = await session.call_tool("directory_tree", {"path": "."})
            print(result.content[0].text)

            print("\n=== search_files (pattern: **/*.txt, recursive glob) ===")
            result = await session.call_tool("search_files", {"path": ".", "pattern": "**/*.txt"})
            print(result.content[0].text)

            print("\n=== get_file_info ===")
            result = await session.call_tool("get_file_info", {"path": "notes/todo.txt"})
            print(result.content[0].text)

            print(f"\n=== attempting to read OUTSIDE the sandbox ({OUTSIDE_FILE}) ===")
            result = await session.call_tool("read_text_file", {"path": OUTSIDE_FILE})
            print(f"isError: {result.isError}")
            print(result.content[0].text)


if __name__ == "__main__":
    asyncio.run(main())
