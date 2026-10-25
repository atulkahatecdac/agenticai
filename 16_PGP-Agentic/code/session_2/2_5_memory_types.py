import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.memory import (
    ConversationBufferMemory,
    ConversationSummaryMemory,
    VectorStoreRetrieverMemory,
)
from langchain_core._api.deprecation import (
    LangChainDeprecationWarning,
    LangChainPendingDeprecationWarning,
)

# langchain_core re-enables its own deprecation warnings on import (it calls
# warnings.filterwarnings("default", ...) internally), which runs AFTER our
# filters above and so overrides them. Re-apply "ignore" now that the import
# has happened, so ours is the one that wins.
warnings.filterwarnings("ignore", category=LangChainDeprecationWarning)
warnings.filterwarnings("ignore", category=LangChainPendingDeprecationWarning)

load_dotenv(override=True)

llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)

# -----------------------------
# 1. ConversationBufferMemory
# Stores every turn verbatim, in order. Simple and lossless, but grows
# unbounded - every past message gets resent to the LLM on every call,
# so token cost climbs with conversation length.
# -----------------------------
print("=" * 70)
print("1. ConversationBufferMemory - stores every turn verbatim")
print("=" * 70)

buffer_memory = ConversationBufferMemory()
buffer_memory.save_context(
    {"input": "Hi, I'd like to check the status of my order #12345."},
    {"output": "Sure! Your order is out for delivery and should arrive today."},
)
buffer_memory.save_context(
    {"input": "Great, can you also change the delivery address on that order?"},
    {"output": "Yes, please share the new address and I'll update it right away."},
)

print(buffer_memory.load_memory_variables({})["history"])

# -----------------------------
# 2. ConversationSummaryMemory
# Instead of storing raw turns, asks an LLM to progressively rewrite a
# running summary after each turn. Size stays roughly constant regardless
# of conversation length, at the cost of an LLM call per turn and losing
# verbatim wording/detail.
# -----------------------------
print("\n" + "=" * 70)
print("2. ConversationSummaryMemory - condenses history via an LLM")
print("=" * 70)

summary_memory = ConversationSummaryMemory(llm=llm)
summary_memory.save_context(
    {"input": "Hi, I ordered a blender last week but it arrived damaged."},
    {"output": "I'm sorry to hear that! Would you like a replacement or a refund?"},
)
summary_memory.save_context(
    {"input": "I'd like a replacement please."},
    {"output": "Done - a replacement blender is on its way and should arrive in 3 days."},
)
summary_memory.save_context(
    {"input": "Also, do you offer next-day delivery for future orders?"},
    {"output": "Yes, next-day delivery is available at checkout for an extra fee."},
)

print(summary_memory.load_memory_variables({})["history"])

# -----------------------------
# 3. VectorStoreRetrieverMemory
# Stores each turn as an embedding in a vector store and, given a new
# input, retrieves only the top-k most SIMILAR past turns - not the most
# recent ones. Good for long-term recall across a long history where most
# of it is irrelevant to the current question.
# -----------------------------
print("\n" + "=" * 70)
print("3. VectorStoreRetrieverMemory - retrieves relevant past turns by similarity")
print("=" * 70)

embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
# FAISS needs at least one text to initialize the index
vectorstore = FAISS.from_texts(["memory store initialized"], embeddings)
retriever = vectorstore.as_retriever(search_kwargs={"k": 2})
vector_memory = VectorStoreRetrieverMemory(retriever=retriever)

# A support chatbot session covering six unrelated turns about one order
vector_memory.save_context(
    {"input": "I bought a laptop from your store last week."},
    {"output": "Thanks for letting us know - how can I help with your laptop?"},
)
vector_memory.save_context(
    {"input": "What is your return policy?"},
    {"output": "You can return any product within 30 days of purchase for a full refund."},
)
vector_memory.save_context(
    {"input": "The laptop battery is not working properly."},
    {"output": "Sorry to hear that - let's get that battery issue looked into."},
)
vector_memory.save_context(
    {"input": "What are the delivery charges?"},
    {"output": "Delivery is free for orders above Rs. 999, otherwise it's Rs. 99."},
)
vector_memory.save_context(
    {"input": "I want to replace the laptop instead of repairing it."},
    {"output": "Sure, we can process a replacement for your laptop."},
)
vector_memory.save_context(
    {"input": "How do I contact customer support?"},
    {"output": "You can reach our support team via email, chat, or our helpline."},
)

# The query below is about the battery (turn 3) - notice the retriever
# pulls that turn back even though turn 6 (asking how to contact support)
# is far more recent: similarity, not recency, decides what comes back
query = "My laptop battery drains really fast, what should I do?"
print(f"Query: '{query}'")
print(vector_memory.load_memory_variables({"prompt": query})["history"])
