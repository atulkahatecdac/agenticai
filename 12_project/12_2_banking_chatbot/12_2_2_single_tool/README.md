# Step 2 — One Tool: Balance Enquiry

## Files changed

- `../mock_bank.py` (new) — shared mock bank backend, SQLite-based (`bank.db`,
  stdlib `sqlite3`, auto-created and seeded on first import): six customer
  records (INR balances, Indian digit-grouping via `format_inr`), `get_balance()`.
  Three customer ids are reserved to match named characters the deck itself uses
  in later steps — John (CUST1001, step 7 standard-auth demo), Sancy (CUST1003,
  step 7 restricted-auth demo), Sanjay (CUST1004, step 8 session-memory demo).
  Later steps append fields/functions to this file rather than redefining it.
  Because it's a real database, mutations from later steps' demos (address
  changes, etc.) persist across runs — call `mock_bank.reset_db()` to restore
  the seed values.
- `12_2_2_single_tool.py` (new) — extends step 1 with one bound tool.

## Architecture change

Standard LangGraph tool-calling loop, following
`14_advanced/09_langsmith/09_2_trace_langgraph_agent_end_to_end.py`:

```
START -> agent -> (conditional: tool_calls?) -> tools -> agent -> END
                                 \-> no tool calls -> END
```

One `@tool`-decorated function, `get_account_balance(customer_id)`, wraps
`mock_bank.get_balance`. The LLM decides whether to call it based on the user's
natural-language intent. There is still no authentication layer (that's step 8) —
the caller must state the customer ID explicitly in the query, and the system
prompt instructs the model to ask for it rather than guess.

## Demo prompt

```
What is the account balance for customer CUST1001?
```

## Expected output

The agent calls `get_account_balance("CUST1001")` and returns the real (mock)
balance from `mock_bank.py`: John Mathews, ₹52,340.75.

## Failure case

```
What is my cheque book status?
```

No tool exists for this yet — the agent must say it doesn't have that capability,
not hallucinate a status. This is the expected gap step 3 closes by adding the
remaining five tools. If the model instead invents a cheque-book answer, that's a
hallucination bug the same way an invented balance would have been in step 1.

## Regression test

Re-run step 1's prompts:

- `"What is my account balance?"` (no customer ID) — the agent must ask which
  customer/account, not guess a customer ID and not silently pick one from
  `mock_bank.py`.
- `"Can you show me my last 5 transactions?"` — still no transactions tool exists,
  so this must still fail honestly, same as step 1.

## Run

```
python 12_2_2_single_tool.py
```
