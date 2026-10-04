# pip install openai-agents
import asyncio
import sys

from agents import Agent, Runner

from common import MODEL

sys.stdout.reconfigure(encoding="utf-8")

# =====================================================================
# STEP 2: the problem. A plain LLM chatbot - no tools, no documents.
#
# The model has never seen this customer's policy. It can only:
#   - say it does not know (the good case), or
#   - invent a believable number like "Rs. 5 lakh" (the dangerous case).
# Either way it cannot answer the question in the diagram.
# Every later step fixes this by giving the agent a way to LOOK THINGS UP.
#
# Run it:
#   python 2_plain_chatbot.py
#   python 2_plain_chatbot.py "your own question"
# =====================================================================

agent = Agent(
    name="Insurance Assistant (no tools)",
    model=MODEL,
    instructions="You are a helpful customer-service assistant for SecureLife health insurance. "
                 "Answer the customer's question.",
)

QUESTIONS = [
    "What is the coverage amount in my health insurance policy?",
    "Is my policy active, and until when?",
    "Is maternity covered in my plan?",
]


async def main() -> None:
    questions = [" ".join(sys.argv[1:])] if len(sys.argv) > 1 else QUESTIONS
    for q in questions:
        result = await Runner.run(agent, q)
        print(f"CUSTOMER : {q}\nASSISTANT: {result.final_output}\n")
    print("-> No tools, no data: the answer is a guess or a polite 'I don't know'.")
    print("   Step 3 gives the agent its first tool.")


if __name__ == "__main__":
    asyncio.run(main())
