import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

import csv
import os
import sys
from typing import Annotated, TypedDict
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

load_dotenv(override=True)

# Tool/LLM output can contain characters outside Windows' default console
# codepage (cp1252) - reconfigure stdout to UTF-8 so printing doesn't crash.
sys.stdout.reconfigure(encoding="utf-8")

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# =====================================================================
# "Message graph" pattern for a multi-turn banking FAQ chatbot.
#
# LangGraph's own `MessageGraph` class (a StateGraph whose entire state
# is a single append-only message list) is deprecated as of LangGraph
# v1.0 in favor of exactly what's used below: a plain StateGraph whose
# state has one field typed `Annotated[list, add_messages]`. Every node
# receives the FULL running conversation and returns only the NEW
# messages it wants to add - `add_messages` merges them into the
# existing list (matching by message id for edits) rather than each
# node having to manage the whole history itself.
# =====================================================================


class ChatState(TypedDict):
    messages: Annotated[list, add_messages]


# ---------------------------------------------------------------------
# Tiny FAQ "retriever" over 3_langgraph/Dataset_Banking_chatbot.csv -
# an in-memory Chroma vector store (local HuggingFace embeddings, no
# API calls) holding the dataset's Query column, searched by
# similarity against the user's latest message.
# ---------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "..", "..", "3_langgraph", "Dataset_Banking_chatbot.csv")

faq_docs = []
with open(CSV_PATH, newline="", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        faq_docs.append(Document(page_content=row["Query"], metadata={"response": row["Response"]}))

embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
vectordb = Chroma.from_documents(faq_docs, embedding=embeddings)
SIMILARITY_THRESHOLD = 0.3


def retrieve_faq(state: ChatState) -> ChatState:
    # Only the LATEST human message drives retrieval - the rest of the
    # accumulated message list is still there for the generate node to
    # use as conversational context (see the follow-up turn below).
    last_question = state["messages"][-1].content
    results = vectordb.similarity_search_with_relevance_scores(last_question, k=1)

    if results and results[0][1] >= SIMILARITY_THRESHOLD:
        doc, score = results[0]
        context = f"Relevant FAQ answer: {doc.metadata['response']}"
        print(f'[retrieve_faq] matched "{doc.page_content}" (score={score:.2f})')
    else:
        best_score = results[0][1] if results else 0.0
        context = "No matching FAQ entry found - answer from general banking knowledge."
        print(f"[retrieve_faq] no match above threshold (best score={best_score:.2f})")

    return {"messages": [SystemMessage(content=context)]}


def generate(state: ChatState) -> ChatState:
    # The LLM sees the ENTIRE accumulated message list - every past
    # human/system/AI message - not just this turn's question.
    response = llm.invoke(state["messages"])
    return {"messages": [response]}


# ---------------------------------------------------------------------
# Graph: START -> retrieve_faq -> generate -> END
# ---------------------------------------------------------------------
graph = StateGraph(ChatState)
graph.add_node("retrieve_faq", retrieve_faq)
graph.add_node("generate", generate)
graph.add_edge(START, "retrieve_faq")
graph.add_edge("retrieve_faq", "generate")
graph.add_edge("generate", END)

app = graph.compile()

if __name__ == "__main__":
    # One long-lived conversation object, threaded turn to turn - each
    # invoke() call appends to `conversation["messages"]` rather than
    # starting fresh, which is exactly what a message graph is for.
    conversation = {"messages": []}

    turns = [
        "How do I report a lost debit card?",
        "And roughly how long until I get a replacement?",
        "What's the weather like today?",
    ]

    for turn in turns:
        print("=" * 70)
        print(f"User: {turn}")
        conversation["messages"].append(HumanMessage(content=turn))
        conversation = app.invoke(conversation)
        print(f"Assistant: {conversation['messages'][-1].content}")
        print(f"(running message count: {len(conversation['messages'])})")
