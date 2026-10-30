# pip install openai tiktoken chromadb python-dotenv

import sys
import re
import tiktoken
import chromadb
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(override=True)
sys.stdout.reconfigure(encoding="utf-8")

client = OpenAI()
MODEL = "gpt-4o-mini"
encoding = tiktoken.encoding_for_model(MODEL)

# =====================================================================
# Five ways to keep a growing conversation from blowing past the
# context window, applied to the SAME 16-message conversation and the
# SAME follow-up question, so the tradeoffs are visible in the actual
# output rather than just described.
#
# The follow-up question asks for a fact (an order number) stated in
# message #0, then buried behind 15 later, unrelated support questions.
# Sliding Window is EXPECTED to genuinely lose it - that's the point,
# not a bug - the other four strategies are specifically designed not
# to, each in a different way.
# =====================================================================

CONVERSATION = [
    {"role": "user", "content": "Hi, I'm following up on order #ORD-88213. It still hasn't arrived and it's been 9 days."},
    {"role": "assistant", "content": "I'm sorry to hear that. Let me look into order #ORD-88213 for you - can you confirm the shipping address on file?"},
    {"role": "user", "content": "Yes, it's 42 Lotus Apartments, Baner Road, Pune 411045."},
    {"role": "assistant", "content": "Thanks, I've located the order. It shows as shipped but stuck at the regional hub. I'll escalate it and follow up within 24 hours."},
    {"role": "user", "content": "Okay, while I have you - do you offer price matching if I find the same item cheaper elsewhere?"},
    {"role": "assistant", "content": "We don't offer price matching, but we do have a 30-day best-price guarantee on select categories - I can check if your item qualifies."},
    {"role": "user", "content": "No need, it's a different category. Separate question - how long is your standard return window?"},
    {"role": "assistant", "content": "Our standard return window is 30 days from delivery, provided the item is unused and in original packaging."},
    {"role": "user", "content": "Got it. Also, does my Growth-tier subscription include free returns?"},
    {"role": "assistant", "content": "Yes, Growth-tier and above includes free return shipping on all eligible items."},
    {"role": "user", "content": "Perfect. One more - can I change my billing cycle from monthly to annual mid-cycle?"},
    {"role": "assistant", "content": "Yes, you can switch at Billing Settings > Change Billing Cycle - it takes effect at the start of your next cycle."},
    {"role": "user", "content": "Great, thanks. Also just curious, do you have a referral program?"},
    {"role": "assistant", "content": "Yes! You get a $10 credit for every friend who signs up using your referral link, found under Account > Referrals."},
    {"role": "user", "content": "Nice, I'll check that out later."},
    {"role": "assistant", "content": "Sounds good! Let me know if there's anything else I can help with."},
]
FOLLOW_UP_QUESTION = "Can you remind me what my order number was, one more time?"


# ---- 1. Sliding Window: keep only the latest N messages ----
def sliding_window(conversation: list[dict], window_size: int) -> list[dict]:
    return conversation[-window_size:]


# ---- 2. Summarization: replace older messages with one summary ----
def summarization(conversation: list[dict], keep_last: int) -> list[dict]:
    older, recent = conversation[:-keep_last], conversation[-keep_last:]
    if not older:
        return recent
    transcript = "\n".join(f"{m['role']}: {m['content']}" for m in older)
    summary = client.responses.create(
        model=MODEL,
        instructions="Summarize this conversation concisely, but preserve any specific facts, "
                     "IDs, order numbers, or addresses mentioned - those are often needed later.",
        input=transcript,
    ).output_text
    return [{"role": "system", "content": f"Summary of earlier conversation: {summary}"}] + recent


# ---- 3. Semantic Retrieval: pull only the messages relevant to THIS query ----
def semantic_retrieval(conversation: list[dict], query: str, top_k: int) -> list[dict]:
    collection = chromadb.Client().create_collection("context_memory")
    collection.add(
        ids=[str(i) for i in range(len(conversation))],
        documents=[m["content"] for m in conversation],
    )
    results = collection.query(query_texts=[query], n_results=top_k)
    kept_indices = sorted(int(i) for i in results["ids"][0])  # restore chronological order
    return [conversation[i] for i in kept_indices]


# ---- 4. Token-Based Trimming: keep the newest messages that fit a real token budget ----
def token_based_trimming(conversation: list[dict], max_tokens: int) -> list[dict]:
    kept, total = [], 0
    for message in reversed(conversation):
        tokens = len(encoding.encode(message["content"]))
        if total + tokens > max_tokens:
            break
        kept.insert(0, message)
        total += tokens
    return kept


# ---- 5. Priority-Based Context: always keep flagged-critical messages + recent ones ----
def is_critical(content: str) -> bool:
    # A real system would flag this during extraction (like the semantic-memory
    # examples elsewhere in 15_real); a keyword heuristic is enough to demonstrate it.
    return bool(re.search(r"#ORD-|order number|shipping address", content, re.I))


def priority_based_context(conversation: list[dict], recent_n: int) -> list[dict]:
    critical_idx = {i for i, m in enumerate(conversation) if is_critical(m["content"])}
    recent_idx = set(range(max(0, len(conversation) - recent_n), len(conversation)))
    return [conversation[i] for i in sorted(critical_idx | recent_idx)]


def run_strategy(label: str, trimmed: list[dict]):
    full_tokens = sum(len(encoding.encode(m["content"])) for m in CONVERSATION)
    kept_tokens = sum(len(encoding.encode(m["content"])) for m in trimmed)
    has_order_number = any("ORD-88213" in m["content"] for m in trimmed)

    print("=" * 70)
    print(f"[{label}]")
    print(f"Messages kept: {len(trimmed)}/{len(CONVERSATION)}  |  Tokens kept: {kept_tokens}/{full_tokens}  |  "
          f"Order number literally in context: {has_order_number}")

    response = client.responses.create(model=MODEL, input=trimmed + [{"role": "user", "content": FOLLOW_UP_QUESTION}])
    print(f"Answer: {response.output_text}\n")


if __name__ == "__main__":
    run_strategy("1. Sliding Window (last 6 messages)", sliding_window(CONVERSATION, window_size=6))
    run_strategy("2. Summarization (summarize all but the last 4)", summarization(CONVERSATION, keep_last=4))
    run_strategy("3. Semantic Retrieval (top 4 relevant to the follow-up question)",
                 semantic_retrieval(CONVERSATION, FOLLOW_UP_QUESTION, top_k=4))
    run_strategy("4. Token-Based Trimming (200-token budget)", token_based_trimming(CONVERSATION, max_tokens=200))
    run_strategy("5. Priority-Based Context (critical facts + last 4)", priority_based_context(CONVERSATION, recent_n=4))
