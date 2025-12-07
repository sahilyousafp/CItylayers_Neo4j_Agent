"""
Open-Meteo Weather Agent - Fetches weather data from Open-Meteo API
Free, open-source weather API with no authentication required
"""
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from .base_agent import BaseAgent
import requests


class OpenMeteoAgent(BaseAgent):
    """
    Agent responsible for fetching weather data using Open-Meteo API.
    
    Open-Meteo provides:
    - Current weather
    - Historical weather data
    - Weather forecasts
    - No API key required
    - Free and open-source
    
    API Documentation: https://open-meteo.com/
    """

    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize Open-Meteo Agent.
        
        Args:
            config: Optional configuration dictionary
        """
        super().__init__(config)
        self.base_url = "https://api.open-meteo.com/v1"
        
    def process(
        self,
        latitude: float,
        longitude: float,
        start_date: str = None,
        end_date: str = None,
        temperature_unit: str = "celsius",
        include_current: bool = True
    ) -> Dict[str, Any]:
        """
        Fetch weather data for a location.
        
        Args:
            latitude: Latitude of location
            longitude: Longitude of location
            start_date: Start date (YYYY-MM-DD), defaults to 7 days ago
            end_date: End date (YYYY-MM-DD), defaults to today
            temperature_unit: Temperature unit ('celsius' or 'fahrenheit')
            include_current: Include current weather data
            
        Returns:
            Dictionary containing:
                - ok: Success status
                - data: List of weather records
                - current: Current weather if requested
                - location: Location info
                - error: Error message if any
        """
        try:
            # Parse dates
            if end_date is None:
                end = datetime.now()
            else:
                end = datetime.strptime(end_date, "%Y-%m-%d")
            
            if start_date is None:
                start = end - timedelta(days=7)
            else:
                start = datetime.strptime(start_date, "%Y-%m-%d")
            
            # Build API request for historical/forecast data
            params = {
                "latitude": latitude,
                "longitude": longitude,
                "start_date": start.strftime("%Y-%m-%d"),
                "end_date": end.strftime("%Y-%m-%d"),
                "daily": "temperature_2m_max,temperature_2m_min,temperature_2m_mean,precipitation_sum,windspeed_10m_max",
                "temperature_unit": temperature_unit,
                "timezone": "auto"
            }
            
            response = requests.get(f"{self.base_url}/forecast", params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Parse daily data
            records = []
            if "daily" in data:
                daily = data["daily"]
                dates = daily.get("time", [])
                
                for i, date in enumerate(dates):
                    record = {
                        "date": date,
                        "latitude": latitude,
                        "longitude": longitude,
                        "tmax": daily.get("temperature_2m_max", [])[i] if i < len(daily.get("temperature_2m_max", [])) else None,
                        "tmin": daily.get("temperature_2m_min", [])[i] if i < len(daily.get("temperature_2m_min", [])) else None,
                        "tavg": daily.get("temperature_2m_mean", [])[i] if i < len(daily.get("temperature_2m_mean", [])) else None,
                        "prcp": daily.get("precipitation_sum", [])[i] if i < len(daily.get("precipitation_sum", [])) else None,
                        "wspd": daily.get("windspeed_10m_max", [])[i] if i < len(daily.get("windspeed_10m_max", [])) else None,
                    }
                    # Remove None values
                    record = {k: v for k, v in record.items() if v is not None}
                    records.append(record)
            
            result = {
                "ok": True,
                "data": records,
                "location": {
                    "latitude": latitude,
                    "longitude": longitude,
                    "elevation": data.get("elevation"),
                    "timezone": data.get("timezone"),
                },
                "count": len(records),
                "start_date": start.strftime("%Y-%m-%d"),
                "end_date": end.strftime("%Y-%m-%d"),
            }
            
            # Get current weather if requested
            if include_current:
                current_data = self.get_current_weather(latitude, longitude, temperature_unit)
                if current_data.get("ok"):
                    result["current"] = current_data.get("current")
            
            return result
            
        except requests.exceptions.Timeout:
            return {
                "ok": False,
                "error": "Request timed out. Please try again.",
                "data": [],
            }
        except requests.exceptions.RequestException as e:
            return {
                "ok": False,
                "error": f"API request failed: {str(e)}",
                "data": [],
            }
        except Exception as e:
            return {
                "ok": False,
                "error": str(e),
                "data": [],
            }

    def get_current_weather(
        self,
        latitude: float,
        longitude: float,
        temperature_unit: str = "celsius"
    ) -> Dict[str, Any]:
        """
        Get current weather for a location.
        
        Args:
            latitude: Latitude
            longitude: Longitude
            temperature_unit: Temperature unit ('celsius' or 'fahrenheit')
            
        Returns:
            Dictionary with current weather data
        """
        try:
            params = {
                "latitude": latitude,
                "longitude": longitude,
                "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m,wind_direction_10m",
                "temperature_unit": temperature_unit,
                "timezone": "auto"
            }
            
            response = requests.get(f"{self.base_url}/forecast", params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if "current" in data:
                current = data["current"]
                return {
                    "ok": True,
                    "current": {
                        "time": current.get("time"),
                        "temperature": current.get("temperature_2m"),
                        "apparent_temperature": current.get("apparent_temperature"),
                        "humidity": current.get("relative_humidity_2m"),
                        "precipitation": current.get("precipitation"),
                        "weather_code": current.get("weather_code"),
                        "wind_speed": current.get("wind_speed_10m"),
                        "wind_direction": current.get("wind_direction_10m"),
                    },
                    "location": {
                        "latitude": latitude,
                        "longitude": longitude,
                    }
                }
            
            return {
                "ok": False,
                "error": "No current weather data available",
            }
            
        except Exception as e:
            return {
                "ok": False,
                "error": str(e),
            }

    def get_hourly_forecast(
        self,
        latitude: float,
        longitude: float,
        hours: int = 24,
        temperature_unit: str = "celsius"
    ) -> Dict[str, Any]:
        """
        Get hourly weather forecast.
        
        Args:
            latitude: Latitude
            longitude: Longitude
            hours: Number of hours to forecast (default: 24)
            temperature_unit: Temperature unit ('celsius' or 'fahrenheit')
            
        Returns:
            Dictionary with hourly forecast data
        """
        try:
            params = {
                "latitude": latitude,
                "longitude": longitude,
                "hourly": "temperature_2m,relative_humidity_2m,precipitation,weather_code,wind_speed_10m",
                "temperature_unit": temperature_unit,
                "timezone": "auto",
                "forecast_days": (hours // 24) + 1
            }
            
            response = requests.get(f"{self.base_url}/forecast", params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if "hourly" in data:
                hourly = data["hourly"]
                times = hourly.get("time", [])[:hours]
                
                records = []
                for i, time in enumerate(times):
                    record = {
                        "time": time,
                        "temperature": hourly.get("temperature_2m", [])[i] if i < len(hourly.get("temperature_2m", [])) else None,
                        "humidity": hourly.get("relative_humidity_2m", [])[i] if i < len(hourly.get("relative_humidity_2m", [])) else None,
                        "precipitation": hourly.get("precipitation", [])[i] if i < len(hourly.get("precipitation", [])) else None,
                        "weather_code": hourly.get("weather_code", [])[i] if i < len(hourly.get("weather_code", [])) else None,
                        "wind_speed": hourly.get("wind_speed_10m", [])[i] if i < len(hourly.get("wind_speed_10m", [])) else None,
                    }
                    # Remove None values
                    record = {k: v for k, v in record.items() if v is not None}
                    records.append(record)
                
                return {
                    "ok": True,
                    "data": records,
                    "count": len(records),
                    "location": {
                        "latitude": latitude,
                        "longitude": longitude,
                    }
                }
            
            return {
                "ok": False,
                "error": "No hourly forecast data available",
                "data": [],
            }
            
        except Exception as e:
            return {
                "ok": False,
                "error": str(e),
                "data": [],
            }

    def get_info(self) -> Dict[str, Any]:
        """
        Return information about the Open-Meteo agent.
        
        Returns:
            Dictionary with agent capabilities and configuration
        """
        return {
            "name": "Open-Meteo Weather Agent",
            "description": "Fetches weather data from Open-Meteo API",
            "available": True,
            "api_url": self.base_url,
            "requires_auth": False,
            "capabilities": [
                "Current weather data",
                "Historical weather data (7 days back)",
                "Weather forecasts (7 days ahead)",
                "Hourly weather data",
                "Daily aggregates",
                "Global coverage",
                "No API key required",
                "Free and open-source",
            ],
            "data_parameters": [
                "temperature_2m - Temperature at 2 meters (°C/°F)",
                "apparent_temperature - Feels like temperature",
                "relative_humidity_2m - Relative humidity (%)",
                "precipitation - Precipitation (mm)",
                "weather_code - WMO weather code",
                "wind_speed_10m - Wind speed at 10 meters (km/h)",
                "wind_direction_10m - Wind direction (°)",
            ],
            "temperature_units": ["celsius", "fahrenheit"],
            "documentation": "https://open-meteo.com/en/docs",
        }
