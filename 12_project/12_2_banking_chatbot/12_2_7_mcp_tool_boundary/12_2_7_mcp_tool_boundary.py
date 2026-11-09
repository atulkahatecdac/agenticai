import asyncio
import csv
import operator
import os
import sys
from typing import Annotated, Literal, TypedDict

import streamlit as st
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.types import Send
from pydantic import BaseModel, Field

load_dotenv(override=True)

# Unlike every earlier step, this file no longer imports mock_bank directly -
# that's the whole point of this step. Only the three MCP server subprocess
# files (accounts_mcp_server.py etc.) touch mock_bank now; this file just
# knows their paths, on the sys.executable subprocess command line below.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# =====================================================================
# Step 7 - Move Accounts/Transaction/Service's tool implementations out
# of this process entirely, into three separate MCP servers
# (accounts_mcp_server.py, transaction_mcp_server.py,
# service_mcp_server.py - one stdio subprocess each), following
# 6_mcp/6_22_langgraph_agent_mcp_tools.py's MultiServerMCPClient
# pattern. The seven @tool-decorated functions from step 6 are gone
# from this file - only their MCP server counterparts remain, and this
# file now just asks the MCP client for whatever tools each server
# exposes. Upgrading a banking API backend now only means changing the
# relevant server file; this agent file doesn't change. FAQ Agent is
# unchanged - MCP is a tool-calling concept, and FAQ has no tools, only
# a retriever, so there's nothing to move for it.
#
# MCP tools from langchain_mcp_adapters are async-only, so
# make_specialist_agent's agent node became `async def` (llm_with_tools
# .ainvoke instead of .invoke), and the coordinator's run_specialist -
# itself a plain sync function called inside a Send-dispatch worker
# thread - now runs each specialist via asyncio.run(app.ainvoke(...))
# instead of app.invoke(...). The coordinator graph itself is still
# invoked synchronously from the Streamlit UI (coordinator_app.invoke) -
# only the inner specialist graphs needed to become async-invokable.
# =====================================================================

MCP_SERVERS = {
    "accounts": {
        "transport": "stdio",
        "command": sys.executable,
        "args": [os.path.join(BASE_DIR, "accounts_mcp_server.py")],
    },
    "transaction": {
        "transport": "stdio",
        "command": sys.executable,
        "args": [os.path.join(BASE_DIR, "transaction_mcp_server.py")],
    },
    "service": {
        "transport": "stdio",
        "command": sys.executable,
        "args": [os.path.join(BASE_DIR, "service_mcp_server.py")],
    },
}

mcp_client = MultiServerMCPClient(MCP_SERVERS)


@st.cache_resource(show_spinner=False)
def load_mcp_tools() -> dict:
    # show_spinner is off deliberately - same NoSessionContext reason as
    # load_faq_vectordb below: this can be called from inside a Send-dispatch
    # worker thread on cache misses after the process has been running a while.
    tools = asyncio.run(mcp_client.get_tools())
    return {t.name: t for t in tools}


mcp_tools = load_mcp_tools()

# Appended to every specialist prompt below. Found via manual testing: when a
# single customer message mixes an in-scope topic with an out-of-scope one
# (e.g. "tell me my last transaction and address" dispatched to both
# Transaction and Service agents), a specialist would treat the WHOLE message
# as "not really mine" and decline even its own in-scope part, instead of
# answering what it actually could. That defeats the point of dispatching to
# multiple specialists in the first place - synthesize can't merge an answer
# a specialist never gave.
COMPOUND_REQUEST_NOTE = (
    " The customer's message may ask about several things at once, only some "
    "of which are yours to handle - a coordinator has already dispatched this "
    "same message to whichever other specialists are needed for the rest. "
    "Still fully answer the part that IS in your scope, using your tools - "
    "don't decline your own part just because the message also mentions "
    "something outside your scope."
)

