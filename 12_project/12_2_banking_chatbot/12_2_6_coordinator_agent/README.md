# Step 6 — Coordinator Agent: Multi-Specialist Dispatch + Synthesis

## Files changed

- `../mock_bank.py` — added `get_service_details(customer_id)`, a read-only
  lookup of a customer's current address, cheque-book status, and KYC status.
  The columns already existed; there was simply never a *read* function for
  them, only the three *write* ones (`update_address`, `request_cheque_book`,
  `update_kyc`) carried over from step 3.
- `12_2_6_coordinator_agent.py` (new) — step 5's four specialists, mostly
  unchanged, now sitting behind a real coordinator instead of a single-pick
  router. Service Agent gains a fourth tool (`get_service_details`, wrapping
  the new `mock_bank` function above).

## Architecture change

Step 5's router could only pick **one** specialist per turn, so a cross-domain
question ("balance AND last 5 transactions") only ever got a partial answer. This
step extends that into a proper coordinator using LangGraph's `Send` API for
genuine parallel fan-out/fan-in, following
`14_advanced/08_langgraph_cycles_HIL_persistence/08_5_parallel_trip_planner_send_api.py`:

```
START -> classify_intent -> (Send fan-out, 1-4 in parallel) -> run_specialist -> synthesize -> END
```

