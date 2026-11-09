from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

client = Anthropic()

response = client.messages.create(
    model="claude-haiku-4-5-20251001",
    max_tokens=200,
    messages=[
        {
            "role": "user",
            "content": "Explain Artificial Intelligence."
        }
    ]
)

print(response.content[0].text)
