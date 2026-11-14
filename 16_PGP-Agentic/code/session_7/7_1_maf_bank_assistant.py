# Microsoft Agent Framework (MAF) - SecureBank assistant: an agent with tools.
# MAF is the successor to AutoGen and Semantic Kernel. One Agent class wraps any
# chat client; plain Python functions become tools with @tool.
#
# pip install agent-framework-core agent-framework-openai python-dotenv requests
# Needs OPENAI_API_KEY and EXCHANGE_RATE_API_KEY (free key at exchangerate-api.com) in .env

import asyncio
import os
from typing import Annotated

import requests
from agent_framework import Agent, tool
from agent_framework.openai import OpenAIChatCompletionClient
from dotenv import load_dotenv

load_dotenv(override=True)

# Mock core-banking data (a real bank would call its account service here)
ACCOUNTS = {
    "ACC-1001": {"owner": "Priya Sharma", "balance": 125000.00},
    "ACC-1002": {"owner": "Rahul Verma", "balance": 8400.50},
}


@tool
def get_balance(account_id: Annotated[str, "SecureBank account id, e.g. ACC-1001"]) -> str:
    """Return the owner and current balance (INR) of a SecureBank account."""
    account = ACCOUNTS.get(account_id.upper())
    print(f"  [tool] get_balance({account_id})")
    if account is None:
        return f"No account {account_id}."
    return f"{account['owner']}: INR {account['balance']:,.2f}"


@tool
def get_forex_rate(target: Annotated[str, "ISO currency code, e.g. USD or EUR"]) -> float:
    """Return how many units of the target currency one Indian rupee (INR) buys today."""
    url = f"https://v6.exchangerate-api.com/v6/{os.getenv('EXCHANGE_RATE_API_KEY')}/latest/INR"
    rate = requests.get(url, timeout=10).json()["conversion_rates"][target.upper()]
    print(f"  [tool] get_forex_rate({target}) -> {rate}")
    return rate


agent = Agent(
    OpenAIChatCompletionClient(model="gpt-4o-mini"),
    name="bank_assistant",
    instructions="You are SecureBank's assistant. Use the tools for balances and live exchange rates. "
    "Be brief and show amounts with their currency.",
    tools=[get_balance, get_forex_rate],
)


async def main():
    # 1. One call, full answer - the agent decides which tools to call
    result = await agent.run("What is the balance of ACC-1001?")
    print("ANSWER:", result.text)

    # 2. Same agent, streamed; two tools in one question
    print("\nSTREAM: ", end="")
    stream = agent.run("How much is the balance of ACC-1001 worth in US dollars?", stream=True)
    async for update in stream:
        print(update.text, end="", flush=True)
    print()


if __name__ == "__main__":
    asyncio.run(main())
