# pip install autogen-agentchat autogen-ext python-dotenv requests

import asyncio
import os
import requests
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient
from dotenv import load_dotenv

load_dotenv(override=True)

async def get_forex_rate(target: str) -> float:
    """Fetch live forex rate of USD against target currency."""
    url = f"https://v6.exchangerate-api.com/v6/{os.getenv('EXCHANGE_RATE_API_KEY')}/latest/USD"
    return requests.get(url).json()["conversion_rates"][target.upper()]

agent = AssistantAgent(
    name="forex_agent",
    model_client=OpenAIChatCompletionClient(model="gpt-4o-mini"),
    tools=[get_forex_rate],
)

async def main():
    await Console(agent.run_stream(task="What is the current forex rate of USD to INR?"))

if __name__ == "__main__":
    asyncio.run(main())