"""Guardrails AI: validators that check (and fix) an LLM's output before a customer sees it.

NeMo Guardrails (16_2) steers the CONVERSATION - which topics are allowed, what the bot may say.
Guardrails AI checks one specific OUTPUT against rules you write as validators, and decides what
happens on failure: fix it, raise, filter, or re-ask the LLM.

Needs its own venv - guardrails-ai pulls langchain-core 1.x, which breaks this repo's 0.3 pins:
    uv venv .venv-guardrails --python 3.12
    .venv-guardrails\\Scripts\\activate            (macOS/Linux: source .venv-guardrails/bin/activate)
    uv pip install -r 16_5_requirements.txt
    python 16_5_guardrails_ai_validators.py         (no API key needed - it validates sample replies)

Ready-made validators (toxic language, PII, competitor checks, ...) come from the Guardrails Hub:
`guardrails configure` (free token from hub.guardrailsai.com), then e.g.
`guardrails hub install hub://guardrails/toxic_language`. The custom ones below need no Hub.
"""
import re
import sys
from typing import Any, Dict

from guardrails import Guard, OnFailAction
from guardrails.errors import ValidationError
from guardrails.validators import FailResult, PassResult, ValidationResult, Validator, register_validator

sys.stdout.reconfigure(encoding="utf-8")


# ---------------------------------------------------------------------
# Validator 1 - FIX: replace competitor names instead of failing.
# ---------------------------------------------------------------------
@register_validator(name="shop/no-competitors", data_type="string")
class NoCompetitors(Validator):
    def __init__(self, competitors: list[str], on_fail=OnFailAction.FIX):
        super().__init__(on_fail=on_fail, competitors=competitors)
        self.pattern = re.compile("|".join(map(re.escape, competitors)), re.IGNORECASE)

    def _validate(self, value: str, metadata: Dict[str, Any]) -> ValidationResult:
        if not self.pattern.search(value):
            return PassResult()
        return FailResult(error_message="Mentions a competitor", fix_value=self.pattern.sub("another retailer", value))


# ---------------------------------------------------------------------
# Validator 2 - uses METADATA passed in at call time: a refund may not
# exceed what the customer actually paid.
# ---------------------------------------------------------------------
@register_validator(name="shop/refund-limit", data_type="string")
class RefundLimit(Validator):
    def _validate(self, value: str, metadata: Dict[str, Any]) -> ValidationResult:
        limit = metadata["order_value"]
        amounts = [int(a.replace(",", "")) for a in re.findall(r"(?:Rs\.?|₹)\s?([\d,]+)", value)]
        too_big = [a for a in amounts if a > limit]
        if too_big:
            return FailResult(error_message=f"Offers ₹{too_big[0]:,} but the order was ₹{limit:,}")
        return PassResult()


# ---------------------------------------------------------------------
# Validator 3 - no promises the support bot is not allowed to make.
# ---------------------------------------------------------------------
@register_validator(name="shop/no-guarantees", data_type="string")
class NoGuarantees(Validator):
    PHRASES = ("guarantee", "definitely", "100%", "promise you")

    def _validate(self, value: str, metadata: Dict[str, Any]) -> ValidationResult:
        found = [p for p in self.PHRASES if p in value.lower()]
        if found:
            return FailResult(error_message=f"Makes a promise: '{found[0]}'")
        return PassResult()


# One Guard, three validators. Each sets its own on_fail action:
#   FIX       -> use fix_value and carry on
#   EXCEPTION -> raise, so the app can fall back to a safe template reply
#   NOOP      -> record the failure but let the text through (log-only mode)
guard = Guard(name="support-reply").use(
    NoCompetitors(competitors=["GadgetHub", "ElectroWorld"]),
    RefundLimit(on_fail=OnFailAction.EXCEPTION),
    NoGuarantees(on_fail=OnFailAction.NOOP),
)

DRAFTS = [
    "Hi Priya, we have approved a refund of ₹2,499 for your headphones. It reaches your card in 5-7 days.",
    "Hi Rahul, GadgetHub may be cheaper, but we can replace your charger free of charge this week.",
    "Hi Meera, we will definitely fix it - a technician visits on Monday.",
    "Hi Arjun, as an apology we are refunding ₹25,000 for your ₹2,499 order.",
]

if __name__ == "__main__":
    for draft in DRAFTS:
        print("=" * 78 + f"\nLLM draft : {draft}")
        try:
            outcome = guard.validate(draft, metadata={"order_value": 2499})
            failures = [f"{s.validator_name}: {s.failure_reason}" for s in outcome.validation_summaries or []]
            changed = outcome.validated_output != draft
            print(f"Passed    : {outcome.validation_passed}{'  (fixed)' if changed else ''}")
            if failures:
                print(f"Flagged   : {'; '.join(failures)}")
            print(f"Send      : {outcome.validated_output}")
        except ValidationError as e:      # EXCEPTION action - never send this draft
            print(f"BLOCKED   : {str(e).splitlines()[0][:150]}")
            print("Send      : (safe fallback) Thanks for your patience - a colleague will confirm your refund today.")
    print("=" * 78)
    print("Same idea with an LLM call: guard(model='gpt-4o-mini', messages=[...], metadata={...}) validates the")
    print("reply as it comes back, and OnFailAction.REASK sends the error back to the LLM for a corrected answer.")
