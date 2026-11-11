# pip install mcp-server-sqlite
#
# This demo uses Anthropic's OFFICIAL reference SQLite MCP server
# (the `mcp-server-sqlite` package, launched below as a subprocess) instead
# of a hand-rolled one - unlike ../10_mcp/10_3_database_mcp_server.py and
# ../10_mcp/10_5_secure_mcp_server.py in module 10, there is no
# server script to write here. The official server is generic: it exposes
# raw SQL tools (create_table, write_query, read_query, list_tables,
# describe_table) plus one built-in resource, memo://insights, that
# append_insight appends to - a living note the client can re-read at any
# time. This client just drives that ready-made server against a small
# books catalog.
import asyncio
import os
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from pydantic import AnyUrl

# The memo://insights resource can contain emoji - reconfigure stdout to
# UTF-8 so printing it doesn't crash under Windows' default cp1252 console.
sys.stdout.reconfigure(encoding="utf-8")

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "official_books.db")


async def main():
    server_params = StdioServerParameters(
        command="mcp-server-sqlite",
        args=["--db-path", DB_PATH],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            print("Tools exposed by the official SQLite server:")
            for t in tools.tools:
                print(f"  - {t.name}: {t.description}")

            print("\n=== create_table ===")
            result = await session.call_tool("create_table", {
                "query": """CREATE TABLE IF NOT EXISTS books (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    author TEXT NOT NULL,
                    year INTEGER NOT NULL
                )"""
            })
            print(result.content[0].text)

            print("\n=== write_query (insert rows) ===")
            for title, author, year in [
                ("The Pragmatic Programmer", "David Thomas & Andrew Hunt", 1999),
                ("Clean Code", "Robert C. Martin", 2008),
                ("Designing Data-Intensive Applications", "Martin Kleppmann", 2017),
            ]:
                result = await session.call_tool("write_query", {
                    "query": f"INSERT INTO books (title, author, year) VALUES ('{title}', '{author}', {year})"
                })
                print(result.content[0].text)

            print("\n=== list_tables ===")
            result = await session.call_tool("list_tables", {})
            print(result.content[0].text)

            print("\n=== describe_table ===")
            result = await session.call_tool("describe_table", {"table_name": "books"})
            print(result.content[0].text)

            print("\n=== read_query (select) ===")
            result = await session.call_tool("read_query", {"query": "SELECT * FROM books ORDER BY year"})
            print(result.content[0].text)

            print("\n=== append_insight ===")
            result = await session.call_tool("append_insight", {
                "insight": "All 3 catalogued books are software engineering classics published between 1999 and 2017."
            })
            print(result.content[0].text)

            print("\n=== reading memo://insights resource ===")
            result = await session.read_resource(AnyUrl("memo://insights"))
            print(result.contents[0].text)


if __name__ == "__main__":
    asyncio.run(main())
