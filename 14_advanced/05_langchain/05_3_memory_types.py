import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.messages import get_buffer_string
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

load_dotenv(override=True)

llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)

# The old ConversationBufferMemory / ConversationSummaryMemory /
# VectorStoreRetrieverMemory classes are deprecated (and removed in
# LangChain 1.0). The three IDEAS behind them are still the main ways to
# give a chatbot memory, and each takes only a few lines with today's
# building blocks: a message history, an LCEL chain, and a vector store.

# -----------------------------
# 1. Buffer memory
# Stores every turn verbatim, in order. Simple and lossless, but grows
# unbounded - every past message gets resent to the LLM on every call,
# so token cost climbs with conversation length.
# -----------------------------
print("=" * 70)
print("1. Buffer memory - stores every turn verbatim")
print("=" * 70)

buffer_history = InMemoryChatMessageHistory()
buffer_history.add_user_message("Hi, I'd like to check the status of my order #12345.")
buffer_history.add_ai_message("Sure! Your order is out for delivery and should arrive today.")
buffer_history.add_user_message("Great, can you also change the delivery address on that order?")
buffer_history.add_ai_message("Yes, please share the new address and I'll update it right away.")

# This list of messages is exactly what would be sent to the LLM next turn
# (05_4_persistent_chatbot.py plugs a history like this into a chain).
print(get_buffer_string(buffer_history.messages))

# -----------------------------
# 2. Summary memory
# Instead of storing raw turns, an LLM progressively rewrites a running
# summary after each turn. Size stays roughly constant regardless of
# conversation length, at the cost of an LLM call per turn and losing
# verbatim wording/detail.
# -----------------------------
print("\n" + "=" * 70)
print("2. Summary memory - condenses history via an LLM")
print("=" * 70)

summarize = (
    ChatPromptTemplate.from_template(
        "Progressively summarize the conversation, adding to the previous "
        "summary and returning a new summary of 2-3 sentences.\n\n"
        "Current summary:\n{summary}\n\n"
        "New lines of conversation:\n{new_lines}\n\n"
        "New summary:"
    )
    | llm
    | StrOutputParser()
)

def save_turn(summary: str, user: str, ai: str) -> str:
    return summarize.invoke({"summary": summary or "(empty)",
                             "new_lines": f"Human: {user}\nAI: {ai}"})

summary = ""
summary = save_turn(summary, "Hi, I ordered a blender last week but it arrived damaged.",
                    "I'm sorry to hear that! Would you like a replacement or a refund?")
summary = save_turn(summary, "I'd like a replacement please.",
                    "Done - a replacement blender is on its way and should arrive in 3 days.")
summary = save_turn(summary, "Also, do you offer next-day delivery for future orders?",
                    "Yes, next-day delivery is available at checkout for an extra fee.")

print(summary)

# -----------------------------
# 3. Vector-store memory
# Stores each turn as an embedding in a vector store and, given a new
# input, retrieves only the top-k most SIMILAR past turns - not the most
# recent ones. Good for long-term recall across a long history where most
# of it is irrelevant to the current question.
# -----------------------------
print("\n" + "=" * 70)
print("3. Vector-store memory - retrieves relevant past turns by similarity")
print("=" * 70)

embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# A support chatbot session covering six unrelated turns about one order
turns = [
    ("I bought a laptop from your store last week.",
     "Thanks for letting us know - how can I help with your laptop?"),
    ("What is your return policy?",
     "You can return any product within 30 days of purchase for a full refund."),
    ("The laptop battery is not working properly.",
     "Sorry to hear that - let's get that battery issue looked into."),
    ("What are the delivery charges?",
     "Delivery is free for orders above Rs. 999, otherwise it's Rs. 99."),
    ("I want to replace the laptop instead of repairing it.",
     "Sure, we can process a replacement for your laptop."),
    ("How do I contact customer support?",
     "You can reach our support team via email, chat, or our helpline."),
]
vectorstore = FAISS.from_texts([f"input: {u}\noutput: {a}" for u, a in turns], embeddings)
retriever = vectorstore.as_retriever(search_kwargs={"k": 2})

# The query below is about the battery (turn 3) - notice the retriever
# pulls that turn back even though turn 6 (asking how to contact support)
# is far more recent: similarity, not recency, decides what comes back
query = "My laptop battery drains really fast, what should I do?"
print(f"Query: '{query}'")
for doc in retriever.invoke(query):
    print(doc.page_content)
