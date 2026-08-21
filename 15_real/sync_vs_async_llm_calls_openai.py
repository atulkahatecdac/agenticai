# pip install openai python-dotenv
#
# Requires OPENAI_API_KEY set in the repo root .env

import os
import time
import asyncio
from dotenv import load_dotenv
from openai import OpenAI, AsyncOpenAI

load_dotenv(override=True)

# ============================================================
# Same idea shown two ways against the OpenAI API, using one
# single running example (the UK's Brexit referendum) split into
# three independent prompts:
#
# 1. SYNC  - each call_llm() blocks until OpenAI replies, so the
#    three prompts (mandate/sentiment/translate) run one after
#    another - total time is roughly the sum of all three.
# 2. ASYNC - each call_llm() is awaited concurrently via
#    asyncio.gather(), so OpenAI can process all three requests
#    around the same time - total time is roughly the slowest one,
#    not the sum.
#
# The only difference between the two clients below is
# OpenAI vs AsyncOpenAI.
# ============================================================

MODEL = "gpt-4o-mini"

PROMPTS = {
    "mandate": "In 2-3 sentences, explain the mandate British people gave in the "
               "2016 referendum on whether the UK should remain in or leave the "
               "European Union.",
    "sentiment": "Classify the overall sentiment (positive/negative/neutral) of "
                 "British public opinion toward the EU membership question, and "
                 "justify it in one sentence.",
    "translate": "In French, explain in 2-3 sentences the main factors that led "
                 "British people to vote to leave the EU.",
}


# ---- 1. Sync version ----
sync_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def call_llm_sync(prompt: str) -> str:
    response = sync_client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content or ""


def run_sync():
    print("=== SYNC (sequential) ===\n")
    start = time.time()

    for label, prompt in PROMPTS.items():
        t0 = time.time()
        result = call_llm_sync(prompt)
        print(f"[{label}] ({time.time() - t0:.2f}s)\n{result}\n")

    print(f"Total sync time: {time.time() - start:.2f} seconds\n")


# ---- 2. Async version ----
async_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))


async def call_llm_async(prompt: str) -> str:
    response = await async_client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content or ""


async def run_async():
    print("=== ASYNC (concurrent) ===\n")
    start = time.time()

    tasks = [call_llm_async(prompt) for prompt in PROMPTS.values()]
    results = await asyncio.gather(*tasks)

    for label, result in zip(PROMPTS.keys(), results):
        print(f"[{label}]\n{result}\n")

    print(f"Total async time: {time.time() - start:.2f} seconds\n")


if __name__ == "__main__":
    run_sync()
    asyncio.run(run_async())
