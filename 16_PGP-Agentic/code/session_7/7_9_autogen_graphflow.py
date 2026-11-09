# pip install autogen-agentchat autogen-ext python-dotenv

import asyncio
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import DiGraphBuilder, GraphFlow
from autogen_ext.models.openai import OpenAIChatCompletionClient
from dotenv import load_dotenv

load_dotenv(override=True)

# 1. Create an OpenAI model client
client = OpenAIChatCompletionClient(model="gpt-4o-mini")

# 2. Create agents
writer = AssistantAgent(
    name="writer",
    model_client=client,
    system_message="Draft a short paragraph on cosine similarity."
)

reviewer = AssistantAgent(
    name="reviewer",
    model_client=client,
    system_message="Review the draft and suggest improvements."
)

# 3. Build the directed graph
builder = DiGraphBuilder()
builder.add_node(writer)
builder.add_node(reviewer)
builder.add_edge("writer", "reviewer")  # use agent names, not objects
graph = builder.build()

# 4. Create the GraphFlow
flow = GraphFlow(participants=[writer, reviewer], graph=graph)

# 5. Run the workflow using async stream
async def main():
    stream = flow.run_stream(task="Write a short paragraph about cosine similarity.")
    async for event in stream:
        print(event)

# 6. Execute
asyncio.run(main())
