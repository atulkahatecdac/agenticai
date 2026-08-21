# pip install python-dotenv openai-agents google-search-results

import os
from dotenv import load_dotenv
from agents import Agent, Runner, function_tool
from serpapi import GoogleSearch

load_dotenv(override=True)

# --------------------------------
# Tools
# --------------------------------
@function_tool
def search_properties(city: str) -> str:
    """Searches the web for residential properties for sale in the given city."""
    results = GoogleSearch({
        "engine": "google",
        "q": f"residential properties for sale in {city}",
        "api_key": os.environ["SERPAPI_API_KEY"],
    }).get_dict()

    organic = results.get("organic_results", [])[:5]
    if not organic:
        return f"No property listings found for {city}."

    lines = [f"- {item.get('title', '')}: {item.get('snippet', '')}" for item in organic]
    return "\n".join(lines)

@function_tool
def search_property_details(property_name: str, city: str) -> str:
    """Searches the web for nearby schools, local attractions, and price/rate
    information for a specific named property in a city."""
    results = GoogleSearch({
        "engine": "google",
        "q": f"{property_name} {city} nearby schools attractions price rate",
        "api_key": os.environ["SERPAPI_API_KEY"],
    }).get_dict()

    organic = results.get("organic_results", [])[:5]
    if not organic:
        return f"No details found for {property_name} in {city}."

    lines = [f"- {item.get('title', '')}: {item.get('snippet', '')}" for item in organic]
    return "\n".join(lines)

# --------------------------------
# Agent 1: finds properties in a city
# --------------------------------
property_search_agent = Agent(
    name="PropertySearchAgent",
    model="gpt-4o-mini",
    tools=[search_properties],
    instructions=(
        "You help users find residential properties in a given city. "
        "Use the search_properties tool, then present a short numbered list "
        "of property/project names found, one line each."
    ),
)

# --------------------------------
# Agent 2: details for one chosen property
# --------------------------------
property_details_agent = Agent(
    name="PropertyDetailsAgent",
    model="gpt-4o-mini",
    tools=[search_property_details],
    instructions=(
        "You help users evaluate one specific property. Use the "
        "search_property_details tool, then summarize the findings under three "
        "headings: 'Nearby Schools', 'Local Attractions', and 'Property Rates'."
    ),
)

# --------------------------------
# Main
# --------------------------------
if __name__ == "__main__":
    city = input("Enter a city name to search for properties: ").strip()

    print(f"\nAgent 1: Searching for properties in {city}...\n")
    search_result = Runner.run_sync(
        property_search_agent,
        f"Find residential properties for sale in {city}."
    )
    print(search_result.final_output)

    property_name = input("\nEnter the name of a property from the list above: ").strip()

    print(f"\nAgent 2: Looking up details for '{property_name}' in {city}...\n")
    details_result = Runner.run_sync(
        property_details_agent,
        f"Give me nearby schools, local attractions, and rates for the property "
        f"'{property_name}' in {city}."
    )
    print(details_result.final_output)
