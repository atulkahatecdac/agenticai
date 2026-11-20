import json
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()
client = Anthropic()

MODEL = "claude-sonnet-5-5"
SYSTEM = (
    "You are ShopAssist, an online store's support assistant. "
    "Returns are accepted within 30 days of delivery. "
    "Use the tools to look up orders and to start returns. "
    "Answer in one or two sentences."
)

ORDERS = {
    "ORD-12345678": {
        "item": "jacket",
        "status": "delivered",
        "delivered_days_ago": 20,
    },
}

TOOLS = [
    {
        "name": "lookup_order",
        "description": "Look up an order by its ID. Returns the "
                       "item, the status and how many days ago "
                       "it was delivered.",
        "input_schema": {
            "type": "object",
            "properties": {"order_id": {"type": "string"}},
            "required": ["order_id"],
        },
    },
    {
        "name": "start_return",
        "description": "Start a return for a delivered order that "
                       "is inside the 30-day window. Returns the "
                       "return label number.",
        "input_schema": {
            "type": "object",
            "properties": {"order_id": {"type": "string"}},
            "required": ["order_id"],
        },
    },
]


def lookup_order(order_id):
    return ORDERS.get(order_id, {"error": "order not found"})


def start_return(order_id):
    return {"return_label": "RET-2048", "order_id": order_id}


TOOL_FUNCTIONS = {"lookup_order": lookup_order,
                  "start_return": start_return}

messages = [{"role": "user", "content":
             "I want to return the jacket from order ORD-12345678."}]

turn = 0
while True:
    turn += 1
    response = client.messages.create(
        model=MODEL,
        max_tokens=500,
        output_config={"effort": "low"},
        system=SYSTEM,
        tools=TOOLS,
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
            output = TOOL_FUNCTIONS[block.name](**block.input)
            results.append({"type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(output)})
    messages.append({"role": "user", "content": results})

for block in response.content:
    if block.type == "text":
        print(block.text)