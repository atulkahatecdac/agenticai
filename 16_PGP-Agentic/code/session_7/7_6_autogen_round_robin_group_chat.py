# pip install autogen-agentchat autogen-ext python-dotenv

import asyncio
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.messages import TextMessage
from dotenv import load_dotenv

# --- Environment setup ---
load_dotenv(override=True)

# --- Model client ---
model_client = OpenAIChatCompletionClient(model="gpt-4o-mini")

# --- Agents ---
primary_agent = AssistantAgent(
    name="primary",
    model_client=model_client,
    system_message="You are a helpful AI assistant. Write clear, concise, and factual responses.",
)

critic_agent = AssistantAgent(
    name="critic",
    model_client=model_client,
    system_message="Provide brief, constructive feedback. Respond with 'STOP' when satisfied.",
)

# --- Termination rule ---
termination_condition = MaxMessageTermination(10) | TextMentionTermination("STOP")

# --- Team setup ---
team = RoundRobinGroupChat(
    participants=[primary_agent, critic_agent],
    termination_condition=termination_condition,
)

# --- Async main ---
async def main():
    print("Starting team discussion...\n")

    # Run the team conversation and stream messages
    async for message in team.run_stream(task="The inflation problem of the 1970s and how Volcker solved it."):
        if isinstance(message, TextMessage):
            print(f"\n[{message.source.upper()}]\n{message.content}\n")

    print("\nTeam discussion complete.\n")

    await model_client.close()
    print("Model client closed.\n")

# --- Entry point ---
if __name__ == "__main__":
    asyncio.run(main())
