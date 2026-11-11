from mcp.server.fastmcp import FastMCP
import requests
import os
from dotenv import load_dotenv

load_dotenv()

mcp = FastMCP("ExchangeRate")

@mcp.tool()
def convert_currency(from_currency: str, to_currency: str, amount: float) -> str:
    """
    Convert currency from one type to another.
    
    Args:
        from_currency: Source currency code (e.g., 'USD', 'EUR')
        to_currency: Target currency code (e.g., 'INR', 'GBP')
        amount: Amount to convert
    
    Returns:
        Conversion result with rate and converted amount
    """
    try:
        api_key = os.getenv("EXCHANGE_RATE_API_KEY")
        if not api_key:
            return "Error: EXCHANGE_RATE_API_KEY not found in environment variables"
        
        url = f"https://v6.exchangerate-api.com/v6/{api_key}/pair/{from_currency}/{to_currency}/{amount}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get("result") == "success":
            rate = data.get("conversion_rate")
            result = data.get("conversion_result")
            return f"{amount} {from_currency} = {result} {to_currency} (Rate: {rate})"
        else:
            return f"Error: {data.get('error-type', 'Unknown error')}"
            
    except Exception as e:
        return f"Error converting currency: {e}"

if __name__ == "__main__":
    mcp.run()