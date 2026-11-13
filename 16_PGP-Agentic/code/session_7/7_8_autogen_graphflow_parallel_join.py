# pip install autogen-agentchat autogen-ext python-dotenv

import asyncio
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import DiGraphBuilder, GraphFlow
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient
from dotenv import load_dotenv

load_dotenv(override=True)

# Create an OpenAI model client
client = OpenAIChatCompletionClient(model="gpt-4o-mini")

# Create agents
writer = AssistantAgent("writer", model_client=client, system_message="Draft a short paragraph on agentic AI.")
editor1 = AssistantAgent("editor1", model_client=client, system_message="Edit the paragraph for grammar.")
editor2 = AssistantAgent("editor2", model_client=client, system_message="Edit the paragraph for style.")
final_reviewer = AssistantAgent(
    "final_reviewer",
    model_client=client,
    system_message="Consolidate the grammar and style edits into a final version.",
)

# Build the workflow graph
builder = DiGraphBuilder()
builder.add_node(writer).add_node(editor1).add_node(editor2).add_node(final_reviewer)

# Fan-out from writer to editors
builder.add_edge("writer", "editor1")
builder.add_edge("writer", "editor2")

# Fan-in both editors into final reviewer
builder.add_edge("editor1", "final_reviewer")
builder.add_edge("editor2", "final_reviewer")

# Build and validate the graph
graph = builder.build()

# Create the flow
flow = GraphFlow(
    participants=builder.get_participants(),
    graph=graph,
)

# Async function to run the flow
async def main():
    await Console(flow.run_stream(task="Write a short paragraph about agentic AI."))

# Run the async main
asyncio.run(main())
