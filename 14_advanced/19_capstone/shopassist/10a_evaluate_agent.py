import asyncio
import os
import sys
from dotenv import load_dotenv
from anthropic import Anthropic
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

load_dotenv()
client = Anthropic()

MODEL = "claude-sonnet-5-5"
SYSTEM = (
    "You are ShopAssist, an online store's support assistant. "
    "Returns are accepted within 30 days of delivery. "
    "Use the tools to look up orders and to start returns. "
    "Answer in one or two sentences."
)

SERVER = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "08a_mcp_server.py")
server_params = StdioServerParameters(command=sys.executable, args=[SERVER])

# 04a checked only the final answer. An agent can give a good answer and
# still do the wrong thing on the way, so here we check the tool calls.
# (question, tools that must be called, tools that must NOT be called)
CASES = [
    ("I want to return the jacket from order ORD-12345678.",
     {"lookup_order", "start_return"}, set()),
    ("I want to return the lamp from order ORD-87654321.",   # 45 days ago
     {"lookup_order"}, {"start_return"}),
    ("I want to return my jacket.",                          # no order ID
     set(), {"lookup_order", "start_return"}),
    ("Where is my order ORD-12345678?",                      # only a question
     {"lookup_order"}, {"start_return"}),
]


async def run_agent(session, tools, text):
    """The 08c loop. Returns the tools called, in order, and the reply."""
    messages = [{"role": "user", "content": text}]
    called = []
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
                called.append(block.name)
                output = await session.call_tool(block.name, block.input)
                results.append({"type": "tool_result",
                                "tool_use_id": block.id,
                                "content": output.content[0].text,
                                "is_error": output.isError})
        messages.append({"role": "user", "content": results})
    reply = ""
    for block in response.content:
        if block.type == "text":
            reply = block.text
    return called, reply


def check(called, must, must_not):
    if not must <= set(called):
        return f"missing {must - set(called)}"
    if must_not & set(called):
        return f"should not call {must_not & set(called)}"
    # Always look the order up before starting a return.
    if "start_return" in called and (
            "lookup_order" not in called
            or called.index("lookup_order") > called.index("start_return")):
        return "start_return before lookup_order"
    return ""


async def main():
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            mcp_tools = await session.list_tools()
            tools = [{"name": t.name,
                      "description": t.description,
                      "input_schema": t.inputSchema}
                     for t in mcp_tools.tools]

            score = 0
            for text, must, must_not in CASES:
                called, reply = await run_agent(session, tools, text)
                problem = check(called, must, must_not)
                score += not problem
                print("PASS" if not problem else "FAIL", "|", text[:45],
                      "|", called, "|", problem or reply[:40])
            print("score:", score, "/", len(CASES))


asyncio.run(main())
