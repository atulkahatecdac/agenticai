# pip install openai-agents
import asyncio
import json
import sys
from dataclasses import asdict

from agents import Agent, RunContextWrapper, Runner, function_tool

from common import MODEL, CustomerSession, load_step, print_trace

sys.stdout.reconfigure(encoding="utf-8")

# =====================================================================
# STEP 9: HUMAN-IN-THE-LOOP - the agent may READ alone, but a WRITE
# (filing a claim) waits for a person.
#
#   @function_tool(needs_approval=True)
#
# When the agent calls submit_claim, the Agents SDK does NOT run it.
# Runner.run() returns early with result.interruptions = [the pending
# call]. A human looks at the exact arguments and decides:
#     state = result.to_state()
#     state.approve(item)   or   state.reject(item)
#     result = await Runner.run(agent, state)      # the run continues
# Approve -> the tool runs and the API creates the claim.
# Reject  -> the tool never runs; the agent is told and informs the customer.
#
# The paused run can be saved as text (state.to_string()) and resumed
# later, in another process - step 10 uses that to pause in the customer's
# web request and resume when the approver clicks a button.
#
# Rule used here: EVERY claim needs approval. (needs_approval also accepts
# a function, e.g. "only claims above Rs. 25,000" - a one-line change.)
#
# Run it (start the API first:  python 5a_insurance_api.py):
#   python 9_hitl_claim.py              you are the approver: type y or n
#   python 9_hitl_claim.py --approve    approve automatically
#   python 9_hitl_claim.py --reject     reject automatically
# =====================================================================

api = load_step("5b_structured_request.py")
step6 = load_step("6_agent_all_tools.py")

CLAIM_INSTRUCTIONS = """

Filing a claim:
- You need: the policy (it must be Active), the amount in rupees, the reason (illness/injury and treatment),
  the hospital name and city, and the admission date (YYYY-MM-DD). Ask for anything that is missing.
- Then call submit_claim once. A claims officer must approve the submission first.
- If it was submitted: give the claim id and say a claims officer will review it. Never promise approval or payment.
- If the submission was rejected: say it was not submitted and that SecureLife support will contact them."""


def instructions(ctx: RunContextWrapper[CustomerSession], agent) -> str:
    """Step 6 instructions + how to file a claim. Also used by step 10."""
    return step6.instructions(ctx, agent) + CLAIM_INSTRUCTIONS


@function_tool(needs_approval=True)          # <- the whole HITL feature is this flag
def submit_claim(ctx: RunContextWrapper[CustomerSession], policy_id: str, amount: int, reason: str,
                 hospital: str, admission_date: str) -> str:
    """File a health insurance claim for the logged-in customer. This is a WRITE: it creates a claim.

    Args:
        policy_id: the customer's Active policy, e.g. P12345.
        amount: claimed amount in rupees.
        reason: illness or injury and the treatment.
        hospital: hospital name and city.
        admission_date: YYYY-MM-DD.
    """
    return json.dumps(api.file_claim(ctx.context.customer_id, policy_id, amount, reason, hospital, admission_date))


agent = Agent[CustomerSession](
    name="SecureLife Insurance Assistant (claims)",
    model=MODEL,
    instructions=instructions,
    tools=step6.TOOLS + [submit_claim],
)

QUESTION = ("I was admitted to City Hospital, Pune on 20 September 2026 for 2 days for a fractured arm. "
            "The bill was Rs. 18,000. Please file a reimbursement claim on my health policy.")


def decide(item) -> bool:
    if "--approve" in sys.argv:
        return True
    if "--reject" in sys.argv:
        return False
    return input("  Approve this claim? [y/n] ").strip().lower().startswith("y")


async def main() -> None:
    question = " ".join(a for a in sys.argv[1:] if not a.startswith("--")) or QUESTION
    print(f"CUSTOMER: {question}\n")
    result = await Runner.run(agent, question, context=CustomerSession())

    shown = 0
    while result.interruptions:               # the run paused: one or more calls wait for a human
        print_trace(result, start=shown)
        shown = len(result.new_items)
        state = result.to_state()
        print(f"\n  The paused run, saved as text, is {len(state.to_string(context_serializer=asdict)):,} characters - it could wait in a")
        print("  database for hours. A claims officer now reviews the exact call:\n")
        for item in result.interruptions:
            print(f"  TOOL  {item.name}")
            for k, v in json.loads(item.arguments).items():
                print(f"        {k:<15} {v}")
            if decide(item):
                print("  -> APPROVED\n")
                state.approve(item)
            else:
                print("  -> REJECTED\n")
                state.reject(item, rejection_message="A claims officer rejected this claim submission.")
        result = await Runner.run(agent, state)      # resume where it stopped

    print_trace(result, start=shown)
    print("\n-> Reads ran on their own; the write waited for a person.")
    print("   Step 10 puts everything - tools, RAG, MCP, guardrails, approvals - into one web app.")


if __name__ == "__main__":
    asyncio.run(main())
