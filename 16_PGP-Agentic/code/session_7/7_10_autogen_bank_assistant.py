# AutoGen AgentChat - the same SecureBank assistant as 7_1_maf_bank_assistant.py.
# Compare the two files line by line: AssistantAgent + model_client vs Agent + client.
#
# pip install autogen-agentchat autogen-ext[openai] python-dotenv requests
# Needs OPENAI_API_KEY and EXCHANGE_RATE_API_KEY in .env

import asyncio
import os

import requests
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient
from dotenv import load_dotenv

load_dotenv(override=True)

ACCOUNTS = {
    "ACC-1001": {"owner": "Priya Sharma", "balance": 125000.00},
    "ACC-1002": {"owner": "Rahul Verma", "balance": 8400.50},
}


async def get_balance(account_id: str) -> str:
    """Return the owner and current balance (INR) of a SecureBank account, e.g. ACC-1001."""
    account = ACCOUNTS.get(account_id.upper())
    if account is None:
        return f"No account {account_id}."
    return f"{account['owner']}: INR {account['balance']:,.2f}"


async def get_forex_rate(target: str) -> float:
    """Return how many units of the target currency (e.g. USD) one Indian rupee (INR) buys today."""
    url = f"https://v6.exchangerate-api.com/v6/{os.getenv('EXCHANGE_RATE_API_KEY')}/latest/INR"
    return requests.get(url, timeout=10).json()["conversion_rates"][target.upper()]


model_client = OpenAIChatCompletionClient(model="gpt-4o-mini")

agent = AssistantAgent(
    name="bank_assistant",
    model_client=model_client,
    system_message="You are SecureBank's assistant. Use the tools for balances and live exchange rates. "
    "Be brief and show amounts with their currency.",
    tools=[get_balance, get_forex_rate],
    reflect_on_tool_use=True,  # turn raw tool output into a sentence for the customer
)


async def main():
    await Console(agent.run_stream(task="How much is the balance of ACC-1001 worth in US dollars?"))
    await model_client.close()


if __name__ == "__main__":
    asyncio.run(main())
