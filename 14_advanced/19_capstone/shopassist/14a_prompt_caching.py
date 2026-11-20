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
# Claude Sonnet 5.5 prices, US$ per million tokens.
PRICE = {"input": 2.00, "cache_write": 2.50, "cache_read": 0.10, "output": 10.00}

HERE = os.path.dirname(os.path.abspath(__file__))
SERVER = os.path.join(HERE, "12a_mcp_server_sqlite.py")
server_params = StdioServerParameters(command=sys.executable, args=[SERVER])

# The full policy text goes into the system prompt. It is the same for
# every request, which makes it a good thing to cache. (Caching needs a
# prefix of at least 512 tokens on this model, so a short prompt alone
# would not be cached.)
POLICIES = ""
for name in sorted(os.listdir(os.path.join(HERE, "policies"))):
    with open(os.path.join(HERE, "policies", name), encoding="utf-8") as f:
        POLICIES += f.read() + "\n"

SYSTEM = (
    "You are ShopAssist, an online store's support assistant. "
    "Use the tools to look up orders and to start returns. "
    "Answer in one or two sentences, using these store policies:\n\n"
    + POLICIES
)


def cost(usage):
    """Print the token counts of one call and what it cost."""
    dollars = (usage.input_tokens * PRICE["input"]
               + usage.cache_creation_input_tokens * PRICE["cache_write"]
               + usage.cache_read_input_tokens * PRICE["cache_read"]
               + usage.output_tokens * PRICE["output"]) / 1_000_000
    print(f"    input {usage.input_tokens}, cache write "
          f"{usage.cache_creation_input_tokens}, cache read "
          f"{usage.cache_read_input_tokens}, output {usage.output_tokens}"
          f"  -> ${dollars:.5f}")
    return dollars


async def ask(session, tools, text):
    print("\nCustomer:", text)
    messages = [{"role": "user", "content": text}]
    total = 0
    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=1000,
            output_config={"effort": "low"},
            # New, two cache points (cached tokens cost ~5% of the input price):
            # 1. the end of the conversation: reused by the next call in this
            #    loop (after a tool call), when only the tool result is new
            cache_control={"type": "ephemeral"},
            # 2. the end of tools + system: the same for every question,
            #    so even a brand-new question reuses it
            system=[{"type": "text", "text": SYSTEM,
                     "cache_control": {"type": "ephemeral"}}],
            tools=tools,
            messages=messages,
        )
        total += cost(response.usage)
        if response.stop_reason != "tool_use":
            break
        messages.append({"role": "assistant", "content": response.content})
        results = []
        for block in response.content:
            if block.type == "tool_use":
                print(f"  run {block.name}({block.input})")
                output = await session.call_tool(block.name, block.input)
                results.append({"type": "tool_result",
                                "tool_use_id": block.id,
                                "content": output.content[0].text,
                                "is_error": output.isError})
        messages.append({"role": "user", "content": results})
    for block in response.content:
        if block.type == "text":
            print("ShopAssist:", block.text)
    print(f"  question cost: ${total:.5f}")


async def main():
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = [{"name": t.name, "description": t.description,
                      "input_schema": t.inputSchema}
                     for t in (await session.list_tools()).tools]

            # The first call writes the cache; the calls after it read it.
            await ask(session, tools, "Can I return a pair of socks?")
            await ask(session, tools, "Where is my order ORD-87654321?")
            await ask(session, tools, "How long does a UPI refund take?")


asyncio.run(main())
