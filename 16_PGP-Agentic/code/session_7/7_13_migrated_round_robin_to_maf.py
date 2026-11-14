# Migration example: 7_11_autogen_round_robin_group_chat.py rewritten for the
# Microsoft Agent Framework (MAF). Same two agents, same task, same stop rules.
#
#   AutoGen AgentChat                         Microsoft Agent Framework
#   AssistantAgent(name, model_client,        Agent(client, name=..., instructions=...)
#                  system_message=...)
#   RoundRobinGroupChat(participants)         GroupChatBuilder(participants, selection_func)
#   MaxMessageTermination(8)                  max_rounds=8
#   TextMentionTermination("APPROVED")        termination_condition=<plain function>
#   team.run_stream(task=...)                 workflow.run(task, stream=True)
#
# pip install agent-framework-core agent-framework-openai agent-framework-orchestrations python-dotenv
# Needs OPENAI_API_KEY in .env
# Each agent sees the previous agent's reply as an assistant message. Very small local
# models (e.g. llama3.2 via Ollama) may answer that with an empty reply; qwen3:8b handled it.

import asyncio

from agent_framework import Agent, AgentResponseUpdate, Message
from agent_framework.openai import OpenAIChatCompletionClient
from agent_framework.orchestrations import GroupChatBuilder, GroupChatState
from dotenv import load_dotenv

load_dotenv(override=True)

client = OpenAIChatCompletionClient(model="gpt-4o-mini")

writer = Agent(
    client,
    name="writer",
    instructions="You write short, polite letters to SecureBank customers (max 120 words). "
    "When you get feedback, rewrite the whole letter.",
)
compliance = Agent(
    client,
    name="compliance",
    # One extra sentence vs 7_11: in MAF the writer's turns arrive as assistant
    # messages, so tell the reviewer explicitly whose text it is checking.
    instructions="You are SecureBank's compliance officer reviewing the latest letter written by 'writer'. "
    "It must state the reason, mention the customer's right to ask for their credit report, and make no "
    "promises. Give brief feedback, or reply APPROVED if it meets all three rules.",
)


def round_robin(state: GroupChatState) -> str:
    """Replaces RoundRobinGroupChat: pick speakers in a fixed order."""
    names = list(state.participants)
    return names[state.current_round % len(names)]


def compliance_approved(conversation: list[Message]) -> bool:
    """Replaces TextMentionTermination('APPROVED')."""
    last = conversation[-1] if conversation else None
    return bool(last and last.author_name == "compliance" and "APPROVED" in (last.text or "").upper())


workflow = GroupChatBuilder(
    participants=[writer, compliance],
    selection_func=round_robin,
    termination_condition=compliance_approved,
    max_rounds=8,  # replaces MaxMessageTermination(8)
    intermediate_output_from=[writer, compliance],  # stream each agent's turn
).build()

TASK = "Write to customer CUST-77: their personal loan application was rejected because their debt-to-income ratio is too high."


async def main():
    last_author = None
    stream = workflow.run(TASK, stream=True)
    async for event in stream:  # replaces team.run_stream(...)
        if event.type == "intermediate" and isinstance(event.data, AgentResponseUpdate):
            author = event.data.author_name
            if author and author != last_author:
                print(f"\n\n[{author.upper()}]")
                last_author = author
            print(event.data.text, end="", flush=True)
    print()


if __name__ == "__main__":
    asyncio.run(main())
