from mcp.server.fastmcp import FastMCP
import requests

mcp = FastMCP("Crypto")

@mcp.tool()
def get_cryptocurrency_price(crypto: str) -> str:
    """
    Gets the price of a cryptocurrency.
    Args:
        crypto: symbol of the cryptocurrency (e.g., 'bitcoin', 'ethereum').
    """
    try:
        # Use CoinGecko API to fetch current price in INR
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {"ids": crypto.lower(), "vs_currencies": "usd"}
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        price_usd = data.get(crypto.lower(), {}).get("usd")
        if price_usd is not None:
            return f"The price of {crypto} is ${price_usd}."
        else:
            return f"Price for {crypto} not found."
    except Exception as e:
        return f"Error fetching price for {crypto}: {e}"

if __name__ == "__main__":
    mcp.run()
