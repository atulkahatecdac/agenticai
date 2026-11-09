import asyncio
import csv
import operator
import os
import sqlite3
import sys
from typing import Annotated, Literal, TypedDict

import streamlit as st
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import StructuredTool
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.types import Send
from pydantic import BaseModel, Field

load_dotenv(override=True)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(BASE_DIR))
import mock_idp  # noqa: E402

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# =====================================================================
# Step 8 - Two things land together, as they do in the deck (slides
# 10-11):
#
# 1. AUTHENTICATION. A login gate (mock_idp.authenticate) replaces
#    trusting whatever customer ID appears in chat text. Every specialist
#    call is now scoped SERVER-SIDE via scope_tool_to_customer() below -
#    the LLM's own customer_id argument, if it supplies one, is silently
#    discarded and overridden with the authenticated session's ID. This
#    is a real fix, not cosmetic: since step 2, any customer could type
#    a DIFFERENT customer's ID and the tools would have trusted it. It
#    also removes the "please provide your customer ID" friction that's
#    been in every specialist prompt since step 2 - the system already
#    knows who's asking.
#
#    A second, narrower gate: update_kyc requires "standard" auth level.
#    CUST1003 (Sancy) is deliberately the one "restricted" account (see
#    mock_idp.py), matching slide 10's John/Sancy example - this build
#    has no credit-limit tool, so KYC update stands in for the
#    "elevated operation" the deck demos.
#
# 2. SESSION STORE. A tiny checkpointed "memory" graph (mirroring
#    3_langgraph/3_4_langgraph_memory.py's simple accumulate-via-
#    SqliteSaver pattern) persists conversation history per customer_id,
#    surviving a full app restart - closing the deck's "Sanjay" gap
#    (slide 11): a customer asking about something from a prior session
#    no longer gets "I have no record of that."
#
#    The coordinator graph (classify/dispatch/run_specialist/synthesize)
#    deliberately stays UNCHECKPOINTED, exactly as it worked in steps
#    6-7: specialist_replies uses operator.add, which accumulates
#    correctly WITHIN one turn's parallel fan-out, but would accumulate
#    WITHOUT bound ACROSS turns if that graph itself were checkpointed
#    (an empty-list input doesn't reset an operator.add channel - it's
#    additive, not a replacement). Splitting "durable message history"
#    (the memory graph) from "this turn's scratch orchestration state"
#    (the coordinator graph) sidesteps that landmine entirely - only the
#    conversation actually needs to survive across turns/restarts, and
#    add_messages (merge-by-id) is safe to accumulate forever in a way
#    operator.add on scratch fields is not.
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
    tools = asyncio.run(mcp_client.get_tools())
    return {t.name: t for t in tools}


mcp_tools = load_mcp_tools()


def scope_tool_to_customer(base_tool, customer_id: str, block_message: str | None = None):
    """Wrap an MCP tool so customer_id is always overridden with the
    authenticated session's ID before the call reaches the tool - whatever
    customer_id the LLM itself supplies (if any) is silently discarded. This
    is what makes cross-account access structurally impossible here, not
    just discouraged by a prompt. block_message, if given, makes the tool
    refuse unconditionally instead of forwarding the call at all (used for
    the elevated-auth KYC gate)."""

    async def scoped_coroutine(**kwargs) -> str:
        if block_message is not None:
            return block_message
        kwargs["customer_id"] = customer_id
        return await base_tool.ainvoke(kwargs)

    return StructuredTool(
        name=base_tool.name,
        description=base_tool.description,
        args_schema=base_tool.args_schema,
        coroutine=scoped_coroutine,
    )


AUTH_NOTE = (
    " You never need to ask for a customer ID - the system automatically "
    "applies the authenticated customer's own ID to every tool call, "
    "regardless of what ID (if any) they type. If their message names a "
    "different customer ID than their own, you can still only ever act on "
    "their own account - let them know that plainly rather than silently "
    "substituting their own ID without explanation."
)

