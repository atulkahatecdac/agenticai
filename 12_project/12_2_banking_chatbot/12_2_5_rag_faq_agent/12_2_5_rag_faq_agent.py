import csv
import os
import sys
from typing import Annotated, Literal, TypedDict

import streamlit as st
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel, Field

load_dotenv(override=True)

# mock_bank.py lives one directory up, shared across every step from here on.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(BASE_DIR))
import mock_bank  # noqa: E402

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# =====================================================================
# Step 5 - Add a fourth specialist: a RAG-backed FAQ/Knowledge agent.
# The deck's six banking tools only ever cover structured, per-customer
# data - they can't answer "how do I open an account?" or "what's your
# lost-card policy?", and shouldn't try to (that's exactly the kind of
# question a naive agent would otherwise hallucinate). This is the
# missing piece the original deck skipped. Structurally this specialist
# is NOT a tool-calling agent like the other three - it follows
# 14_advanced/07_langgraph/07_5_message_graph_bank_faq.py's retrieve -> generate
# shape instead, over 3_langgraph/Dataset_Banking_chatbot.csv via Chroma
# + local HuggingFace embeddings (no extra API calls).
#
# This step also removes step 4's manual specialist picker: a small
# router (structured-output classification, following
# 14_advanced/07_langgraph/07_4_conditional_routing_specialists.py) now picks
# ONE specialist per turn automatically. That's a first slice of what
# the deck calls the "coordinator" (slide 8's steps 01-02: parse intent,
# identify the specialist) - what's still missing, and what step 6 adds,
# is handling a request that needs MORE THAN ONE specialist in the same
# turn (parallel dispatch + merging results). A cross-domain question
# here still only gets the one routed specialist's partial answer.
# =====================================================================


@tool
def get_account_balance(customer_id: str) -> str:
    """Look up the current account balance for a bank customer by their customer ID."""
    result = mock_bank.get_balance(customer_id)
    if "error" in result:
        return result["error"]
    balance = mock_bank.format_inr(result["balance"])
    return f"Customer {result['name']} (ID {customer_id}) has a balance of {balance}."


@tool
def get_transaction_details(customer_id: str, count: int = 5) -> str:
    """Retrieve a bank customer's most recent transactions by their customer ID."""
    result = mock_bank.get_transactions(customer_id, count)
    if "error" in result:
        return result["error"]
    lines = [
        f"{t['date']}: {t['description']} ({mock_bank.format_inr(t['amount'])})"
        for t in result["transactions"]
    ]
    return f"Recent transactions for {result['name']} (ID {customer_id}):\n" + "\n".join(lines)


@tool
def request_statement(customer_id: str, period: str = "last 30 days") -> str:
    """Generate an account statement for a bank customer for a given period (e.g. 'last 30 days')."""
    result = mock_bank.generate_statement(customer_id, period)
    if "error" in result:
        return result["error"]
    lines = [
        f"{t['date']}: {t['description']} ({mock_bank.format_inr(t['amount'])})"
        for t in result["transactions"]
    ]
    closing = mock_bank.format_inr(result["closing_balance"])
    return (
        f"Statement for {result['name']} (ID {customer_id}), {result['period']}:\n"
        + "\n".join(lines)
        + f"\nClosing balance: {closing}"
    )


@tool
def change_of_address(customer_id: str, new_address: str) -> str:
    """Update a bank customer's mailing address by their customer ID."""
    result = mock_bank.update_address(customer_id, new_address)
    if "error" in result:
        return result["error"]
    return f"Address for {result['name']} (ID {customer_id}) updated to: {result['address']}."


@tool
def request_cheque_book(customer_id: str) -> str:
    """Request a new cheque book for a bank customer by their customer ID."""
    result = mock_bank.request_cheque_book(customer_id)
    if "error" in result:
        return result["error"]
    return (
        f"Cheque book request for {result['name']} (ID {customer_id}) status: "
        f"{result['cheque_book_status']}."
    )


@tool
def update_kyc(customer_id: str, kyc_details: str) -> str:
    """Submit updated KYC details for a bank customer by their customer ID."""
    result = mock_bank.update_kyc(customer_id, kyc_details)
    if "error" in result:
        return result["error"]
    return (
        f"KYC update for {result['name']} (ID {customer_id}) received "
        f"({result['submitted_details']}). Status: {result['kyc_status']}."
    )


