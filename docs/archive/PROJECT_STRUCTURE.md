# Project Structure - Location Agent

## ✅ Core Application Files

### Main Application
- `app.py` - Flask web application (main entry point)
- `config.py` - Centralized configuration management
- `.env` - Environment variables (API keys, credentials)
- `requirements.txt` - Python dependencies

### Documentation
- `README.md` - Project overview and setup instructions
- `TROUBLESHOOTING.md` - Common issues and solutions
- `setup.py` - Automated setup script

## ✅ Agents Module (`agents/`)

Modular AI agent system for different data sources:

- `base_agent.py` - Abstract base class for all agents
- `neo4j_agent.py` - **PRIMARY AGENT** - Natural language to Neo4j Cypher
- `osm_agent.py` - OpenStreetMap data integration
- `web_scraper_agent.py` - Web scraping and visualization recommendations
- `meteostat_agent.py` - Weather data integration
- `__init__.py` - Agent registration and exports

### Key Features of Neo4jAgent
- Converts natural language to Cypher queries
- Supports spatial queries (regions, coordinates)
- Category filtering (6 main categories)
- Returns individual place nodes with lat/lon for mapping
- Context-aware query enhancement

## ✅ Frontend (`static/` & `templates/`)

- `static/` - CSS, JavaScript, images
- `templates/` - HTML templates (Jinja2)

## ✅ Tests (`tests/`)

Unit tests for agent functionality

## 🗑️ Files to Remove

These files should be deleted as they are not needed:

1. **`debug_columns.txt`** - Debug output file
2. **`chattomap/`** - Old virtual environment (entire directory)
3. **`neo4j_agent_backup.py`** - Backup file (if exists)
4. **`chat_to_map.ipynb`** - Jupyter notebook (if exists)

### Cleanup Commands

**Windows:**
```cmd
del debug_columns.txt
rmdir /s /q chattomap
```

**Linux/Mac:**
```bash
rm debug_columns.txt
rm -rf chattomap
```

## 📦 Dependencies Summary

### Core Framework
- Flask 3.0.3 - Web framework
- python-dotenv 1.0.0 - Environment variable management

### LangChain & AI
- langchain 0.3.0
- langchain-google-genai 2.0.0
- langchain-neo4j 0.2.0
- langchain-core 0.3.0
- langchain-community 0.3.0
- google-generativeai 0.8.0

### Database
- neo4j 5.19.0 - Neo4j Python driver

### Data Processing
- pandas 2.2.2 - Data manipulation
- pydantic 2.7.1 - Data validation

### Geospatial
- geopandas 0.14.4
- shapely 2.0.4
- fiona 1.9.6
- pyproj 3.6.1

### Visualization
- pydeck 0.9.1 - Map visualization
- matplotlib 3.8.4

### Web Scraping
- requests 2.31.0
- beautifulsoup4 4.12.3
- lxml 5.1.0

### Other
- meteostat 1.6.7 - Weather data
- markdown2 2.4.10 - Markdown rendering

## 🔧 Configuration Files

### `.env` (Environment Variables)
```env
NEO4J_URI=neo4j+s://...
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=...
GOOGLE_API_KEY=...
GOOGLE_MODEL=gemini-2.0-flash-exp
FLASK_SECRET_KEY=...
MAPBOX_ACCESS_TOKEN=...
```

### `.gitignore`
Configured to exclude:
- Python cache (`__pycache__/`, `*.pyc`)
- Virtual environments (`venv/`, `env/`)
- Environment variables (`.env`)
- IDE files (`.vscode/`, `.idea/`)
- Debug files (`debug_columns.txt`)
- Notebooks (`*.ipynb`)
- Backup files (`*_backup.py`)

## 🎯 Main Entry Points

### Running the Application
```bash
python app.py
```
- Starts Flask server on port 5000
- Access at `http://localhost:5000`

### Setup Script
```bash
python setup.py
```
- Checks Python version
- Creates .env template
- Installs dependencies
- Verifies installation

## 🔄 Data Flow

1. **User Query** → Frontend (templates/index.html)
2. **Frontend** → POST /chat → app.py
3. **app.py** → Neo4jAgent.process()
4. **Neo4jAgent** → Google Gemini (Cypher generation)
5. **Neo4jAgent** → Neo4j Database (query execution)
6. **app.py** → Response (JSON with answer + context_records)
7. **Frontend** → GET /map-data
8. **app.py** → Processes context_records → Returns GeoJSON
9. **Frontend** → Renders map with markers

## 📊 Database Schema

### Nodes
- **Place**: location, latitude, longitude, place_id, grade, comments
- **Category**: category_id (1-6), type, description
- **Place_Grade**: grade value, links places to categories
- **Comment**: comment text, timestamps
- **Image**: image URLs

### Relationships
- `(Place)-[:HAS_GRADE]->(Place_Grade)-[:BELONGS_TO]->(Category)`
- `(Place)-[:HAS_COMMENT]->(Comment)`
- `(Place)-[:HAS_IMAGE]->(Image)`

### Categories
1. Beauty
2. Sound
3. Movement
4. Protection
5. Climate Comfort
6. Activities

## 🚀 Quick Start Checklist

- [ ] Clone repository
- [ ] Create virtual environment: `python -m venv venv`
- [ ] Activate virtual environment
- [ ] Run setup: `python setup.py`
- [ ] Configure .env with your credentials
- [ ] Run application: `python app.py`
- [ ] Access http://localhost:5000
- [ ] Test query: "Show me beautiful places in Vienna"

## ⚠️ Known Issues & Fixes

### Issue: LLM Returns Counts Instead of Places
**Status:** ✅ FIXED
- Updated `CYPHER_GENERATION_TEMPLATE` to explicitly forbid COUNT/GROUP BY
- Simplified prompt for better clarity
- Added examples of correct query patterns

### Issue: Missing langchain_neo4j Module
**Status:** ✅ FIXED
- Updated requirements.txt with correct package versions
- Added langchain-neo4j 0.2.0

### Issue: Outdated Dependencies
**Status:** ✅ FIXED
- Updated to latest compatible versions
- Added python-dotenv for .env support
- Added markdown2 for markdown rendering

## 🔐 Security Notes

- Never commit `.env` file to version control
- Keep API keys and passwords secure
- Use strong `FLASK_SECRET_KEY` in production
- Validate and sanitize all user inputs
- Use read-only database credentials if possible

## 📈 Next Steps / Improvements

1. Add unit tests for all agents
2. Implement caching for frequent queries
3. Add rate limiting for API calls
4. Implement user authentication
5. Add query history/favorites
6. Optimize map rendering for large datasets
7. Add export functionality (CSV, JSON)
8. Implement advanced filtering UI
9. Add analytics/usage tracking
10. Create deployment documentation

## 🆘 Support

If you encounter issues:
1. Check `TROUBLESHOOTING.md`
2. Review console logs (browser & server)
3. Test components individually
4. Check GitHub issues
5. Create new issue with details
