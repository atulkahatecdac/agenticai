# pip install flask mcp python-dotenv
#
# Step 2 of the auth progression: version_1 exposed the MCP server over HTTP
# with no protection at all. Here we add the basic mechanics that every real
# OAuth2 setup builds on - the client must send "Authorization: Bearer <token>",
# and we reject the request with 401 + a "WWW-Authenticate" challenge header
# if it's missing or wrong. The token itself is just a static shared secret
# from .env for now (no Scalekit/authorization server yet) - that comes next.
#
# NOTE for `mcp dev` / MCP Inspector: this file is NOT an MCP transport, it's a
# plain REST wrapper (a "/search?query=" endpoint) around a stdio MCP client
# call. Pointing `mcp dev` at tavily_mcp_server.py talks stdio directly to the
# server and never touches this file or its auth check - that's expected, not
# a bug. Real MCP-over-HTTP uses a streamable-http/SSE transport that speaks
# JSON-RPC, and a client like Inspector can be pointed at that directly and
# get challenged for a token. To exercise the auth here, call this Flask
# endpoint directly (curl/Postman/browser), not through Inspector.
import os
from functools import wraps
from dotenv import load_dotenv
from flask import Flask, request, jsonify
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

load_dotenv(override=True)

app = Flask(__name__)

SERVER_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tavily_mcp_server.py")
ACCESS_TOKEN = os.getenv("MCP_ACCESS_TOKEN")
REALM = "tavily-mcp"

def require_bearer_token(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")

        if not auth_header.startswith("Bearer "):
            response = jsonify({"error": "invalid_request", "error_description": "Missing bearer token"})
            response.status_code = 401
            response.headers["WWW-Authenticate"] = f'Bearer realm="{REALM}"'
            return response

        token = auth_header.removeprefix("Bearer ").strip()
        if token != ACCESS_TOKEN:
            response = jsonify({"error": "invalid_token", "error_description": "Bearer token is invalid"})
            response.status_code = 401
            response.headers["WWW-Authenticate"] = f'Bearer realm="{REALM}", error="invalid_token"'
            return response

        return view(*args, **kwargs)
    return wrapper

async def call_tavily_search(query: str) -> str:
    server_params = StdioServerParameters(command="python", args=[SERVER_SCRIPT])

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("tavily_search", {"query": query})
            return result.content[0].text

@app.route("/search", methods=["GET"])
@require_bearer_token
def search():
    query = request.args.get("query")
    if not query:
        return jsonify({"error": "query parameter is required"}), 400

    result = asyncio.run(call_tavily_search(query))
    return jsonify({"query": query, "result": result})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True, use_reloader=False)
