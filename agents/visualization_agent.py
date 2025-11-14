"""
Visualization Agent - Handles map visualizations using PyDeck
"""
from typing import Dict, Any, List
from .base_agent import BaseAgent
from viz.pydeck_viz import PydeckVisualizer


class VisualizationAgent(BaseAgent):
    """
    Agent responsible for creating map visualizations from location data.
    Supports multiple visualization modes: scatter, heatmap, hexagon, choropleth.
    """

    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize Visualization Agent.
        
        Args:
            config: Optional configuration dictionary with keys:
                - default_mode: Default visualization mode
                - radius: Default radius for visualizations
                - elevation_scale: Scale for 3D hexagon elevation
        """
        super().__init__(config)
        self.visualizer = PydeckVisualizer()
        self.default_mode = self.config.get("default_mode", "scatter")

    def process(
        self,
        records: List[Dict[str, Any]],
        mode: str = None,
        radius: int = None,
        elevation_scale: int = None,
        center_lat: float = None,
        center_lon: float = None,
        zoom: int = None,
    ) -> str:
        """
        Generate HTML visualization from location records.
        
        Args:
            records: List of location records from database
            mode: Visualization mode (scatter, heatmap, hexagon, choropleth)
            radius: Radius for scatter/hexagon visualizations
            elevation_scale: Scale for 3D hexagon elevation
            center_lat: Latitude for map center (preserves view)
            center_lon: Longitude for map center (preserves view)
            zoom: Zoom level (preserves view)
            
        Returns:
            HTML string containing the embedded PyDeck visualization
        """
        viz_mode = mode or self.default_mode
        viz_radius = radius or self.config.get("radius", 5000)
        viz_elevation = elevation_scale or self.config.get("elevation_scale", 100)

        try:
            html = self.visualizer.render_html(
                records=records,
                mode=viz_mode,
                radius=viz_radius,
                elevation_scale=viz_elevation,
                center_lat=center_lat,
                center_lon=center_lon,
                zoom=zoom,
            )
            return html
        except Exception as e:
            return f"<div style='padding:12px;color:#b00020;'>Error rendering visualization: {str(e)}</div>"

    def get_supported_modes(self) -> List[str]:
        """
        Get list of supported visualization modes.
        
        Returns:
            List of mode names
        """
        return ["scatter", "heatmap", "hexagon", "choropleth", "arc"]

    def set_default_mode(self, mode: str) -> None:
        """
        Set the default visualization mode.
        
        Args:
            mode: Visualization mode name
        """
        if mode in self.get_supported_modes():
            self.default_mode = mode
            self.config["default_mode"] = mode

    def get_info(self) -> Dict[str, Any]:
        """
        Return information about the Visualization agent.
        
        Returns:
            Dictionary with agent capabilities and configuration
        """
        return {
            "name": "Visualization Agent",
            "description": "Creates interactive map visualizations using PyDeck",
            "capabilities": [
                "Scatter plot visualization",
                "Heatmap generation",
                "3D hexagon aggregation",
                "Choropleth polygon rendering",
                "Arc layer for connections/flow",
            ],
            "supported_modes": self.get_supported_modes(),
            "default_mode": self.default_mode,
            "library": "PyDeck (deck.gl)",
        }