COMPOUND_REQUEST_NOTE = (
    " The customer's message may ask about several things at once, only some "
    "of which are yours to handle - a coordinator has already dispatched this "
    "same message to whichever other specialists are needed for the rest. "
    "Still fully answer the part that IS in your scope, using your tools - "
    "don't decline your own part just because the message also mentions "
    "something outside your scope."
)

CONCISE_ANSWER_NOTE = (
    " Only report the specific information the customer actually asked for. "
    "If a tool call returns more than that (e.g. a full statement when they "
    "only asked for the last transaction, or address + cheque book status + "
    "KYC status together when they only asked about one of those), mention "
    "only the part they asked about and leave the rest out unless they ask "
    "for it too."
)

# Found via manual testing of the deck's own demo phrase for this step
# ("What happened with the suspicious transaction I flagged last week?"):
# the conversation shown to each specialist can include turns from a PRIOR
# session, restored by the session store - but a narrowly-scoped specialist
# prompt ("you only handle X, say anything else is outside your scope") was
# treating a question about something already discussed earlier as an
# out-of-scope new request and declining it, even though the answer was
# sitting right there in the visible history. Recalling something already
# shown isn't "attempting something outside scope" - it's just reading.
RECALL_NOTE = (
    " The conversation shown to you may include turns from a previous "
    "session, restored by the session store - if the customer asks about "
    "something already discussed earlier (e.g. a transaction, balance, or "
    "status you or they already mentioned), answer directly from that "
    "conversation history instead of calling a tool again or declining as "
    "out of scope."
)

ACCOUNTS_PROMPT = (
    "You are the Accounts specialist agent for a bank. You have exactly one tool: "
    "get_account_balance. You only handle balance enquiries. If asked about "
    "anything else, clearly say that is outside your scope - do not attempt it "
    "and do not guess."
    + AUTH_NOTE
    + COMPOUND_REQUEST_NOTE
    + CONCISE_ANSWER_NOTE
    + RECALL_NOTE
)

