# A live data API (CoinGecko, free, no key) exposed through MCP in two ways:
#
#   - RESOURCE  crypto://price/{coin}     -> data the app/user READS (no side effects)
#   - TOOL      get_cryptocurrency_price  -> an action the LLM decides to CALL
#
# `{coin}` makes the resource a *template*: one URI pattern covers every coin,
# and the client fills it in (crypto://price/bitcoin, crypto://price/ethereum).
# The client lists templates with list_resource_templates() and reads one with
# read_resource(). Try both in the MCP Inspector: mcp dev 10_2_crypto_mcp_server.py
import json

import requests
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Crypto")

PRICE_URL = "https://api.coingecko.com/api/v3/simple/price"


def fetch_price(coin: str) -> dict:
    """Call the live API once; shared by the resource and the tool."""
    params = {"ids": coin.lower(), "vs_currencies": "usd,inr", "include_24hr_change": "true"}
    response = requests.get(PRICE_URL, params=params, timeout=10)
    response.raise_for_status()
    return response.json().get(coin.lower(), {})


@mcp.resource("crypto://price/{coin}", mime_type="application/json")
def crypto_price_resource(coin: str) -> str:
    """Live price of a cryptocurrency in USD and INR, with the 24h change."""
    data = fetch_price(coin)
    if not data:
        return json.dumps({"coin": coin, "error": "not found"})
    return json.dumps({
        "coin": coin.lower(),
        "usd": data.get("usd"),
        "inr": data.get("inr"),
        "change_24h_pct": round(data.get("usd_24h_change", 0.0), 2),
    })


@mcp.tool()
def get_cryptocurrency_price(crypto: str) -> str:
    """
    Gets the price of a cryptocurrency.
    Args:
        crypto: CoinGecko id of the cryptocurrency (e.g., 'bitcoin', 'ethereum').
    """
    try:
        price_usd = fetch_price(crypto).get("usd")
        if price_usd is not None:
            return f"The price of {crypto} is ${price_usd}."
        return f"Price for {crypto} not found."
    except Exception as e:
        return f"Error fetching price for {crypto}: {e}"


if __name__ == "__main__":
    mcp.run()
