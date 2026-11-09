from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI()

response = client.responses.create(
    model="gpt-4o-mini",
    instructions="You are a person who understands AI very well.",
    input="Explain Artificial Intelligence.",
    temperature=0.9
)

print(response.output_text)
