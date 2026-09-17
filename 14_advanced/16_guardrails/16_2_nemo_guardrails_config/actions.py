import re

from nemoguardrails.actions.actions import action

SECRET_OVERRIDE_CODE = "CLAIMS-OVERRIDE-7719"

INJECTION_PATTERNS = [
    r"ignore (all |your )?(previous|prior|above) instructions",
    r"disregard (all |your )?(previous|prior|above) (instructions|rules)",
    r"new instructions?:",
    r"system (notice|prompt)\b",
    r"you are now",
    r"reveal (the )?(system prompt|hidden prompt|internal)",
    r"forget (everything|all) (you (were|have been) told|above)",
]


@action()
async def check_input_injection(text: str) -> bool:
    """INPUT RAIL: does the raw user message look like a prompt-injection attempt?
    Runs before the main LLM is ever called."""
    lower = text.lower()
    return any(re.search(pattern, lower) for pattern in INJECTION_PATTERNS)


@action()
async def check_output_leak(text: str) -> bool:
    """OUTPUT RAIL: did the secret override code slip into the draft response?
    Runs after generation but before the response reaches the policyholder."""
    return SECRET_OVERRIDE_CODE in text
