# Location Agent - City Layers 🗺️

**Version 2.0.0** | *Last Updated: February 14, 2026*

The **Location Agent** is a modular AI-powered application for [City Layers](https://citylayers.eu). It enables users to query a Neo4j database using natural language, visualize data on interactive maps with advanced heatmap capabilities, and integrate various data sources like OpenStreetMap.

> 🔐 **Security-First Design**: All API keys and credentials are managed through environment variables with comprehensive security features.

## ✨ What's New in v2.0

- 🎨 **Grade-Based Heatmap** with 1-100 scale visualization
- 📊 **Dynamic Legend** that adapts to your data
- 🏢 **3D Building Overlay** - visualizations render on top of buildings
- 🎯 **Enhanced Category Filtering** with dedicated UI controls
- 📈 **Smoother Gradients** with broader radius and optimized parameters

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
- **Suggested filter questions** for quick data exploration
- **Client-side filtering** for instant follow-up queries

### Advanced Query Features
- **Nested/Follow-up Questions**: Ask progressive filtering questions without re-querying the database
- **Smart Filter Detection**: Automatically detects grade-based, top-N, and comparison queries
- **One-Click Suggestions**: Get 4 contextual filter buttons after each query
- **Progressive Filtering**: Stack multiple filters on existing results
- **Auto-Reset**: Smart detection of when to reset filters (zoom changes, category switches)

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
- LLM Provider: Ollama (local) or Google Gemini API
- Mapbox Access Token (for maps)

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/sahilyousafp/CItylayers_Neo4j_Agent.git
cd "Location Agent"

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

#### 🔐 Security Setup

**Copy the example environment file:**
```bash
cp .env.example .env
```

**Fill in your actual credentials in `.env`:**
```env
# Neo4j Database
NEO4J_URI=neo4j+s://your-instance.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-password

# LLM Provider (ollama or google)
LLM_PROVIDER=ollama

# Ollama (for local LLM)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1

# Google Gemini AI (if using Google)
GOOGLE_API_KEY=your-google-api-key
GOOGLE_MODEL=gemini-2.0-flash-exp

# Flask
FLASK_SECRET_KEY=your-secret-key-for-sessions

# Mapbox
MAPBOX_ACCESS_TOKEN=your-mapbox-token
```

**Generate secure keys:**
```python
# For FLASK_SECRET_KEY
import secrets
print(secrets.token_hex(32))
```

**⚠️ IMPORTANT SECURITY NOTES:**
- ✅ `.env` file is in `.gitignore` - NEVER commit it
- ✅ All credentials are validated on startup
- ✅ No default credentials in source code
- ✅ Use `.env.example` as a template only

### 3. Run the Application

```bash
python app.py
```

Access at `http://localhost:5000`

## 💡 Usage Examples

### Basic Queries
```
"Show me beautiful places in Vienna"
"Find movement spots near Stephansplatz"
"What are the most active locations?"
```

### Follow-up Filtering
After any query, use suggested filter questions or type:
```
"Which ones are highly rated?"    → Filters to grade ≥ 70
"Show me the top 5"               → Top 5 by grade
"Above 80"                        → Grade > 80
"The best ones"                   → Grade ≥ 80
```

### Progressive Filtering Example
```
1. "Show me movement points in Vienna"  → 100 points displayed
2. "Above 80"                           → 30 points (filtered)
3. "Top 10"                             → 10 points (further filtered)
4. Zoom out significantly               → Auto-resets to 100 points
```

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

## 🔐 Security Features

### Credential Management
All sensitive credentials are stored in environment variables and loaded via `.env` file.

**Protected Files:**
- `.env` - Contains all API keys and credentials (NEVER commit)
- `.env.local` - Local overrides
- `.env.*.local` - Environment-specific overrides

### Security Checklist
- ✅ `.env` file is in `.gitignore`
- ✅ No hardcoded credentials in source code
- ✅ `.env.example` provided as template
- ✅ Config validation ensures required credentials are present
- ✅ All API keys loaded from environment variables

### Best Practices
1. **Rotate credentials regularly** - Update API keys and passwords periodically
2. **Use different credentials per environment** - Dev, staging, and production should be separate
3. **Limit API key permissions** - Use least-privilege principle
4. **Monitor API usage** - Watch for unusual activity
5. **Never share `.env` files** - Use secure channels for credential sharing

### Emergency Response
If credentials are accidentally committed:
1. **Immediately rotate all exposed credentials**
2. **Remove from git history** using `git filter-branch` or BFG Repo-Cleaner
3. **Force push cleaned history** (coordinate with team)
4. **Audit logs** for unauthorized access

## 📝 Changelog

### Version 2.0.0 - 2026-02-14

#### Security Enhancements ✨
- 🔐 Removed all hardcoded credentials from `config.py`
- ✅ Added mandatory validation for critical environment variables
- 📝 Created `.env.example` template
- 🛡️ Enhanced `.gitignore` to prevent accidental credential commits
- 📄 Added `.gitattributes` for security and consistency
- 📚 Comprehensive security documentation

#### Major Features
- **Grade-based heatmap** with 1-100 scale display
- **Dynamic legend** that adapts to actual data range
- **Nested/Follow-up Questions** - Progressive filtering without re-querying
- **Client-side filtering** - Instant results for follow-up queries
- **Suggested filter questions** - 4 contextual buttons after each query
- **Smart auto-reset** - Detects zoom changes and category switches

#### Visualization Improvements
- **Overlay on 3D buildings** - All visualizations render above buildings
- **Category-based filtering** with dedicated filter button
- **Multiple viz modes**: Scatter, Heatmap, Arc Network, Hexagon
- **Theme switching**: Light/Dark mode support
- **Enhanced filter responses** with statistics and top locations table

#### Technical Changes
- Added comprehensive JSDoc documentation
- Organized code into logical sections
- Improved function naming and comments
- Added proper error handling
- Performance optimizations for heatmap updates

#### Bug Fixes
- Fixed markers not appearing after initial data load
- Resolved visualization layer ordering issues
- Corrected grade scale conversion (10x multiplier)
- Fixed legend not updating with category changes

### Version 1.x - Previous
- Core Mapbox GL JS integration
- deck.gl visualization layers
- Neo4j database integration
- Chat-based location querying
- Region selection with polygon drawing
- Category filtering system

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
- Check existing issues on [GitHub](https://github.com/sahilyousafp/CItylayers_Neo4j_Agent/issues)
- Create a new issue with detailed description
- Include logs and error messages

## 📚 Additional Documentation

For more detailed information on specific features, see:
- **Security**: See security section above for credential management
- **Agent Documentation**: `agents/LLM_DOCUMENTATION.md` for LLM integration details
- **Testing**: `tests/phase1_phase2/` for test cases and results

## 🎯 Credits

- **Mapbox GL JS**: Map rendering
- **deck.gl**: WebGL-powered visualizations
- **H3**: Hexagonal spatial indexing
- **Neo4j**: Graph database backend
- **Marked.js**: Markdown rendering
- **Google Gemini / Ollama**: LLM providers

## 📄 License

[Add your license information here]

---

**Repository**: [CItylayers_Neo4j_Agent](https://github.com/sahilyousafp/CItylayers_Neo4j_Agent)  
**Maintained by**: City Layers Team  
**Last Updated**: February 14, 2026
