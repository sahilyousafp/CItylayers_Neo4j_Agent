"""
OSM Agent - Fetches OpenStreetMap data and overlays it on visualizations
"""
import requests
from typing import Dict, Any, List, Optional, Tuple
from .base_agent import BaseAgent


class OSMAgent(BaseAgent):
    """
    Agent responsible for fetching OpenStreetMap data using Overpass API
    and preparing it for layered visualization with existing map data.
    
    Supports querying various OSM features like:
    - Buildings, roads, amenities
    - Points of interest (restaurants, shops, etc.)
    - Natural features (parks, water bodies)
    - Infrastructure (hospitals, schools, etc.)
    """

    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize OSM Agent.
        
        Args:
            config: Optional configuration dictionary with keys:
                - overpass_url: Overpass API endpoint (default: public instance)
                - timeout: Request timeout in seconds (default: 30)
                - max_results: Maximum results to fetch (default: 1000)
        """
        super().__init__(config)
        self.overpass_url = self.config.get(
            "overpass_url",
            "https://overpass-api.de/api/interpreter"
        )
        self.timeout = self.config.get("timeout", 30)
        self.max_results = self.config.get("max_results", 1000)
        
    def process(
        self,
        bbox: Tuple[float, float, float, float] = None,
        center: Tuple[float, float] = None,
        radius: float = 5000,
        feature_type: str = "amenity",
        feature_value: str = None,
        tags: List[str] = None
    ) -> Dict[str, Any]:
        """
        Fetch OSM data for specified area and features.
        
        Args:
            bbox: Bounding box (min_lat, min_lon, max_lat, max_lon)
            center: Center point (lat, lon) - used with radius if bbox not provided
            radius: Search radius in meters (default: 5000)
            feature_type: OSM tag key (e.g., 'amenity', 'building', 'highway')
            feature_value: OSM tag value (e.g., 'restaurant', 'school', 'park')
            tags: Additional tags to filter (e.g., ['name', 'cuisine'])
            
        Returns:
            Dictionary containing:
                - ok: Success status
                - features: List of OSM features with geometry and properties
                - count: Number of features found
                - bbox: Bounding box used for query
                - error: Error message if any
        """
        try:
            # Build Overpass query
            query = self._build_overpass_query(
                bbox=bbox,
                center=center,
                radius=radius,
                feature_type=feature_type,
                feature_value=feature_value
            )
            
            # Execute query
            response = requests.post(
                self.overpass_url,
                data={"data": query},
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Parse and format results
            features = self._parse_osm_data(data, tags)
            
            # Calculate bounding box if not provided
            if not bbox and features:
                bbox = self._calculate_bbox(features)
            
            return {
                "ok": True,
                "features": features[:self.max_results],
                "count": len(features),
                "bbox": bbox,
                "feature_type": feature_type,
                "feature_value": feature_value,
            }
            
        except Exception as e:
            return {
                "ok": False,
                "error": str(e),
                "features": [],
                "count": 0,
            }

    def _build_overpass_query(
        self,
        bbox: Tuple[float, float, float, float] = None,
        center: Tuple[float, float] = None,
        radius: float = 5000,
        feature_type: str = "amenity",
        feature_value: str = None
    ) -> str:
        """
        Build Overpass QL query string.
        
        Args:
            bbox: Bounding box (min_lat, min_lon, max_lat, max_lon)
            center: Center point (lat, lon)
            radius: Search radius in meters
            feature_type: OSM tag key
            feature_value: OSM tag value
            
        Returns:
            Overpass QL query string
        """
        # Build filter
        if feature_value:
            tag_filter = f'["{feature_type}"="{feature_value}"]'
        else:
            tag_filter = f'["{feature_type}"]'
        
        # Build area specification
        if bbox:
            min_lat, min_lon, max_lat, max_lon = bbox
            area_spec = f"({min_lat},{min_lon},{max_lat},{max_lon})"
        elif center:
            lat, lon = center
            area_spec = f"(around:{radius},{lat},{lon})"
        else:
            # Default to small area if nothing specified
            area_spec = "(around:1000,0,0)"
        
        # Build complete query
        query = f"""
        [out:json][timeout:{self.timeout}];
        (
          node{tag_filter}{area_spec};
          way{tag_filter}{area_spec};
          relation{tag_filter}{area_spec};
        );
        out geom;
        """
        
        return query

    def _parse_osm_data(
        self,
        data: Dict[str, Any],
        tags: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Parse Overpass API response into feature list.
        
        Args:
            data: Overpass API response JSON
            tags: List of tag keys to extract
            
        Returns:
            List of feature dictionaries
        """
        features = []
        elements = data.get("elements", [])
        
        for element in elements:
            element_type = element.get("type")
            element_id = element.get("id")
            tags_dict = element.get("tags", {})
            
            # Extract geometry based on element type
            geometry = None
            if element_type == "node":
                lat = element.get("lat")
                lon = element.get("lon")
                if lat and lon:
                    geometry = {
                        "type": "Point",
                        "coordinates": [lon, lat]
                    }
            elif element_type == "way":
                # Ways have geometry as list of nodes
                geom = element.get("geometry", [])
                if geom:
                    coordinates = [[node["lon"], node["lat"]] for node in geom]
                    # Check if it's a closed polygon
                    if len(coordinates) > 2 and coordinates[0] == coordinates[-1]:
                        geometry = {
                            "type": "Polygon",
                            "coordinates": [coordinates]
                        }
                    else:
                        geometry = {
                            "type": "LineString",
                            "coordinates": coordinates
                        }
            elif element_type == "relation":
                # Relations are complex - just get center if available
                center = element.get("center")
                if center:
                    geometry = {
                        "type": "Point",
                        "coordinates": [center["lon"], center["lat"]]
                    }
            
            if not geometry:
                continue
            
            # Extract properties
            properties = {
                "osm_id": element_id,
                "osm_type": element_type,
                "name": tags_dict.get("name", ""),
            }
            
            # Add requested tags
            if tags:
                for tag in tags:
                    if tag in tags_dict:
                        properties[tag] = tags_dict[tag]
            else:
                # Add all tags if none specified
                properties.update(tags_dict)
            
            features.append({
                "type": "Feature",
                "geometry": geometry,
                "properties": properties
            })
        
        return features

    def _calculate_bbox(
        self,
        features: List[Dict[str, Any]]
    ) -> Tuple[float, float, float, float]:
        """
        Calculate bounding box from features.
        
        Args:
            features: List of features
            
        Returns:
            Bounding box (min_lat, min_lon, max_lat, max_lon)
        """
        lats = []
        lons = []
        
        for feature in features:
            geom = feature.get("geometry", {})
            geom_type = geom.get("type")
            coords = geom.get("coordinates", [])
            
            if geom_type == "Point":
                lons.append(coords[0])
                lats.append(coords[1])
            elif geom_type == "LineString":
                for coord in coords:
                    lons.append(coord[0])
                    lats.append(coord[1])
            elif geom_type == "Polygon":
                for ring in coords:
                    for coord in ring:
                        lons.append(coord[0])
                        lats.append(coord[1])
        
        if lats and lons:
            return (min(lats), min(lons), max(lats), max(lons))
        return (0, 0, 0, 0)

    def query_by_location_name(
        self,
        location_name: str,
        feature_type: str = "amenity",
        feature_value: str = None
    ) -> Dict[str, Any]:
        """
        Query OSM data by location name (city, region, etc.).
        First geocodes the location, then fetches OSM data.
        
        Args:
            location_name: Name of location (e.g., "New York", "London")
            feature_type: OSM tag key
            feature_value: OSM tag value
            
        Returns:
            Dictionary with OSM features
        """
        try:
            # Use Nominatim to geocode location
            nominatim_url = "https://nominatim.openstreetmap.org/search"
            params = {
                "q": location_name,
                "format": "json",
                "limit": 1
            }
            headers = {"User-Agent": "CityLayers-OSM-Agent/1.0"}
            
            response = requests.get(nominatim_url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            results = response.json()
            
            if not results:
                return {
                    "ok": False,
                    "error": f"Location '{location_name}' not found",
                    "features": [],
                    "count": 0,
                }
            
            # Get bounding box from first result
            result = results[0]
            bbox = result.get("boundingbox")  # [min_lat, max_lat, min_lon, max_lon]
            
            if bbox:
                # Reorder to match our format
                bbox = (float(bbox[0]), float(bbox[2]), float(bbox[1]), float(bbox[3]))
                
                # Query OSM with this bbox
                return self.process(
                    bbox=bbox,
                    feature_type=feature_type,
                    feature_value=feature_value
                )
            else:
                return {
                    "ok": False,
                    "error": "Could not determine bounding box",
                    "features": [],
                    "count": 0,
                }
                
        except Exception as e:
            return {
                "ok": False,
                "error": str(e),
                "features": [],
                "count": 0,
            }

    def get_city_boundary(
        self,
        city_name: str
    ) -> Dict[str, Any]:
        """
        Fetch city boundary polygon from OSM.
        
        Args:
            city_name: Name of the city
            
        Returns:
            Dictionary containing:
                - ok: Success status
                - geometry: GeoJSON geometry of city boundary
                - properties: City properties (name, population, etc.)
                - error: Error message if any
        """
        try:
            # First, geocode to get the OSM relation ID for the city
            nominatim_url = "https://nominatim.openstreetmap.org/search"
            params = {
                "q": city_name,
                "format": "json",
                "limit": 1,
                "polygon_geojson": 1,
                "addressdetails": 1
            }
            headers = {"User-Agent": "CityLayers-OSM-Agent/1.0"}
            
            response = requests.get(nominatim_url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            results = response.json()
            
            if not results:
                return {
                    "ok": False,
                    "error": f"City '{city_name}' not found",
                }
            
            result = results[0]
            
            # If we have a polygon directly from Nominatim, use it
            if "geojson" in result:
                return {
                    "ok": True,
                    "geometry": result["geojson"],
                    "properties": {
                        "name": result.get("display_name", city_name),
                        "osm_type": result.get("osm_type"),
                        "osm_id": result.get("osm_id"),
                    }
                }
            
            # Otherwise, query Overpass for admin boundary
            osm_type = result.get("osm_type")
            osm_id = result.get("osm_id")
            
            if not osm_id:
                return {
                    "ok": False,
                    "error": "Could not determine OSM ID for city",
                }
            
            # Build Overpass query for the specific relation
            if osm_type == "relation":
                type_prefix = "rel"
            elif osm_type == "way":
                type_prefix = "way"
            else:
                type_prefix = "node"
            
            query = f"""
            [out:json][timeout:{self.timeout}];
            (
              {type_prefix}({osm_id});
            );
            out geom;
            """
            
            response = requests.post(
                self.overpass_url,
                data={"data": query},
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            elements = data.get("elements", [])
            
            if not elements:
                return {
                    "ok": False,
                    "error": "No boundary data found",
                }
            
            element = elements[0]
            
            # Parse geometry
            geometry = None
            if element.get("type") == "way":
                geom = element.get("geometry", [])
                if geom:
                    coordinates = [[node["lon"], node["lat"]] for node in geom]
                    if coordinates[0] != coordinates[-1]:
                        coordinates.append(coordinates[0])  # Close the polygon
                    geometry = {
                        "type": "Polygon",
                        "coordinates": [coordinates]
                    }
            elif element.get("type") == "relation":
                # For relations, construct MultiPolygon from member ways
                members = element.get("members", [])
                polygons = []
                
                for member in members:
                    if member.get("type") == "way" and member.get("role") in ["outer", ""]:
                        geom = member.get("geometry", [])
                        if geom:
                            coordinates = [[node["lon"], node["lat"]] for node in geom]
                            if len(coordinates) > 2:
                                if coordinates[0] != coordinates[-1]:
                                    coordinates.append(coordinates[0])
                                polygons.append([coordinates])
                
                if polygons:
                    if len(polygons) == 1:
                        geometry = {
                            "type": "Polygon",
                            "coordinates": polygons[0]
                        }
                    else:
                        geometry = {
                            "type": "MultiPolygon",
                            "coordinates": polygons
                        }
            
            if not geometry:
                return {
                    "ok": False,
                    "error": "Could not parse boundary geometry",
                }
            
            return {
                "ok": True,
                "geometry": geometry,
                "properties": {
                    "name": element.get("tags", {}).get("name", city_name),
                    "osm_type": element.get("type"),
                    "osm_id": element.get("id"),
                    **element.get("tags", {})
                }
            }
            
        except Exception as e:
            return {
                "ok": False,
                "error": str(e),
            }

    def get_info(self) -> Dict[str, Any]:
        """
        Return information about the OSM agent.
        
        Returns:
            Dictionary with agent capabilities and configuration
        """
        return {
            "name": "OSM Agent",
            "description": "Fetches OpenStreetMap data for layered visualizations",
            "capabilities": [
                "Query OSM features by bounding box or center point",
                "Support for nodes, ways, and relations",
                "Flexible tag-based filtering",
                "Geocoding location names to coordinates",
                "GeoJSON output format",
                "Automatic bounding box calculation",
            ],
            "configuration": {
                "overpass_url": self.overpass_url,
                "timeout": self.timeout,
                "max_results": self.max_results,
            },
            "supported_features": [
                "amenity - Restaurants, shops, hospitals, schools, etc.",
                "building - Building footprints",
                "highway - Roads, paths, streets",
                "natural - Parks, water bodies, forests",
                "leisure - Parks, playgrounds, sports facilities",
                "tourism - Hotels, attractions, museums",
                "shop - Various retail establishments",
                "landuse - Land use categories",
            ],
            "data_sources": [
                "OpenStreetMap (via Overpass API)",
                "Nominatim (for geocoding)",
            ],
        }
