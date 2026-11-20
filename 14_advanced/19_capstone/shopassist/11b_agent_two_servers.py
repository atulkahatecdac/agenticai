import asyncio
import os
import sys
from contextlib import AsyncExitStack
from dotenv import load_dotenv
from anthropic import Anthropic
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

load_dotenv()
client = Anthropic()

MODEL = "claude-sonnet-5-5"
# The policy rules are no longer written in the prompt:
# Claude finds them with the search_policy tool.
SYSTEM = (
    "You are ShopAssist, an online store's support assistant. "
    "Use search_policy for any question about store rules, and "
    "lookup_order / start_return for a customer's order. "
    "Answer in one or two sentences."
)

HERE = os.path.dirname(os.path.abspath(__file__))
SERVERS = {
    "orders": os.path.join(HERE, "08a_mcp_server.py"),
    "policies": os.path.join(HERE, "11a_policy_server.py"),
}


async def ask(sessions, tools, tool_owner, text):
    """The 08c loop. tool_owner says which server runs each tool."""
    print("\nCustomer:", text)
    messages = [{"role": "user", "content": text}]
    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=1000,
            output_config={"effort": "low"},
            system=SYSTEM,
            tools=tools,
            messages=messages,
        )
        if response.stop_reason != "tool_use":
            break
        messages.append({"role": "assistant", "content": response.content})
        results = []
        for block in response.content:
            if block.type == "tool_use":
                server = tool_owner[block.name]
                print(f"  run {block.name}({block.input}) on the '{server}' server")
                output = await sessions[server].call_tool(block.name, block.input)
                results.append({"type": "tool_result",
                                "tool_use_id": block.id,
                                "content": output.content[0].text,
                                "is_error": output.isError})
        messages.append({"role": "user", "content": results})
    for block in response.content:
        if block.type == "text":
            print("ShopAssist:", block.text)


async def connect(stack, name, path, sessions, tools, tool_owner):
    """Start one MCP server and add its tools to the shared list."""
    params = StdioServerParameters(command=sys.executable, args=[path])
    read, write = await stack.enter_async_context(stdio_client(params))
    session = await stack.enter_async_context(ClientSession(read, write))
    await session.initialize()
    sessions[name] = session
    for t in (await session.list_tools()).tools:
        tools.append({"name": t.name, "description": t.description,
                      "input_schema": t.inputSchema})
        tool_owner[t.name] = name


async def main():
    # AsyncExitStack keeps both connections open until the end of the block.
    async with AsyncExitStack() as stack:
        sessions, tools, tool_owner = {}, [], {}
        for name, path in SERVERS.items():
            await connect(stack, name, path, sessions, tools, tool_owner)
        print("tools:", tool_owner)

        await ask(sessions, tools, tool_owner,
                  "Can I return a pair of socks?")
        await ask(sessions, tools, tool_owner,
                  "How long does a UPI refund take?")
        await ask(sessions, tools, tool_owner,
                  "Can I return the jacket from order ORD-12345678?")


asyncio.run(main())