- `classify_intent` now returns a **list** of specialists (step 5's `Routing`
  had a single `Literal` field; this step's has `list[Literal[...]]`).
- `dispatch_to_specialists` turns that list into one `Send("run_specialist", ...)`
  per specialist — LangGraph runs all of them concurrently in the same superstep,
  exactly like the trip planner's flight-search + city-research branches.
- `specialist_replies` is `Annotated[list[dict], operator.add]` so replies from
  parallel branches accumulate instead of one overwriting another — same reducer
  pattern as the trip planner's `flight_options`/`city_reports`.
- `synthesize` merges every reply into one coherent answer. For the common case
  (exactly one specialist), it skips the extra LLM call and returns that
  specialist's reply directly — no need to "synthesize" a single input, and it
  keeps single-domain questions as cheap as they were in step 5.

This is the first architecture that actually handles a mixed banking query
end-to-end in **one turn**, matching slide 8's payoff description.

**A real bug caught during testing**: `st.cache_resource`'s spinner
(`load_faq_vectordb`) tried to update Streamlit UI from inside `run_specialist`'s
`Send`-dispatch worker thread, which has no Streamlit script context, and raised
`NoSessionContext`. Fixed with `show_spinner=False` — caching still works
identically, it just doesn't try to paint a spinner from a background thread.
This didn't affect step 5 because specialists were invoked directly on the main
thread there, with no `Send`/executor involved.

**A precision problem also caught during testing**: the first router prompt
routed *every* address-change and lost-card question to an extra, unnecessary
specialist alongside the correct one (e.g. Accounts Agent tagging along on a pure
address change) — technically harmless since the extra specialist just declines
and synthesis still produces the right answer, but wasteful, and exactly the kind
of "multi-domain requests cost 2.5x more" problem slide 15 (step 12: cost
tracking) warns about. Tightened the router prompt with explicit guidance
("most questions need exactly one specialist," "sounding related isn't a reason
to include it") plus a few worked examples, and confirmed the over-inclusion
stopped without breaking the genuine cross-domain case.

**A real routing bug found via manual testing** (not the automated demo prompts):
`classify_intent` originally classified using only `state["messages"][-1].content`
— the bare latest message, with zero conversation context. A user who answered
"what is my balance?" → "please provide your customer ID" with just a bare
`"CUST1006"` got that reply routed to the FAQ Agent, which of course found no FAQ
entry for a customer ID string and replied "I don't have information on that."
Fixed by giving the router the full conversation transcript (`format_transcript`)
instead of the isolated last message, plus explicit prompt guidance that a short,
question-less reply is usually answering something the assistant just asked for.
Confirmed fixed: the same "balance?" → "CUST1006" sequence now correctly routes
the ID to the Accounts Agent and returns the real balance.

**A known remaining limitation, not fixed**: classifier precision on *compound*
follow-up phrasing is still imperfect — e.g. after establishing a customer ID,
`"ok balance and address"` consistently routed to Service Agent only, dropping
the balance half (a clearer phrasing, `"tell me my balance and update my
address"`, routes to both specialists correctly). This is normal LLM-classifier
behavior, not an architecture gap - chasing every ambiguous phrasing with more
one-off prompt patches doesn't scale. This is exactly what step 10's evaluation
suite exists to catch systematically (a documented test case, not a guess), so
it's left as a known limitation here rather than papered over with another
prompt tweak.

**A real capability gap found via manual testing**: asking for "my last
transaction and address" surfaced that the Service Agent had never had a way to
*read* the current address — `change_of_address` only ever *sets* a new one.
This is the same tool/intent mismatch already documented in steps 3-5 for
cheque-book *status* (an action-only tool, no status lookup) - it had now shown
up for a third domain (address), so rather than documenting it a third time,
`get_service_details` was added to close the gap for all three Service fields
(address, cheque-book status, KYC status) at once. As a side effect, the step
3-5 cheque-book-status quirk is now also fixed at this step: "what is my cheque
book status?" gets a real status back instead of a decline.

**A second, more structural bug found in the same test**: even after adding the
tool, the Service Agent still didn't call it when the SAME message also asked
about something out of its scope (`"...tell me my last transaction and
address"` - Transaction Agent's part, not Service's). It consistently treated
the *whole* message as "not really mine" and declined its own in-scope part too
- reproduced 3/3 times. This defeats the entire point of dispatching a message
to multiple specialists: `synthesize` can't merge an answer a specialist never
gave. Fixed by appending a shared `COMPOUND_REQUEST_NOTE` to all four specialist
prompts, explicitly telling each one to still answer its own in-scope part even
when the same message also mentions something that belongs to another
specialist. Confirmed fixed 3/3 runs after the change - the address now comes
back correctly alongside the transaction.

**A third bug found in the same test, the opposite failure mode**: once the
address started coming back correctly, it arrived buried in extra detail nobody
asked for - a full 30-day statement (with closing balance) instead of just the
last transaction, plus cheque book status and KYC status volunteered alongside
the address just because `get_service_details` happens to return all three
together. A tool returning more than was asked for isn't a reason to report all
of it. Fixed with a second shared note, `CONCISE_ANSWER_NOTE`, appended to all
four prompts, plus tightened `TRANSACTION_PROMPT` guidance on when to call
`get_transaction_details(count=1)` vs. `request_statement`. Confirmed fixed
across 5 repeated runs (concise, scoped answers) without breaking the cases that
*should* return more detail - "last 5 transactions" and an explicit statement
request both still return full detail as before.

## Demo prompts

- **The payoff**: `"What is my balance and show me my last 5 transactions for
  customer CUST1001?"` — routes to Accounts Agent **and** Transaction Agent in
  parallel, synthesized into one answer covering both.
- **Regression, single-domain**: `"What is the account balance for customer
  CUST1001?"` → Accounts Agent only.
- **Regression, FAQ**: `"How do I report a lost debit card?"` → FAQ Agent only.
- **Regression, service action**: `"Please update the address for customer
  CUST1003 to '99 Residency Road, Bengaluru'."` → Service Agent only.
- **Context-aware routing (bug fix)**: type `"what is my balance"`, then reply
  with just `"CUST1006"` on its own — routes to Accounts Agent and returns the
  real balance, not to FAQ Agent.
- **Compound in-scope + out-of-scope request (bug fix)**: `"my customer id is
  CUST1006 ... tell me my last transaction and address"` — routes to Transaction
  Agent **and** Service Agent, and the reply is now both complete (address
  included) and concise (just the one transaction and the address - no full
  statement, no cheque book/KYC status volunteered).
- **Service read capability (new tool)**: `"What is my cheque book status for
  customer CUST1003?"` — now returns the real status ("Dispatched") instead of
  the decline documented as a known limitation in steps 3-5.

## Expected output

The cross-domain prompt gets ONE reply containing both the real balance and the
real last-5-transactions list, with no "please ask the Transaction Agent"
hand-off — that hand-off was the whole gap steps 4 and 5 left open. All three
single-domain regressions route to exactly one specialist each, matching steps
4/5's results.

## Failure case

Not a functional bug in the current state (both issues above were caught and
fixed during this step's own testing, not left as demonstrated failures). The
thing to watch for going forward: `classify_intent` can still occasionally
under- or over-classify on ambiguous phrasing — the eval suite in step 10 should
include cases that catch this class of routing-precision failure, not just
"does the tool exist" checks.

## Regression test

Re-ran step 5's demo/regression prompts (single-domain balance, FAQ, service
action) — all still route to exactly one specialist and produce identical
answers. Verified headlessly via `streamlit.testing.v1.AppTest`.

## Run

```
streamlit run 12_2_6_coordinator_agent.py
```
