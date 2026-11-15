import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

import sys
from typing import Annotated, Literal, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.types import Command
from pydantic import BaseModel, Field

load_dotenv(override=True)
sys.stdout.reconfigure(encoding="utf-8")

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# =====================================================================
# The SUPERVISOR pattern: one coordinating agent, several specialist
# agents, each with its own tools and prompt. The supervisor never does
# the work itself - it reads the conversation, picks who acts next, and
# decides when the job is done.
#
#                 +--> flights_agent --+
#   supervisor ---+                    +--> supervisor --> ... --> writer
#                 +--> hotels_agent ---+
#
# Hand-offs use Command(goto=...): a node returns both its state update
# AND the next node, so the routing lives with the decision instead of
# in a separate conditional-edge function.
# (08_5 fans out with Send to run copies of ONE node in parallel; here
#  different agents take turns, and an LLM decides the order.)
# =====================================================================


# ---------------------------------------------------------------------
# Each specialist's tools - mock data so the demo is repeatable.
# ---------------------------------------------------------------------
FLIGHTS = {
    ("Mumbai", "Singapore"): [("SQ 423", "08:10", 21400), ("AI 342", "23:45", 17900), ("6E 1003", "02:30", 15200)],
    ("Singapore", "Mumbai"): [("SQ 422", "19:55", 20800), ("AI 343", "16:20", 18300)],
}
HOTELS = {
    "Singapore": [("Marina View", 9800, 4.6), ("Orchard Stay", 6400, 4.2), ("Chinatown Inn", 3900, 3.9)],
}


@tool
def search_flights(origin: str, destination: str) -> str:
    """List flights from origin to destination with departure time and price in rupees."""
    rows = FLIGHTS.get((origin.title(), destination.title()), [])
    return "\n".join(f"{f} departs {t}, ₹{p:,}" for f, t, p in rows) or "No flights found."


@tool
def search_hotels(city: str, max_price_per_night: int) -> str:
    """List hotels in a city at or under a nightly price in rupees, with guest rating."""
    rows = [h for h in HOTELS.get(city.title(), []) if h[1] <= max_price_per_night]
    return "\n".join(f"{n}: ₹{p:,}/night, rating {r}" for n, p, r in rows) or "No hotels in that budget."


class TripState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    turns: int


def briefing(state: TripState) -> str:
    """What every agent is shown: the request plus the reports so far.
    Agents share results, not each other's tool-call chatter."""
    request = state["messages"][0].content
    reports = [f"- {m.name}: {m.content}" for m in state["messages"][1:] if getattr(m, "name", None)]
    return f"Traveller's request: {request}\n\nReports so far:\n" + ("\n".join(reports) or "(none yet)")


# ---------------------------------------------------------------------
# A specialist = a small tool-calling loop (06_3) with its own prompt
# and tools. It reports back to the supervisor with one named message.
# ---------------------------------------------------------------------
def make_specialist(name: str, prompt: str, tools: list):
    model = llm.bind_tools(tools)
    by_name = {t.name: t for t in tools}

    def node(state: TripState) -> Command[Literal["supervisor"]]:
        # Each specialist keeps its own scratchpad (msgs); only its final
        # report goes back into the shared state.
        msgs: list[BaseMessage] = [SystemMessage(prompt), HumanMessage(briefing(state))]
        ai = None
        for _ in range(4):
            ai = model.invoke(msgs)
            msgs.append(ai)
            if not ai.tool_calls:
                break
            for call in ai.tool_calls:
                print(f"   {name} -> {call['name']}({call['args']})")
                msgs.append(ToolMessage(str(by_name[call["name"]].invoke(call["args"])), tool_call_id=call["id"]))
        report = AIMessage(content=ai.content, name=name)
        print(f"   {name} reports: {ai.content[:160]}")
        return Command(goto="supervisor", update={"messages": [report]})

    return node


flights_agent = make_specialist(
    "flights_agent",
    "You are the flights specialist. Use search_flights for the outbound AND return legs. "
    "Recommend one flight each way that fits the traveller's budget and timing, with prices.",
    [search_flights],
)
hotels_agent = make_specialist(
    "hotels_agent",
    "You are the hotels specialist. Use search_hotels. Recommend one hotel that fits the "
    "budget left after flights (if flights were already chosen), with the total for all nights.",
    [search_hotels],
)


# ---------------------------------------------------------------------
# The supervisor: structured output picks the next worker or FINISH.
# ---------------------------------------------------------------------
class Route(BaseModel):
    reason: str = Field(description="One short sentence: what is still missing?")   # think first...
    next: Literal["flights_agent", "hotels_agent", "FINISH"] = Field(              # ...then decide
        description="Who acts next. FINISH once flights AND a hotel have been recommended."
    )


SUPERVISOR_PROMPT = (
    "You coordinate a travel team: flights_agent books flights, hotels_agent books hotels. "
    "Read the conversation and choose who should act next. Do flights before hotels, so the "
    "hotel can use the remaining budget. Choose FINISH when both have reported."
)
router = llm.with_structured_output(Route)


def supervisor(state: TripState) -> Command[Literal["flights_agent", "hotels_agent", "writer"]]:
    if state["turns"] >= 4:                       # safety net: never loop forever
        return Command(goto="writer")
    done = sorted({m.name for m in state["messages"] if getattr(m, "name", None)})
    decision = router.invoke([
        SystemMessage(SUPERVISOR_PROMPT),
        HumanMessage(f"{briefing(state)}\n\nAgents that have already reported: {', '.join(done) or 'none'}"),
    ])
    print(f"\n[supervisor] -> {decision.next}: {decision.reason}")
    goto = "writer" if decision.next == "FINISH" else decision.next
    return Command(goto=goto, update={"turns": state["turns"] + 1})


def writer(state: TripState) -> dict:
    final = llm.invoke([
        SystemMessage("Write the final trip plan for the traveller from the team's reports: "
                      "flights each way, hotel, and the total cost against the budget. Be brief."),
        HumanMessage(briefing(state)),
    ])
    return {"messages": [final]}


graph = StateGraph(TripState)
graph.add_node("supervisor", supervisor)
graph.add_node("flights_agent", flights_agent)
graph.add_node("hotels_agent", hotels_agent)
graph.add_node("writer", writer)
graph.add_edge(START, "supervisor")
graph.add_edge("writer", END)
# No add_conditional_edges: every Command(goto=...) is the edge.
app = graph.compile()

if __name__ == "__main__":
    request = (
        "Plan a 3-night trip from Mumbai to Singapore for one person. Total budget ₹60,000 "
        "for flights and hotel. I prefer not to fly overnight."
    )
    print("REQUEST:", request)
    result = app.invoke({"messages": [HumanMessage(request)], "turns": 0})
    print("\n" + "=" * 70 + "\nTRIP PLAN\n" + "=" * 70)
    print(result["messages"][-1].content)
