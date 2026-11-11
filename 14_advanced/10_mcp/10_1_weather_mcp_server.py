from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Weather")

@mcp.tool()
def get_weather(location: str) -> str:
    """
    Gets the weather given a location
    Args:
    location: location, can be city, country, state, etc.
    """
    return "The weather is hot and dry"

if __name__ == "__main__":
   mcp.run()