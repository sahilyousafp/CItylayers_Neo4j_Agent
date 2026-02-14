# Location Agent - City Layers

**Version 2.0.0** | *Last Updated: December 1, 2025*

The **Location Agent** is a modular AI-powered application for [City Layers](https://citylayers.eu). It enables users to query a Neo4j database using natural language, visualize data on interactive maps with advanced heatmap capabilities, and integrate various data sources like OpenStreetMap.

## ✨ What's New in v2.0

- 🎨 **Grade-Based Heatmap** with 1-100 scale visualization
- 📊 **Dynamic Legend** that adapts to your data
- 🏢 **3D Building Overlay** - visualizations render on top of buildings
- 🎯 **Enhanced Category Filtering** with dedicated UI controls
- 📈 **Smoother Gradients** with broader radius and optimized parameters

See [CHANGELOG.md](CHANGELOG.md) for complete version history.

## 🎯 Key Features

### Visualization Modes
- **Map View**: Interactive markers with click-to-query
- **Scatter Plot**: Color-coded by category
- **Heatmap**: Grade-based intensity (1-100 scale) ⭐ NEW
- **Arc Network**: High-grade location connections
- **Hexagon**: H3 hexagon-based regional analysis

### Data & Queries
- Natural language to Cypher query conversion
- Multi-category support (Beauty, Sound, Movement, Protection, Climate Comfort, Activities)
- Spatial filtering (polygon drawing, viewport bounds)
- Real-time visualization updates

### UI/UX
- Theme switching (Light/Dark mode)
- Panel resizing and collapse
- Place search with Mapbox Geocoding
- Chat interface for natural queries

## 📂 Project Structure

```
Location Agent/
├── agents/                    # Modular agent system
│   ├── neo4j_agent.py        # Neo4j queries & Cypher generation
│   ├── osm_agent.py          # OpenStreetMap integration
│   ├── web_scraper_agent.py  # Scraping & recommendations
│   └── meteostat_agent.py    # Weather data
├── static/
│   ├── css/styles.css        # Application styles
│   └── js/app.js             # Main client logic (2.0)
├── templates/
│   └── index.html            # Single-page application
├── tests/                    # Unit tests
├── app.py                    # Flask server
├── config.py                 # Configuration
├── requirements.txt          # Python dependencies
├── CHANGELOG.md              # Version history
├── HEATMAP_VISUALIZATION.md  # Heatmap guide
└── README.md                 # This file
```

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Neo4j Database (Cloud or Local)
- Google Gemini API Key ([Get one here](https://makersuite.google.com/app/apikey))
- Mapbox Access Token (for maps)

### 1. Installation

```bash
# Clone the repository
git clone <repository-url>
cd "Location Agent"

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

Create/update the `.env` file with your credentials:

```env
# Neo4j Database
NEO4J_URI=neo4j+s://your-instance.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-password

# Google Gemini AI
GOOGLE_API_KEY=your-google-api-key
GOOGLE_MODEL=gemini-2.0-flash-exp

# Flask
FLASK_SECRET_KEY=your-secret-key-for-sessions

# Mapbox
MAPBOX_ACCESS_TOKEN=your-mapbox-token
```

### 3. Run the Application

```bash
python app.py
```

Access at `http://localhost:5000`

## 🤖 Agent Architecture

### Neo4jAgent (`agents/neo4j_agent.py`)
Converts natural language to Cypher queries for the City Layers Neo4j database.

**Features:**
- Natural language to Cypher translation
- Spatial query support (regions, coordinates)
- Category filtering (Beauty, Sound, Movement, Protection, Climate Comfort, Activities)
- Context-aware responses

**Usage:**
```python
from agents import Neo4jAgent
from config import Config

agent = Neo4jAgent(Config.AGENTS["neo4j"])
result = agent.process(
    query="Show me beautiful places in Vienna",
    category_filter="1"  # Beauty category
)
```

### OSMAgent (`agents/osm_agent.py`)
Fetches OpenStreetMap data for contextual information.

**Features:**
- Query by bounding box, radius, or location name
- Fetch amenities, buildings, roads
- City boundary extraction

### WebScraperAgent (`agents/web_scraper_agent.py`)
Scrapes websites and recommends visualizations.

**Features:**
- Location extraction from text
- Visualization recommendations (Scatter, Heatmap, Hexagon)

## 🎯 Common Issues & Solutions

### Issue: LLM not querying properly

**Symptoms:**
- Getting aggregated counts instead of individual places
- Missing location data on map
- Incomplete query results

**Solutions:**
1. **Check Prompt Templates**: The Cypher generation template should explicitly forbid COUNT/GROUP BY
2. **Verify Model**: Ensure using correct Gemini model (gemini-2.0-flash-exp recommended)
3. **Check Logs**: Look for generated Cypher queries in console output
4. **Test Query**: Use Neo4j Browser to verify Cypher works correctly

### Issue: Module not found errors

```bash
pip install --upgrade -r requirements.txt
```

### Issue: No data on map

**Check:**
1. Database connection (Neo4j credentials in `.env`)
2. API key validity (Google Gemini)
3. Console logs for Cypher execution errors
4. Database contains places with lat/lon coordinates

## 🔧 Development

### Adding a New Data Source

1. **Create Agent File** (`agents/my_agent.py`):
```python
from .base_agent import BaseAgent

class MyAgent(BaseAgent):
    def process(self, query, **kwargs):
        # Your logic here
        return {"ok": True, "data": []}
    
    def get_info(self):
        return {"name": "My Agent"}
```

2. **Register Agent** (`agents/__init__.py`):
```python
from .my_agent import MyAgent
__all__ = [..., "MyAgent"]
```

3. **Initialize in App** (`app.py`):
```python
SESSIONS[sid] = {
    # ...
    "my_agent": MyAgent(),
}
```

### Running Tests

```bash
python -m pytest tests/
```

## 📊 Database Schema

The Neo4j database uses this structure:
- **Place** nodes: location, latitude, longitude, category, grade
- **Category** nodes: category_id (1-6), type, description
- **Place_Grade** nodes: connect places to categories
- **Comment** nodes: user comments about places
- **Relationships**: 
  - `(Place)-[:HAS_GRADE]->(Place_Grade)-[:BELONGS_TO]->(Category)`
  - `(Place)-[:HAS_COMMENT]->(Comment)`

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

[Add your license here]

## 🆘 Support

For issues or questions:
- Check existing issues on GitHub
- Create a new issue with detailed description
- Include logs and error messages
