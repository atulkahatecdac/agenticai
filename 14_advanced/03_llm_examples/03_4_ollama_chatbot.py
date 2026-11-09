import sys
from openai import OpenAI

sys.stdout.reconfigure(encoding="utf-8")  # model output can include characters outside Windows' cp1252 console codepage

client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama"
)

messages = []

print("Ollama chatbot - type 'exit' or 'quit' to stop.\n")

while True:
    user_input = input("You: ").strip()
    if user_input.lower() in ("exit", "quit"):
        break

    messages.append({"role": "user", "content": user_input})

    response = client.chat.completions.create(
        model="qwen3:8b",
        messages=messages
    )

    reply = response.choices[0].message.content
    messages.append({"role": "assistant", "content": reply})

    print(f"Bot: {reply}\n")
