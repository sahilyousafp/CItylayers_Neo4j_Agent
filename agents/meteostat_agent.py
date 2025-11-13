"""
Meteostat Agent - Fetches weather and climate data
"""
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from .base_agent import BaseAgent


class MeteostatAgent(BaseAgent):
    """
    Agent responsible for fetching weather and climate data using Meteostat API.
    
    Provides access to:
    - Historical weather data
    - Climate normals
    - Weather statistics
    - Temperature, precipitation, wind, etc.
    """

    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize Meteostat Agent.
        
        Args:
            config: Optional configuration dictionary with keys:
                - cache_dir: Directory for caching data (default: None)
                - max_age: Maximum cache age in days (default: 30)
        """
        super().__init__(config)
        self.cache_dir = self.config.get("cache_dir", None)
        self.max_age = self.config.get("max_age", 30)
        
        # Try to import meteostat
        try:
            from meteostat import Point, Daily, Hourly, Stations, Monthly
            self.Point = Point
            self.Daily = Daily
            self.Hourly = Hourly
            self.Monthly = Monthly
            self.Stations = Stations
            self.meteostat_available = True
        except ImportError:
            self.meteostat_available = False
        
    def process(
        self,
        latitude: float,
        longitude: float,
        start_date: str = None,
        end_date: str = None,
        interval: str = "daily",
        parameters: List[str] = None
    ) -> Dict[str, Any]:
        """
        Fetch weather data for a location.
        
        Args:
            latitude: Latitude of location
            longitude: Longitude of location
            start_date: Start date (YYYY-MM-DD), defaults to 30 days ago
            end_date: End date (YYYY-MM-DD), defaults to today
            interval: Data interval ('hourly', 'daily', 'monthly')
            parameters: List of parameters to retrieve (e.g., ['temp', 'prcp'])
            
        Returns:
            Dictionary containing:
                - ok: Success status
                - data: List of weather records
                - location: Location info
                - interval: Data interval
                - error: Error message if any
        """
        if not self.meteostat_available:
            return {
                "ok": False,
                "error": "Meteostat library not installed. Run: pip install meteostat",
                "data": [],
            }
        
        try:
            # Parse dates
            if end_date is None:
                end = datetime.now()
            else:
                end = datetime.strptime(end_date, "%Y-%m-%d")
            
            if start_date is None:
                start = end - timedelta(days=30)
            else:
                start = datetime.strptime(start_date, "%Y-%m-%d")
            
            # Create point
            location = self.Point(latitude, longitude)
            
            # Fetch data based on interval
            if interval == "hourly":
                data = self.Hourly(location, start, end)
            elif interval == "monthly":
                data = self.Monthly(location, start, end)
            else:  # daily
                data = self.Daily(location, start, end)
            
            # Fetch the data
            df = data.fetch()
            
            if df.empty:
                return {
                    "ok": True,
                    "data": [],
                    "message": "No data available for this location and period",
                    "location": {"latitude": latitude, "longitude": longitude},
                    "interval": interval,
                }
            
            # Convert to list of dictionaries
            records = []
            for idx, row in df.iterrows():
                record = {
                    "date": idx.strftime("%Y-%m-%d"),
                    "latitude": latitude,
                    "longitude": longitude,
                }
                
                # Add all available columns
                for col in df.columns:
                    if row[col] is not None and not str(row[col]) == 'nan':
                        record[col] = float(row[col]) if isinstance(row[col], (int, float)) else str(row[col])
                
                records.append(record)
            
            return {
                "ok": True,
                "data": records,
                "location": {"latitude": latitude, "longitude": longitude},
                "interval": interval,
                "count": len(records),
                "start_date": start.strftime("%Y-%m-%d"),
                "end_date": end.strftime("%Y-%m-%d"),
            }
            
        except Exception as e:
            return {
                "ok": False,
                "error": str(e),
                "data": [],
            }

    def get_nearby_stations(
        self,
        latitude: float,
        longitude: float,
        radius: int = 50000
    ) -> Dict[str, Any]:
        """
        Get nearby weather stations.
        
        Args:
            latitude: Latitude
            longitude: Longitude
            radius: Search radius in meters (default: 50km)
            
        Returns:
            Dictionary with nearby stations
        """
        if not self.meteostat_available:
            return {
                "ok": False,
                "error": "Meteostat library not installed",
                "stations": [],
            }
        
        try:
            location = self.Point(latitude, longitude)
            stations = self.Stations()
            stations = stations.nearby(latitude, longitude, radius)
            df = stations.fetch()
            
            if df.empty:
                return {
                    "ok": True,
                    "stations": [],
                    "message": "No stations found nearby",
                }
            
            stations_list = []
            for idx, row in df.iterrows():
                station = {
                    "id": idx,
                    "name": row.get("name", "Unknown"),
                    "latitude": float(row["latitude"]) if "latitude" in row else None,
                    "longitude": float(row["longitude"]) if "longitude" in row else None,
                    "elevation": float(row["elevation"]) if "elevation" in row else None,
                }
                stations_list.append(station)
            
            return {
                "ok": True,
                "stations": stations_list,
                "count": len(stations_list),
            }
            
        except Exception as e:
            return {
                "ok": False,
                "error": str(e),
                "stations": [],
            }

    def get_climate_normals(
        self,
        latitude: float,
        longitude: float
    ) -> Dict[str, Any]:
        """
        Get climate normals (monthly averages) for a location.
        
        Args:
            latitude: Latitude
            longitude: Longitude
            
        Returns:
            Dictionary with monthly climate normals
        """
        if not self.meteostat_available:
            return {
                "ok": False,
                "error": "Meteostat library not installed",
                "data": [],
            }
        
        try:
            # Get 30 years of data for climate normals
            end = datetime.now()
            start = end - timedelta(days=365 * 30)
            
            location = self.Point(latitude, longitude)
            data = self.Monthly(location, start, end)
            df = data.fetch()
            
            if df.empty:
                return {
                    "ok": True,
                    "data": [],
                    "message": "No climate data available",
                }
            
            # Calculate monthly averages
            monthly_avg = df.groupby(df.index.month).mean()
            
            normals = []
            month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                          'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            
            for month in range(1, 13):
                if month in monthly_avg.index:
                    row = monthly_avg.loc[month]
                    normal = {
                        "month": month,
                        "month_name": month_names[month - 1],
                        "latitude": latitude,
                        "longitude": longitude,
                    }
                    
                    for col in monthly_avg.columns:
                        if not str(row[col]) == 'nan':
                            normal[col] = float(row[col])
                    
                    normals.append(normal)
            
            return {
                "ok": True,
                "data": normals,
                "location": {"latitude": latitude, "longitude": longitude},
                "type": "climate_normals",
            }
            
        except Exception as e:
            return {
                "ok": False,
                "error": str(e),
                "data": [],
            }

    def get_info(self) -> Dict[str, Any]:
        """
        Return information about the Meteostat agent.
        
        Returns:
            Dictionary with agent capabilities and configuration
        """
        return {
            "name": "Meteostat Agent",
            "description": "Fetches weather and climate data from Meteostat",
            "available": self.meteostat_available,
            "capabilities": [
                "Historical weather data (hourly, daily, monthly)",
                "Climate normals (30-year averages)",
                "Nearby weather stations",
                "Temperature, precipitation, wind, pressure data",
                "Global coverage",
            ],
            "configuration": {
                "cache_dir": self.cache_dir,
                "max_age": self.max_age,
            },
            "data_parameters": [
                "tavg - Average temperature (°C)",
                "tmin - Minimum temperature (°C)",
                "tmax - Maximum temperature (°C)",
                "prcp - Precipitation (mm)",
                "snow - Snow depth (mm)",
                "wdir - Wind direction (°)",
                "wspd - Wind speed (km/h)",
                "wpgt - Wind peak gust (km/h)",
                "pres - Air pressure (hPa)",
                "tsun - Sunshine duration (min)",
            ],
            "intervals": ["hourly", "daily", "monthly"],
        }
