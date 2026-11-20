import json
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()
client = Anthropic()

MODEL = "claude-sonnet-5-5"
SYSTEM = (
    "You are ShopAssist, an online store's support assistant. "
    "Returns are accepted within 30 days of delivery. "
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
            "properties": {
                "order_id": {
                    "type": "string",
                    "description": "The order ID, like ORD-12345678",
                }
            },
            "required": ["order_id"],
        },
    }
]


def lookup_order(order_id):
    return ORDERS.get(order_id, {"error": "order not found"})


messages = [{
    "role": "user",
    "content": "Can I still return the jacket "
               "from order ORD-12345678?",
}]

response = client.messages.create(
    model=MODEL,
    max_tokens=300,
    output_config={"effort": "low"},
    system=SYSTEM,
    tools=TOOLS,
    messages=messages,
)
print("stop_reason:", response.stop_reason)

for block in response.content:
    if block.type == "tool_use":
        print("Claude asks for:", block.name, block.input)
        # block.input is a JSON string, e.g. '{"order_id": "ORD-12345678"}'
        # ** converts it into order_id="ORD-12345678"
        result = lookup_order(**block.input)
        print("our code returns:", result)
        messages.append(
            {"role": "assistant", "content": response.content}
        )
        messages.append({"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": block.id,
             "content": json.dumps(result)}
        ]})

final = client.messages.create(
    model=MODEL,
    max_tokens=300,
    output_config={"effort": "low"},
    system=SYSTEM,
    tools=TOOLS,
    messages=messages,
)
print("stop_reason:", final.stop_reason)
for block in final.content:
    if block.type == "text":
        print(block.text)