ACCOUNTS_PROMPT = (
    "You are the Accounts specialist agent for a bank. You have exactly one tool: "
    "get_account_balance. You only handle balance enquiries. If asked about "
    "transactions, statements, address changes, cheque books, KYC, or general FAQ "
    "questions, clearly say that is outside your scope and name the right agent "
    "(Transaction Agent, Service Agent, or FAQ Agent) instead - do not attempt it "
    "and do not guess. Never guess a customer ID - ask for it if missing."
)

TRANSACTION_PROMPT = (
    "You are the Transaction specialist agent for a bank. You have two tools: "
    "get_transaction_details and request_statement. You only handle transaction "
    "history and statement requests. If asked about balances, address changes, "
    "cheque books, KYC, or general FAQ questions, clearly say that is outside "
    "your scope and name the right agent (Accounts Agent, Service Agent, or FAQ "
    "Agent) instead - do not attempt it. Never guess a customer ID - ask for it "
    "if missing."
)

SERVICE_PROMPT = (
    "You are the Service specialist agent for a bank. You have three tools: "
    "change_of_address, request_cheque_book, update_kyc. You only handle service "
    "operations - address changes, cheque book requests, and KYC updates. If asked "
    "about balances, transactions, statements, or general FAQ questions, clearly "
    "say that is outside your scope and name the right agent (Accounts Agent, "
    "Transaction Agent, or FAQ Agent) instead - do not attempt it. Never guess a "
    "customer ID - ask for it if missing."
)

FAQ_PROMPT = (
    "You are the FAQ specialist agent for a bank. Answer general banking "
    "questions (how to open an account, lost-card procedures, loan process, "
    "policies, etc.) using ONLY the FAQ context you are given for this turn - "
    "never use outside knowledge, and never make up an answer that isn't in the "
    "context. If the context says no matching FAQ entry was found, say plainly "
    "that you don't have information on that - do not guess. You do not have "
    "access to any customer's real account data (balance, transactions, address, "
    "cheque book, KYC) - if asked for that, say so and name the right specialist "
    "(Accounts Agent, Transaction Agent, or Service Agent) instead."
)


class ChatState(TypedDict):
    messages: Annotated[list, add_messages]


def make_specialist_agent(tools: list):
    """Factory mirroring 14_advanced/07_langgraph/07_4_conditional_routing_specialists.py's
    make_specialist(): every specialist shares the same underlying LLM and the same
    agent/tools loop - what makes each one a "specialist" is purely which tools it's
    bound to and what its system prompt says it may do, nothing structural."""
    llm_with_tools = llm.bind_tools(tools)

    def agent(state: ChatState) -> ChatState:
        return {"messages": [llm_with_tools.invoke(state["messages"])]}

    def should_continue(state: ChatState) -> str:
        return "tools" if state["messages"][-1].tool_calls else "end"

    graph = StateGraph(ChatState)
    graph.add_node("agent", agent)
    graph.add_node("tools", ToolNode(tools))
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", "end": END})
    graph.add_edge("tools", "agent")
    return graph.compile()


# ---------------------------------------------------------------------
# FAQ specialist: retrieve -> generate, following
# 14_advanced/07_langgraph/07_5_message_graph_bank_faq.py. The Chroma
# vectorstore is expensive to build (loads a local embedding model and
# embeds ~150 FAQ rows), and Streamlit reruns this whole script on every
# interaction - st.cache_resource builds it once per app process and
# reuses it across reruns instead of rebuilding it on every message.
# ---------------------------------------------------------------------
FAQ_SIMILARITY_THRESHOLD = 0.3


@st.cache_resource(show_spinner="Loading FAQ knowledge base...")
def load_faq_vectordb():
    csv_path = os.path.join(BASE_DIR, "..", "..", "..", "3_langgraph", "Dataset_Banking_chatbot.csv")
    faq_docs = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            faq_docs.append(Document(page_content=row["Query"], metadata={"response": row["Response"]}))
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    return Chroma.from_documents(faq_docs, embedding=embeddings)


def retrieve_faq(state: ChatState) -> ChatState:
    vectordb = load_faq_vectordb()
    last_question = state["messages"][-1].content
    results = vectordb.similarity_search_with_relevance_scores(last_question, k=1)
    if results and results[0][1] >= FAQ_SIMILARITY_THRESHOLD:
        doc, _ = results[0]
        context = f"Relevant FAQ answer: {doc.metadata['response']}"
    else:
        context = "No matching FAQ entry found - tell the user you don't have information on this."
    return {"messages": [SystemMessage(content=context)]}


