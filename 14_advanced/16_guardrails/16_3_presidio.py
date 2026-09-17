import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

import sys
from dotenv import load_dotenv
from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

load_dotenv(override=True)
sys.stdout.reconfigure(encoding="utf-8")

# =====================================================================
# SETUP (safe to add to the repo's shared requirements.txt - unlike
# guardrails-ai, presidio has no openai/langchain-core pin to clash with):
#
#   pip install presidio-analyzer presidio-anonymizer
#   python -m spacy download en_core_web_lg   # one-time, ~600MB - presidio's
#                                              # default NLP engine for PERSON/
#                                              # LOCATION-style detection
#
# 16_1-16_2 were all "is this message/response OK to send - yes or no"
# gates (a regex scan, a Colang flow, a Guard.validate()). Presidio is a
# different shape: it doesn't pass/fail anything. AnalyzerEngine.analyze()
# just FINDS PII spans in text (name, phone, email, ...) and returns them
# as a list of RecognizerResult(entity_type, start, end, score) - it never
# touches the string. AnonymizerEngine.anonymize() is the separate step
# that actually rewrites the text, and you choose a different operator
# PER ENTITY TYPE: "replace" (swap in a placeholder), "mask" (keep some
# characters, e.g. a card's last 4 digits), "hash" (deterministic - the
# same policy number always hashes the same way, so support staff can
# still tell "same policyholder mentioned this claim twice" without ever
# seeing the raw number), "redact" (delete outright), or "encrypt".
#
# CUSTOM RECOGNIZERS: presidio's built-ins cover generic PII (names,
# emails, phone numbers, credit cards, SSNs, ...) but have no idea what a
# SecureLife policy number looks like. A PatternRecognizer is the
# lightweight way to teach it one - just a regex plus a score, registered
# on the same registry the built-ins live in.
#
# GOTCHA FOUND WHILE BUILDING THIS: presidio ships recognizers for many
# countries (UK national insurance numbers, Spanish DNIs, driver's
# licenses, URLs, ...) and by default AnalyzerEngine.analyze() runs ALL
# of them. A US-formatted phone number like "987-654-3210" satisfies the
# UK "NHS number" checksum pattern too, and being an exact-format-and-
# checksum match it scored 1.0 - HIGHER than the real PHONE_NUMBER hit's
# 0.75 - so it won that span and phone numbers fell through to the
# DEFAULT operator (or straight into the anonymized text unmasked, if you
# hadn't set a DEFAULT) instead of getting the PHONE_NUMBER mask you
# configured. Passing analyze(..., entities=[...]) to name exactly the
# entity types you care about avoids this rather than trying to out-guess
# every country-specific recognizer that might collide.
# =====================================================================

# SecureLife's own policy-number format: SL-<4 digit year>-<6 digit id>.
POLICY_NUMBER_RECOGNIZER = PatternRecognizer(
    supported_entity="SECURELIFE_POLICY_NUMBER",
    patterns=[Pattern(name="securelife_policy_number", regex=r"\bSL-\d{4}-\d{6}\b", score=0.9)],
)

WANTED_ENTITIES = ["PERSON", "PHONE_NUMBER", "EMAIL_ADDRESS", "CREDIT_CARD", "SECURELIFE_POLICY_NUMBER"]

ANONYMIZE_OPERATORS = {
    "PERSON": OperatorConfig("replace", {"new_value": "<PERSON>"}),
    "EMAIL_ADDRESS": OperatorConfig("replace", {"new_value": "<EMAIL>"}),
    "PHONE_NUMBER": OperatorConfig("mask", {"type": "mask", "masking_char": "*", "chars_to_mask": 6, "from_end": True}),
    "CREDIT_CARD": OperatorConfig("mask", {"type": "mask", "masking_char": "*", "chars_to_mask": 12, "from_end": True}),
    "SECURELIFE_POLICY_NUMBER": OperatorConfig("hash", {"hash_type": "sha256"}),
    "DEFAULT": OperatorConfig("replace", {"new_value": "<REDACTED>"}),
}

analyzer = AnalyzerEngine()
analyzer.registry.add_recognizer(POLICY_NUMBER_RECOGNIZER)
anonymizer = AnonymizerEngine()


def check_message(policyholder_message: str) -> None:
    print(f"  Original: {policyholder_message!r}")

    results = analyzer.analyze(text=policyholder_message, language="en", entities=WANTED_ENTITIES)
    if not results:
        print("  [detected] no PII found")
    else:
        for r in results:
            print(f"  [detected] {r.entity_type} (score={r.score:.2f}): {policyholder_message[r.start:r.end]!r}")

    outcome = anonymizer.anonymize(text=policyholder_message, analyzer_results=results, operators=ANONYMIZE_OPERATORS)
    print(f"  [safe to log/forward] {outcome.text!r}")


def banner(title: str) -> None:
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


if __name__ == "__main__":
    banner("SANITY CHECK: clean message, no PII")
    check_message("How long is the waiting period before a claim can be made?")

    banner("SCENARIO 1: name + phone + email in a claim message")
    check_message(
        "Hi, my name is Priya Nair, you can reach me at 987-654-3210 or priya@example.com "
        "about my claim."
    )

    banner("SCENARIO 2: a credit card number typed into the chat by mistake")
    check_message("Can you charge the renewal to my card 4111-1111-1111-1111 instead of auto-debit?")

    banner("SCENARIO 3: SecureLife's own policy number - custom recognizer, not a presidio built-in")
    check_message("I'd like an update on claim status for policy number SL-2024-118823, please.")
