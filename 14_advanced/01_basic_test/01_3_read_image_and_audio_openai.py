# Read the same text in three languages (Hindi, French, Japanese) twice
# with LangChain and OpenAI:
#   1. from an image  (multilingual_text.png)  - gpt-4o
#   2. from audio     (hindi/french/japanese.mp3) - gpt-audio-mini
#
# Needs OPENAI_API_KEY in the repo's .env.
# The image and the three MP3 files sit next to this script.

import os
import sys
import base64
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

load_dotenv(override=True)
sys.stdout.reconfigure(encoding="utf-8")  # Hindi/Japanese in the Windows console

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def to_base64(file_name):
    with open(os.path.join(BASE_DIR, file_name), "rb") as f:
        return base64.b64encode(f.read()).decode()


# ---- 1. Text from an image ----
vision_llm = ChatOpenAI(model="gpt-4o")
image_b64 = to_base64("multilingual_text.png")

image_message = HumanMessage(content=[
    {"type": "text", "text": "This image has the same text in three languages. "
                             "Write out each one exactly as written, naming the language, "
                             "then give one English translation."},
    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}},
])

print("=== IMAGE ===\n")
print(vision_llm.invoke([image_message]).content)


# ---- 2. The same text from audio ----
audio_llm = ChatOpenAI(model="gpt-audio-mini")

print("\n=== AUDIO ===")
for file_name in ["hindi.mp3", "french.mp3", "japanese.mp3"]:
    audio_message = HumanMessage(content=[
        {"type": "text", "text": "Write out exactly what is said in this audio, in its original "
                                 "language and script, then give an English translation."},
        {"type": "input_audio", "input_audio": {"data": to_base64(file_name), "format": "mp3"}},
    ])
    print(f"\n[{file_name}]")
    print(audio_llm.invoke([audio_message]).content)
