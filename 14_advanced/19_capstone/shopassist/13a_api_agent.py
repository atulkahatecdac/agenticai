import os
import sys
from contextlib import AsyncExitStack, asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from anthropic import AsyncAnthropic
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from pydantic import BaseModel

# 03a's web app + 11b's agent: the browser talks to FastAPI, FastAPI runs
# the agentic loop, and the tools come from two MCP servers.
# Run:  uvicorn 13a_api_agent:app --port 8000   then open http://localhost:8000

load_dotenv()
client = AsyncAnthropic()          # async client, so one slow call doesn't block the server

MODEL = "claude-sonnet-5-5"
SYSTEM = (
    "You are ShopAssist, an online store's support assistant. "
    "Use search_policy for any question about store rules, and "
    "lookup_order / start_return for a customer's order. "
    "Answer in one or two sentences."
)

HERE = os.path.dirname(os.path.abspath(__file__))
SERVERS = {
    "orders": os.path.join(HERE, "12a_mcp_server_sqlite.py"),
    "policies": os.path.join(HERE, "11a_policy_server.py"),
}

sessions, tools, tool_owner = {}, [], {}
histories = {}                     # one conversation per session_id


@asynccontextmanager
async def lifespan(app):
    """Start both MCP servers once, when the web server starts."""
    async with AsyncExitStack() as stack:
        for name, path in SERVERS.items():
            params = StdioServerParameters(command=sys.executable, args=[path])
            read, write = await stack.enter_async_context(stdio_client(params))
            session = await stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
            sessions[name] = session
            for t in (await session.list_tools()).tools:
                tools.append({"name": t.name, "description": t.description,
                              "input_schema": t.inputSchema})
                tool_owner[t.name] = name
        yield                      # the web server runs here


app = FastAPI(lifespan=lifespan)


class ChatIn(BaseModel):
    text: str
    session_id: str = "default"    # the browser can send its own ID


@app.post("/chat")
async def chat(body: ChatIn):
    history = histories.setdefault(body.session_id, [])
    history.append({"role": "user", "content": body.text})
    input_tokens = 0
    while True:                    # the agentic loop from 08c
        response = await client.messages.create(
            model=MODEL,
            max_tokens=1000,
            output_config={"effort": "low"},
            system=SYSTEM,
            tools=tools,
            messages=history,
        )
        input_tokens += response.usage.input_tokens
        history.append({"role": "assistant", "content": response.content})
        if response.stop_reason != "tool_use":
            break
        results = []
        for block in response.content:
            if block.type == "tool_use":
                output = await sessions[tool_owner[block.name]].call_tool(
                    block.name, block.input)
                results.append({"type": "tool_result",
                                "tool_use_id": block.id,
                                "content": output.content[0].text,
                                "is_error": output.isError})
        history.append({"role": "user", "content": results})

    reply = ""
    for block in response.content:
        if block.type == "text":
            reply = block.text
    return {"reply": reply, "input_tokens": input_tokens}


# Same frontend as 03a.
app.mount("/", StaticFiles(directory=Path(HERE) / "static", html=True))