TRANSACTION_PROMPT = (
    "You are the Transaction specialist agent for a bank. You have two tools: "
    "get_transaction_details (use count=1 if the customer asks for just their "
    "last/most recent transaction, or a higher count if they ask for several) "
    "and request_statement (only use this if they explicitly ask for a "
    "statement, not for a single transaction). You only handle transaction "
    "history and statement requests. If asked about anything else, clearly say "
    "that is outside your scope - do not attempt it. A question like 'what "
    "happened with the suspicious transaction I flagged last week?' is asking "
    "you to recall a transaction detail already visible in the conversation "
    "above (e.g. one already marked '(flagged)' in an earlier reply) - that is "
    "squarely transaction history, in your scope, and answerable directly from "
    "the conversation above without any new tool call. Only decline as "
    "out-of-scope if there is genuinely nothing about it anywhere above."
    + AUTH_NOTE
    + COMPOUND_REQUEST_NOTE
    + CONCISE_ANSWER_NOTE
    + RECALL_NOTE
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
    "attempt it. If update_kyc reports that elevated authentication is required, "
    "tell the customer that plainly and that they should contact customer "
    "support - don't retry it or work around it."
    + AUTH_NOTE
    + COMPOUND_REQUEST_NOTE
    + CONCISE_ANSWER_NOTE
    + RECALL_NOTE
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
    make_specialist(). Async agent node - MCP tools only support async invocation,
    and ToolNode picks the sync-or-async tool-call path based on whether the graph
    itself is invoked via .invoke() or .ainvoke()."""
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
# 14_advanced/07_langgraph/07_5_message_graph_bank_faq.py. Unchanged since
# step 5 - no MCP tools, no per-customer scoping needed (it never
# touches account data).
# ---------------------------------------------------------------------
FAQ_SIMILARITY_THRESHOLD = 0.3


@st.cache_resource(show_spinner=False)
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


def build_specialists(customer_id: str, auth_level: str) -> dict:
    """Rebuilt fresh every rerun for whoever is currently authenticated - cheap
    (just wrapping already-loaded, cached MCP tool objects), so this doesn't
    need st.cache_resource the way tool discovery and the FAQ vectorstore do."""
    kyc_block_message = None
    if auth_level == "restricted":
        kyc_block_message = (
            "This operation requires elevated authentication, which this "
            "account does not currently have. Please contact customer support "
            "to proceed."
        )

    return {
        "accounts": {
            "name": "Accounts Agent",
            "app": make_specialist_agent(
                [scope_tool_to_customer(mcp_tools["get_account_balance"], customer_id)]
            ),
            "system_prompt": ACCOUNTS_PROMPT,
        },
        "transaction": {
            "name": "Transaction Agent",
            "app": make_specialist_agent(
                [
                    scope_tool_to_customer(mcp_tools["get_transaction_details"], customer_id),
                    scope_tool_to_customer(mcp_tools["request_statement"], customer_id),
                ]
            ),
            "system_prompt": TRANSACTION_PROMPT,
        },
        "service": {
            "name": "Service Agent",
            "app": make_specialist_agent(
                [
                    scope_tool_to_customer(mcp_tools["get_service_details"], customer_id),
                    scope_tool_to_customer(mcp_tools["change_of_address"], customer_id),
                    scope_tool_to_customer(mcp_tools["request_cheque_book"], customer_id),
                    scope_tool_to_customer(
                        mcp_tools["update_kyc"], customer_id, block_message=kyc_block_message
                    ),
                ]
            ),
            "system_prompt": SERVICE_PROMPT,
        },
        "faq": {"name": "FAQ Agent", "app": faq_app, "system_prompt": FAQ_PROMPT},
    }


# =====================================================================
# Coordinator graph (unchecked/pointered) - classify_intent -> (fan-out
# via Send) -> run_specialist (1-4 in parallel) -> synthesize -> END.
# Identical mechanics to steps 6-7; only run_specialist's specialists
# lookup changes (built per-session now, via a factory closing over the
# current customer's scoped tools).
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

A short reply with no question in it (e.g. just an address) is usually \
answering something the assistant asked for in the immediately preceding turn - \
route it to whichever specialist needed that missing information, not to faq \
just because it isn't phrased as a question itself.

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
action is being requested, this is a general procedure question)""")

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


def build_coordinator_graph(specialists: dict):
    def run_specialist(state: dict) -> dict:
        info = specialists[state["specialist_key"]]
        specialist_input = [SystemMessage(content=info["system_prompt"])] + state["messages"]
        # Every specialist graph is invoked via ainvoke - required for the
        # MCP-backed ones since their ToolNode only supports async tool calls;
        # this function itself stays a plain sync callable (Send dispatch
        # calls it synchronously from a worker thread), so asyncio.run() gives
        # that thread its own fresh event loop with no conflict.
        result = asyncio.run(info["app"].ainvoke({"messages": specialist_input}))
        return {"specialist_replies": [{"specialist": info["name"], "reply": result["messages"][-1].content}]}

    graph = StateGraph(CoordinatorState)
    graph.add_node("classify_intent", classify_intent)
    graph.add_node("run_specialist", run_specialist)
    graph.add_node("synthesize", synthesize)
    graph.add_edge(START, "classify_intent")
    graph.add_conditional_edges("classify_intent", dispatch_to_specialists, ["run_specialist"])
    graph.add_edge("run_specialist", "synthesize")
    graph.add_edge("synthesize", END)
    return graph.compile()  # deliberately NOT checkpointed - see module docstring


# =====================================================================
# Session store: a trivial checkpointed graph whose only job is to hold
# messages: Annotated[list, add_messages], following
# 3_langgraph/3_4_langgraph_memory.py's SqliteSaver example. add_messages
# merges by message id, so re-adding an already-persisted message is a
# safe no-op - this channel is meant to accumulate forever, unlike the
# coordinator's per-turn scratch state above.
# =====================================================================

