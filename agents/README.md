# Agents Module

This directory contains modular AI agents that handle different aspects of the application.

## Architecture

The agents follow a modular design pattern where each agent is responsible for a specific task:

- **BaseAgent**: Abstract base class that all agents inherit from
- **Neo4jAgent**: Handles database queries and natural language to Cypher conversion
- **VisualizationAgent**: Creates map visualizations using PyDeck
- **WebScraperAgent**: Scrapes websites and recommends visualizations

## Current Agents

### Neo4jAgent

**Purpose**: Converts natural language queries to Cypher and retrieves data from Neo4j database.

**Key Methods**:
- `process(query, chat_history)`: Process a natural language query
- `get_info()`: Get agent information and capabilities

**Configuration**:
```python
config = {
    "neo4j_uri": "neo4j+s://...",
    "neo4j_username": "neo4j",
    "neo4j_password": "...",
    "google_model": "gemini-flash-latest",
    "temperature": 0
}
agent = Neo4jAgent(config)
```

### VisualizationAgent

**Purpose**: Generates interactive map visualizations from location data.

**Key Methods**:
- `process(records, mode, radius, elevation_scale)`: Generate HTML visualization
- `get_supported_modes()`: Get list of available visualization modes
- `set_default_mode(mode)`: Set default visualization mode

**Supported Modes**:
- `scatter`: Scatter plot with markers
- `heatmap`: Density heatmap
- `hexagon`: 3D hexagonal aggregation
- `choropleth`: Polygon choropleth maps

### WebScraperAgent

**Purpose**: Scrapes websites, extracts location data, and recommends the best visualization type based on the question and data.

**Key Methods**:
- `process(urls, question, extract_locations)`: Scrape URLs and get visualization recommendation
- `get_info()`: Get agent information and capabilities

**Configuration**:
```python
config = {
    "timeout": 10,  # Request timeout in seconds
    "max_urls": 5,  # Maximum URLs to scrape
    "user_agent": "Mozilla/5.0..."  # Custom user agent
}
agent = WebScraperAgent(config)
```

**Example Usage**:
```python
from agents import WebScraperAgent

agent = WebScraperAgent()
result = agent.process(
    urls=["https://example.com/data"],
    question="Show me the distribution of stores",
    extract_locations=True
)

print(result["recommendation"]["primary"]["type"])  # e.g., "scatter"
print(result["locations"])  # Extracted location data
```

**Capabilities**:
- Web scraping with BeautifulSoup
- Location extraction from text (cities, countries)
- Table and list extraction
- Query analysis (comparison, distribution, density, flow, aggregation)
- Smart visualization recommendation based on:
  - Question intent
  - Data characteristics
  - Number of locations
  - Data types present

**Visualization Recommendations**:
- `scatter`: Best for discrete point locations and distribution questions
- `heatmap`: Recommended for density/concentration and hotspot analysis
- `hexagon`: Ideal for aggregating multiple points (>10 locations)
- `choropleth`: Suggested for regional comparisons with statistical data
- `arc`: Used for flow/connection/route visualization

## Adding a New Agent

To add a new agent to the system:

### 1. Create Agent File

Create a new file in the `agents/` directory (e.g., `my_agent.py`):

```python
"""
My Agent - Description of what this agent does
"""
from typing import Dict, Any
from .base_agent import BaseAgent


class MyAgent(BaseAgent):
    """
    Agent description and purpose.
    """

    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the agent.
        
        Args:
            config: Optional configuration dictionary
        """
        super().__init__(config)
        # Initialize agent-specific components
        self.my_component = self._init_component()

    def _init_component(self):
        """Initialize internal components"""
        pass

    def process(self, *args, **kwargs) -> Any:
        """
        Main processing method - implement your agent logic here.
        
        Args:
            *args: Variable arguments
            **kwargs: Keyword arguments
            
        Returns:
            Processing results
        """
        try:
            # Your agent logic here
            result = self._do_something()
            return {"ok": True, "result": result}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def get_info(self) -> Dict[str, Any]:
        """
        Return agent information.
        
        Returns:
            Dictionary with agent metadata
        """
        return {
            "name": "My Agent",
            "description": "What this agent does",
            "capabilities": [
                "Capability 1",
                "Capability 2",
            ],
        }
```

### 2. Register in `__init__.py`

Add your agent to `agents/__init__.py`:

```python
from .base_agent import BaseAgent
from .neo4j_agent import Neo4jAgent
from .visualization_agent import VisualizationAgent
from .my_agent import MyAgent  # Add this line

__all__ = ["BaseAgent", "Neo4jAgent", "VisualizationAgent", "MyAgent"]  # Add to list
```

### 3. Integrate in `app.py`

Import and initialize your agent in the session store:

```python
from agents import Neo4jAgent, VisualizationAgent, MyAgent

def get_session_store() -> Dict[str, Any]:
    # ... existing code ...
    if sid not in SESSIONS:
        SESSIONS[sid] = {
            "chat_history": [],
            "last_context_records": [],
            "neo4j_agent": Neo4jAgent(),
            "viz_agent": VisualizationAgent(),
            "my_agent": MyAgent(),  # Add your agent
        }
    return SESSIONS[sid]
```

### 4. Create Endpoint (Optional)

If your agent needs a dedicated endpoint:

```python
@app.route("/my-endpoint", methods=["POST"])
def my_endpoint():
    store = get_session_store()
    my_agent: MyAgent = store["my_agent"]
    
    payload = request.get_json(silent=True) or {}
    
    try:
        result = my_agent.process(**payload)
        return jsonify(result)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
```

## Best Practices

1. **Inheritance**: Always inherit from `BaseAgent` to maintain consistency
2. **Error Handling**: Wrap processing logic in try-except blocks
3. **Configuration**: Accept configuration via `__init__` with sensible defaults
4. **Documentation**: Document all methods with docstrings
5. **Type Hints**: Use type hints for better code clarity
6. **Stateless**: Keep agents stateless when possible; store state in session
7. **Info Method**: Implement `get_info()` to describe capabilities

## Example Usage

```python
from agents import Neo4jAgent, VisualizationAgent

# Initialize agents
neo4j_agent = Neo4jAgent()
viz_agent = VisualizationAgent()

# Process query
result = neo4j_agent.process("Find restaurants in New York")

# Generate visualization
html = viz_agent.process(
    records=result["context_records"],
    mode="scatter"
)

# Get agent info
print(neo4j_agent.get_info())
print(viz_agent.get_info())
```

## Testing

When adding a new agent, test it independently:

```python
# test_my_agent.py
from agents import MyAgent

def test_my_agent():
    agent = MyAgent()
    result = agent.process(test_input="sample")
    assert result["ok"] == True
    print(agent.get_info())

if __name__ == "__main__":
    test_my_agent()
```
