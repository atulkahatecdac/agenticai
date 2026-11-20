import asyncio
import json
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
    "If the customer is upset, asks for a person, or the problem "
    "needs a decision you cannot make, use escalate_to_human. "
    "Answer in one or two sentences."
)

# Same as 08c (now with the SQLite server), plus one LOCAL tool that is
# not on the MCP server: escalate_to_human. A tool list can mix both.
HERE = os.path.dirname(os.path.abspath(__file__))
SERVER = os.path.join(HERE, "12a_mcp_server_sqlite.py")
server_params = StdioServerParameters(command=sys.executable, args=[SERVER])

ESCALATE_TOOL = {
    "name": "escalate_to_human",
    "description": "Hand the conversation to a human support agent. "
                   "Use when the customer asks for a person, is upset, "
                   "or needs an exception to the policy. Returns a "
                   "ticket number to give to the customer.",
    "input_schema": {
        "type": "object",
        "properties": {
            "reason": {"type": "string",
                       "description": "One sentence: why a human is needed"},
            "order_id": {"type": "string"},
        },
        "required": ["reason"],
    },
}


def escalate_to_human(reason, order_id=""):
    """Save a ticket for the human team (here: a line in a file)."""
    os.makedirs(os.path.join(HERE, ".trace"), exist_ok=True)
    with open(os.path.join(HERE, ".trace", "escalations.jsonl"), "a") as f:
        f.write(json.dumps({"reason": reason, "order_id": order_id}) + "\n")
    return {"ticket": "TCK-501", "message": "A person will reply within 24 hours."}


async def main():
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # 1. Ask the server for its tools and convert them to
            #    Claude's format (inputSchema -> input_schema).
            mcp_tools = await session.list_tools()
            tools = [{"name": t.name,
                      "description": t.description,
                      "input_schema": t.inputSchema}
                     for t in mcp_tools.tools]
            tools.append(ESCALATE_TOOL)                  # new: local tool
            print("tools (MCP + local):", [t["name"] for t in tools])

            messages = [{"role": "user", "content":
                         "My lamp from ORD-87654321 broke on the first day and you "
                         "say I can't return it? This is ridiculous, I want to "
                         "talk to a manager."}]

            # 2. The agentic loop from 07a.
            turn = 0
            while True:
                turn += 1
                response = client.messages.create(
                    model=MODEL,
                    max_tokens=1000,
                    output_config={"effort": "low"},
                    system=SYSTEM,
                    tools=tools,
                    messages=messages,
                )
                print(f"turn {turn}: stop_reason = {response.stop_reason}")
                if response.stop_reason != "tool_use":
                    break
                messages.append({"role": "assistant", "content": response.content})
                results = []
                for block in response.content:
                    if block.type == "tool_use":
                        print(f"  run {block.name}({block.input})")
                        # 3. New: a local tool runs here, the rest on the MCP server.
                        if block.name == "escalate_to_human":
                            output = escalate_to_human(**block.input)
                            results.append({"type": "tool_result",
                                            "tool_use_id": block.id,
                                            "content": json.dumps(output)})
                            continue
                        output = await session.call_tool(block.name, block.input)
                        results.append({"type": "tool_result",
                                        "tool_use_id": block.id,
                                        "content": output.content[0].text,
                                        "is_error": output.isError})
                messages.append({"role": "user", "content": results})

            for block in response.content:
                if block.type == "text":
                    print(block.text)


asyncio.run(main())