SESSION_DB_PATH = os.path.join(BASE_DIR, "session_checkpoints.sqlite")


@st.cache_resource(show_spinner=False)
def get_checkpointer():
    conn = sqlite3.connect(SESSION_DB_PATH, check_same_thread=False)
    return SqliteSaver(conn)


class MemoryState(TypedDict):
    messages: Annotated[list, add_messages]


def memory_noop(state: MemoryState) -> MemoryState:
    return {}


memory_graph = StateGraph(MemoryState)
memory_graph.add_node("noop", memory_noop)
memory_graph.add_edge(START, "noop")
memory_graph.add_edge("noop", END)
memory_app = memory_graph.compile(checkpointer=get_checkpointer())

# =====================================================================
# Streamlit web UI - login gate, then the same shared chat as steps 6-7.
# =====================================================================

st.set_page_config(page_title="Banking Assistant - Step 8", page_icon="\U0001F3E6")

if "auth" not in st.session_state:
    st.session_state.auth = None

if st.session_state.auth is None:
    st.title("Banking Assistant — Step 8: Login")
    st.caption(
        "Every specialist call is scoped server-side to whoever logs in here - "
        "the customer ID in a chat message is never trusted for tool calls."
    )
    with st.form("login_form"):
        customer_id_input = st.text_input("Customer ID", placeholder="e.g. CUST1001")
        pin_input = st.text_input("PIN", type="password")
        submitted = st.form_submit_button("Log in")
    if submitted:
        auth_result = mock_idp.authenticate(customer_id_input.strip().upper(), pin_input.strip())
        if "error" in auth_result:
            st.error(auth_result["error"])
        else:
            st.session_state.auth = auth_result
            st.rerun()
    st.stop()

customer_id = st.session_state.auth["customer_id"]
auth_level = st.session_state.auth["auth_level"]
config = {"configurable": {"thread_id": customer_id}}

specialists = build_specialists(customer_id, auth_level)
coordinator_app = build_coordinator_graph(specialists)

st.title("Banking Assistant — Step 8: Auth + Session")
header_col, logout_col = st.columns([4, 1])
with header_col:
    st.caption(
        f"Logged in as {customer_id} ({auth_level} auth). Conversation history "
        "persists across restarts - close and reopen this app and it's still here."
    )
with logout_col:
    if st.button("Log out", use_container_width=True):
        st.session_state.auth = None
        st.session_state.pop("messages", None)
        st.session_state.pop("routing_log", None)
        st.rerun()

if "messages" not in st.session_state:
    existing_state = memory_app.get_state(config).values
    st.session_state.messages = existing_state.get("messages", []) if existing_state else []
if "routing_log" not in st.session_state:
    # UI-only annotation (which specialist(s) handled each reply) - unlike
    # `messages`, this does NOT survive a restart, since it isn't part of
    # what's persisted. See the module docstring's "design principle" note.
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
            if ai_index < len(st.session_state.routing_log):
                st.caption(f"→ routed to {' + '.join(st.session_state.routing_log[ai_index])}")
        ai_index += 1

user_input = st.chat_input("Ask a banking question...")
if user_input:
    new_message = HumanMessage(content=user_input)
    with st.chat_message("user"):
        st.write(user_input)

    memory_app.invoke({"messages": [new_message]}, config=config)
    full_history = memory_app.get_state(config).values["messages"]

    with st.chat_message("assistant"):
        with st.spinner("Routing and thinking..."):
            result = coordinator_app.invoke(
                {
                    "messages": full_history,
                    "specialists_needed": [],
                    "specialist_replies": [],
                    "final_answer": "",
                }
            )
        memory_app.invoke({"messages": [result["messages"][-1]]}, config=config)
        st.session_state.messages = memory_app.get_state(config).values["messages"]
        routed_names = [r["specialist"] for r in result["specialist_replies"]]
        st.session_state.routing_log.append(routed_names)
        st.write(result["final_answer"])
        st.caption(f"→ routed to {' + '.join(routed_names)}")
