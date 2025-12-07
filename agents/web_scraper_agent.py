"""
Web Scraper Agent - Scrapes websites and recommends visualizations
"""
import re
import requests
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup
from .base_agent import BaseAgent


class WebScraperAgent(BaseAgent):
    """
    Agent responsible for scraping websites, extracting location/data information,
    and recommending the best visualization based on the question and extracted data.
    """

    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize Web Scraper Agent.
        
        Args:
            config: Optional configuration dictionary with keys:
                - timeout: Request timeout in seconds (default: 10)
                - max_urls: Maximum number of URLs to scrape (default: 5)
                - user_agent: Custom user agent string
        """
        super().__init__(config)
        self.timeout = self.config.get("timeout", 10)
        self.max_urls = self.config.get("max_urls", 5)
        self.user_agent = self.config.get(
            "user_agent",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        
    def process(
        self,
        urls: List[str],
        question: str = "",
        extract_locations: bool = True
    ) -> Dict[str, Any]:
        """
        Scrape websites and recommend visualization based on question and data.
        
        Args:
            urls: List of website URLs to scrape
            question: User's question about the data
            extract_locations: Whether to extract location data
            
        Returns:
            Dictionary containing:
                - ok: Success status
                - scraped_data: List of scraped content from each URL
                - locations: Extracted location information
                - recommendation: Visualization recommendation
                - error: Error message if any
        """
        try:
            # Limit number of URLs
            urls = urls[:self.max_urls]
            
            # Scrape each URL
            scraped_data = []
            all_text = []
            
            for url in urls:
                try:
                    data = self._scrape_url(url)
                    if data["ok"]:
                        scraped_data.append(data)
                        all_text.append(data["text"])
                except Exception as e:
                    scraped_data.append({
                        "ok": False,
                        "url": url,
                        "error": str(e)
                    })
            
            # Combine all text for analysis
            combined_text = "\n\n".join(all_text)
            
            # Extract locations if requested
            locations = []
            if extract_locations:
                locations = self._extract_locations(combined_text)
            
            # Analyze data and recommend visualization
            recommendation = self._recommend_visualization(
                question=question,
                text=combined_text,
                locations=locations
            )
            
            return {
                "ok": True,
                "scraped_data": scraped_data,
                "locations": locations,
                "recommendation": recommendation,
                "question": question,
            }
            
        except Exception as e:
            return {
                "ok": False,
                "error": str(e),
                "scraped_data": [],
                "locations": [],
                "recommendation": None,
            }

    def fetch_location_info(self, location_name: str, lat: float = None, lon: float = None) -> Dict[str, Any]:
        """
        Fetch general information about a location from Wikipedia API.
        
        Args:
            location_name: Name of the location
            lat: Optional latitude for geo-search
            lon: Optional longitude for geo-search
            
        Returns:
            Dictionary with location information
        """
        try:
            # Use Wikipedia API
            base_url = "https://en.wikipedia.org/w/api.php"
            
            # Search for the article
            search_params = {
                "action": "query",
                "format": "json",
                "list": "search",
                "srsearch": location_name,
                "srlimit": 1
            }
            
            response = requests.get(base_url, params=search_params, timeout=self.timeout)
            response.raise_for_status()
            search_data = response.json()
            
            if not search_data.get("query", {}).get("search"):
                return {"ok": False, "error": "No Wikipedia article found"}
            
            # Get the page title
            page_title = search_data["query"]["search"][0]["title"]
            
            # Get page extract and coordinates
            page_params = {
                "action": "query",
                "format": "json",
                "titles": page_title,
                "prop": "extracts|coordinates|pageimages",
                "exintro": True,
                "explaintext": True,
                "exsentences": 3,
                "piprop": "original"
            }
            
            response = requests.get(base_url, params=page_params, timeout=self.timeout)
            response.raise_for_status()
            page_data = response.json()
            
            pages = page_data.get("query", {}).get("pages", {})
            if not pages:
                return {"ok": False, "error": "No page data found"}
            
            page = list(pages.values())[0]
            
            info = {
                "ok": True,
                "title": page.get("title", location_name),
                "description": page.get("extract", ""),
                "url": f"https://en.wikipedia.org/wiki/{page_title.replace(' ', '_')}"
            }
            
            # Add coordinates if available
            if "coordinates" in page and page["coordinates"]:
                coords = page["coordinates"][0]
                info["lat"] = coords.get("lat")
                info["lon"] = coords.get("lon")
            
            # Add image if available
            if "original" in page.get("pageimages", {}):
                info["image"] = page["pageimages"]["original"]["source"]
            
            return info
            
        except Exception as e:
            return {
                "ok": False,
                "error": f"Failed to fetch location info: {str(e)}"
            }

    def _scrape_url(self, url: str) -> Dict[str, Any]:
        """
        Scrape a single URL and extract content.
        
        Args:
            url: URL to scrape
            
        Returns:
            Dictionary with scraped data
        """
        headers = {"User-Agent": self.user_agent}
        
        response = requests.get(url, headers=headers, timeout=self.timeout)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()
        
        # Extract text
        text = soup.get_text()
        
        # Clean up text
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        # Extract tables
        tables = []
        for table in soup.find_all('table'):
            table_data = []
            for row in table.find_all('tr'):
                cells = [cell.get_text(strip=True) for cell in row.find_all(['td', 'th'])]
                if cells:
                    table_data.append(cells)
            if table_data:
                tables.append(table_data)
        
        # Extract lists
        lists = []
        for ul in soup.find_all(['ul', 'ol']):
            items = [li.get_text(strip=True) for li in ul.find_all('li', recursive=False)]
            if items:
                lists.append(items)
        
        return {
            "ok": True,
            "url": url,
            "title": soup.title.string if soup.title else "",
            "text": text[:5000],  # Limit text length
            "tables": tables,
            "lists": lists,
        }

    def _extract_locations(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract location information from text.
        
        Args:
            text: Text to extract locations from
            
        Returns:
            List of location dictionaries
        """
        locations = []
        
        # Pattern for city, country pairs
        city_country_pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?),\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b'
        matches = re.findall(city_country_pattern, text)
        
        for city, country in matches:  # No limit - extract all locations
            locations.append({
                "type": "city",
                "city": city,
                "country": country,
                "location": f"{city}, {country}"
            })
        
        # Pattern for standalone cities
        city_pattern = r'\b(New York|Los Angeles|Chicago|Houston|Phoenix|Philadelphia|San Antonio|San Diego|Dallas|San Jose|London|Paris|Tokyo|Berlin|Madrid|Rome|Amsterdam|Vienna|Brussels|Copenhagen)\b'
        cities = set(re.findall(city_pattern, text))
        
        for city in list(cities):  # No limit - extract all cities
            if not any(loc["city"] == city for loc in locations):
                locations.append({
                    "type": "city",
                    "city": city,
                    "location": city
                })
        
        return locations

    def _recommend_visualization(
        self,
        question: str,
        text: str,
        locations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Recommend the best visualization type based on question and data.
        
        Args:
            question: User's question
            text: Scraped text content
            locations: Extracted locations
            
        Returns:
            Visualization recommendation dictionary
        """
        question_lower = question.lower()
        text_lower = text.lower()
        
        # Analyze question intent
        has_comparison = any(word in question_lower for word in ['compare', 'versus', 'vs', 'difference', 'between'])
        has_distribution = any(word in question_lower for word in ['where', 'distribution', 'spread', 'located'])
        has_density = any(word in question_lower for word in ['density', 'concentration', 'hotspot', 'cluster'])
        has_flow = any(word in question_lower for word in ['flow', 'route', 'from', 'to', 'connection'])
        has_aggregate = any(word in question_lower for word in ['total', 'sum', 'aggregate', 'overall'])
        
        # Analyze data characteristics
        num_locations = len(locations)
        has_numeric_data = bool(re.search(r'\d+(?:,\d+)*(?:\.\d+)?', text))
        has_countries = any('country' in loc.get('type', '') or loc.get('country') for loc in locations)
        
        # Recommendation logic
        recommendations = []
        
        if has_density and num_locations > 20:
            recommendations.append({
                "type": "heatmap",
                "confidence": 0.9,
                "reason": "High density of locations with clustering analysis needed"
            })
        
        if has_aggregate and num_locations > 10:
            recommendations.append({
                "type": "hexagon",
                "confidence": 0.85,
                "reason": "Aggregating multiple points into 3D hexagonal bins"
            })
        
        if has_distribution and num_locations > 5:
            recommendations.append({
                "type": "scatter",
                "confidence": 0.8,
                "reason": "Showing distribution of discrete locations"
            })
        
        if has_countries or (has_comparison and has_numeric_data):
            recommendations.append({
                "type": "choropleth",
                "confidence": 0.75,
                "reason": "Comparing regional statistics across countries/areas"
            })
        
        if has_flow:
            recommendations.append({
                "type": "arc",
                "confidence": 0.85,
                "reason": "Showing flow or connections between locations"
            })
        
        # Default fallback
        if not recommendations:
            if num_locations > 100:
                recommendations.append({
                    "type": "heatmap",
                    "confidence": 0.6,
                    "reason": "Large number of locations (heatmap for density)"
                })
            elif num_locations > 20:
                recommendations.append({
                    "type": "hexagon",
                    "confidence": 0.6,
                    "reason": "Moderate number of locations (hexagon aggregation)"
                })
            else:
                recommendations.append({
                    "type": "scatter",
                    "confidence": 0.7,
                    "reason": "Default scatter plot for point locations"
                })
        
        # Sort by confidence and return top recommendation
        recommendations.sort(key=lambda x: x["confidence"], reverse=True)
        
        return {
            "primary": recommendations[0] if recommendations else None,
            "alternatives": recommendations[1:3] if len(recommendations) > 1 else [],
            "num_locations_found": num_locations,
            "data_characteristics": {
                "has_numeric_data": has_numeric_data,
                "has_locations": num_locations > 0,
                "location_count": num_locations,
            }
        }

    def get_info(self) -> Dict[str, Any]:
        """
        Return information about the Web Scraper agent.
        
        Returns:
            Dictionary with agent capabilities and configuration
        """
        return {
            "name": "Web Scraper Agent",
            "description": "Scrapes websites, extracts location data, and recommends visualizations",
            "capabilities": [
                "Web scraping with BeautifulSoup",
                "Location extraction from text",
                "Table and list extraction",
                "Visualization recommendation based on query analysis",
                "Support for multiple visualization types (scatter, heatmap, hexagon, choropleth, arc)",
            ],
            "configuration": {
                "timeout": self.timeout,
                "max_urls": self.max_urls,
                "user_agent": self.user_agent[:50] + "...",
            },
            "supported_visualizations": [
                "scatter - Discrete point locations",
                "heatmap - Density/concentration maps",
                "hexagon - 3D aggregated hexagonal bins",
                "choropleth - Regional statistical comparisons",
                "arc - Flow/connection visualization",
            ],
        }
