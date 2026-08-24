import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

import operator
import os
import sys
import time
from datetime import date, timedelta
from typing import Annotated, TypedDict
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from serpapi import GoogleSearch
from langchain_openai import ChatOpenAI
from langchain_tavily import TavilySearch
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send

load_dotenv(override=True)

# LLM output can contain characters outside Windows' default console
# codepage (cp1252) - reconfigure stdout to UTF-8 so printing doesn't crash.
sys.stdout.reconfigure(encoding="utf-8")

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.5)
search_tool = TavilySearch(max_results=4)

# The trip always starts from Mumbai (BOM) - if origin ever becomes a
# second user input alongside destination_country, this would need to
# become a lookup instead of a constant.
ORIGIN_IATA = "BOM"

# =====================================================================
# Fan-out/fan-in with LangGraph's Send API, grounded in REAL web search
# (Tavily) instead of asking the LLM to "suggest realistic-sounding"
# flights/hotels/attractions from its own training data.
#
# determine_cities doesn't know in advance how many parallel branches
# to create - the exact 4 cities depend on which country the USER
# names at runtime. Send is built exactly for this: a routing function
# returns a LIST of Send(node_name, input_dict) objects instead of a
# single next-node string, and LangGraph runs all of them concurrently
# in the same superstep - here that's 1 flight search + 4 city research
# calls (5 independent, real-search-backed LLM calls) running at once.
#
# Every Send target writes into a SHARED state field, so those fields
# need a reducer (Annotated[..., operator.add]) - without one, two
# branches finishing in the same superstep and both trying to overwrite
# the same key would silently clobber each other instead of combining.
# =====================================================================


def web_search(query: str) -> str:
    result = search_tool.invoke({"query": query})
    snippets = [
        f"- {item.get('title', '')}: {item.get('content', '')[:600]}"
        for item in result.get("results", [])
    ]
    return "\n".join(snippets) if snippets else "(no search results found)"


def format_flight_options(flights_data: list, max_options: int = 3) -> str:
    """flights_data is SerpApi's raw google_flights 'best_flights'/'other_flights'
    list - already real, structured data (actual airlines, flight numbers, prices),
    so this just formats it. No LLM involved - nothing here can be invented."""
    lines = []
    for option in flights_data[:max_options]:
        legs = option["flights"]
        route = " -> ".join(f"{leg['airline']} {leg['flight_number']}" for leg in legs)
        stops = len(legs) - 1
        if stops == 0:
            stop_desc = "nonstop"
        else:
            via = ", ".join(leg["arrival_airport"]["id"] for leg in legs[:-1])
            stop_desc = f"{stops} stop(s) via {via}"
        duration_hours = option["total_duration"] / 60
        lines.append(
            f"- {route} | {stop_desc} | {duration_hours:.1f}h total | "
            f"${option['price']} ({option.get('type', 'Round trip')})"
        )
    return "\n".join(lines) if lines else "(no flight data found for this route/date)"


class CityReport(TypedDict):
    city: str
    report: str


class TripState(TypedDict):
    origin: str
    destination_country: str
    start_date: str
    end_date: str
    duration_days: int
    cities: list[str]
    arrival_airport_iata: str
    flight_options: Annotated[list[str], operator.add]
    city_reports: Annotated[list[CityReport], operator.add]
    summary: str


TRIP_START_TIME = 0.0


def elapsed() -> float:
    return time.time() - TRIP_START_TIME


# ---------------------------------------------------------------------
# Node 1: initialize_trip - fixed logic, no LLM. Computes real dates
# (1 month from today, 10 days long).
# ---------------------------------------------------------------------
def initialize_trip(state: TripState) -> TripState:
    start = date.today() + timedelta(days=30)
    end = start + timedelta(days=10)
    print(f"[initialize_trip] {state['origin']} -> {state['destination_country']}: {start} to {end}")
    return {"start_date": start.isoformat(), "end_date": end.isoformat(), "duration_days": 10}


# ---------------------------------------------------------------------
# Node 2: determine_cities - a REAL search grounds which 4 cities/
# regions are actually worth visiting in the user's chosen country,
# rather than a hardcoded list.
# ---------------------------------------------------------------------
class CityList(BaseModel):
    cities: list[str] = Field(
        description="Exactly 4 major cities or regions worth visiting, in a sensible geographic travel order."
    )
    arrival_airport_iata: str = Field(
        description=(
            "The 3-letter IATA code of the main international gateway airport a traveler would fly "
            "into to start this trip - this may be a different, larger city than the 4 chosen "
            "regions if none of them has a major international airport (e.g. Hanoi/HAN for a trip "
            "that also visits Ninh Binh and Ha Long Bay, neither of which has one)."
        )
    )


def determine_cities(state: TripState) -> TripState:
    print(f"[determine_cities] searching for top destinations in {state['destination_country']}...")
    search_results = web_search(f"best cities and regions to visit in {state['destination_country']} for tourists")
    prompt = (
        f"Based on this real search data about {state['destination_country']}, pick exactly 4 major "
        f"cities or regions that would make a great {state['duration_days']}-day trip, ordered in a "
        f"sensible geographic travel route. Also identify the main international gateway airport.\n\n"
        f"Search data:\n{search_results}"
    )
    result = llm.with_structured_output(CityList).invoke(prompt)
    print(f"[determine_cities] chosen: {result.cities} (arrival airport: {result.arrival_airport_iata})")
    return {"cities": result.cities, "arrival_airport_iata": result.arrival_airport_iata}


