# Needs Docker Desktop running - see 11_3_github_mcp_readonly_client.py for
# the Docker/image notes.
#
# Write-side demo of GitHub's OFFICIAL MCP server. Unlike 11_3 (which only reads
# octocat/Hello-World), this one actually creates content - a file and an
# issue - so it targets a THROWAWAY public repo under a THROWAWAY GitHub
# account made just for this demo, never the account/repo you use for real
# work. Owner/repo/token all come from .env (GITHUB_DEMO_OWNER,
# GITHUB_DEMO_REPO, GITHUB_WRITE_TOKEN) - nothing is hardcoded here, so
# this script itself carries no trace of any specific account.
#
# The content pushed is a small inline string, not a real file read off
# disk - keeps the demo fully self-contained, with no local paths baked in.
import asyncio
import os
import sys
from datetime import datetime, timezone
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

load_dotenv(override=True)
sys.stdout.reconfigure(encoding="utf-8")

GITHUB_WRITE_TOKEN = os.getenv("GITHUB_WRITE_TOKEN")
OWNER = os.getenv("GITHUB_DEMO_OWNER")
REPO = os.getenv("GITHUB_DEMO_REPO")

if not all([GITHUB_WRITE_TOKEN, OWNER, REPO]):
    raise ValueError(
        "Missing GITHUB_WRITE_TOKEN / GITHUB_DEMO_OWNER / GITHUB_DEMO_REPO in .env. "
        "These must point at a THROWAWAY GitHub account + public repo made just for this "
        "demo, not your real account - see the plan/README notes for setup steps."
    )


async def main():
    server_params = StdioServerParameters(
        command="docker",
        args=[
            "run", "-i", "--rm",
            "-e", "GITHUB_PERSONAL_ACCESS_TOKEN",
            "ghcr.io/github/github-mcp-server",
            "stdio",
            "--toolsets=repos,issues",  # no --read-only this time - this demo needs to write
        ],
        env={**os.environ, "GITHUB_PERSONAL_ACCESS_TOKEN": GITHUB_WRITE_TOKEN},
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

            print(f"=== create_or_update_file (demo_notes/{timestamp}.md) ===")
            result = await session.call_tool("create_or_update_file", {
                "owner": OWNER,
                "repo": REPO,
                "path": f"demo_notes/note_{int(datetime.now().timestamp())}.md",
                "content": f"# MCP demo note\n\nWritten via the official GitHub MCP server at {timestamp}.\n",
                "message": "Add note via official GitHub MCP server demo",
                "branch": "main",
            })
            print(result.content[0].text)

            # This server version consolidates create/update/etc. into one
            # issue_write tool, selected via the "method" argument, rather
            # than separate create_issue/update_issue tools.
            print("\n=== issue_write (method=create) ===")
            result = await session.call_tool("issue_write", {
                "method": "create",
                "owner": OWNER,
                "repo": REPO,
                "title": f"MCP demo issue - {timestamp}",
                "body": "Opened automatically by 11_4_github_mcp_write_client.py to demonstrate the issue_write tool.",
            })
            print(result.content[0].text)


if __name__ == "__main__":
    asyncio.run(main())
