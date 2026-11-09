# pip install autogen-agentchat autogen-ext python-dotenv requests

import asyncio
import os
import requests
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.ui import Console
from autogen_agentchat.messages import TextMessage
from autogen_ext.models.openai import OpenAIChatCompletionClient
from dotenv import load_dotenv

# Load API keys/config
load_dotenv(override=True)

# Initialize model client
model_client = OpenAIChatCompletionClient(model="gpt-4o-mini")

# Define forex tool that calls real API
async def get_forex_rate(target: str) -> float:
    """Get the live forex rate of USD against a target currency."""
    api_key = os.getenv("EXCHANGE_RATE_API_KEY")
    url = f"https://v6.exchangerate-api.com/v6/{api_key}/latest/USD"
    
    try:
        response = requests.get(url)
        data = response.json()
        
        if response.status_code == 200 and "conversion_rates" in data:
            rate = data["conversion_rates"].get(target.upper())
            if rate:
                return rate
            else:
                return f"Currency code '{target}' not found"
        else:
            return f"API Error: {data.get('error-type', 'Unknown error')}"
    except Exception as e:
        return f"Error fetching rate: {str(e)}"

# Create AssistantAgent
agent = AssistantAgent(
    name="forex_agent",
    model_client=model_client,
    tools=[get_forex_rate],
    system_message="You are a helpful forex assistant who provides live exchange rates and interesting facts!",
)

# Create text message
text_message = TextMessage(
    content="Hello! Can you tell me the USD to INR exchange rate today and an interesting or a historical fact about it or foreign exchange, in general?"
    "Please ensure that there is an interesting fact also in the output", 
    source="User"
)

# Run the agent
async def main() -> None:
    await Console(agent.run_stream(task=text_message.content))
    await model_client.close()

if __name__ == "__main__":
    asyncio.run(main())