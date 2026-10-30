import os
'''
Step-by-step explanation of how this chatbot works

1. User enters a question
   The user can ask a banking-related question in any natural wording.
   Example: "lost my debit card", "cannot find debit card", "debit card stolen"

2. Query normalization
   Every incoming user question is converted into a single canonical intent.
   This is done using an LLM-based normalizer so that different phrasings map
   to the same banking FAQ question.
   Example:
   - "lost my debit card"
   - "debit card missing"
   - "cannot find my debit card"
   All become:
   "How do I report a lost or stolen debit card?"

3. Canonical intent as the single key
   The canonical question is used consistently as:
   - the lookup key for short-term memory
   - the query for vector database similarity search

4. Short-term memory lookup
   The chatbot first checks an in-memory LRU cache using the canonical intent.
   If the same intent has already been answered in the current session,
   the stored answer is returned immediately without calling the vector database.

5. Vector database search
   If the intent is not found in short-term memory:
   - The canonical question is embedded
   - A similarity search is performed against the Chroma vector database
   - The closest matching FAQ entry is retrieved

6. Confidence threshold
   The similarity distance is checked against a threshold.
   If the match is weak, the answer is rejected to avoid incorrect responses.

7. Memory update
   When a valid answer is found from the vector database:
   - The answer is stored in short-term memory using the canonical intent
   - Future paraphrases of the same intent will hit STM directly

8. Response returned to the user
   The chatbot returns:
   - the final answer
   - the source of the answer (short_term_memory or vector_db)

This design ensures consistent intent handling, efficient reuse of answers,
minimal vector database calls, and deterministic behavior across paraphrases.
'''

# pip install langchain-huggingface langchain-chroma

from typing import TypedDict, Optional
from collections import OrderedDict
import pandas as pd

from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
import chromadb
from chromadb.config import Settings

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

load_dotenv(override=True)

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)

MAX_STM_ENTRIES = 500
VECTOR_DISTANCE_THRESHOLD = 0.7

CSV_PATH = os.path.join(BASE_DIR, "Dataset_banking_chatbot.csv")
PERSIST_DIR = os.path.join(BASE_DIR, "banking_chromadb")
COLLECTION_NAME = "chroma_bank_faq"

class ShortTermMemory:
    def __init__(self, max_size=500):
        self.cache = OrderedDict()
        self.max_size = max_size

    def get(self, key: str):
        if key not in self.cache:
            return None

        self.cache.move_to_end(key)
        return self.cache[key]

    def put(self, key: str, answer: str):
        self.cache[key] = answer
        self.cache.move_to_end(key)

        if len(self.cache) > self.max_size:
            self.cache.popitem(last=False)

stm = ShortTermMemory(MAX_STM_ENTRIES)

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-mpnet-base-v2"
)

df = pd.read_csv(CSV_PATH, encoding="latin-1")
texts = df["Query"].astype(str).tolist()
metadatas = df[["Query", "Response"]].to_dict(orient="records")

client = chromadb.PersistentClient(
    path=PERSIST_DIR,
    settings=Settings()
)

# If collection already exists, use it
if COLLECTION_NAME in [c.name for c in client.list_collections()]:
    vectordb = Chroma(
        persist_directory=PERSIST_DIR,
        embedding_function=embeddings,
        collection_name=COLLECTION_NAME
    )
else: # If collection doesn't exist, create it
    vectordb = Chroma.from_texts(
        texts=texts,
        embedding=embeddings,
        metadatas=metadatas,
        collection_name=COLLECTION_NAME,
        persist_directory=PERSIST_DIR
    )
    # vectordb.persist()

class ChatState(TypedDict):
    question: str
    normalized_question: Optional[str]
    answer: Optional[str]
    found: bool
    source: str

# Check if the query is a canonical question, meaning it ends with a question mark
def is_canonical(q: str) -> bool:
    q = q.strip().lower()
    return q.endswith("?") and (
        q.startswith("how do i") or
        q.startswith("what is") or
        q.startswith("how can i")
    )

def normalize_query(q: str) -> str:
    
    # If the query is already canonical, return it without normalization
    if is_canonical(q):
        return q

    prompt = f"""
You are an intent normalizer for a banking FAQ system.

Convert the user query into ONE canonical intent question.
Rules:
- Use the SAME wording every time for the same intent
- Prefer existing banking FAQ-style questions
- Do NOT invent new intent variants

Canonical examples:
- Debit card lost → "How do I report a lost or stolen debit card?"
- Debit card missing → "How do I report a lost or stolen debit card?"
- Card stolen → "How do I report a lost or stolen debit card?"

User query: "{q}"

Return ONLY the canonical question.
"""
    resp = llm.invoke([HumanMessage(content=prompt)])
    normalized = resp.content.strip().strip('"')
    print(f"[Normalize] '{q}' → '{normalized}'")
    return normalized

def normalize_node(state: ChatState) -> ChatState:
    return {
        "normalized_question": normalize_query(state["question"])
    }

# Check if the question is already in short-term memory and return the answer
def stm_node(state: ChatState) -> ChatState:
    key = state["normalized_question"]
    answer = stm.get(key)
    if answer is not None:
        return {
            "answer": answer,
            "found": True,
            "source": "short_term_memory"
        }
    return {"found": False}

# Check if the question is in the vector database and return the answer
def vector_db_node(state: ChatState) -> ChatState:
    key = state["normalized_question"]

    results = vectordb.similarity_search_with_score(key, k=1)
    if not results:
        return {"found": False}

    doc, distance = results[0]
    print(f"[VectorDB] distance = {distance:.4f}")

    if distance > VECTOR_DISTANCE_THRESHOLD:
        return {"found": False}

    answer = doc.metadata["Response"]
    stm.put(key, answer)

    return {
        "answer": answer,
        "found": True,
        "source": f"vector_db (distance={distance:.3f})"
    }

def not_found_node(state: ChatState) -> ChatState:
    return {
        "answer": "I'm sorry, I couldn't find an answer for that.",
        "found": False,
        "source": "none"
    }

graph = StateGraph(ChatState)

graph.add_node("normalize", normalize_node)
graph.add_node("stm", stm_node)
graph.add_node("vector_db", vector_db_node)
graph.add_node("not_found", not_found_node)

graph.add_edge(START, "normalize")
graph.add_edge("normalize", "stm")

graph.add_conditional_edges(
    "stm",
    lambda s: END if s["found"] else "vector_db"
)

graph.add_conditional_edges(
    "vector_db",
    lambda s: END if s["found"] else "not_found"
)

graph.add_edge("not_found", END)

app = graph.compile()

if __name__ == "__main__":
    print("Banking FAQ Chatbot")
    print("Type 'exit' to quit\n")

    while True:
        q = input("You: ").strip()
        if q.lower() == "exit":
            break

        result = app.invoke({
            "question": q,
            "normalized_question": None,
            "answer": None,
            "found": False,
            "source": ""
        })

        print(f"Bot: {result['answer']}")
        print(f"[source: {result['source']}]\n")
