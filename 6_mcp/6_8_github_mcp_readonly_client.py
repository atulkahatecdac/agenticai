# Needs Docker Desktop running - no `pip install`, the official server ships
# as the image `ghcr.io/github/github-mcp-server` (pulled automatically on
# first run).
#
# GitHub's OFFICIAL MCP server (github/github-mcp-server), run locally in
# Docker rather than through a third-party hosted proxy.
#
# Rather than touching a real personal account/repo, this demo deliberately targets `octocat/Hello-World`
# - GitHub's own long-standing public repo, built for exactly this kind of
# API demo - and only touches read tools. The token only needs a
# fine-grained PAT scoped to "Public Repositories (read-only)", which grants
# zero access to anyone's private data. See .env for GITHUB_READONLY_TOKEN.
import asyncio
import os
import sys
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

load_dotenv(override=True)
sys.stdout.reconfigure(encoding="utf-8")

GITHUB_READONLY_TOKEN = os.getenv("GITHUB_READONLY_TOKEN")
if not GITHUB_READONLY_TOKEN:
    raise ValueError(
        "Missing GITHUB_READONLY_TOKEN in .env - generate a fine-grained PAT scoped to "
        "'Public Repositories (read-only)' and set it there."
    )

OWNER, REPO = "octocat", "Hello-World"


async def main():
    server_params = StdioServerParameters(
        command="docker",
        args=[
            "run", "-i", "--rm",
            "-e", "GITHUB_PERSONAL_ACCESS_TOKEN",
            "ghcr.io/github/github-mcp-server",
            "stdio",
            "--read-only",              # server refuses write tools even if asked
            "--toolsets=repos,issues",  # keep the tool list small and on-topic
        ],
        env={**os.environ, "GITHUB_PERSONAL_ACCESS_TOKEN": GITHUB_READONLY_TOKEN},
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            print(f"Tools exposed in --read-only mode ({len(tools.tools)} total):")
            for t in tools.tools:
                print(f"  - {t.name}")

            print(f"\n=== get_file_contents ({OWNER}/{REPO}: README) ===")
            result = await session.call_tool("get_file_contents", {
                "owner": OWNER, "repo": REPO, "path": "README",
            })
            print(result.content[0].text)

            print(f"\n=== list_issues ({OWNER}/{REPO}) ===")
            result = await session.call_tool("list_issues", {
                "owner": OWNER, "repo": REPO, "perPage": 5,
            })
            print(result.content[0].text[:1000])

            print(f"\n=== search_repositories (query: 'agentic ai') ===")
            result = await session.call_tool("search_repositories", {"query": "agentic ai", "perPage": 5})
            print(result.content[0].text[:1000])

            # Prove the read-only boundary is enforced by the SERVER, not
            # just "we chose not to call" a write tool (same pattern as the
            # sandbox-escape check in 6_7_filesystem_mcp_client.py).
            print("\n=== attempting create_issue (should be rejected, server is --read-only) ===")
            try:
                result = await session.call_tool("create_issue", {
                    "owner": OWNER, "repo": REPO, "title": "should never be created",
                })
                print(f"isError: {result.isError}")
                print(result.content[0].text)
            except Exception as e:
                print(f"Rejected: tool not available in read-only mode ({e})")


if __name__ == "__main__":
    asyncio.run(main())