# Also found via manual testing - the opposite failure mode from
# COMPOUND_REQUEST_NOTE above: asked for just "my last transaction and
# address", the Transaction Agent pulled a full 30-day statement (closing
# balance included) instead of the single most recent transaction, and the
# Service Agent's get_service_details tool returns address + cheque book
# status + KYC status together, so the reply volunteered all three when only
# the address was asked for. A tool returning more than was asked for is not
# a reason to report all of it.
CONCISE_ANSWER_NOTE = (
    " Only report the specific information the customer actually asked for. "
    "If a tool call returns more than that (e.g. a full statement when they "
    "only asked for the last transaction, or address + cheque book status + "
    "KYC status together when they only asked about one of those), mention "
    "only the part they asked about and leave the rest out unless they ask "
    "for it too."
)

ACCOUNTS_PROMPT = (
    "You are the Accounts specialist agent for a bank. You have exactly one tool: "
    "get_account_balance. You only handle balance enquiries. If asked about "
    "anything else, clearly say that is outside your scope - do not attempt it "
    "and do not guess. Never guess a customer ID - ask for it if missing."
    + COMPOUND_REQUEST_NOTE
    + CONCISE_ANSWER_NOTE
)

TRANSACTION_PROMPT = (
    "You are the Transaction specialist agent for a bank. You have two tools: "
    "get_transaction_details (use count=1 if the customer asks for just their "
    "last/most recent transaction, or a higher count if they ask for several) "
    "and request_statement (only use this if they explicitly ask for a "
    "statement, not for a single transaction). You only handle transaction "
    "history and statement requests. If asked about anything else, clearly say "
    "that is outside your scope - do not attempt it. Never guess a customer ID - "
    "ask for it if missing."
    + COMPOUND_REQUEST_NOTE
    + CONCISE_ANSWER_NOTE
)

SERVICE_PROMPT = (
    "You are the Service specialist agent for a bank. You have four tools: "
    "get_service_details (look up current address, cheque book status, and KYC "
    "status), change_of_address, request_cheque_book, update_kyc. Use "
    "get_service_details whenever the customer asks what their current address, "
    "cheque book status, or KYC status IS, rather than asking them to change "
    "something - only use the other three tools when they want to actually "
    "change/request/update something. You only handle service operations. If "
    "asked about anything else, clearly say that is outside your scope - do not "
    "attempt it. Never guess a customer ID - ask for it if missing."
    + COMPOUND_REQUEST_NOTE
    + CONCISE_ANSWER_NOTE
)

FAQ_PROMPT = (
    "You are the FAQ specialist agent for a bank. Answer general banking "
    "questions (how to open an account, lost-card procedures, loan process, "
    "policies, etc.) using ONLY the FAQ context you are given for this turn - "
    "never use outside knowledge, and never make up an answer that isn't in the "
    "context. If the context says no matching FAQ entry was found, say plainly "
    "that you don't have information on that - do not guess. You do not have "
    "access to any customer's real account data."
    + COMPOUND_REQUEST_NOTE
    + CONCISE_ANSWER_NOTE
)


class ChatState(TypedDict):
    messages: Annotated[list, add_messages]


def make_specialist_agent(tools: list):
    """Factory mirroring 14_advanced/07_langgraph/07_4_conditional_routing_specialists.py's
    make_specialist(): every specialist shares the same underlying LLM and the same
    agent/tools loop - what makes each one a "specialist" is purely which tools it's
    bound to and what its system prompt says it may do, nothing structural. The
    agent node is async here because MCP tools (from langchain_mcp_adapters) only
    support async invocation - ToolNode picks the sync or async tool-call path based
    on whether the GRAPH is invoked via .invoke() or .ainvoke(), so this graph must
    always be run with .ainvoke()."""
    llm_with_tools = llm.bind_tools(tools)

    async def agent(state: ChatState) -> ChatState:
        return {"messages": [await llm_with_tools.ainvoke(state["messages"])]}

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
# 14_advanced/07_langgraph/07_5_message_graph_bank_faq.py. Unchanged from
# step 6 - no MCP tools involved, plain sync nodes. LangGraph runs sync
# nodes fine even when the compiled graph is invoked via .ainvoke()
# (used uniformly for every specialist in run_specialist below), so
# this graph didn't need to change to stay compatible.
# ---------------------------------------------------------------------
FAQ_SIMILARITY_THRESHOLD = 0.3


