# Weather MCP server for 6_17_trip_planner_mcp_app.py, backed by Open-Meteo
# (https://open-meteo.com) - free, no API key. Unlike 6_1_weather_mcp_server.py,
# which returns a hard-coded string, this one returns real current conditions.
# Run on its own with `mcp dev 6_17_weather_mcp_server.py` to try it in the
# MCP Inspector.
import requests
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Weather")

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

# WMO weather interpretation codes used by Open-Meteo (abridged)
WMO_CODES = {
    0: "clear sky", 1: "mainly clear", 2: "partly cloudy", 3: "overcast",
    45: "fog", 48: "depositing rime fog",
    51: "light drizzle", 53: "drizzle", 55: "dense drizzle",
    61: "slight rain", 63: "rain", 65: "heavy rain",
    71: "slight snow", 73: "snow", 75: "heavy snow",
    80: "rain showers", 81: "heavy rain showers", 82: "violent rain showers",
    95: "thunderstorm", 96: "thunderstorm with hail", 99: "thunderstorm with heavy hail",
}


@mcp.tool()
def get_current_weather(city: str) -> str:
    """
    Get the current weather for a city.
    Args:
    city: city name, optionally with country, e.g. "Rome" or "Rome, Italy"
    """
    # The geocoder matches on a place name only, so drop any ", country" suffix
    name = city.split(",")[0].strip()
    geo = requests.get(GEOCODE_URL, params={"name": name, "count": 1}, timeout=15).json()
    if not geo.get("results"):
        return f"Could not find a location called '{city}'."
    place = geo["results"][0]

    current = requests.get(
        FORECAST_URL,
        params={
            "latitude": place["latitude"],
            "longitude": place["longitude"],
            "current": "temperature_2m,apparent_temperature,relative_humidity_2m,wind_speed_10m,weather_code",
        },
        timeout=15,
    ).json()["current"]

    conditions = WMO_CODES.get(current["weather_code"], f"weather code {current['weather_code']}")
    return (
        f"{place['name']}, {place.get('country', '')}: {conditions}, "
        f"{current['temperature_2m']}°C (feels like {current['apparent_temperature']}°C), "
        f"humidity {current['relative_humidity_2m']}%, wind {current['wind_speed_10m']} km/h"
    )


if __name__ == "__main__":
    mcp.run()
