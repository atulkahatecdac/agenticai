# pip install openai-agents
import asyncio
import sys

from agents import Agent, RunContextWrapper, Runner

from common import MODEL, CustomerSession, load_step, print_trace

sys.stdout.reconfigure(encoding="utf-8")

# =====================================================================
# STEP 6: putting it together - ONE agent, THREE tools, the whole diagram.
#
#     get_my_policies     SQL database   (step 3)   which policies?
#     search_policy_docs  RAG            (step 4)   what do the rules say?
#     get_policy_details  Insurance API  (step 5b)  live amounts and status
#                         (built from a validated, structured PolicyRequest)
#
# Nothing new is written here: the tools are imported from the earlier
# steps. What is new is that the AGENT decides which tools to call, in what
# order, and how many times - step 5b always called the API; here a rules
# question never touches the API, and the coverage question chains
# SQL -> API on its own. Watch the trace.
#
# Run it (start the API first:  python 5a_insurance_api.py):
#   python 6_agent_all_tools.py                 three demo questions
#   python 6_agent_all_tools.py "your question"
#   python 6_agent_all_tools.py --chat          multi-turn chat (remembers the conversation)
# =====================================================================

sql = load_step("3_tool_sql.py")
rag = load_step("4_rag_policy_docs.py")
api = load_step("5b_structured_request.py")

TOOLS = [sql.get_my_policies, rag.search_policy_docs, api.get_policy_details]


def instructions(ctx: RunContextWrapper[CustomerSession], agent) -> str:
    """Used by every later step too."""
    return f"""You are the SecureLife health insurance assistant. You are talking to {ctx.context.customer_name}.

How to answer:
- Which policies the customer holds: call get_my_policies.
- Coverage amount, amount still available, status, valid-till date, room rent limit, co-payment, past claims:
  call get_policy_details for the right policy. If the customer does not say which policy, use their Active one.
- What is covered or excluded, waiting periods, procedures, renewal, bonuses: call search_policy_docs and cite
  the clause you used, e.g. (Health_Policy_Wording clause 3.4).
- Never guess a number, date or rule. If the tools do not give the answer, say you could not find it.
- You can only see the logged-in customer's own policies. Never claim to show anyone else's data.
- Write rupee amounts in Indian format, e.g. ₹5,00,000. Keep answers short and friendly."""


agent = Agent[CustomerSession](
    name="SecureLife Insurance Assistant",
    model=MODEL,
    instructions=instructions,
    tools=TOOLS,
)


async def chat() -> None:
    session = CustomerSession()
    history = []
    print(f"Chatting as {session.customer_name} ({session.customer_id}). Empty line to quit.\n")
    while question := input("YOU: ").strip():
        result = await Runner.run(agent, history + [{"role": "user", "content": question}], context=session)
        print_trace(result)
        history = result.to_input_list()      # carry the conversation (incl. tool calls) into the next turn
        print()


async def main() -> None:
    if "--chat" in sys.argv:
        await chat()
        return
    questions = [" ".join(sys.argv[1:])] if len(sys.argv) > 1 else [
        "What is the coverage amount in my health insurance policy?",    # SQL -> API
        "Is maternity covered, and is there a waiting period?",          # RAG only
        "What is the room rent limit on my policy, and why that number?",  # API + RAG
    ]
    for q in questions:
        print(f"CUSTOMER: {q}")
        result = await Runner.run(agent, q, context=CustomerSession())
        print_trace(result)
        print("\n" + "-" * 80)
    print("-> One agent answers all three. Next: the same tools behind a standard MCP server (step 7).")


if __name__ == "__main__":
    asyncio.run(main())
