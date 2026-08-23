import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

import sys
import re
import requests
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import create_tool_calling_agent, AgentExecutor

load_dotenv(override=True)

# Tool output can contain characters outside Windows' default console
# codepage (cp1252) - reconfigure stdout to UTF-8 so printing doesn't crash.
sys.stdout.reconfigure(encoding="utf-8")

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# =====================================================================
# Four tools. geocode_city -> get_current_weather -> recommend_clothing
# is a strict chain: each one's OUTPUT format matches the next one's
# expected INPUT format on purpose (free Open-Meteo API, no key
# required). find_nearby_places branches off geocode_city's coordinates
# independently, via OpenStreetMap's Overpass API (also free, no key).
# =====================================================================

@tool
def geocode_city(city: str) -> str:
    """Look up a city's coordinates. Input: a city name, e.g. Tokyo.
    Returns a string 'latitude,longitude' - feed this directly into
    get_current_weather."""
    resp = requests.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": city, "count": 1, "language": "en", "format": "json"},
        timeout=10,
    ).json()
    results = resp.get("results", [])
    if not results:
        return f"Could not find coordinates for {city}"
    loc = results[0]
    return f"{loc['latitude']},{loc['longitude']}"

@tool
def get_current_weather(lat_lon: str) -> str:
    """Get current temperature and wind speed for a location.
    Input: 'latitude,longitude', exactly as returned by geocode_city
    (e.g. '35.6895,139.6917'). Returns a string like
    'temperature=18.2C, wind_speed=12.4km/h' - feed this directly into
    recommend_clothing."""
    lat_str, lon_str = lat_lon.split(",")[:2]
    resp = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": lat_str.strip(),
            "longitude": lon_str.strip(),
            "current": "temperature_2m,wind_speed_10m",
            "timezone": "auto",
        },
        timeout=10,
    ).json()
    current = resp.get("current", {})
    return f"temperature={current.get('temperature_2m')}C, wind_speed={current.get('wind_speed_10m')}km/h"

@tool
def recommend_clothing(weather_summary: str) -> str:
    """Recommend what to wear given a weather summary string, exactly as
    returned by get_current_weather (e.g. 'temperature=18.2C,
    wind_speed=12.4km/h'). Pure logic, no external call."""
    temp_match = re.search(r"temperature=(-?\d+\.?\d*)", weather_summary)
    wind_match = re.search(r"wind_speed=(-?\d+\.?\d*)", weather_summary)
    temp = float(temp_match.group(1)) if temp_match else None
    wind = float(wind_match.group(1)) if wind_match else None

    if temp is None:
        return "Could not parse a temperature from that weather summary."

    if temp < 10:
        outfit = "a warm coat and gloves"
    elif temp < 18:
        outfit = "a light jacket"
    elif temp < 27:
        outfit = "a t-shirt, no jacket needed"
    else:
        outfit = "light, breathable clothing"

    if wind is not None and wind > 25:
        outfit += " (and something windproof - it's quite windy)"

    return f"Recommended outfit: {outfit}."

@tool
def find_nearby_places(lat_lon: str) -> str:
    """Find nearby tourist attractions and restaurants for a location,
    via OpenStreetMap's Overpass API. Input: 'latitude,longitude',
    exactly as returned by geocode_city (e.g. '35.6895,139.6917').
    Returns up to 5 attractions and 5 restaurants within 2km as
    'Name (attraction)' / 'Name (restaurant)', one per line."""
    lat_str, lon_str = lat_lon.split(",")[:2]
    query = f"""
    [out:json][timeout:15];
    (
      node["tourism"="attraction"](around:2000,{lat_str.strip()},{lon_str.strip()});
      node["amenity"="restaurant"](around:2000,{lat_str.strip()},{lon_str.strip()});
    );
    out body 30;
    """
    try:
        resp = requests.post(
            "https://overpass-api.de/api/interpreter",
            data={"data": query},
            timeout=20,
            # Overpass's public instance blocks/deprioritizes requests
            # carrying requests' default generic User-Agent - identify
            # this client explicitly, per Overpass's usage policy.
            headers={"User-Agent": "agenticai-course-demo/1.0"},
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.RequestException as e:
        return f"Nearby-places lookup failed ({e}). Try again or answer without it."

    attractions, restaurants = [], []
    for el in data.get("elements", []):
        name = el.get("tags", {}).get("name")
        if not name:
            continue
        category = el["tags"].get("tourism") or el["tags"].get("amenity")
        if category == "attraction" and len(attractions) < 5:
            attractions.append(name)
        elif category == "restaurant" and len(restaurants) < 5:
            restaurants.append(name)

    lines = [f"{n} (attraction)" for n in attractions] + [f"{n} (restaurant)" for n in restaurants]
    return "\n".join(lines) if lines else "No nearby attractions or restaurants found."

tools = [geocode_city, get_current_weather, recommend_clothing, find_nearby_places]

if __name__ == "__main__":
    city = input("Enter a city: ").strip() or "Tokyo"
    question = (
        f"What should I wear outside today in {city}? Also suggest "
        "nearby attractions and restaurants."
    )

    # =====================================================================
    # 1. AGENT-DRIVEN chaining
    # The agent itself reads each tool result and decides what to pass as
    # the next tool call's arguments - there is no code anywhere that says
    # "take geocode_city's output and pass it to get_current_weather". The
    # LLM infers that from the tool descriptions and the shape of what came
    # back. Flexible, but costs an LLM call per step and can misparse a
    # result if its format is ever ambiguous.
    # =====================================================================
    print("=" * 70)
    print("1. AGENT-DRIVEN chaining (tool-calling agent)")
    print("=" * 70)

    prompt = ChatPromptTemplate.from_messages([
        ("human", "{input}"),
        MessagesPlaceholder("agent_scratchpad"),
    ])

    agent = create_tool_calling_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True, max_iterations=6)
    agent_result = agent_executor.invoke({"input": question})

    # =====================================================================
    # 2. DETERMINISTIC chaining
    # The EXACT same tools, the EXACT same data flow - but hardcoded by
    # the developer instead of decided by an LLM. No reasoning, no tokens
    # spent deciding "what's next", nothing that can misinterpret an
    # observation. The tradeoff: this only works because we already know
    # the pipeline shape in advance. It can't handle a question that needs
    # a different sequence of tools, or a different number of steps.
    # =====================================================================
    print("\n" + "=" * 70)
    print("2. DETERMINISTIC chaining (hardcoded, no agent)")
    print("=" * 70)

    coords = geocode_city.invoke({"city": city})
    print(f"geocode_city output:        {coords}")

    weather = get_current_weather.invoke({"lat_lon": coords})
    print(f"get_current_weather output: {weather}")

    recommendation = recommend_clothing.invoke({"weather_summary": weather})
    print(f"recommend_clothing output:  {recommendation}")

    places = find_nearby_places.invoke({"lat_lon": coords})
    print(f"find_nearby_places output:\n{places}")

    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)
    print(f"Agent-driven:  {agent_result['output']}")
    print(f"Deterministic: {recommendation}")
    print(f"Nearby places:\n{places}")
