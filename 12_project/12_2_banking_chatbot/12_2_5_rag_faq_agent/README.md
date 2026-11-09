# Step 5 — RAG FAQ Agent + Internal Routing

## Files changed

- `12_2_5_rag_faq_agent.py` (new) — step 4's three tool specialists, unchanged,
  plus a fourth (RAG FAQ Agent), now behind a **router** instead of a manual
  picker. No sidebar — one plain chat window.

## Architecture change

Two changes land together in this step:

**1. A fourth specialist: RAG FAQ Agent.** The deck's six banking tools only ever
cover structured, per-customer data — there's no way to answer "how do I open an
account?" or "what's your lost-card policy?", and a tool-calling agent shouldn't
try to guess at those. This specialist is built differently from the other three —
it follows `14_advanced/07_langgraph/07_5_message_graph_bank_faq.py`'s shape, not the
agent/tools loop:

```
START -> retrieve_faq -> generate -> END
```

`retrieve_faq` embeds the user's latest message and does a similarity search
against a Chroma vectorstore built from `3_langgraph/Dataset_Banking_chatbot.csv`
(local `sentence-transformers/all-MiniLM-L6-v2` via `langchain_huggingface` — no
extra API calls). Above a 0.3 relevance-score threshold, the matched FAQ's answer
is injected as a `SystemMessage`; below it, the injected message tells the model
plainly that nothing matched. `generate` then answers from that context, never
from outside knowledge. Building the vectorstore is expensive and Streamlit
reruns the whole script on every interaction, so it's wrapped in
`@st.cache_resource` — built once per app process.

**2. Internal routing, replacing step 4's manual selectbox.** A small router
(structured-output classification into `accounts` / `transaction` / `service` /
`faq`, following `14_advanced/07_langgraph/07_4_conditional_routing_specialists.py`)
now picks the specialist for each turn automatically — the user just chats, in
one shared window, no picker. This is a first slice of what the deck calls the
"coordinator" (slide 8's steps 01-02: parse intent, identify the specialist).
**What's still missing** — and what step 6 adds — is handling a request that
needs *more than one* specialist in the same turn (parallel dispatch + merging
results). A cross-domain question here still only gets the one routed
specialist's partial answer, same gap step 4 surfaced, just automated instead of
manual.

Conversation state is one shared `st.session_state.messages` list (not
per-specialist anymore) — this also means context now carries across a
specialist switch mid-conversation (e.g. a customer ID given to the Accounts
Agent is visible to the Transaction Agent on the next turn), which step 4's
isolated-histories design didn't allow. A parallel `routing_log` list drives a
small caption under each reply naming which specialist handled it, for
transparency.

## Demo prompts

- **In-domain, grounded**: `"How do I report a lost debit card?"` → routes to FAQ
  Agent.
- **Proves no hallucination**: `"What is the weather like today?"` → FAQ Agent,
  relevance score comes back negative (checked directly against the retriever:
  `-0.14`), well below the 0.3 threshold, so it says it has no information rather
  than guessing.
- **Ambiguous**: `"What is my account balance?"` → routes to FAQ Agent (matches a
  generic "how do I check my balance" FAQ entry) and gives an honest but generic
  how-to answer instead of this customer's real number — new evidence for the
  still-missing coordinator, not a bug (see step 4's README for the same finding
  from the manual-picker era).
- **Regression, in-domain**: `"What is the account balance for customer
  CUST1001?"` → routes to Accounts Agent, same result as steps 3/4.
- **Regression, cross-domain (still broken)**: `"What is my balance and show me
  my last 5 transactions for customer CUST1001?"` → routes to Accounts Agent
  (single specialist), answers the balance half, declines the transactions half.
  Response phrasing varies slightly run to run, but this split-answer behavior is
  consistent.

## Failure case

Not a code bug — see the "ambiguous" and "cross-domain" cases above, both
expected given there's still no multi-specialist dispatch. The actual bug to
watch for would be the FAQ Agent inventing an answer instead of saying it has no
information; the system prompt forbids it and the demo confirms it stays honest.

## Regression test

Re-ran the in-domain and cross-domain prompts from step 4 — all still pass, now
routed automatically instead of manually selected. Verified headlessly via
`streamlit.testing.v1.AppTest`, including a multi-turn case confirming the router
switches specialists correctly turn-to-turn (asked for a balance, then asked a
follow-up about transactions — routed to Accounts Agent then Transaction Agent).

## Run

```
streamlit run 12_2_5_rag_faq_agent.py
```

First launch is slower (loading the local embedding model + building the
vectorstore); subsequent reruns in the same app process are fast thanks to
`st.cache_resource`. Just type — no specialist to pick.
