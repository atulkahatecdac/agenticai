# AutoGen AgentChat - SecureBank: a round-robin team.
# A writer drafts a loan-rejection letter; a compliance officer reviews it.
# They take turns until compliance says APPROVED (or 8 messages pass).
# Migrated to the Microsoft Agent Framework in 7_13_migrated_round_robin_to_maf.py.
#
# pip install autogen-agentchat autogen-ext[openai] python-dotenv
# Needs OPENAI_API_KEY in .env

import asyncio

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_agentchat.messages import TextMessage
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_ext.models.openai import OpenAIChatCompletionClient
from dotenv import load_dotenv

load_dotenv(override=True)

model_client = OpenAIChatCompletionClient(model="gpt-4o-mini")

writer = AssistantAgent(
    name="writer",
    model_client=model_client,
    system_message="You write short, polite letters to SecureBank customers (max 120 words). "
    "When you get feedback, rewrite the whole letter.",
)
compliance = AssistantAgent(
    name="compliance",
    model_client=model_client,
    system_message="You are SecureBank's compliance officer. Check the latest letter: it must state the reason, "
    "mention the customer's right to ask for their credit report, and make no promises. "
    "Give brief feedback, or reply APPROVED if it meets all three rules.",
)

team = RoundRobinGroupChat(
    participants=[writer, compliance],
    termination_condition=MaxMessageTermination(8) | TextMentionTermination("APPROVED"),
)

TASK = "Write to customer CUST-77: their personal loan application was rejected because their debt-to-income ratio is too high."


async def main():
    async for message in team.run_stream(task=TASK):
        if isinstance(message, TextMessage) and message.source != "user":
            print(f"\n[{message.source.upper()}]\n{message.content}")
    await model_client.close()


if __name__ == "__main__":
    asyncio.run(main())
