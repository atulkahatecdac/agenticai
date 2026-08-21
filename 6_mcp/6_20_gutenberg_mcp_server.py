from mcp.server.fastmcp import FastMCP
import requests

mcp = FastMCP("Gutenberg")

# Trailing slash matters: "/books" (no slash) 301-redirects to "/books/",
# and that redirect hop has been observed to stall/time out - hitting the
# canonical "/books/" URL directly avoids the redirect altogether.
GUTENDEX_URL = "https://gutendex.com/books/"

@mcp.tool()
def search_gutenberg_books(query: str) -> str:
    """
    Searches Project Gutenberg's free ebook catalog via the Gutendex API (no key required).
    Args:
        query: search term - title, author name, or subject (e.g. 'Jane Austen', 'dragons').
    Returns up to 5 matches as 'Title by Author(s) [id=..., downloads=...]', one per line,
    ordered by popularity.
    """
    try:
        response = requests.get(GUTENDEX_URL, params={"search": query}, timeout=10)
        response.raise_for_status()
        results = response.json().get("results", [])
        if not results:
            return f"No Project Gutenberg books found for '{query}'."

        lines = []
        for book in results[:5]:
            authors = ", ".join(a["name"] for a in book.get("authors", [])) or "Unknown author"
            lines.append(
                f"{book['title']} by {authors} "
                f"[id={book['id']}, downloads={book.get('download_count', 0)}]"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"Error searching Project Gutenberg for '{query}': {e}"

if __name__ == "__main__":
    mcp.run()
