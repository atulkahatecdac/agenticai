# Step 4 — Specialist Agents: Domain Isolation, No Coordinator Yet

## Files changed

- `12_2_4_specialist_agents.py` (new) — three domain-scoped specialist graphs
  sharing one LLM, no coordinator.

## Architecture change

Step 3's one agent with six tools is split into three specialists, each its own
compiled LangGraph app built by a shared factory (`make_specialist_agent(tools)`,
mirroring `14_advanced/07_langgraph/07_4_conditional_routing_specialists.py`'s
`make_specialist()`):

- **Accounts Agent** — `get_account_balance` only.
- **Transaction Agent** — `get_transaction_details` + `request_statement`.
- **Service Agent** — `change_of_address` + `request_cheque_book` + `update_kyc`.

Same underlying `ChatOpenAI` model for all three — what makes each one a
"specialist" is purely its tool binding and system prompt, not a different model.
Each specialist's prompt explicitly instructs it to decline anything outside its
own domain rather than attempt it.

**There is deliberately no coordinator in this step.** The Streamlit UI's
specialist `selectbox` stands in for that missing piece — a human has to decide
which specialist to talk to, which is exactly the gap slide 7 calls out: *"who
decides which specialist to call?"* Each specialist keeps its own independent
conversation history (`st.session_state.histories[name]`), proving isolation:
nothing said to one is visible to another. The UI is a plain selectbox + chat —
no sidebar; type the demo prompts below directly into the chat box after picking
the right specialist from the dropdown.

## Demo prompts

Three in-domain prompts prove each specialist still does its job:

- Accounts: `"What is the account balance for customer CUST1001?"`
- Transaction: `"Show me the last 5 transactions for customer CUST1001."`
- Service: `"Please update the address for customer CUST1003 to '99 Residency Road, Bengaluru'."`

## Expected output

Each specialist answers correctly from its own scoped tool(s) — identical results
to step 3's single agent, just now split across three isolated contexts.

## Failure case — proves isolation, then surfaces the next problem

**Isolation**: ask the Accounts Agent an out-of-scope question —
`"What is my cheque book status for customer CUST1003?"` — it must decline and
point to another specialist, not attempt the tool it doesn't have. Unlike step 3,
where one agent silently had access to everything, the Accounts Agent here
*cannot* reach `request_cheque_book` even if it wanted to; it was never bound to
that tool.

**The problem this step surfaces**: ask the Accounts Agent the step 3 cross-domain
prompt — `"What is my balance and show me my last 5 transactions for customer
CUST1001?"` — it answers the balance half correctly and, for the transactions
half, tells the user to go ask the Transaction Agent. No single specialist can
satisfy a cross-domain request alone, and nothing here automatically splits the
request and merges the answers. That routing/synthesis gap is exactly what step 6
(coordinator) closes — this step's code is not the fix.

## Regression test

No new capability was added this step (that's the point — pure restructuring).
Verify the *total* capability across all three specialists still matches step 3's
single agent: balance, transactions, statements, address change, cheque book
request, and KYC update all still work, each now reachable only through the
specialist that owns that domain. Confirmed headlessly via
`streamlit.testing.v1.AppTest` for all three in-domain prompts plus both failure
demos above.

## Run

```
streamlit run 12_2_4_specialist_agents.py
```

Pick a specialist from the dropdown, then type into the chat box.
