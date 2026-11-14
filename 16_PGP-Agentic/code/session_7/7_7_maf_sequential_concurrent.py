# Microsoft Agent Framework (MAF) - SecureBank: ready-made orchestrations.
# You don't always need WorkflowBuilder. MAF ships builders for the common patterns:
#   SequentialBuilder  - agents in a fixed order, each sees what came before
#   ConcurrentBuilder  - agents in parallel on the same input, results collected
#   (GroupChatBuilder, HandoffBuilder and MagenticBuilder cover the rest - see 7_8 and 7_13)
#
# pip install agent-framework-core agent-framework-openai agent-framework-orchestrations python-dotenv
# Needs OPENAI_API_KEY in .env

import asyncio

from agent_framework import Agent
from agent_framework.openai import OpenAIChatCompletionClient
from agent_framework.orchestrations import ConcurrentBuilder, SequentialBuilder
from dotenv import load_dotenv

load_dotenv(override=True)

client = OpenAIChatCompletionClient(model="gpt-4o-mini")

# --- Sequential: draft an SMS campaign, then have compliance fix it ---
copywriter = Agent(
    client,
    name="copywriter",
    instructions="You write one promotional SMS (max 160 characters) for SecureBank. Return only the SMS.",
)
compliance = Agent(
    client,
    name="compliance",
    instructions="You are SecureBank's compliance officer. Rewrite the SMS above so it has no guaranteed "
    "returns, includes 'T&C apply', and stays under 160 characters. Return only the final SMS.",
)
sequential = SequentialBuilder(
    participants=[copywriter, compliance],
    intermediate_output_from=[copywriter],  # also surface the draft, not only the final SMS
).build()

# --- Concurrent: three reviewers look at a product idea at the same time ---
risk = Agent(client, name="risk", instructions="Give the top credit-risk concern in one sentence.")
legal = Agent(client, name="legal", instructions="Give the top regulatory concern in one sentence.")
customer = Agent(client, name="customer_experience", instructions="Give the top customer-experience concern in one sentence.")
concurrent = ConcurrentBuilder(participants=[risk, legal, customer]).build()


async def main():
    print("=== SequentialBuilder: copywriter -> compliance ===")
    result = await sequential.run("Launch offer: fixed deposit at 8.1% for senior citizens.")
    for response in result.get_intermediate_outputs() + result.get_outputs():
        print(f"[{response.messages[-1].author_name}] {response.text}")

    print("\n=== ConcurrentBuilder: risk || legal || customer_experience ===")
    result = await concurrent.run("New product idea: a zero-fee credit card for college students with a INR 50,000 limit.")
    for message in result.get_outputs()[-1].messages:
        print(f"[{message.author_name}] {message.text}")


if __name__ == "__main__":
    asyncio.run(main())