def faq_generate(state: ChatState) -> ChatState:
    return {"messages": [llm.invoke(state["messages"])]}


faq_graph = StateGraph(ChatState)
faq_graph.add_node("retrieve_faq", retrieve_faq)
faq_graph.add_node("generate", faq_generate)
faq_graph.add_edge(START, "retrieve_faq")
faq_graph.add_edge("retrieve_faq", "generate")
faq_graph.add_edge("generate", END)
faq_app = faq_graph.compile()


SPECIALISTS = {
    "Accounts Agent": {"app": make_specialist_agent([get_account_balance]), "system_prompt": ACCOUNTS_PROMPT},
    "Transaction Agent": {
        "app": make_specialist_agent([get_transaction_details, request_statement]),
        "system_prompt": TRANSACTION_PROMPT,
    },
    "Service Agent": {
        "app": make_specialist_agent([change_of_address, request_cheque_book, update_kyc]),
        "system_prompt": SERVICE_PROMPT,
    },
    "FAQ Agent": {"app": faq_app, "system_prompt": FAQ_PROMPT},
}

# ---------------------------------------------------------------------
# Router: picks ONE specialist per turn, following
# 14_advanced/07_langgraph/07_4_conditional_routing_specialists.py.
# ---------------------------------------------------------------------
ROUTES = {
    "accounts": "Accounts Agent",
    "transaction": "Transaction Agent",
    "service": "Service Agent",
    "faq": "FAQ Agent",
}

router_prompt = ChatPromptTemplate.from_template("""\
Classify the customer's banking question below into exactly one specialist:

- accounts: balance enquiries
- transaction: transaction history or statement requests
- service: address changes, cheque book requests, KYC updates
- faq: general banking questions not about this specific customer's account \
(how do I..., what is your policy on..., procedures)

Question: {question}""")


class Routing(BaseModel):
    specialist: Literal["accounts", "transaction", "service", "faq"] = Field(
        description="Which specialist should handle this banking question."
    )


router_chain = router_prompt | llm.with_structured_output(Routing)


def route(question: str) -> str:
    # with_structured_output's return type isn't fully resolved by static
    # analysis here (same as 14_advanced/07_langgraph/07_4_conditional_routing_specialists.py) -
    # harmless at runtime, since we always pass a Pydantic class, never a dict schema.
    result = router_chain.invoke({"question": question})
    return ROUTES[result.specialist]  # type: ignore[union-attr]


# =====================================================================
# Streamlit web UI - one shared chat, no specialist picker. The router
# decides internally which specialist answers each turn; a caption
# under each reply names it, for transparency.
# =====================================================================

st.set_page_config(page_title="Banking Assistant - Step 5", page_icon="\U0001F3E6")
st.title("Banking Assistant — Step 5: RAG FAQ Agent")
st.caption(
    "Four specialists - Accounts, Transaction, Service, and a RAG-grounded FAQ "
    "agent. A router now picks one per turn automatically. It still can't split "
    "a cross-domain question across more than one specialist - that's step 6."
)

if "messages" not in st.session_state:
    empty_messages: list = []
    st.session_state.messages = empty_messages
if "routing_log" not in st.session_state:
    empty_routing_log: list = []
    st.session_state.routing_log = empty_routing_log

ai_index = 0
for message in st.session_state.messages:
    if isinstance(message, HumanMessage):
        with st.chat_message("user"):
            st.write(message.content)
    elif isinstance(message, AIMessage) and message.content:
        with st.chat_message("assistant"):
            st.write(message.content)
            st.caption(f"→ routed to {st.session_state.routing_log[ai_index]}")
        ai_index += 1

user_input = st.chat_input("Ask a banking question...")
if user_input:
    st.session_state.messages.append(HumanMessage(content=user_input))
    with st.chat_message("user"):
        st.write(user_input)
    with st.chat_message("assistant"):
        with st.spinner("Routing and thinking..."):
            specialist_name = route(user_input)
            specialist_input = [
                SystemMessage(content=SPECIALISTS[specialist_name]["system_prompt"])
            ] + st.session_state.messages
            result = SPECIALISTS[specialist_name]["app"].invoke({"messages": specialist_input})
        reply = result["messages"][-1]
        st.session_state.messages.append(reply)
        st.session_state.routing_log.append(specialist_name)
        st.write(reply.content)
        st.caption(f"→ routed to {specialist_name}")
