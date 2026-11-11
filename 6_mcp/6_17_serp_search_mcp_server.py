# Web-search MCP server for 6_17_trip_planner_mcp_app.py, backed by SerpApi
# (real Google results). Run on its own with `mcp dev 6_17_serp_search_mcp_server.py`
# to try it in the MCP Inspector.
#
# Needs SERPAPI_API_KEY in the repo root .env (https://serpapi.com, free tier
# available). Client library: google-search-results (imported as `serpapi`).
import os

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from serpapi import GoogleSearch

load_dotenv(override=True)

mcp = FastMCP("SerpSearch")


@mcp.tool()
def web_search(query: str, max_results: int = 5) -> str:
    """
    Search the web with Google (via SerpApi) and return the top results.
    Args:
    query: what to search for, e.g. "top things to do in Rome"
    max_results: how many results to return (1-10)
    """
    api_key = os.getenv("SERPAPI_API_KEY")
    if not api_key:
        return "Error: SERPAPI_API_KEY is not set in .env"

    max_results = max(1, min(int(max_results), 10))
    results = GoogleSearch({"q": query, "num": max_results, "api_key": api_key}).get_dict()
    if "error" in results:
        return f"Error from SerpApi: {results['error']}"

    organic = results.get("organic_results", [])[:max_results]
    if not organic:
        return f"No results found for '{query}'."
    return "\n".join(
        f"{i}. {r.get('title', '')}\n   {r.get('link', '')}\n   {r.get('snippet', '')}"
        for i, r in enumerate(organic, 1)
    )


if __name__ == "__main__":
    mcp.run()
