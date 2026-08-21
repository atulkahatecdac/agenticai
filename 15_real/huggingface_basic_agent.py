# pip install huggingface_hub python-dotenv
#
# Requires HUGGINGFACEHUB_API_TOKEN set in the repo root .env
# (create one at https://huggingface.co/settings/tokens)

from huggingface_hub import InferenceClient

from dotenv import load_dotenv
import os
load_dotenv(override=True)

client = InferenceClient(token=os.getenv("HUGGINGFACEHUB_API_TOKEN"))

response = client.chat_completion(
    model="Qwen/Qwen2.5-7B-Instruct",
    messages=[
        {"role": "system", "content": "You are a helpful assistant"},
        {"role": "user", "content": "Explain agentic AI in one paragraph"}
    ]
)

print(response.choices[0].message.content)
