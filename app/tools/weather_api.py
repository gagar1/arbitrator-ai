"""Weather API integration for shipping and logistics disputes."""

import aiohttp
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import os

logger = logging.getLogger(__name__)


class WeatherAPI:
    """Weather API client for retrieving historical and current weather data."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("WEATHER_API_KEY")
        self.base_url = "https://api.openweathermap.org/data/2.5"
        self.historical_url = "https://api.openweathermap.org/data/3.0/onecall/timemachine"
    
    async def get_current_weather(self, location: str) -> Dict[str, Any]:
        """Get current weather for a location."""
        try:
            if not self.api_key:
                return {"error": "Weather API key not configured"}
            
            url = f"{self.base_url}/weather"
            params = {
                "q": location,
                "appid": self.api_key,
                "units": "metric"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._format_weather_data(data)
                    else:
                        return {
                            "error": f"Weather API error: {response.status}",
                            "location": location
                        }
        
        except Exception as e:
            logger.error(f"Error fetching current weather: {str(e)}")
            return {"error": "Failed to fetch weather data", "details": str(e)}
    
    async def get_historical_weather(self, 
                                   latitude: float, 
                                   longitude: float, 
                                   date: datetime) -> Dict[str, Any]:
        """Get historical weather data for a specific date and location."""
        try:
            if not self.api_key:
                return {"error": "Weather API key not configured"}
            
            timestamp = int(date.timestamp())
            url = self.historical_url
            params = {
                "lat": latitude,
                "lon": longitude,
                "dt": timestamp,
                "appid": self.api_key,
                "units": "metric"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._format_historical_data(data)
                    else:
                        return {
                            "error": f"Historical weather API error: {response.status}",
                            "date": date.isoformat()
                        }
        
        except Exception as e:
            logger.error(f"Error fetching historical weather: {str(e)}")
            return {"error": "Failed to fetch historical weather data", "details": str(e)}
    
    async def get_weather_for_dispute(self, 
                                    location: str, 
                                    incident_date: datetime,
                                    duration_days: int = 7) -> Dict[str, Any]:
        """Get weather data relevant to a shipping/logistics dispute."""
        try:
            # Get coordinates for the location first
            coords = await self._get_coordinates(location)
            if "error" in coords:
                return coords
            
            weather_data = {
                "location": location,
                "incident_date": incident_date.isoformat(),
                "analysis_period": f"{duration_days} days",
                "weather_conditions": [],
                "severe_weather_events": [],
                "impact_assessment": {}
            }
            
            # Get weather data for the incident period
            for i in range(duration_days):
                check_date = incident_date + timedelta(days=i)
                daily_weather = await self.get_historical_weather(
                    coords["lat"], coords["lon"], check_date
                )
                
                if "error" not in daily_weather:
                    weather_data["weather_conditions"].append(daily_weather)
                    
                    # Check for severe weather
                    if self._is_severe_weather(daily_weather):
                        weather_data["severe_weather_events"].append({
                            "date": check_date.isoformat(),
                            "conditions": daily_weather,
                            "severity": self._assess_severity(daily_weather)
                        })
            
            # Generate impact assessment
            weather_data["impact_assessment"] = self._assess_weather_impact(
                weather_data["weather_conditions"],
                weather_data["severe_weather_events"]
            )
            
            return weather_data
            
        except Exception as e:
            logger.error(f"Error analyzing weather for dispute: {str(e)}")
            return {"error": "Failed to analyze weather data", "details": str(e)}
    
    async def _get_coordinates(self, location: str) -> Dict[str, Any]:
        """Get latitude and longitude for a location."""
        try:
            url = f"{self.base_url}/weather"
            params = {
                "q": location,
                "appid": self.api_key
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "lat": data["coord"]["lat"],
                            "lon": data["coord"]["lon"]
                        }
                    else:
                        return {"error": f"Failed to get coordinates for {location}"}
        
        except Exception as e:
            return {"error": f"Coordinate lookup failed: {str(e)}"}
    
    def _format_weather_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Format weather API response data."""
        return {
            "location": data["name"],
            "country": data["sys"]["country"],
            "temperature": data["main"]["temp"],
            "feels_like": data["main"]["feels_like"],
            "humidity": data["main"]["humidity"],
            "pressure": data["main"]["pressure"],
            "visibility": data.get("visibility", 0) / 1000,  # Convert to km
            "wind_speed": data["wind"]["speed"],
            "wind_direction": data["wind"].get("deg", 0),
            "weather_main": data["weather"][0]["main"],
            "weather_description": data["weather"][0]["description"],
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _format_historical_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Format historical weather data."""
        current = data["data"][0] if "data" in data and data["data"] else data.get("current", {})
        
        return {
            "date": datetime.fromtimestamp(current["dt"]).isoformat(),
            "temperature": current["temp"],
            "feels_like": current["feels_like"],
            "humidity": current["humidity"],
            "pressure": current["pressure"],
            "visibility": current.get("visibility", 0) / 1000,
            "wind_speed": current["wind_speed"],
            "wind_direction": current.get("wind_deg", 0),
            "weather_main": current["weather"][0]["main"],
            "weather_description": current["weather"][0]["description"]
        }
    
    def _is_severe_weather(self, weather_data: Dict[str, Any]) -> bool:
        """Determine if weather conditions are severe."""
        severe_conditions = [
            weather_data.get("wind_speed", 0) > 15,  # > 15 m/s (strong wind)
            weather_data.get("weather_main", "").lower() in ["thunderstorm", "snow", "extreme"],
            weather_data.get("visibility", 10) < 1,  # < 1 km visibility
            weather_data.get("temperature", 0) < -10 or weather_data.get("temperature", 0) > 40
        ]
        
        return any(severe_conditions)
    
    def _assess_severity(self, weather_data: Dict[str, Any]) -> str:
        """Assess the severity of weather conditions."""
        wind_speed = weather_data.get("wind_speed", 0)
        weather_main = weather_data.get("weather_main", "").lower()
        visibility = weather_data.get("visibility", 10)
        
        if wind_speed > 25 or weather_main == "extreme" or visibility < 0.5:
            return "extreme"
        elif wind_speed > 15 or weather_main in ["thunderstorm", "snow"] or visibility < 1:
            return "severe"
        else:
            return "moderate"
    
    def _assess_weather_impact(self, 
                             conditions: List[Dict[str, Any]], 
                             severe_events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Assess the potential impact of weather on shipping/logistics."""
        return {
            "total_days_analyzed": len(conditions),
            "severe_weather_days": len(severe_events),
            "impact_level": "high" if len(severe_events) > 2 else "moderate" if len(severe_events) > 0 else "low",
            "shipping_delays_likely": len(severe_events) > 0,
            "force_majeure_applicable": len(severe_events) > 1,
            "recommendations": [
                "Weather conditions may justify shipping delays" if len(severe_events) > 0 else "Weather unlikely to impact shipping",
                "Consider force majeure clause" if len(severe_events) > 1 else "Standard contract terms apply"
            ]
        }