@st.cache_resource(show_spinner=False)
def load_faq_vectordb():
    # show_spinner is off deliberately: run_specialist (below) executes inside
    # LangGraph's Send-dispatch worker thread, which has no Streamlit script
    # context, so a spinner update from in here raises NoSessionContext.
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
    "accounts": {
        "name": "Accounts Agent",
        "app": make_specialist_agent([mcp_tools["get_account_balance"]]),
        "system_prompt": ACCOUNTS_PROMPT,
    },
    "transaction": {
        "name": "Transaction Agent",
        "app": make_specialist_agent(
            [mcp_tools["get_transaction_details"], mcp_tools["request_statement"]]
        ),
        "system_prompt": TRANSACTION_PROMPT,
    },
    "service": {
        "name": "Service Agent",
        "app": make_specialist_agent(
            [
                mcp_tools["get_service_details"],
                mcp_tools["change_of_address"],
                mcp_tools["request_cheque_book"],
                mcp_tools["update_kyc"],
            ]
        ),
        "system_prompt": SERVICE_PROMPT,
    },
    "faq": {"name": "FAQ Agent", "app": faq_app, "system_prompt": FAQ_PROMPT},
}

# =====================================================================
# Coordinator graph: classify_intent -> (fan-out via Send) ->
# run_specialist (1-4 in parallel) -> synthesize -> END.
# classify_intent returns a LIST of specialists; dispatch_to_specialists
# turns that list into one Send per specialist, all running in the same
# superstep. specialist_replies uses operator.add as its reducer so
# replies from parallel branches accumulate instead of clobbering each
# other, exactly like flight_options/city_reports in the trip-planner
# example.
# =====================================================================


class Routing(BaseModel):
    specialists: list[Literal["accounts", "transaction", "service", "faq"]] = Field(
        description=(
            "Every specialist needed to fully answer this banking question - "
            "most questions need exactly one. Only include more than one if the "
            "question explicitly spans multiple domains (e.g. a balance question "
            "AND a transactions question in the same message needs both "
            "'accounts' and 'transaction')."
        )
    )


router_prompt = ChatPromptTemplate.from_template("""\
Here is the conversation so far between a bank customer and the assistant:

{transcript}

Identify which specialist(s) are needed to answer the customer's MOST RECENT \
message, using the conversation above for context. Most messages need exactly \
ONE specialist - only include more than one if the message explicitly asks for \
multiple distinct things at once. A topic merely sounding related to a \
specialist's domain is not a reason to include it - only include a specialist \
if the message needs THAT specialist's own capability.

A short reply with no question in it (e.g. just a customer ID or an address) is \
usually answering something the assistant asked for in the immediately preceding \
turn - route it to whichever specialist needed that missing information, not to \
faq just because it isn't phrased as a question itself.

- accounts: balance enquiries
- transaction: transaction history or statement requests
- service: address changes, cheque book requests, KYC updates
- faq: general banking questions not about this specific customer's account \
(how do I..., what is your policy on..., procedures)

Examples:
- "What is my balance?" -> accounts
- "What is my balance and show me my last 5 transactions?" -> accounts, transaction
- "Please update my address" -> service (NOT accounts, even though it's account-related)
- "How do I report a lost debit card?" -> faq (NOT service - no specific customer \
action is being requested, this is a general procedure question)
- Assistant just asked "Please provide your customer ID so I can check your \
balance", customer replies "CUST1001" -> accounts (this is the missing customer \
ID for the balance request, not a new FAQ question)""")

router_chain = router_prompt | llm.with_structured_output(Routing)


class CoordinatorState(TypedDict):
    messages: Annotated[list, add_messages]
    specialists_needed: list[str]
    specialist_replies: Annotated[list[dict], operator.add]
    final_answer: str


def format_transcript(messages: list) -> str:
    lines = []
    for m in messages:
        if isinstance(m, HumanMessage):
            lines.append(f"Customer: {m.content}")
        elif isinstance(m, AIMessage) and m.content:
            lines.append(f"Assistant: {m.content}")
    return "\n".join(lines)


