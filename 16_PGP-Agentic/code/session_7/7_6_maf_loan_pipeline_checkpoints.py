# Microsoft Agent Framework (MAF) - SecureBank: a loan pipeline with parallel checks and checkpoints.
#
#   intake --> credit_officer  --+
#          \-> fraud_analyst   --+--> merge_checks --> loan_decision
#
# The two checks run in parallel (fan-out), the merge waits for both (fan-in).
# With checkpoint_storage set, MAF saves the workflow state after every superstep, so a run
# can be resumed later - after a crash, a deploy, or a human sign-off days later.
#
# pip install agent-framework-core agent-framework-openai python-dotenv
# Needs OPENAI_API_KEY in .env. Checkpoints are written to ./loan_checkpoints next to this script.

import asyncio
import os
import shutil
from typing import Annotated

from agent_framework import (
    Agent,
    AgentExecutorRequest,
    AgentExecutorResponse,
    FileCheckpointStorage,
    Message,
    WorkflowBuilder,
    WorkflowContext,
    executor,
    tool,
)
from agent_framework.openai import OpenAIChatCompletionClient
from dotenv import load_dotenv

load_dotenv(override=True)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CHECKPOINT_DIR = os.path.join(BASE_DIR, "loan_checkpoints")

client = OpenAIChatCompletionClient(model="gpt-4o-mini")


@tool
def get_credit_score(customer_id: Annotated[str, "SecureBank customer id, e.g. CUST-77"]) -> str:
    """Return the customer's credit bureau score and existing EMIs."""
    return f"{customer_id}: CIBIL score 742, existing EMIs INR 12,000/month, no defaults."


@tool
def check_fraud_flags(customer_id: Annotated[str, "SecureBank customer id, e.g. CUST-77"]) -> str:
    """Return fraud and KYC flags for the customer."""
    return f"{customer_id}: KYC complete, no fraud flags, address verified 2023."


credit_officer = Agent(
    client,
    name="credit_officer",
    instructions="You assess repayment capacity for a loan application. Use the tool. "
    "Reply in 2 sentences ending with 'CREDIT: OK' or 'CREDIT: RISKY'.",
    tools=[get_credit_score],
)
fraud_analyst = Agent(
    client,
    name="fraud_analyst",
    instructions="You check a loan application for fraud and KYC risk. Use the tool. "
    "Reply in 2 sentences ending with 'FRAUD: CLEAR' or 'FRAUD: SUSPICIOUS'.",
    tools=[check_fraud_flags],
)
loan_decision = Agent(
    client,
    name="loan_decision",
    instructions="You are SecureBank's loan committee. Given a credit assessment and a fraud assessment, "
    "reply with APPROVE or REJECT and a 2-sentence reason for the customer.",
)


@executor(id="intake")
async def intake(application: str, ctx: WorkflowContext[AgentExecutorRequest]) -> None:
    """Start node: hand the same application to both checkers."""
    await ctx.send_message(AgentExecutorRequest(messages=[Message("user", [application])]))


@executor(id="merge_checks")
async def merge_checks(results: list[AgentExecutorResponse], ctx: WorkflowContext[AgentExecutorRequest]) -> None:
    """Fan-in: receives both assessments at once and asks the committee for a decision."""
    report = "\n\n".join(f"{r.executor_id}:\n{r.agent_response.text}" for r in results)
    await ctx.send_message(AgentExecutorRequest(messages=[Message("user", [report])]))


def build_workflow(storage: FileCheckpointStorage):
    return (
        WorkflowBuilder(start_executor=intake, output_from=[loan_decision], checkpoint_storage=storage)
        .add_fan_out_edges(intake, [credit_officer, fraud_analyst])
        .add_fan_in_edges([credit_officer, fraud_analyst], merge_checks)
        .add_edge(merge_checks, loan_decision)
        .build()
    )


APPLICATION = "Customer CUST-77, salaried, monthly income INR 1,10,000, applies for a personal loan of INR 5,00,000 over 3 years."


async def run_and_trace(stream) -> None:
    decision = ""
    async for event in stream:
        if event.type == "executor_invoked":
            print(f"  [runs] {event.executor_id}")
        elif event.type == "output":
            decision += event.data.text  # streamed: the decision arrives token by token
    print(f"  DECISION: {decision.strip()}")


async def main():
    shutil.rmtree(CHECKPOINT_DIR, ignore_errors=True)  # start every demo clean
    storage = FileCheckpointStorage(CHECKPOINT_DIR)
    workflow = build_workflow(storage)

    print("=== Run 1: full pipeline, checkpointed after every superstep ===")
    await run_and_trace(workflow.run(APPLICATION, stream=True))

    checkpoints = sorted(await storage.list_checkpoints(workflow_name=workflow.name), key=lambda c: c.timestamp)
    print(f"\n{len(checkpoints)} checkpoints saved in {CHECKPOINT_DIR}:")
    for i, cp in enumerate(checkpoints):
        senders = sorted(cp.messages) or ["-"]  # cp.messages: undelivered messages, keyed by sender
        print(f"  #{i}  superstep {cp.iteration_count}  messages waiting from: {', '.join(senders)}")

    # Pretend the process died just before the committee met: resume from the checkpoint
    # that holds merge_checks' report. Only loan_decision runs - the checks are NOT repeated.
    resume_from = next(cp for cp in checkpoints if "merge_checks" in cp.messages)
    print(f"\n=== Run 2: a NEW workflow object resumes from checkpoint {resume_from.checkpoint_id[:8]} ===")
    fresh = build_workflow(storage)
    await run_and_trace(fresh.run(checkpoint_id=resume_from.checkpoint_id, stream=True))


if __name__ == "__main__":
    asyncio.run(main())