# ---------------------------------------------------------------------
# The fan-out point: returns a Send per parallel task instead of a
# single next-node name.
# ---------------------------------------------------------------------
def dispatch_research(state: TripState) -> list[Send]:
    # For example: Search flights for NRT (Tokyo), then 4 city reports (Tokyo, Osaka, Kyoto, Hiroshima)
    sends = [Send("search_flights", {
        "arrival_airport_iata": state["arrival_airport_iata"],
        "start_date": state["start_date"],
        "end_date": state["end_date"],
    })]
    for city in state["cities"]:
        sends.append(Send("research_city", {
            "city": city,
            "start_date": state["start_date"],
            "end_date": state["end_date"],
        }))
    return sends


# ---------------------------------------------------------------------
# Parallel branch A: flight search via SerpApi's Google Flights engine -
# real airline data (actual flight numbers, prices, durations, stops),
# not a web-search summary the LLM has to interpret. No LLM call here
# at all: the data is already real and structured, so there's nothing
# for an LLM to add except a chance to misstate a number.
# ---------------------------------------------------------------------
def search_flights(state: dict) -> dict:
    t0 = elapsed()
    print(f"[search_flights]  started at t={t0:.1f}s")
    try:
        results = GoogleSearch({
            "engine": "google_flights",
            "departure_id": ORIGIN_IATA,
            "arrival_id": state["arrival_airport_iata"],
            "outbound_date": state["start_date"],
            "return_date": state["end_date"],
            "currency": "USD",
            "hl": "en",
            "api_key": os.environ["SERPAPI_API_KEY"],
        }).get_dict()
        flights_data = results.get("best_flights") or results.get("other_flights") or []
        summary = format_flight_options(flights_data)
    except Exception as e:
        summary = f"(flight search failed: {e})"
    print(f"[search_flights]  finished at t={elapsed():.1f}s (took {elapsed() - t0:.1f}s)")
    return {"flight_options": [summary]}


# ---------------------------------------------------------------------
# Parallel branch B: one call per city, grounded in a real web search.
# The COUNT of these (4) is only known at runtime (it comes out of
# determine_cities), which is why Send is needed rather than hardcoded
# static edges.
# ---------------------------------------------------------------------
def research_city(state: dict) -> dict:
    city = state["city"]
    t0 = elapsed()
    print(f"[research_city:{city}] started at t={t0:.1f}s")
    search_results = web_search(f"{city} hotels and top tourist attractions")
    prompt = (
        f"Based on this real search data about {city}, summarize: (1) two real accommodation options "
        f"with rough nightly price if the data supports it, and (2) the 3 best must-see attractions. "
        f"Keep it brief with clear headers, and don't invent details the data doesn't support.\n\n"
        f"Search data:\n{search_results}"
    )
    response = llm.invoke(prompt)
    print(f"[research_city:{city}] finished at t={elapsed():.1f}s (took {elapsed() - t0:.1f}s)")
    return {"city_reports": [{"city": city, "report": response.content}]}


# ---------------------------------------------------------------------
# Fan-in: every Send target's edge points here, so this node only runs
# once ALL 5 parallel branches have completed and their results have
# been combined into flight_options/city_reports via their reducers.
# ---------------------------------------------------------------------
def summarize_trip(state: TripState) -> TripState:
    print(f"[summarize_trip] all research done at t={elapsed():.1f}s - writing final itinerary...")
    city_section = "\n\n".join(f"### {r['city']}\n{r['report']}" for r in state["city_reports"])
    flight_section = "\n\n".join(state["flight_options"])

    prompt = f"""Write a friendly, organized {state['duration_days']}-day trip summary to \
{state['destination_country']}, {state['start_date']} to {state['end_date']}, starting from {state['origin']}.

Flights:
{flight_section}

City research:
{city_section}

Produce a short day-by-day rough itinerary across these cities, then a one-paragraph overall summary."""
    response = llm.invoke(prompt)
    return {"summary": response.content}


graph = StateGraph(TripState)
graph.add_node("initialize_trip", initialize_trip)
graph.add_node("determine_cities", determine_cities)
graph.add_node("search_flights", search_flights)
graph.add_node("research_city", research_city)
graph.add_node("summarize_trip", summarize_trip)

graph.add_edge(START, "initialize_trip")
graph.add_edge("initialize_trip", "determine_cities")
graph.add_conditional_edges("determine_cities", dispatch_research, ["search_flights", "research_city"])
graph.add_edge("search_flights", "summarize_trip")
graph.add_edge("research_city", "summarize_trip")
graph.add_edge("summarize_trip", END)

app = graph.compile()

if __name__ == "__main__":
    destination_country = input("Which country would you like to visit? ").strip() or "Japan"

    initial: TripState = {
        "origin": "Mumbai",
        "destination_country": destination_country,
        "start_date": "",
        "end_date": "",
        "duration_days": 0,
        "cities": [],
        "arrival_airport_iata": "",
        "flight_options": [],
        "city_reports": [],
        "summary": "",
    }

    TRIP_START_TIME = time.time()
    result = app.invoke(initial)
    total_elapsed = time.time() - TRIP_START_TIME

    print("\n" + "=" * 70)
    print(f"5 parallel LLM calls (1 flight search + 4 city research) - total wall-clock: {total_elapsed:.1f}s")
    print("If this were sequential, it would take roughly the SUM of each call's individual duration above.")
    print("=" * 70)
    print(result["summary"])
