# Sync vs async LLM calls with LangChain and Google Gemini.
#
# Needs GOOGLE_API_KEY in the repo's .env.
#
# SYNC  - llm.invoke() waits for each answer, so the three prompts run
#         one after another: total time = the sum of all three.
# ASYNC - llm.ainvoke() + asyncio.gather() sends all three together:
#         total time = roughly the slowest one.

import time
import asyncio
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv(override=True)

llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite")

PROMPTS = [
    "In 2 sentences, what is agentic AI?",
    "In 2 sentences, what is RAG (retrieval-augmented generation)?",
    "In 2 sentences, what is MCP (Model Context Protocol)?",
    "In 2 sentences, what are guardrails in an LLM application?",
    "In 2 sentences, what is an LLM hallucination?",
]


def run_sync():
    start = time.time()
    for prompt in PROMPTS:
        print(llm.invoke(prompt).content, "\n")
    print(f"Sync total: {time.time() - start:.1f} s\n")


async def run_async():
    start = time.time()
    results = await asyncio.gather(*(llm.ainvoke(p) for p in PROMPTS))
    for r in results:
        print(r.content, "\n")
    print(f"Async total: {time.time() - start:.1f} s")


if __name__ == "__main__":
    run_sync()
    asyncio.run(run_async())
