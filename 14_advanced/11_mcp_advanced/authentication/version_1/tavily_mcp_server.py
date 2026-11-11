# pip install mcp tavily-python python-dotenv
# Also add TAVILY_API_KEY to .env file
import os
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from tavily import TavilyClient

load_dotenv(override=True)

mcp = FastMCP("TavilySearch")
tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

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
    mcp.run()
