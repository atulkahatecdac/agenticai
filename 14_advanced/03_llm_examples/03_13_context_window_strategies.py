import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)

import sys
import tiktoken
from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, trim_messages
from langchain_openai import ChatOpenAI

load_dotenv(override=True)
sys.stdout.reconfigure(encoding="utf-8")

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
enc = tiktoken.get_encoding("o200k_base")      # the gpt-4o family's tokenizer


def count_tokens(messages) -> int:
    return sum(len(enc.encode(m.content)) for m in messages)


# =====================================================================
# Context management: three ways to keep a request inside the context
# window (and the bill small) when the conversation or document grows.
#
#   1. Windowing     - keep only the most recent turns
#   2. Summarisation - replace old turns with a short summary
#   3. Chunking      - split a long document, process pieces, combine
# =====================================================================

# A long support conversation: 20 turns about one laptop order.
history = [SystemMessage("You are a helpful support agent for an electronics shop.")]
history += [HumanMessage("Hi, my order is ORD-4471, a 14-inch laptop. My name is Priya.")]
history += [AIMessage("Thanks Priya, I can see order ORD-4471 for the 14-inch laptop.")]
for i in range(1, 10):
    history += [HumanMessage(f"Question {i}: does the laptop support feature number {i}? Please explain in detail.")]
    history += [AIMessage(f"Yes - feature {i} is supported. " + "It works as described in the manual. " * 12)]
question = HumanMessage("Remind me - what is my order number and my name?")

print("=" * 70)
print(f"Full history: {len(history)} messages, {count_tokens(history)} tokens")
print("=" * 70)

# ---------------------------------------------------------------------
# 1. WINDOWING - trim_messages keeps the newest messages that fit in a
#    token budget. Cheap and simple, but the oldest facts fall out:
#    the order number and name were in turn 1.
# ---------------------------------------------------------------------
windowed = trim_messages(
    history,
    max_tokens=400,
    token_counter=count_tokens,
    strategy="last",          # keep the end of the conversation
    include_system=True,      # but always keep the system prompt
    start_on="human",         # never start on an orphaned AI reply
)
print(f"\n1. WINDOWING  -> {len(windowed)} messages, {count_tokens(windowed)} tokens")
print("   Answer:", llm.invoke(windowed + [question]).content)

# ---------------------------------------------------------------------
# 2. SUMMARISATION - fold the older turns into one summary message and
#    keep the last few turns verbatim. Costs one extra LLM call, but
#    keeps the important facts.
# ---------------------------------------------------------------------
old, recent = history[1:-4], history[-4:]
# Send the old turns as ONE transcript to summarise - passed as chat
# messages, the model tends to carry on the conversation instead.
transcript = "\n".join(f"{m.type}: {m.content}" for m in old)
summary = llm.invoke(
    "Summarise this support conversation in 2 sentences. "
    f"Keep every name, ID and number.\n\n{transcript}"
).content
summarised = [history[0], SystemMessage(f"Summary of the earlier conversation: {summary}")] + recent
print(f"\n2. SUMMARISATION -> {len(summarised)} messages, {count_tokens(summarised)} tokens")
print("   Summary:", summary)
print("   Answer:", llm.invoke(summarised + [question]).content)

# ---------------------------------------------------------------------
# 3. CHUNKING (map-reduce) - a document too long for one call is split,
#    each chunk is summarised on its own (map), then the partial
#    summaries are combined (reduce).
# ---------------------------------------------------------------------
document = "\n".join(
    f"Section {i}: The warranty covers part {i} for {i % 3 + 1} year(s). "
    + "Standard terms and conditions apply to this section. " * 15
    for i in range(1, 9)
)
words = document.split()
chunks = [" ".join(words[i:i + 250]) for i in range(0, len(words), 250)]
print(f"\n3. CHUNKING -> document of {len(enc.encode(document))} tokens split into {len(chunks)} chunks")
partials = [llm.invoke(f"In one sentence, list the parts and warranty years in:\n{c}").content for c in chunks]
final = llm.invoke("Combine these notes into one short list of part -> years:\n" + "\n".join(partials)).content
print("   Combined:", final)

print("\nWhich to use: windowing for chit-chat, summarisation when early facts matter,")
print("chunking (or RAG - Module 04) when one document is bigger than the window.")
