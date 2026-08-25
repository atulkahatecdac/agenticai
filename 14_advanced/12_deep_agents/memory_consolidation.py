import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

import os
import shutil
import sys
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_chroma import Chroma
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

load_dotenv(override=True)
sys.stdout.reconfigure(encoding="utf-8")

# =====================================================================
# Memory consolidation: an episodic store (see episodic_memory_store.py)
# grows one raw episode per interaction - left alone, near-duplicate
# episodes about the same recurring issue pile up, bloating storage and
# diluting recall() with redundant near-identical matches. Consolidation
# is a periodic batch pass: read every raw episode, have an LLM group
# the ones that are really the same underlying pattern, replace each
# group with ONE denser summary episode, and delete the raw originals.
# =====================================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PERSIST_DIR = os.path.join(BASE_DIR, "memory_consolidation_db")
shutil.rmtree(PERSIST_DIR, ignore_errors=True)

vectorstore = Chroma(
    collection_name="episodic_memory",
    embedding_function=OpenAIEmbeddings(model="text-embedding-3-small"),
    persist_directory=PERSIST_DIR,
)

# 8 raw episodes accumulated from real (simulated) support interactions,
# across 3 recurring issue patterns - the messy, redundant state a live
# episodic store actually ends up in after enough traffic.
RAW_EPISODES = [
    "Customer asked: My debit card keeps getting declined at ATMs while I'm on vacation in Italy. | "
    "Resolution: Explained the $500 daily ATM limit and enabled travel notification for Italy.",
    "Customer asked: Card declined twice at an ATM while traveling in Japan. | "
    "Resolution: Enabled travel notification for Japan and confirmed the $500 daily ATM limit.",
    "Customer asked: Worried my card will be declined at ATMs during my upcoming trip to France. | "
    "Resolution: Proactively enabled travel notification for France ahead of the trip.",
    "Customer asked: I was charged twice for the same purchase at a restaurant. | "
    "Resolution: Identified a duplicate authorization hold, explained it clears in 3-5 business days.",
    "Customer asked: Two charges appeared for one hotel booking. | "
    "Resolution: Confirmed it was a pending pre-authorization hold plus the final charge, not a double charge.",
    "Customer asked: My statement shows the same coffee shop charge twice in one day. | "
    "Resolution: Explained the first was a pending hold that dropped off once the real charge posted.",
    "Customer asked: My card was declined at an online betting site. | "
    "Resolution: Explained the gambling merchant category is blocked by default; enabled it in Merchant Controls.",
    "Customer asked: Card declined buying cryptocurrency on an exchange. | "
    "Resolution: Explained crypto purchases are blocked by default under Merchant Controls; enabled that category.",
]
vectorstore.add_texts(RAW_EPISODES)

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)


class ConsolidatedGroup(BaseModel):
    theme: str = Field(description="Short label for the recurring pattern this group of episodes shares.")
    summary: str = Field(
        description="One consolidated episode replacing the whole group, written in the same "
        "'Customer asked: ... | Resolution: ...' style, generalized rather than tied to one customer."
    )
    source_indices: list[int] = Field(description="0-based indices of the raw episodes this group consolidates.")


class ConsolidationPlan(BaseModel):
    groups: list[ConsolidatedGroup] = Field(
        description="Every raw episode index must appear in exactly one group. Group episodes describing "
        "the same underlying issue/resolution pattern together, even if worded differently; an episode with "
        "no close match forms a group of its own."
    )


def consolidate() -> ConsolidationPlan:
    numbered = "\n".join(f"{i}. {doc}" for i, doc in enumerate(RAW_EPISODES))
    prompt = f"""Here are {len(RAW_EPISODES)} raw episodic memories from a bank support agent:

{numbered}

Group the episodes that describe the same recurring issue/resolution pattern, and write one
consolidated summary episode per group."""
    return llm.with_structured_output(ConsolidationPlan).invoke(prompt)


if __name__ == "__main__":
    print(f"BEFORE: {vectorstore.get()['ids'].__len__()} raw episode(s) in the store\n")

    plan = consolidate()
    for group in plan.groups:
        print(f"[{group.theme}] consolidates raw episode(s) {group.source_indices}")
        print(f"  -> {group.summary}\n")

    vectorstore.delete(ids=vectorstore.get()["ids"])
    vectorstore.add_texts([group.summary for group in plan.groups])

    print(f"AFTER: {vectorstore.get()['ids'].__len__()} consolidated episode(s) in the store "
          f"(from {len(RAW_EPISODES)} raw ones)")
