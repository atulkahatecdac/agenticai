# Microsoft Agent Framework (MAF) - SecureBank: multi-turn sessions and structured output.
# An Agent is stateless; conversation history lives in an AgentSession you pass in.
# response_format=<Pydantic model> makes the reply come back as a typed object -
# here, free-text customer complaints become support tickets.
#
# pip install agent-framework-core agent-framework-openai python-dotenv
# Needs OPENAI_API_KEY in .env

import asyncio
from typing import Literal

from agent_framework import Agent
from agent_framework.openai import OpenAIChatCompletionClient
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv(override=True)

agent = Agent(
    OpenAIChatCompletionClient(model="gpt-4o-mini"),
    name="bank_assistant",
    instructions="You are SecureBank's assistant. Be concise and polite.",
)


class SupportTicket(BaseModel):
    category: Literal["cards", "loans", "fraud", "accounts", "other"]
    urgency: Literal["low", "medium", "high"]
    account_id: str | None
    summary: str


COMPLAINTS = [
    "My debit card was swallowed by the ATM at MG Road this morning. Account ACC-1001.",
    "I see two transactions I never made on ACC-1002 - someone is using my card in Dubai!",
    "What is the interest rate on your home loans for salaried customers?",
]


async def main():
    # --- Part 1: sessions = memory across turns ---
    print("=== Without a session: every run starts from scratch ===")
    await agent.run("Hi, I'm Priya. My account is ACC-1001 and I prefer short answers.")
    print((await agent.run("Which account did I mention?")).text)

    print("\n=== With a session: the agent remembers ===")
    session = agent.create_session()
    await agent.run("Hi, I'm Priya. My account is ACC-1001 and I prefer short answers.", session=session)
    print((await agent.run("Which account did I mention, and what is my name?", session=session)).text)

    # --- Part 2: structured output ---
    print("\n=== Structured output: complaint -> SupportTicket ===")
    for text in COMPLAINTS:
        result = await agent.run(f"Create a support ticket for:\n{text}", options={"response_format": SupportTicket})
        ticket: SupportTicket = result.value
        print(f"{ticket.category:8} | {ticket.urgency:6} | {str(ticket.account_id):8} | {ticket.summary}")


if __name__ == "__main__":
    asyncio.run(main())
