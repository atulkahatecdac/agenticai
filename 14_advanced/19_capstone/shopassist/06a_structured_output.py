import json
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()
client = Anthropic()

MODEL = "claude-sonnet-5-5"

SCHEMA = {
    "type": "object",
    "properties": {
        "order_id": {"type": "string"},
        "item": {"type": "string"},
        "reason": {
            "type": "string",
            "enum": ["too_small", "too_big", "damaged", "other"],
        },
    },
    "required": ["order_id", "item", "reason"],
    "additionalProperties": False,
}


def extract(email):
    response = client.messages.create(
        model=MODEL,
        max_tokens=300,
        output_config={
            "effort": "low",
            "format": {"type": "json_schema", "schema": SCHEMA},
        },
        messages=[{
            "role": "user",
            "content": "Extract the return request from this "
                       "customer email.\n\n" + email,
        }],
    )
    for block in response.content:
        if block.type == "text":
            return json.loads(block.text)


EMAILS = [
    "Hi, I want to return the blue jacket from order "
    "ORD-12345678. It arrived last week but it is too small. Alex",
    "Hello, the shoes I got are damaged. Please tell me how "
    "to send them back. Thanks, Sam",
]

for email in EMAILS:
    data = extract(email)
    print(data)