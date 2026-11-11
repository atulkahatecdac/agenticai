import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(BASE_DIR))
import mock_bank  # noqa: E402

from mcp.server.fastmcp import FastMCP  # noqa: E402

# =====================================================================
# Accounts MCP server - the Balance Enquiry tool implementation, moved
# out of the agent process entirely. Runs as its own stdio subprocess,
# started/stopped by whatever MultiServerMCPClient config points at it
# (see 12_2_7_mcp_tool_boundary.py). Following 6_mcp/6_12_crypto_mcp_server.py's
# FastMCP shape - a plain function decorated with @mcp.tool(), same
# docstring-as-schema convention as every @tool-decorated function in
# steps 3-6, just running in a separate process now.
# =====================================================================

mcp = FastMCP("Accounts")


@mcp.tool()
def get_account_balance(customer_id: str) -> str:
    """Look up the current account balance for a bank customer by their customer ID."""
    result = mock_bank.get_balance(customer_id)
    if "error" in result:
        return result["error"]
    balance = mock_bank.format_inr(result["balance"])
    return f"Customer {result['name']} (ID {customer_id}) has a balance of {balance}."


if __name__ == "__main__":
    mcp.run()
