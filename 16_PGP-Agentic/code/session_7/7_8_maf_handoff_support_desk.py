# Microsoft Agent Framework (MAF) - SecureBank: a support desk with handoffs.
# A triage agent talks to the customer and HANDS OFF the conversation to a specialist.
# Unlike 7_5 (the workflow routes once), here the agents decide: the specialist owns the
# conversation until it hands back. HandoffBuilder adds a hidden "handoff" tool to each agent.
# Blocking a card needs human approval (same approval_mode as 7_4).
#
# pip install agent-framework-core agent-framework-openai agent-framework-orchestrations python-dotenv
# Needs OPENAI_API_KEY in .env. Type 'bye' to end the chat.

import asyncio
from typing import Annotated

from agent_framework import Agent, Content, tool
from agent_framework.openai import OpenAIChatCompletionClient
from agent_framework.orchestrations import HandoffAgentUserRequest, HandoffBuilder
from dotenv import load_dotenv

load_dotenv(override=True)

client = OpenAIChatCompletionClient(model="gpt-4o-mini")


@tool(approval_mode="always_require")
def block_card(last4: Annotated[str, "Last 4 digits of the card"]) -> str:
    """Block a SecureBank card immediately."""
    return f"Card ending {last4} is blocked. A replacement will arrive in 5 working days."


@tool
def get_loan_offer(amount: Annotated[float, "Loan amount in INR"]) -> str:
    """Return SecureBank's personal loan offer for an amount."""
    return f"Personal loan of INR {amount:,.0f}: 10.75% p.a., up to 5 years, processing fee 1%."


triage = Agent(
    client,
    name="triage",
    instructions="You are SecureBank's front desk. Greet the customer, understand the need, and hand off "
    "to cards_desk (lost/stolen/declined cards) or loans_desk (loans, EMIs). Do not solve it yourself.",
    require_per_service_call_history_persistence=True,  # required by HandoffBuilder
)
cards_desk = Agent(
    client,
    name="cards_desk",
    instructions="You handle SecureBank card problems. Ask for the last 4 digits if needed, then block the card.",
    tools=[block_card],
    require_per_service_call_history_persistence=True,
)
loans_desk = Agent(
    client,
    name="loans_desk",
    instructions="You handle SecureBank loan questions. Use the tool to quote an offer.",
    tools=[get_loan_offer],
    require_per_service_call_history_persistence=True,
)

workflow = (
    HandoffBuilder(name="securebank_desk", participants=[triage, cards_desk, loans_desk])
    .with_start_agent(triage)
    .build()
)


def show(events) -> list:
    """Print what the agents said and return the requests that need a human."""
    pending = []
    for event in events:
        if event.type == "handoff_sent":
            print(f"  [handoff] {event.data.source} -> {event.data.target}")
        elif event.type == "request_info":
            pending.append(event)
            if isinstance(event.data, HandoffAgentUserRequest):
                for message in event.data.agent_response.messages:
                    if message.text:
                        print(f"{message.author_name or event.executor_id}: {message.text}")
    return pending


async def main():
    first = input("You: ")
    pending = show([e async for e in workflow.run(first, stream=True)])

    while pending:
        responses = {}
        for request in pending:
            if isinstance(request.data, Content) and request.data.type == "function_approval_request":
                call = request.data.function_call
                approved = input(f"  APPROVE {call.name}({call.arguments})? (y/n): ").strip().lower() == "y"
                responses[request.request_id] = request.data.to_function_approval_response(approved=approved)
            elif isinstance(request.data, HandoffAgentUserRequest):
                reply = input("You: ")
                if reply.strip().lower() in {"bye", "exit", "quit"}:
                    responses[request.request_id] = HandoffAgentUserRequest.terminate()
                else:
                    responses[request.request_id] = HandoffAgentUserRequest.create_response(reply)
        pending = show([e async for e in workflow.run(responses=responses, stream=True)])
    print("Chat ended.")


if __name__ == "__main__":
    asyncio.run(main())
