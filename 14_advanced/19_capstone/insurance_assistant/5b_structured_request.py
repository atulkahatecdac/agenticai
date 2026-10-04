# pip install openai-agents pydantic requests
import asyncio
import json
import sys
from typing import Literal

import requests
from agents import Agent, RunContextWrapper, Runner, function_tool
from pydantic import BaseModel, Field, ValidationError

from common import INSURANCE_API_URL, MODEL, CustomerSession, load_step

sys.stdout.reconfigure(encoding="utf-8")

# =====================================================================
# STEP 5b: STRUCTURED OUTPUT -> API - the purple box in the diagram.
#
# An API cannot read "what's my coverage?". It needs exact JSON. So we ask
# the LLM to fill a Pydantic model instead of writing prose:
#
#     {"policy_id": "P12345", "customer_id": "C67890",
#      "coverage_type": "health", "request_type": "get_coverage"}
#
# Pydantic (and the JSON schema the SDK sends to the model) guarantee the
# SHAPE: a request_type outside the list, or a policy id that does not
# look like P12345, is rejected BEFORE the API is called.
#
# One rule on top: customer_id is ALWAYS overwritten with the logged-in
# customer. The model may fill it, but it is never trusted.
#
# This file shows the diagram as a fixed pipeline:
#     question -> LLM (JSON) -> validate -> Insurance API -> LLM (answer)
# Step 6 turns the API call into a TOOL so the agent decides when to use it.
#
# Run it (start the API first:  python 5a_insurance_api.py):
#   python 5b_structured_request.py
# =====================================================================


class PolicyRequest(BaseModel):
    """The request body of POST /api/v1/policy-request (the JSON in the diagram)."""
    policy_id: str = Field(pattern=r"^P\d{5}$", description="Policy id, e.g. P12345")
    customer_id: str = Field(pattern=r"^C\d{5}$", description="Customer id, e.g. C67890")
    coverage_type: Literal["health"]
    request_type: Literal["get_coverage", "get_status", "get_claims"] = Field(
        description="get_coverage: amounts and limits; get_status: status and validity; get_claims: past claims")


def call_insurance_api(req: PolicyRequest) -> dict:
    """Plain function: also used by the MCP server in step 7."""
    try:
        r = requests.post(f"{INSURANCE_API_URL}/api/v1/policy-request", json=req.model_dump(), timeout=10)
    except requests.ConnectionError:
        return {"error": f"The Insurance API is not reachable at {INSURANCE_API_URL}. "
                         "Start it with: python 5a_insurance_api.py"}
    return r.json()


def policy_details(customer_id: str, policy_id: str, request_type: str) -> dict:
    """Build + validate the request for the logged-in customer, then call the API."""
    try:
        req = PolicyRequest(policy_id=policy_id, customer_id=customer_id,
                            coverage_type="health", request_type=request_type)
    except ValidationError as e:
        return {"error": f"Invalid request, not sent to the API: {e.errors()[0]['msg']}"}
    return call_insurance_api(req)


def file_claim(customer_id: str, policy_id: str, amount: int, reason: str, hospital: str,
               admission_date: str) -> dict:
    """The only WRITE. Not used until step 9, where a human must approve it first."""
    body = {"policy_id": policy_id, "customer_id": customer_id, "amount": amount, "reason": reason,
            "hospital": hospital, "admission_date": admission_date}
    try:
        r = requests.post(f"{INSURANCE_API_URL}/api/v1/claims", json=body, timeout=10)
    except requests.ConnectionError:
        return {"error": f"The Insurance API is not reachable at {INSURANCE_API_URL}. "
                         "Start it with: python 5a_insurance_api.py"}
    return r.json()


@function_tool
def get_policy_details(ctx: RunContextWrapper[CustomerSession], policy_id: str,
                       request_type: Literal["get_coverage", "get_status", "get_claims"]) -> str:
    """Ask the Insurance API about one of the customer's policies. Returns live facts:
    get_coverage -> sum insured, amount claimed, amount still available, room rent limit,
                    co-payment, no claim bonus, status and valid-till date;
    get_status   -> status and valid-till date;
    get_claims   -> past claims on the policy.

    Args:
        policy_id: the policy id, e.g. P12345 (get it from get_my_policies first).
        request_type: what to fetch.
    """
    return json.dumps(policy_details(ctx.context.customer_id, policy_id, request_type))


# ---------- the fixed pipeline from the diagram ----------

def request_builder_instructions(ctx: RunContextWrapper[CustomerSession], agent) -> str:
    sql = load_step("3_tool_sql.py")
    policies = sql.fetch_customer_policies(ctx.context.customer_id)
    return ("Convert the customer's question into a request for the Insurance API. "
            f"The customer is {ctx.context.customer_id}. Their policies: {json.dumps(policies['policies'])}. "
            "Prefer the most recently purchased policy unless the customer names one.")


request_builder = Agent[CustomerSession](
    name="Request builder", model=MODEL,
    instructions=request_builder_instructions,
    output_type=PolicyRequest,             # <- structured output: the reply IS a PolicyRequest
)

answer_writer = Agent(
    name="Answer writer", model=MODEL,
    instructions="Answer the customer's question in two or three friendly sentences, using ONLY the API data "
                 "given. Write rupee amounts in Indian format, e.g. Rs. 5,00,000 or ₹5,00,000.",
)


async def pipeline(question: str, session: CustomerSession) -> None:
    print(f"CUSTOMER: {question}")
    built = await Runner.run(request_builder, question, context=session)
    req: PolicyRequest = built.final_output
    print(f"\n  1. LLM -> structured output (a validated PolicyRequest):\n     {req.model_dump_json()}")

    if req.customer_id != session.customer_id:
        print(f"     (customer_id {req.customer_id} replaced by the logged-in {session.customer_id})")
    req.customer_id = session.customer_id

    data = call_insurance_api(req)
    print(f"\n  2. POST /api/v1/policy-request ->\n     {json.dumps(data)}")

    answer = await Runner.run(answer_writer, f"Question: {question}\nAPI data: {json.dumps(data)}")
    print(f"\n  3. LLM -> answer:\nASSISTANT: {answer.final_output}\n")


def show_validation() -> None:
    print("What validation catches (no LLM needed) - none of these reach the API:")
    bad = [
        {"policy_id": "P12345", "customer_id": "C67890", "coverage_type": "health", "request_type": "cancel_policy"},
        {"policy_id": "12345; DROP TABLE coverage", "customer_id": "C67890", "coverage_type": "health",
         "request_type": "get_coverage"},
        {"policy_id": "P12345", "customer_id": "C67890", "coverage_type": "motor", "request_type": "get_coverage"},
        {"policy_id": "P12345", "coverage_type": "health", "request_type": "get_coverage"},
    ]
    for body in bad:
        try:
            PolicyRequest(**body)
            print(f"  ACCEPTED {body}")
        except ValidationError as e:
            err = e.errors()[0]
            print(f"  REJECTED {json.dumps(body)}\n           {err['loc'][0]}: {err['msg']}")
    print()


async def main() -> None:
    show_validation()
    await pipeline("What is the coverage amount in my health insurance policy?", CustomerSession())
    print("-> That is the whole diagram, as a FIXED pipeline that always calls the API.")
    print("   Step 6 gives the agent all three tools and lets it decide which to call.")


if __name__ == "__main__":
    asyncio.run(main())
