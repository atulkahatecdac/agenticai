# Practical multi-MCP application: one Flask UI, one user request, and a
# single workflow that calls FOUR independent real MCP servers in sequence
# to produce one consolidated result - this is the shape most agentic apps
# actually take, unlike the rest of 6_mcp/ which demos one server at a time.
#
#   1. Weather      - Smithery-hosted isdaniel/mcp_weather_server (streamable HTTP)
#   2. Web search    - Smithery-hosted pinkpixel-dev/web-scout-mcp (streamable HTTP)
#   3. Currency      - local 6_5_forex_mcp_server.py (stdio subprocess)
#   4. Save the plan - official @modelcontextprotocol/server-filesystem (stdio subprocess)
#
# Needs: SMITHERY_API_KEY and EXCHANGE_RATE_API_KEY in the repo root .env,
# and Node.js/npx installed (for the filesystem server).
import asyncio
import os
import re

from dotenv import load_dotenv
from flask import Flask, render_template_string, request
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamable_http_client

load_dotenv(override=True)

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SANDBOX_DIR = os.path.join(BASE_DIR, "fs_sandbox")
os.makedirs(SANDBOX_DIR, exist_ok=True)

SMITHERY_API_KEY = os.getenv("SMITHERY_API_KEY")
WEATHER_URL = f"https://server.smithery.ai/isdaniel/mcp_weather_server/mcp?api_key={SMITHERY_API_KEY}"
SEARCH_URL = f"https://server.smithery.ai/pinkpixel-dev/web-scout-mcp/mcp?api_key={SMITHERY_API_KEY}"
FOREX_SERVER_PATH = os.path.join(BASE_DIR, "6_5_forex_mcp_server.py")


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "trip"


async def get_weather(destination: str) -> str:
    async with streamable_http_client(WEATHER_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("get_current_weather", {"city": destination})
            return result.content[0].text


async def get_things_to_do(destination: str) -> str:
    async with streamable_http_client(SEARCH_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "DuckDuckGoWebSearch",
                {"query": f"top things to do in {destination}", "maxResults": 5},
            )
            return result.content[0].text


async def convert_budget(amount: float, from_currency: str, to_currency: str) -> str:
    server_params = StdioServerParameters(command="python", args=[FOREX_SERVER_PATH])
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "convert_currency",
                {"from_currency": from_currency, "to_currency": to_currency, "amount": amount},
            )
            return result.content[0].text


async def save_trip_plan(destination: str, summary: str) -> str:
    server_params = StdioServerParameters(
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", SANDBOX_DIR],
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            await session.call_tool("create_directory", {"path": "trip_plans"})
            path = f"trip_plans/{slugify(destination)}.txt"
            await session.call_tool("write_file", {"path": path, "content": summary})
            return os.path.join(SANDBOX_DIR, path)


async def plan_trip(destination: str, amount: float, from_currency: str, to_currency: str) -> dict:
    results = {}

    try:
        results["weather"] = await get_weather(destination)
    except Exception as e:
        results["weather"] = f"unavailable: {e}"

    try:
        results["things_to_do"] = await get_things_to_do(destination)
    except Exception as e:
        results["things_to_do"] = f"unavailable: {e}"

    try:
        results["budget"] = await convert_budget(amount, from_currency, to_currency)
    except Exception as e:
        results["budget"] = f"unavailable: {e}"

    summary = (
        f"Trip plan for {destination}\n"
        f"{'=' * 40}\n\n"
        f"Current weather:\n{results['weather']}\n\n"
        f"Budget:\n{results['budget']}\n\n"
        f"Things to do:\n{results['things_to_do']}\n"
    )

    try:
        results["saved_path"] = await save_trip_plan(destination, summary)
    except Exception as e:
        results["saved_path"] = f"unavailable: {e}"

    return results


HTML = """
<!doctype html>
<html>
<head>
    <title>MCP Trip Planner</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 700px; margin: 40px auto; padding: 0 20px; }
        h1 { color: #2c3e50; }
        label { display: block; margin-top: 12px; font-weight: bold; }
        input { width: 100%; padding: 6px; margin-top: 4px; box-sizing: border-box; }
        .row { display: flex; gap: 12px; }
        .row > div { flex: 1; }
        input[type=submit] { margin-top: 20px; width: auto; padding: 8px 20px; cursor: pointer; }
        .section { margin-top: 24px; padding: 12px 16px; background: #f7f7f7; border-radius: 6px; }
        .section h2 { margin-top: 0; font-size: 16px; color: #34495e; }
        pre { white-space: pre-wrap; word-wrap: break-word; font-family: inherit; margin: 0; }
    </style>
</head>
<body>
    <h1>MCP Trip Planner</h1>
    <p>Calls 4 real MCP servers (weather, web search, currency conversion, filesystem) to build one trip plan.</p>
    <form method="post">
        <label>Destination</label>
        <input name="destination" value="{{ destination or 'Rome, Italy' }}" required>
        <div class="row">
            <div>
                <label>Budget amount</label>
                <input name="budget_amount" value="{{ budget_amount or '1000' }}" required>
            </div>
            <div>
                <label>From currency</label>
                <input name="budget_from_currency" value="{{ budget_from_currency or 'USD' }}" required>
            </div>
            <div>
                <label>To currency</label>
                <input name="budget_to_currency" value="{{ budget_to_currency or 'EUR' }}" required>
            </div>
        </div>
        <input type="submit" value="Plan my trip">
    </form>

    {% if results %}
    <div class="section">
        <h2>Current Weather</h2>
        <pre>{{ results.weather }}</pre>
    </div>
    <div class="section">
        <h2>Budget in Local Currency</h2>
        <pre>{{ results.budget }}</pre>
    </div>
    <div class="section">
        <h2>Things To Do</h2>
        <pre>{{ results.things_to_do }}</pre>
    </div>
    <div class="section">
        <h2>Saved Plan</h2>
        <pre>{{ results.saved_path }}</pre>
    </div>
    {% endif %}
</body>
</html>
"""


@app.route("/", methods=["GET", "POST"])
def home():
    destination = ""
    budget_amount = ""
    budget_from_currency = ""
    budget_to_currency = ""
    results = None

    if request.method == "POST":
        destination = request.form["destination"]
        budget_amount = request.form["budget_amount"]
        budget_from_currency = request.form["budget_from_currency"].upper()
        budget_to_currency = request.form["budget_to_currency"].upper()

        results = asyncio.run(
            plan_trip(destination, float(budget_amount), budget_from_currency, budget_to_currency)
        )

    return render_template_string(
        HTML,
        destination=destination,
        budget_amount=budget_amount,
        budget_from_currency=budget_from_currency,
        budget_to_currency=budget_to_currency,
        results=results,
    )


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
