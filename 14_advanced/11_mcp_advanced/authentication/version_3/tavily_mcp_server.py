# pip install fastmcp tavily-python python-dotenv
# Also add TAVILY_API_KEY, SCALEKIT_ENVIRONMENT_URL, SCALEKIT_CLIENT_ID,
# SCALEKIT_RESOURCE_ID, MCP_URL to .env file
#
# Step 3 of the auth progression: version_2 faked auth with a static shared
# secret checked by a hand-rolled Flask wrapper around the MCP server.
# Here the MCP server itself becomes a real OAuth2 resource server - fastmcp's
# ScalekitProvider validates access tokens issued by Scalekit (signature,
# expiry, issuer, audience) on every request, and exposes the MCP protected-
# resource-metadata endpoint so a compliant client can discover where to get
# a token from. No Flask wrapper needed anymore: fastmcp serves MCP directly
# over HTTP (streamable-http transport) with auth built in.
import os
from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.server.auth.providers.scalekit import ScalekitProvider
from tavily import TavilyClient

load_dotenv(override=True)

tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

auth = ScalekitProvider(
    environment_url=os.getenv("SCALEKIT_ENVIRONMENT_URL"),
    resource_id=os.getenv("SCALEKIT_RESOURCE_ID"),
    base_url=os.getenv("MCP_URL"),
)

mcp = FastMCP("TavilySearch", auth=auth)

@mcp.tool()
def tavily_search(query: str) -> str:
    """
    Searches the web using Tavily for the given query
    Args:
    query: the search query text
    """
    response = tavily_client.search(query=query, max_results=5)
    results = response.get("results", [])

    if not results:
        return "No results found."

    return "\n\n".join(
        f"{r['title']}\n{r['url']}\n{r['content']}" for r in results
    )

if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
