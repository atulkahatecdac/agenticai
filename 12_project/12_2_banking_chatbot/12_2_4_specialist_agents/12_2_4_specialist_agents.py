import os
import sys
from typing import Annotated, TypedDict

import streamlit as st
from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

load_dotenv(override=True)

# mock_bank.py lives one directory up, shared across every step from here on.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(BASE_DIR))
import mock_bank  # noqa: E402

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# =====================================================================
# Step 4 - Split the one unscoped agent from step 3 into three domain
# specialists, each bound to only its own tools. There is deliberately
# NO coordinator yet (that's step 6, after step 5 adds a fourth - RAG -
# specialist) - nothing in this script picks which specialist handles a
# request. The UI makes that gap visible by requiring a human to pick
# the specialist manually, exactly the problem slide 7 surfaces: "who
# decides which specialist to call?"
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
    "transactions, statements, address changes, cheque books, or KYC, clearly say "
    "that is outside your scope and the customer should talk to the Transaction "
    "Agent or Service Agent instead - do not attempt it and do not guess. Never "
    "guess a customer ID - ask for it if missing."
)

TRANSACTION_PROMPT = (
    "You are the Transaction specialist agent for a bank. You have two tools: "
    "get_transaction_details and request_statement. You only handle transaction "
    "history and statement requests. If asked about balances, address changes, "
    "cheque books, or KYC, clearly say that is outside your scope and the customer "
    "should talk to the Accounts Agent or Service Agent instead - do not attempt "
    "it. Never guess a customer ID - ask for it if missing."
)

SERVICE_PROMPT = (
    "You are the Service specialist agent for a bank. You have three tools: "
    "change_of_address, request_cheque_book, update_kyc. You only handle service "
    "operations - address changes, cheque book requests, and KYC updates. If asked "
    "about balances, transactions, or statements, clearly say that is outside your "
    "scope and the customer should talk to the Accounts Agent or Transaction Agent "
    "instead - do not attempt it. Never guess a customer ID - ask for it if missing."
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


SPECIALISTS = {
    "Accounts Agent": {
        "app": make_specialist_agent([get_account_balance]),
        "system_prompt": ACCOUNTS_PROMPT,
        "scope": "Balance Enquiry only",
    },
    "Transaction Agent": {
        "app": make_specialist_agent([get_transaction_details, request_statement]),
        "system_prompt": TRANSACTION_PROMPT,
        "scope": "Transaction Details + Statement Request",
    },
    "Service Agent": {
        "app": make_specialist_agent([change_of_address, request_cheque_book, update_kyc]),
        "system_prompt": SERVICE_PROMPT,
        "scope": "Change of Address + Cheque Book Request + KYC Update",
    },
}

# =====================================================================
# Streamlit web UI. A selectbox stands in for the missing coordinator -
# a human has to pick the specialist, which is exactly what step 6 (the
# coordinator) will automate. Each specialist keeps its own independent
# conversation history, proving isolation: nothing said to one is
# visible to another.
# =====================================================================

st.set_page_config(page_title="Banking Assistant - Step 4", page_icon="\U0001F3E6")
st.title("Banking Assistant — Step 4: Specialist Agents")
st.caption(
    "Three domain-scoped specialists, each with only its own tools. There is no "
    "coordinator yet - you are the router. That's the gap step 6 closes."
)

if "histories" not in st.session_state:
    histories: dict = {
        name: [SystemMessage(content=info["system_prompt"])] for name, info in SPECIALISTS.items()
    }
    st.session_state.histories = histories

active_specialist = st.selectbox("Choose which specialist to talk to", list(SPECIALISTS))
st.caption(f"Scope: {SPECIALISTS[active_specialist]['scope']}")

history = st.session_state.histories[active_specialist]
for message in history:
    if isinstance(message, HumanMessage):
        with st.chat_message("user"):
            st.write(message.content)
    elif isinstance(message, AIMessage) and message.content:
        with st.chat_message("assistant"):
            st.write(message.content)

user_input = st.chat_input("Ask this specialist...")
if user_input:
    history.append(HumanMessage(content=user_input))
    with st.chat_message("user"):
        st.write(user_input)
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            result = SPECIALISTS[active_specialist]["app"].invoke({"messages": history})
        st.session_state.histories[active_specialist] = result["messages"]
        st.write(result["messages"][-1].content)
