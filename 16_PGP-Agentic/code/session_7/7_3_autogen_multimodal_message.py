import os
# pip install autogen-agentchat autogen-core autogen-ext python-dotenv pillow

import asyncio
from PIL import Image
from dotenv import load_dotenv
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.messages import MultiModalMessage, TextMessage
from autogen_core import Image as AGImage
from autogen_agentchat.agents import AssistantAgent

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

load_dotenv(override=True)

# Load image into Autogen's image type
img = AGImage(Image.open(os.path.join(BASE_DIR, "1911_Solvay_conference.jpg")))

# Define agents with OpenAI model clients
desc_agent = AssistantAgent("desc_agent", OpenAIChatCompletionClient(model="gpt-4o"))
context_agent = AssistantAgent("context_agent", OpenAIChatCompletionClient(model="gpt-4o"))

async def main():
    # Step 1: Ask for image description
    desc = await desc_agent.on_messages([
        MultiModalMessage(
            content=["Describe this historical photograph in detail. What kind of event does this appear to be?", img],
            source="User"
        )], cancellation_token=None
    )
    print("\nDESCRIPTION\n" + "=" * 50 + f"\n{desc.chat_message.content}")

    # Step 2: Ask for deeper historical context
    context = await context_agent.on_messages([
        MultiModalMessage(
            content=["Analyze the setting, time period, and context of this photograph.", img],
            source="User"
        ),
        TextMessage(
            content="If this is the 1911 Solvay Conference, list the attendees by row (front/back) "
                    "and describe their major contributions to physics.",
            source="User"
        )], cancellation_token=None
    )
    print("\nHISTORICAL CONTEXT\n" + "=" * 50 + f"\n{context.chat_message.content}")

    # Close agents cleanly
    await desc_agent.close()
    await context_agent.close()

if __name__ == "__main__":
    asyncio.run(main())
