# Flask front end for 6_14_langchain_agent_mcp_tools.py: instead of a single
# hardcoded question, the user picks a cryptocurrency and a target currency
# from dropdowns, and those choices are woven into the question handed to
# the same LangChain tool-calling agent over the same two MCP servers
# (crypto + forex). Same "watch the agent pick between two MCP-backed
# tools" lesson as 6_14, just driven by a form instead of a fixed string.
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

import asyncio
import importlib
import os
import sys

from flask import Flask, render_template_string, request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# Reuse the MCP client and the agent loop from 6_14 (file names start with a digit).
_agent = importlib.import_module("6_14_langchain_agent_mcp_tools")
client = _agent.client
run_agent = _agent.run_agent

app = Flask(__name__)

# CoinGecko ids (what get_cryptocurrency_price expects), paired with a
# friendly label for the dropdown.
CRYPTOCURRENCIES = [
    ("bitcoin", "Bitcoin (BTC)"),
    ("ethereum", "Ethereum (ETH)"),
    ("litecoin", "Litecoin (LTC)"),
    ("dogecoin", "Dogecoin (DOGE)"),
    ("ripple", "XRP"),
    ("cardano", "Cardano (ADA)"),
    ("solana", "Solana (SOL)"),
    ("polkadot", "Polkadot (DOT)"),
    ("binancecoin", "BNB"),
    ("tron", "TRON (TRX)"),
]

# ISO 4217 codes accepted by convert_currency (exchangerate-api.com).
TARGET_CURRENCIES = [
    ("INR", "Indian Rupee (INR)"),
    ("EUR", "Euro (EUR)"),
    ("GBP", "British Pound (GBP)"),
    ("JPY", "Japanese Yen (JPY)"),
    ("AUD", "Australian Dollar (AUD)"),
    ("CAD", "Canadian Dollar (CAD)"),
    ("CNY", "Chinese Yuan (CNY)"),
    ("SGD", "Singapore Dollar (SGD)"),
    ("CHF", "Swiss Franc (CHF)"),
    ("USD", "US Dollar (USD)"),
]


async def ask_agent(crypto: str, target_currency: str) -> str:
    tools = await client.get_tools()

    question = (
        f"What is the current price of {crypto} in USD, "
        f"and how much is that in {target_currency}?"
    )
    return await run_agent(question, tools)


HTML = """
<!doctype html>
<html>
<head>
    <title>Crypto -> Forex Agent</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 600px; margin: 40px auto; padding: 0 20px; }
        h1 { color: #2c3e50; }
        label { display: block; margin-top: 12px; font-weight: bold; }
        select { width: 100%; padding: 6px; margin-top: 4px; }
        input[type=submit] { margin-top: 20px; padding: 8px 20px; cursor: pointer; }
        .answer { margin-top: 24px; padding: 12px 16px; background: #f7f7f7; border-radius: 6px; white-space: pre-wrap; }
    </style>
</head>
<body>
    <h1>Crypto -> Forex Agent</h1>
    <p>A LangChain tool-calling agent decides how to combine the crypto-price MCP server with the forex MCP server.</p>
    <form method="post">
        <label>Cryptocurrency</label>
        <select name="crypto">
            {% for value, label in cryptocurrencies %}
            <option value="{{ value }}" {% if value == crypto %}selected{% endif %}>{{ label }}</option>
            {% endfor %}
        </select>

        <label>Target currency</label>
        <select name="target_currency">
            {% for value, label in target_currencies %}
            <option value="{{ value }}" {% if value == target_currency %}selected{% endif %}>{{ label }}</option>
            {% endfor %}
        </select>

        <input type="submit" value="Ask the agent">
    </form>

    {% if answer %}
    <div class="answer">{{ answer }}</div>
    {% endif %}
</body>
</html>
"""


@app.route("/", methods=["GET", "POST"])
def home():
    crypto = CRYPTOCURRENCIES[0][0]
    target_currency = TARGET_CURRENCIES[0][0]
    answer = ""

    if request.method == "POST":
        crypto = request.form["crypto"]
        target_currency = request.form["target_currency"]
        answer = asyncio.run(ask_agent(crypto, target_currency))

    return render_template_string(
        HTML,
        cryptocurrencies=CRYPTOCURRENCIES,
        target_currencies=TARGET_CURRENCIES,
        crypto=crypto,
        target_currency=target_currency,
        answer=answer,
    )


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
