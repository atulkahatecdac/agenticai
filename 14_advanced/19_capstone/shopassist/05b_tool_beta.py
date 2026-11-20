from anthropic import Anthropic, beta_tool
from dotenv import load_dotenv

load_dotenv()
client = Anthropic()

MODEL = "claude-sonnet-5-5"

ORDERS = {
    "ORD-12345678": {
        "item": "jacket",
        "status": "delivered",
        "delivered_days_ago": 20,
    }
}

@beta_tool
def lookup_order(order_id: str) -> str:
    """Look up an order by its ID.

    Args:
        order_id: The order ID, like ORD-12345678
    """
    import json
    return json.dumps(
        ORDERS.get(order_id, {"error": "order not found"})
    )

SYSTEM = (
    "You are ShopAssist, an online store's support assistant. "
    "Returns are accepted within 30 days of delivery. "
    "Answer in one or two sentences."
)

runner = client.beta.messages.tool_runner(
    model=MODEL,
    max_tokens=300,
    output_config={"effort": "low"},
    system=SYSTEM,
    tools=[lookup_order],
    messages=[
        {
            "role": "user",
            "content": "Can I still return the jacket from order ORD-12345678?"
        }
    ]
)

final = runner.until_done()

for block in final.content:
    if block.type == "text":
        print(block.text)