# pip install flask mcp
# Exposes the Tavily MCP server (tavily_mcp_server.py) over HTTP on port 10000.
# The Flask app spins up the MCP server as a stdio subprocess and forwards each
# request to it as an MCP tool call.
import os
import asyncio
from flask import Flask, request, jsonify
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

app = Flask(__name__)

SERVER_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tavily_mcp_server.py")

async def call_tavily_search(query: str) -> str:
    server_params = StdioServerParameters(command="python", args=[SERVER_SCRIPT])

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("tavily_search", {"query": query})
            return result.content[0].text

@app.route("/search", methods=["GET"])
def search():
    query = request.args.get("query")
    if not query:
        return jsonify({"error": "query parameter is required"}), 400

    result = asyncio.run(call_tavily_search(query))
    return jsonify({"query": query, "result": result})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True, use_reloader=False)