def classify_intent(state: CoordinatorState) -> dict:
    transcript = format_transcript(state["messages"])
    # See 12_2_5_rag_faq_agent.py's route() for why the # type: ignore is needed -
    # with_structured_output's return type isn't fully resolved by static analysis.
    result = router_chain.invoke({"transcript": transcript})
    return {"specialists_needed": result.specialists}  # type: ignore[union-attr]


def dispatch_to_specialists(state: CoordinatorState) -> list[Send]:
    return [
        Send("run_specialist", {"specialist_key": key, "messages": state["messages"]})
        for key in state["specialists_needed"]
    ]


def run_specialist(state: dict) -> dict:
    info = SPECIALISTS[state["specialist_key"]]
    specialist_input = [SystemMessage(content=info["system_prompt"])] + state["messages"]
    # Every specialist graph is invoked via ainvoke, not invoke - required for
    # the MCP-backed ones (accounts/transaction/service) since their ToolNode
    # only supports async tool calls; the FAQ graph's plain sync nodes run fine
    # under ainvoke too, so one calling convention covers all four uniformly.
    # This function itself stays a plain sync callable (LangGraph's Send
    # dispatch calls it synchronously from a worker thread), so asyncio.run()
    # gives that thread its own fresh event loop with no conflict.
    result = asyncio.run(info["app"].ainvoke({"messages": specialist_input}))
    return {"specialist_replies": [{"specialist": info["name"], "reply": result["messages"][-1].content}]}


def synthesize(state: CoordinatorState) -> dict:
    replies = state["specialist_replies"]
    if len(replies) == 1:
        final = replies[0]["reply"]
    else:
        replies_text = "\n\n".join(f"{r['specialist']}: {r['reply']}" for r in replies)
        prompt = (
            "Combine these specialist responses into ONE clear, natural answer for "
            "the customer. Don't mention the specialist names or that multiple "
            "agents were involved - just answer directly, preserving every factual "
            f"detail from each response:\n\n{replies_text}"
        )
        final = llm.invoke(prompt).content
    return {"final_answer": final, "messages": [AIMessage(content=final)]}


graph = StateGraph(CoordinatorState)
graph.add_node("classify_intent", classify_intent)
graph.add_node("run_specialist", run_specialist)
graph.add_node("synthesize", synthesize)
graph.add_edge(START, "classify_intent")
graph.add_conditional_edges("classify_intent", dispatch_to_specialists, ["run_specialist"])
graph.add_edge("run_specialist", "synthesize")
graph.add_edge("synthesize", END)
coordinator_app = graph.compile()

# =====================================================================
# Streamlit web UI - unchanged from step 6. Same shared chat, same
# routing caption. Nothing about the UI needed to change for the MCP
# boundary - exactly the point: tool implementations moved, the agent
# (and the UI built on top of it) didn't.
# =====================================================================

st.set_page_config(page_title="Banking Assistant - Step 7", page_icon="\U0001F3E6")
st.title("Banking Assistant — Step 7: MCP Tool Boundary")
st.caption(
    "Accounts, Transaction and Service tools now live behind three separate MCP "
    "servers (subprocesses), not in this file. Same coordinator, same UI - proving "
    "tool changes no longer require agent code changes."
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
            st.caption(f"→ routed to {' + '.join(st.session_state.routing_log[ai_index])}")
        ai_index += 1

user_input = st.chat_input("Ask a banking question...")
if user_input:
    st.session_state.messages.append(HumanMessage(content=user_input))
    with st.chat_message("user"):
        st.write(user_input)
    with st.chat_message("assistant"):
        with st.spinner("Routing and thinking..."):
            result = coordinator_app.invoke(
                {
                    "messages": st.session_state.messages,
                    "specialists_needed": [],
                    "specialist_replies": [],
                    "final_answer": "",
                }
            )
        st.session_state.messages = result["messages"]
        routed_names = [r["specialist"] for r in result["specialist_replies"]]
        st.session_state.routing_log.append(routed_names)
        st.write(result["final_answer"])
        st.caption(f"→ routed to {' + '.join(routed_names)}")
