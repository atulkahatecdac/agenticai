# Microsoft Agent Framework (MAF) - SecureBank: middleware around the agent and its tools.
# Middleware wraps every run (agent middleware) or every tool call (function middleware),
# so policy lives in one place instead of in each prompt:
#   1. mask_card_numbers   (agent)    - card numbers never reach the LLM
#   2. audit_log           (function) - every tool call is logged with its arguments and timing
#   3. block_risky_tools   (function) - close_account is refused by policy, whatever the LLM wants
#
# pip install agent-framework-core agent-framework-openai python-dotenv
# Needs OPENAI_API_KEY in .env

import asyncio
import re
import time
from typing import Annotated

from agent_framework import (
    Agent,
    AgentContext,
    FunctionInvocationContext,
    Message,
    agent_middleware,
    function_middleware,
    tool,
)
from agent_framework.openai import OpenAIChatCompletionClient
from dotenv import load_dotenv

load_dotenv(override=True)

CARD_NUMBER = re.compile(r"\b(?:\d[ -]?){12,15}(\d{4})\b")


@tool
def get_balance(account_id: Annotated[str, "SecureBank account id, e.g. ACC-1001"]) -> str:
    """Return the current balance (INR) of a SecureBank account."""
    return f"{account_id}: INR 1,25,000.00"


@tool
def block_card(last4: Annotated[str, "Last 4 digits of the card to block"]) -> str:
    """Block a debit or credit card immediately."""
    return f"Card ending {last4} is now blocked."


@tool
def close_account(account_id: Annotated[str, "SecureBank account id to close"]) -> str:
    """Close a SecureBank account permanently."""
    return f"{account_id} closed."


# --- 1. Agent middleware: runs around the whole agent call ---
@agent_middleware
async def mask_card_numbers(context: AgentContext, call_next):
    """Replace full card numbers in user messages with ****1234 before the LLM sees them."""
    masked = []
    for message in context.messages:
        text = message.text or ""
        if message.role == "user" and CARD_NUMBER.search(text):
            text = CARD_NUMBER.sub(r"****\1", text)
            print(f"  [mask] user message now: {text}")
            message = Message("user", [text])
        masked.append(message)
    context.messages[:] = masked
    await call_next()


# --- 2. Function middleware: runs around every tool call ---
@function_middleware
async def audit_log(context: FunctionInvocationContext, call_next):
    start = time.perf_counter()
    print(f"  [audit] -> {context.function.name}({dict(context.arguments)})")
    await call_next()
    result = context.result
    if isinstance(result, list):  # tool results come back as a list of Content items
        result = " ".join(getattr(item, "text", None) or str(item) for item in result)
    print(f"  [audit] <- {context.function.name} = {result!r} ({time.perf_counter() - start:.3f}s)")


@function_middleware
async def block_risky_tools(context: FunctionInvocationContext, call_next):
    if context.function.name == "close_account":
        print("  [policy] close_account blocked - must be done in a branch")
        context.result = "Refused by SecureBank policy: accounts can only be closed in a branch."
        return  # no call_next() -> the tool never runs
    await call_next()


agent = Agent(
    OpenAIChatCompletionClient(model="gpt-4o-mini"),
    name="bank_assistant",
    instructions="You are SecureBank's assistant. Use the tools to act on the customer's request.",
    tools=[get_balance, block_card, close_account],
    middleware=[mask_card_numbers, audit_log, block_risky_tools],
)


async def main():
    for request in [
        "What is the balance of ACC-1001?",
        "I lost my card 4111 1111 1111 1234, please block it right now.",
        "Close my account ACC-1001 today.",
    ]:
        print(f"\nCUSTOMER: {request}")
        result = await agent.run(request)
        print(f"AGENT:    {result.text}")


if __name__ == "__main__":
    asyncio.run(main())
