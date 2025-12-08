"""
Vegetation Agent: Provides tree and vegetation data from Vienna Open Data
"""

import requests
from typing import Dict, List
from .base_agent import BaseAgent

class VegetationAgent(BaseAgent):
    """Agent for fetching vegetation and tree data from Vienna Open Data"""
    
    def __init__(self):
        super().__init__()
        # Vienna Open Data - Baumkataster (Tree Cadastre) API
        self.base_url = "https://data.wien.gv.at/daten/geo"
        self.tree_dataset_url = "https://data.wien.gv.at/daten/geo?service=WFS&request=GetFeature&version=1.1.0&typeName=ogdwien:BAUMKATOGD&srsName=EPSG:4326&outputFormat=json"
    
    def get_info(self) -> str:
        """Return information about the Vegetation Agent"""
        return "Vegetation Agent: Provides tree and vegetation data from Vienna Open Data including tree species, height, crown diameter, and location."
    
    def process(self, query: str, context: Dict = None) -> Dict:
        """
        Process a query related to vegetation
        
        Args:
            query: The user query
            context: Additional context (e.g., map bounds)
            
        Returns:
            Processing results
        """
        if context and 'bounds' in context:
            return self.get_vegetation_in_bounds(context['bounds'])
        
        return {
            'type': 'info',
            'message': 'Vegetation agent provides tree and vegetation information. Please specify map bounds.'
        }
    
    def get_vegetation_in_bounds(self, bounds: Dict) -> Dict:
        """
        Get vegetation data within specified bounds
        
        Args:
            bounds: Dictionary with 'north', 'south', 'east', 'west' keys
            
        Returns:
            Dictionary with tree data
        """
        try:
            # Vienna Open Data WFS service with bounding box
            north = bounds.get('north')
            south = bounds.get('south')
            east = bounds.get('east')
            west = bounds.get('west')
            
            # Construct WFS request with BBOX filter
            bbox = f"{west},{south},{east},{north},EPSG:4326"
            url = f"{self.tree_dataset_url}&bbox={bbox}"
            
            print(f"Fetching vegetation data from: {url}")
            
            response = requests.get(url, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                trees = []
                
                features = data.get('features', [])
                print(f"Received {len(features)} tree features from Vienna Open Data")
                
                for feature in features[:500]:  # Limit to 500 trees for performance
                    properties = feature.get('properties', {})
                    geometry = feature.get('geometry', {})
                    
                    if geometry.get('type') == 'Point':
                        coords = geometry.get('coordinates', [])
                        if len(coords) >= 2:
                            tree = {
                                'id': properties.get('BAUM_ID', ''),
                                'species': properties.get('GATTUNG_ART', 'Unknown'),
                                'genus': properties.get('GATTUNG', ''),
                                'species_name': properties.get('ART', ''),
                                'height': properties.get('BAUMHOEHE', 0),
                                'crown_diameter': properties.get('KRONENDURCHMESSER', 0),
                                'trunk_circumference': properties.get('STAMMUMFANG', 0),
                                'planting_year': properties.get('PFLANZJAHR', ''),
                                'lat': coords[1],
                                'lon': coords[0]
                            }
                            trees.append(tree)
                
                return {
                    'ok': True,
                    'trees': trees,
                    'count': len(trees),
                    'source': 'Vienna Open Data'
                }
            else:
                print(f"Error fetching vegetation data: {response.status_code}")
                return {
                    'ok': False,
                    'error': f'API returned status {response.status_code}',
                    'trees': []
                }
                
        except Exception as e:
            print(f"Error in get_vegetation_in_bounds: {e}")
            import traceback
            traceback.print_exc()
            return {
                'ok': False,
                'error': str(e),
                'trees': []
            }
    
    def get_tree_species_stats(self, bounds: Dict) -> Dict:
        """
        Get statistics about tree species in the given bounds
        
        Args:
            bounds: Map bounds
            
        Returns:
            Dictionary with species statistics
        """
        result = self.get_vegetation_in_bounds(bounds)
        
        if not result.get('ok'):
            return result
        
        trees = result.get('trees', [])
        species_count = {}
        
        for tree in trees:
            species = tree.get('species', 'Unknown')
            species_count[species] = species_count.get(species, 0) + 1
        
        # Sort by count
        sorted_species = sorted(species_count.items(), key=lambda x: x[1], reverse=True)
        
        return {
            'ok': True,
            'total_trees': len(trees),
            'species_count': len(species_count),
            'top_species': sorted_species[:10],
            'all_species': dict(sorted_species)
        }
