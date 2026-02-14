"""
Movement Agent: Provides public transport data for Austria using Österreichische Verkehrsverbund (ÖBB) API
"""

import requests
from typing import Dict, List, Optional
from .base_agent import BaseAgent

class MovementAgent(BaseAgent):
    """Agent for fetching public transport data in Austria"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://fahrplan.oebb.at/bin/query.exe/dn"
        self.api_url = "https://fahrplan.oebb.at/bin/stboard.exe/dn"
    
    def get_info(self) -> str:
        """Return information about the Movement Agent"""
        return "Movement Agent: Provides public transport data for Austria including nearby stations, departures, and routes."
    
    def process(self, query: str, context: Dict = None) -> Dict:
        """
        Process a query related to public transport
        
        Args:
            query: The user query
            context: Additional context (e.g., current location, map bounds)
            
        Returns:
            Processing results
        """
        if context and 'lat' in context and 'lon' in context:
            return self.search(query, lat=context['lat'], lon=context['lon'])
        
        return {
            'type': 'info',
            'message': 'Movement agent provides public transport information. Please specify a location.'
        }
        
    def get_nearby_stations(self, lat: float, lon: float, radius: int = 1000) -> List[Dict]:
        """
        Get nearby public transport stations
        
        Args:
            lat: Latitude
            lon: Longitude
            radius: Search radius in meters (default 1000m)
            
        Returns:
            List of nearby stations with their information
        """
        import time
        
        # Limit radius to prevent overload
        radius = min(radius, 3000)  # Max 3km to avoid timeouts
        
        try:
            # Using OpenStreetMap Overpass API for public transport stops
            overpass_url = "http://overpass-api.de/api/interpreter"
            
            # Query for public transport stops within radius
            query = f"""
            [out:json][timeout:25];
            (
              node["public_transport"="stop_position"](around:{radius},{lat},{lon});
              node["highway"="bus_stop"](around:{radius},{lat},{lon});
              node["railway"="tram_stop"](around:{radius},{lat},{lon});
              node["railway"="station"](around:{radius},{lat},{lon});
              node["railway"="halt"](around:{radius},{lat},{lon});
            );
            out body;
            """
            
            # Retry logic with exponential backoff
            max_retries = 2
            for attempt in range(max_retries):
                try:
                    response = requests.post(overpass_url, data={'data': query}, timeout=30)
                    
                    if response.status_code == 200:
                        data = response.json()
                        stations = []
                        
                        for element in data.get('elements', []):
                            tags = element.get('tags', {})
                            station = {
                                'id': element.get('id'),
                                'name': tags.get('name', 'Unnamed Stop'),
                                'lat': element.get('lat'),
                                'lon': element.get('lon'),
                                'type': self._get_transport_type(tags),
                                'operator': tags.get('operator', 'Unknown'),
                                'network': tags.get('network', ''),
                            }
                            stations.append(station)
                        
                        return stations
                    elif response.status_code == 504 and attempt < max_retries - 1:
                        # Retry on timeout
                        wait_time = (attempt + 1) * 2
                        print(f"Overpass API timeout, retrying in {wait_time}s... (attempt {attempt + 1}/{max_retries})")
                        time.sleep(wait_time)
                        continue
                    else:
                        print(f"Error fetching stations: {response.status_code}")
                        return []
                        
                except requests.exceptions.Timeout:
                    if attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 2
                        print(f"Request timeout, retrying in {wait_time}s... (attempt {attempt + 1}/{max_retries})")
                        time.sleep(wait_time)
                        continue
                    else:
                        print(f"Request timeout after {max_retries} attempts")
                        return []
                
        except Exception as e:
            print(f"Error in get_nearby_stations: {e}")
            return []
    
    def get_station_departures(self, station_name: str, max_results: int = 10) -> List[Dict]:
        """
        Get upcoming departures from a station
        
        Args:
            station_name: Name of the station
            max_results: Maximum number of results to return
            
        Returns:
            List of departures with line, destination, and time information
        """
        try:
            # This is a simplified implementation
            # In production, you would use the actual ÖBB API with proper authentication
            
            # For now, return sample data structure
            return [{
                'line': 'Sample Line',
                'destination': 'Sample Destination',
                'departure_time': '00:00',
                'platform': '1',
                'type': 'bus'
            }]
            
        except Exception as e:
            print(f"Error fetching departures: {e}")
            return []
    
    def _get_transport_type(self, tags: Dict) -> str:
        """Determine transport type from OSM tags"""
        if 'railway' in tags:
            rail_type = tags['railway']
            if rail_type == 'station':
                return 'train'
            elif rail_type == 'tram_stop':
                return 'tram'
            elif rail_type == 'halt':
                return 'train'
        elif 'highway' in tags and tags['highway'] == 'bus_stop':
            return 'bus'
        elif 'public_transport' in tags:
            return tags.get('bus', 'yes') and 'bus' or 'transit'
        
        return 'transit'
    
    def get_route_between_points(self, from_lat: float, from_lon: float, 
                                   to_lat: float, to_lon: float) -> Optional[Dict]:
        """
        Get public transport route between two points
        
        Args:
            from_lat: Origin latitude
            from_lon: Origin longitude
            to_lat: Destination latitude
            to_lon: Destination longitude
            
        Returns:
            Route information including connections and estimated time
        """
        # This would require ÖBB API access
        # For now, return None to indicate it's not implemented
        return None
    
    def search(self, query: str, **kwargs) -> Dict:
        """
        Search for public transport information
        
        Args:
            query: Search query (station name, location, etc.)
            **kwargs: Additional parameters
            
        Returns:
            Search results
        """
        lat = kwargs.get('lat')
        lon = kwargs.get('lon')
        
        if lat and lon:
            stations = self.get_nearby_stations(lat, lon)
            return {
                'type': 'nearby_stations',
                'query': query,
                'results': stations,
                'count': len(stations)
            }
        
        return {
            'type': 'error',
            'message': 'Please provide latitude and longitude for station search'
        }
