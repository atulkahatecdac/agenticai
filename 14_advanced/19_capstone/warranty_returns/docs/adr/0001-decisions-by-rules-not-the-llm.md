# ADR 0001 – Refund/replace/repair decisions are made by rules, not by the LLM

- **Status:** accepted
- **Date:** 2026-01 (capstone Part 1)

## Context
Each ticket ends in a decision that moves money or goods. LLM output varies from run to run, can be
talked into things (prompt injection), and is hard to audit after the fact.

## Decision
The LLM classifies the ticket and writes the reply. The decision itself is a Python function applied to
the retrieved policy clauses and the order facts (`decision_maker` in `19_6_agent_graph.py`). Every decision must
cite a clause that was actually retrieved (enforced by an output validator in `19_5_guardrails.py`).

## Consequences
- Same ticket, same decision – the 19_9 scorecard and the CI gates are deterministic.
- An injection can at most change the wording, never the money.
- New policy rules need a code change and a new test ticket, not a prompt tweak.
