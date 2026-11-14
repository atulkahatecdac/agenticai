# Microsoft Agent Framework (MAF) - SecureBank: human approval before money moves.
# @tool(approval_mode="always_require") makes the agent stop and ask instead of calling
# the tool. The run comes back with user_input_requests; we show the call to a human,
# then send the decision back in the same session and the agent carries on.
#
# pip install agent-framework-core agent-framework-openai python-dotenv
# Needs OPENAI_API_KEY in .env

import asyncio
from typing import Annotated

from agent_framework import Agent, Message, tool
from agent_framework.openai import OpenAIChatCompletionClient
from dotenv import load_dotenv

load_dotenv(override=True)

BALANCES = {"ACC-1001": 125000.00, "ACC-1002": 8400.50}


@tool  # read-only: runs without asking
def get_balance(account_id: Annotated[str, "SecureBank account id, e.g. ACC-1001"]) -> str:
    """Return the current balance (INR) of a SecureBank account."""
    return f"{account_id}: INR {BALANCES[account_id.upper()]:,.2f}"


@tool(approval_mode="always_require")  # moves money: a human must approve every call
def transfer_funds(
    from_account: Annotated[str, "Account to debit"],
    to_account: Annotated[str, "Account to credit"],
    amount: Annotated[float, "Amount in INR"],
) -> str:
    """Transfer money between two SecureBank accounts."""
    BALANCES[from_account.upper()] -= amount
    BALANCES[to_account.upper()] += amount
    return f"Transferred INR {amount:,.2f} from {from_account} to {to_account}."


agent = Agent(
    OpenAIChatCompletionClient(model="gpt-4o-mini"),
    name="bank_assistant",
    instructions="You are SecureBank's assistant. Use the tools to act on the customer's request.",
    tools=[get_balance, transfer_funds],
)


async def run_with_approvals(request: str) -> str:
    session = agent.create_session()  # approvals must come back in the same session
    result = await agent.run(request, session=session)
    while result.user_input_requests:
        answers = []
        for req in result.user_input_requests:
            call = req.function_call
            print(f"  APPROVAL NEEDED: {call.name}({call.arguments})")
            approved = input("  Approve? (y/n): ").strip().lower() == "y"
            answers.append(Message("user", [req.to_function_approval_response(approved)]))
        result = await agent.run(answers, session=session)
    return result.text


async def main():
    for request in [
        "What is the balance of ACC-1002?",
        "Transfer 5000 rupees from ACC-1001 to ACC-1002.",
    ]:
        print(f"\nCUSTOMER: {request}")
        print(f"AGENT:    {await run_with_approvals(request)}")
    print(f"\nBalances now: {BALANCES}")


if __name__ == "__main__":
    asyncio.run(main())
