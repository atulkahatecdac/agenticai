# AutoGen GraphFlow - SecureBank: the loan checks from 7_6_maf_loan_pipeline_checkpoints.py.
#   credit_officer --+
#                    +--> loan_decision
#   fraud_analyst  --+
# Both start nodes run in parallel; loan_decision waits for both (a join).
# GraphFlow has no checkpoint/resume - one of the things the Agent Framework adds.
#
# pip install autogen-agentchat autogen-ext[openai] python-dotenv
# Needs OPENAI_API_KEY in .env

import asyncio

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import DiGraphBuilder, GraphFlow
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient
from dotenv import load_dotenv

load_dotenv(override=True)

client = OpenAIChatCompletionClient(model="gpt-4o-mini")


async def get_credit_score(customer_id: str) -> str:
    """Return the customer's credit bureau score and existing EMIs, e.g. for CUST-77."""
    return f"{customer_id}: CIBIL score 742, existing EMIs INR 12,000/month, no defaults."


async def check_fraud_flags(customer_id: str) -> str:
    """Return fraud and KYC flags for the customer, e.g. for CUST-77."""
    return f"{customer_id}: KYC complete, no fraud flags, address verified 2023."


credit_officer = AssistantAgent(
    "credit_officer",
    model_client=client,
    tools=[get_credit_score],
    reflect_on_tool_use=True,
    system_message="Assess repayment capacity for the loan application. Use the tool. "
    "Reply in 2 sentences ending with 'CREDIT: OK' or 'CREDIT: RISKY'.",
)
fraud_analyst = AssistantAgent(
    "fraud_analyst",
    model_client=client,
    tools=[check_fraud_flags],
    reflect_on_tool_use=True,
    system_message="Check the loan application for fraud and KYC risk. Use the tool. "
    "Reply in 2 sentences ending with 'FRAUD: CLEAR' or 'FRAUD: SUSPICIOUS'.",
)
loan_decision = AssistantAgent(
    "loan_decision",
    model_client=client,
    system_message="You are SecureBank's loan committee. Using the credit and fraud assessments above, "
    "reply with APPROVE or REJECT and a 2-sentence reason for the customer.",
)

builder = DiGraphBuilder()
for agent in [credit_officer, fraud_analyst, loan_decision]:
    builder.add_node(agent)
builder.add_edge(credit_officer, loan_decision)  # two edges into one node = a join
builder.add_edge(fraud_analyst, loan_decision)
participants = builder.get_participants()
flow = GraphFlow(participants, graph=builder.build())

APPLICATION = "Customer CUST-77, salaried, monthly income INR 1,10,000, applies for a personal loan of INR 5,00,000 over 3 years."


async def main():
    await Console(flow.run_stream(task=APPLICATION))
    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
