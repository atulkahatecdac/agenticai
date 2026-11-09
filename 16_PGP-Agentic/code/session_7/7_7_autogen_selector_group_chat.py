# pip install autogen-agentchat autogen-ext python-dotenv

import asyncio
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from dotenv import load_dotenv

load_dotenv(override=True)

# Initialize model client
model_client = OpenAIChatCompletionClient(model="gpt-4o-mini")

# Define agents
coder = AssistantAgent(
    name="Coder",
    model_client=model_client,
    system_message="Write clean, well-documented Java code based on the user requirement."
)

tester = AssistantAgent(
    name="Tester",
    model_client=model_client,
    system_message="Write test cases to validate the coder's implementation."
)

reviewer = AssistantAgent(
    name="Reviewer",
    model_client=model_client,
    system_message="Review the code and test cases, suggest improvements or say APPROVED if all is good."
)

# --- Termination rule ---
termination_condition = MaxMessageTermination(10) | TextMentionTermination("APPROVED")

# Create dynamic team
team = SelectorGroupChat(
    participants=[coder, tester, reviewer],  
    model_client=model_client,
    termination_condition=termination_condition
    )

async def main():
    print("\n=== Starting Dynamic Team Discussion ===\n")

    # Stream each message from the team
    async for message in team.run_stream(task="Give me a Java SpringBoot code to create an API for a simple banking application."):
        # Handle both TextMessage and delta-style chunks
        if hasattr(message, "content"):
            sender = getattr(message, "sender", "Unknown")
            print(f"\n[{sender}]:\n{message.content}\n{'-' * 60}")

    print("\n=== Discussion Finished ===\n")

    await model_client.close()


if __name__ == "__main__":
    asyncio.run(main())
