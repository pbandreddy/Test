  from typing import Any
import httpx
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("weather")

# Constants
NWS_API_BASE = "https://api.weather.gov"
USER_AGENT = "weather-app/1.0"

async def make_nws_request(url: str) -> dict[str, Any] | None:
    """Make a request to the NWS API with proper error handling."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/geo+json"
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception:
            return None

def format_alert(feature: dict) -> str:
    """Format an alert feature into a readable string."""
    props = feature["properties"]
    return f"""
Event: {props.get('event', 'Unknown')}
Area: {props.get('areaDesc', 'Unknown')}
Severity: {props.get('severity', 'Unknown')}
Description: {props.get('description', 'No description available')}
Instructions: {props.get('instruction', 'No specific instructions provided')}
"""

@mcp.tool()
async def get_alerts(state: str) -> str:
    """Get weather alerts for a US state.

    Args:
        state: Two-letter US state code (e.g. CA, NY)
    """
    url = f"{NWS_API_BASE}/alerts/active/area/{state}"
    data = await make_nws_request(url)

    if not data or "features" not in data:
        return "Unable to fetch alerts or no alerts found."

    if not data["features"]:
        return "No active alerts for this state."

    alerts = [format_alert(feature) for feature in data["features"]]
    return "\n---\n".join(alerts)

@mcp.tool()
async def get_forecast(latitude: float, longitude: float) -> str:
    """Get weather forecast for a location.

    Args:
        latitude: Latitude of the location
        longitude: Longitude of the location
    """
    # First get the forecast grid endpoint
    points_url = f"{NWS_API_BASE}/points/{latitude},{longitude}"
    points_data = await make_nws_request(points_url)

    if not points_data:
        return "Unable to fetch forecast data for this location."

    # Get the forecast URL from the points response
    forecast_url = points_data["properties"]["forecast"]
    forecast_data = await make_nws_request(forecast_url)

    if not forecast_data:
        return "Unable to fetch detailed forecast."

    # Format the periods into a readable forecast
    periods = forecast_data["properties"]["periods"]
    forecasts = []
    for period in periods[:5]:  # Only show next 5 periods
        forecast = f"""
{period['name']}:
Temperature: {period['temperature']}°{period['temperatureUnit']}
Wind: {period['windSpeed']} {period['windDirection']}
Forecast: {period['detailedForecast']}
"""
        forecasts.append(forecast)

    return "\n---\n".join(forecasts)

@mcp.resource("weather://alerts/{state}", description="Weather alerts for a US state")
async def get_alerts_resource(state: str) -> str:
    """Resource to get weather alerts for a US state.
    
    Args:
        state: Two-letter US state code (e.g. CA, NY)
    """
    return await get_alerts(state)

@mcp.resource("weather://forecast/{lat}/{lon}", description="Weather forecast for a location")
async def get_forecast_resource(lat: float, lon: float) -> str:
    """Resource to get weather forecast for a location.
    
    Args:
        lat: Latitude of the location
        lon: Longitude of the location
    """
    return await get_forecast(lat, lon)

@mcp.prompt()
async def weather_analysis_prompt() -> str:
    """Analyze current weather conditions and provide recommendations."""
    return """You are a weather analysis expert. When provided with weather data, please:

1. **Summarize the current conditions** in plain language
2. **Identify any weather alerts or warnings** and their significance
3. **Provide practical recommendations** for:
   - Outdoor activities
   - Travel considerations
   - Safety precautions if needed
4. **Highlight any notable weather patterns** or changes expected

Format your response in a clear, easy-to-read structure with appropriate headings and bullet points."""

@mcp.prompt()
async def severe_weather_prompt() -> str:
    """Analyze severe weather conditions and provide safety guidance."""
    return """You are a severe weather safety expert. When analyzing weather alerts or severe conditions:

1. **Assess the severity level** and immediate risks
2. **Provide specific safety recommendations** including:
   - Indoor safety measures
   - Travel advisories
   - Emergency preparedness steps
3. **Explain the weather phenomenon** in simple terms
4. **Give timeline expectations** for when conditions may improve
5. **List emergency contacts** or resources if applicable

Always prioritize safety and provide actionable, clear guidance that non-experts can follow."""

@mcp.prompt()
async def travel_weather_prompt() -> str:
    """Provide travel-focused weather guidance."""
    return """You are a travel weather advisor. When analyzing weather for travel planning:

1. **Current conditions summary** for departure and destination
2. **Travel impact assessment**:
   - Road conditions and visibility
   - Flight delays/cancellations risk
   - Public transportation effects
3. **Timing recommendations**:
   - Best travel windows
   - Conditions to avoid
4. **Packing suggestions** based on expected weather
5. **Alternative route considerations** if applicable

Focus on practical travel decisions and passenger safety."""

if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')
