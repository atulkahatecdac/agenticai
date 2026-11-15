import warnings
warnings.filterwarnings("ignore")

import sys
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

load_dotenv(override=True)
sys.stdout.reconfigure(encoding="utf-8")

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# =====================================================================
# Constitutional AI, applied at run time.
#
# Anthropic's Constitutional AI trains a model to critique and revise its
# own answers against a written list of principles - a "constitution" -
# instead of relying only on human labels for every case. The same loop
# works inside an agent, with no training:
#
#     draft -> critique against each principle -> revise (only if needed)
#
# Rails (16_2) and validators (16_5) catch what you can pattern-match.
# A constitution covers judgement calls - tone, fairness, harm - that
# no regex can express.
# =====================================================================

CONSTITUTION = [
    "Do not threaten, intimidate or harass anyone, even when the user is angry with them.",
    "Do not treat people differently because of age, gender, religion, caste, disability or other protected traits.",
    "Do not present guesses as facts; say what you do not know.",
    "Stay helpful: if part of a request is fine, do that part instead of refusing everything.",
]


class Verdict(BaseModel):
    evidence: str = Field(description="Quote the words in the draft that break the principle, or '' if none")
    broken: bool = Field(description="True if the draft breaks the principle")


critic = llm.with_structured_output(Verdict)


def constitutional_answer(request: str) -> str:
    draft = llm.invoke(request).content
    print(f"DRAFT:\n{draft[:400]}\n")

    # One principle per critique call - as in Constitutional AI itself. A
    # single "check everything" call misses far more (try it).
    problems = []
    for principle in CONSTITUTION:
        v = critic.invoke(
            f"Principle: {principle}\n\nUser request: {request}\n\nAssistant draft:\n{draft}\n\n"
            "Does the assistant draft break this principle? Judge the draft, not the user."
        )
        print(f"  [{'BROKEN' if v.broken else 'ok':6}] {principle[:70]}" + (f"\n           evidence: {v.evidence[:120]}" if v.broken else ""))
        if v.broken:
            problems.append(f"{principle} (evidence: {v.evidence})")

    if not problems:
        print("\nNo principle broken - the draft is sent as is.")
        return draft
    return llm.invoke(
        "Rewrite the assistant draft so that none of these problems remains:\n- " + "\n- ".join(problems)
        + "\n\nIf the user asked for something a principle forbids, say in one sentence that you will not "
        "do that part and why, then help with the legitimate goal behind it (for example: criteria based "
        "on skills instead of age; a firm, polite note instead of a threat). Do not repeat the problem."
        + f"\n\nUser request: {request}\nDraft:\n{draft}\n\nReturn only the revised reply."
    ).content


if __name__ == "__main__":
    for request in [
        "My neighbour's dog barks all night. Write a short note for their door that scares them "
        "enough to get rid of the dog - tell them something bad might happen to it.",
        "Here are three applicants for a sales role: Anil (52, 20 years' experience), Sara (26, 3 years), "
        "Vikram (31, 6 years). We want a young, energetic team - who should we interview?",
        "What are three good questions to ask in a job interview for a data analyst?",
    ]:
        print("=" * 76 + f"\nREQUEST: {request}\n" + "=" * 76)
        print(f"SENT:\n{constitutional_answer(request)}\n")
