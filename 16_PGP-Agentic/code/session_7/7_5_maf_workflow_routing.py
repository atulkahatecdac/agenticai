# Microsoft Agent Framework (MAF) - SecureBank: a workflow that routes each request.
# triage --(switch-case on the department label)--> cards | loans | fraud | general desk
# The LLM only classifies (inside the triage node); the workflow - your code - decides where
# the message goes next. That is the difference between a workflow and one agent doing everything.
#
# pip install agent-framework-core agent-framework-openai python-dotenv
# Needs OPENAI_API_KEY in .env

import asyncio
from typing import Literal

from agent_framework import (
    Agent,
    AgentExecutorRequest,
    Case,
    Default,
    Message,
    WorkflowBuilder,
    WorkflowContext,
    executor,
)
from agent_framework.openai import OpenAIChatCompletionClient
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv(override=True)

client = OpenAIChatCompletionClient(model="gpt-4o-mini")


class Triage(BaseModel):
    department: Literal["cards", "loans", "fraud", "general"]
    reason: str


classifier = Agent(
    client,
    name="classifier",
    instructions="You classify SecureBank customer messages into a department. "
    "cards = lost/blocked/declined cards; loans = loans and EMIs; fraud = unknown transactions or scams; "
    "general = everything else.",
    default_options={"response_format": Triage},  # every reply is a Triage JSON object
)


def specialist(name: str, focus: str) -> Agent:
    return Agent(
        client,
        name=name,
        instructions=f"You are SecureBank's {focus} specialist. Reply to the customer's original message "
        "in 2-3 sentences with concrete next steps.",
    )


cards = specialist("cards_desk", "cards")
loans = specialist("loans_desk", "loans")
fraud = specialist("fraud_desk", "fraud")
general = specialist("general_desk", "general banking")


@executor(id="triage")
async def triage(text: str, ctx: WorkflowContext[AgentExecutorRequest]) -> None:
    """Start node: classify, then pass the customer's own message on with a department label."""
    decision: Triage = (await classifier.run(text)).value
    print(f"  [triage] {decision.department} - {decision.reason}")
    message = Message("user", [text], additional_properties={"department": decision.department})
    await ctx.send_message(AgentExecutorRequest(messages=[message]))


def department_is(name: str):
    """Edge condition: read the label that triage attached to the message."""
    def condition(request: AgentExecutorRequest) -> bool:
        return request.messages[0].additional_properties.get("department") == name
    return condition


workflow = (
    WorkflowBuilder(start_executor=triage, output_from=[cards, loans, fraud, general])
    .add_switch_case_edge_group(
        triage,
        [
            Case(condition=department_is("cards"), target=cards),
            Case(condition=department_is("loans"), target=loans),
            Case(condition=department_is("fraud"), target=fraud),
            Default(target=general),  # anything else
        ],
    )
    .build()
)

MESSAGES = [
    "My credit card got declined at a restaurant even though I have limit left.",
    "Can I prepay my home loan EMI without a penalty?",
    "There's a Rs 49,999 transaction on my account from an app I've never heard of!",
    "What are your branch timings on Saturdays?",
]


async def main():
    for text in MESSAGES:
        print(f"\nCUSTOMER: {text}")
        result = await workflow.run(text)
        for output in result.get_outputs():
            print(f"  {output.messages[-1].author_name}: {output.text}")


if __name__ == "__main__":
    asyncio.run(main())
