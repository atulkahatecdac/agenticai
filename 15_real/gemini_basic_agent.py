# pip install google-generativeai python-dotenv
import google.generativeai as genai

from dotenv import load_dotenv
import os
load_dotenv(override=True)

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

model = genai.GenerativeModel(
    "gemini-2.5-flash",
    system_instruction="You are a helpful assistant",
)

response = model.generate_content("Explain agentic AI in one paragraph")

print(response.text)
