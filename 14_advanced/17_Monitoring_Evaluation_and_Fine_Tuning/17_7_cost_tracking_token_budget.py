import warnings
warnings.filterwarnings("ignore")

import sys
from collections import defaultdict
from dotenv import load_dotenv
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult
from langchain_openai import ChatOpenAI

load_dotenv(override=True)
sys.stdout.reconfigure(encoding="utf-8")

# =====================================================================
# Cost per run, budgets per user, and an alert before the bill arrives.
#
# Every LLM response carries its token usage. A callback handler sees
# every call any chain or agent makes, so one handler can:
#   1. add up tokens and cost per run, per user and per model
#   2. refuse calls once a user's daily budget is used up (a quota)
#   3. raise an alert when spend crosses a threshold
# 17_3 exports the same token counts to Prometheus for dashboards; this
# is the in-process guard that stops the spending itself.
# =====================================================================

# USD per 1M tokens (input, output) - check the provider's pricing page; prices change.
PRICES = {"gpt-4o-mini": (0.15, 0.60), "gpt-4.1-mini": (0.40, 1.60), "gpt-4o": (2.50, 10.00)}
DAILY_BUDGET_USD = {"free": 0.0004, "pro": 0.05}      # tiny on purpose, so the demo hits it
ALERT_AT = 0.8                                          # alert at 80% of a budget


class BudgetExceeded(Exception):
    pass


class CostTracker(BaseCallbackHandler):
    def __init__(self):
        self.spent = defaultdict(float)                 # user -> USD today
        self.rows = []                                  # one row per LLM call
        self.who = {}                                   # run_id -> metadata of a call in flight

    def check(self, user: str, plan: str) -> None:
        """Call BEFORE the LLM: refuse once the budget is gone."""
        if self.spent[user] >= DAILY_BUDGET_USD[plan]:
            raise BudgetExceeded(f"{user} has used ${self.spent[user]:.5f} of a ${DAILY_BUDGET_USD[plan]} daily budget")

    # Metadata (who is calling) arrives when a call STARTS; usage when it ENDS.
    # run_id links the two.
    def on_chat_model_start(self, serialized, messages, *, run_id, metadata=None, **kwargs) -> None:
        self.who[run_id] = metadata or {}

    def on_llm_end(self, response: LLMResult, *, run_id, **kwargs) -> None:
        meta = self.who.pop(run_id, {})
        user, plan = meta.get("user", "unknown"), meta.get("plan", "pro")
        msg = response.generations[0][0].message
        usage = msg.usage_metadata or {}
        model = (msg.response_metadata or {}).get("model_name", "gpt-4o-mini")
        price_in, price_out = next((p for name, p in PRICES.items() if model.startswith(name)), PRICES["gpt-4o-mini"])
        cost = usage.get("input_tokens", 0) * price_in / 1e6 + usage.get("output_tokens", 0) * price_out / 1e6
        before = self.spent[user]
        self.spent[user] += cost
        self.rows.append((user, model, usage.get("input_tokens", 0), usage.get("output_tokens", 0), cost))
        budget = DAILY_BUDGET_USD[plan]
        if before < ALERT_AT * budget <= self.spent[user]:
            print(f"   ALERT: {user} has passed {ALERT_AT:.0%} of their daily budget")   # Slack / PagerDuty in real life


tracker = CostTracker()
tracker.spent["ravi"] = 0.00030      # spend earlier today - in production, loaded from a database or Redis
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, callbacks=[tracker])


def ask(user: str, plan: str, question: str) -> str:
    tracker.check(user, plan)                                          # 2. quota
    meta = {"metadata": {"user": user, "plan": plan}}
    return llm.invoke(question, config=meta).content


if __name__ == "__main__":
    traffic = [
        ("asha", "pro", "In two sentences, what is a context window?"),
        ("ravi", "free", "Explain RAG in three sentences."),
        ("ravi", "free", "Give one example of RAG used by a bank."),
        ("ravi", "free", "Give one example of RAG used by a hospital."),
        ("asha", "pro", "List three uses of embeddings."),
        ("ravi", "free", "Give one example of RAG used by a school."),
    ]
    for user, plan, question in traffic:
        print(f"[{user}/{plan}] {question}")
        try:
            answer = ask(user, plan, question)
            print(f"   -> {answer[:80]}...")
        except BudgetExceeded as e:
            print(f"   -> REFUSED: {e}. Upgrade, or try again tomorrow.")

    print("\n" + "=" * 70 + "\nCOST REPORT\n" + "=" * 70)
    print(f"{'user':8}{'model':16}{'in':>7}{'out':>7}{'USD':>12}")
    for user, model, tin, tout, cost in tracker.rows:
        print(f"{user:8}{model[:15]:16}{tin:>7}{tout:>7}{cost:>12.6f}")
    for user, total in tracker.spent.items():
        print(f"total {user:6} ${total:.6f}  ({len([r for r in tracker.rows if r[0] == user])} calls)")
    print(f"Average cost per call: ${sum(r[4] for r in tracker.rows) / max(1, len(tracker.rows)):.6f}")
