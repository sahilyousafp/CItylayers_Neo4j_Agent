# Troubleshooting Guide

## Common Issues and Solutions

### 1. LLM Not Querying Properly

**Symptoms:**
- Getting aggregated counts instead of individual places
- Places not showing on map
- Query returns summary instead of location data
- Missing latitude/longitude data

**Root Causes:**
- LLM generating COUNT/GROUP BY queries instead of returning individual places
- Prompt template not clearly instructing to return place nodes
- Model not following instructions

**Solutions:**

1. **Check Generated Cypher Queries:**
   - Look at console output when running the app
   - Find lines starting with "⚡ GENERATED CYPHER:"
   - Verify query returns `p` (place nodes) not `count(p)`

2. **Verify Prompt Template:**
   - Open `agents/neo4j_agent.py`
   - Check `CYPHER_GENERATION_TEMPLATE`
   - Should contain: "NEVER use COUNT, GROUP BY, COLLECT"
   - Should contain: "Always return individual place nodes (p)"

3. **Test with Simple Query:**
   ```python
   # In Python console:
   from agents import Neo4jAgent
   from config import Config
   
   agent = Neo4jAgent(Config.AGENTS["neo4j"])
   result = agent.process("Show me 5 places in Vienna")
   print(f"Records: {len(result['context_records'])}")
   ```

4. **Update Model:**
   - In `.env`, try: `GOOGLE_MODEL=gemini-2.0-flash-exp`
   - Or use a fine-tuned model if available

5. **Manual Cypher Test:**
   ```cypher
   MATCH (p:Place)
   OPTIONAL MATCH (p)-[:HAS_GRADE]->(pg:Place_Grade)-[:BELONGS_TO]->(c:Category)
   WHERE p.location CONTAINS 'Vienna'
   RETURN p, c, pg
   LIMIT 10
   ```
   Run this in Neo4j Browser to verify data structure.

---

### 2. Module Not Found Errors

**Symptoms:**
```
ModuleNotFoundError: No module named 'langchain_neo4j'
```

**Solutions:**

1. **Install/Update Dependencies:**
   ```bash
   pip install --upgrade -r requirements.txt
   ```

2. **Check Virtual Environment:**
   ```bash
   # Make sure you're in virtual environment
   which python  # Linux/Mac
   where python  # Windows
   
   # Should point to venv/bin/python or venv\Scripts\python.exe
   ```

3. **Reinstall Specific Package:**
   ```bash
   pip install --force-reinstall langchain-neo4j
   ```

---

### 3. Database Connection Errors

**Symptoms:**
```
Failed to establish connection to Neo4j
ServiceUnavailable: Failed to establish connection
```

**Solutions:**

1. **Check Credentials in .env:**
   ```env
   NEO4J_URI=neo4j+s://your-instance.databases.neo4j.io
   NEO4J_USERNAME=neo4j
   NEO4J_PASSWORD=your-actual-password
   ```

2. **Test Connection:**
   ```python
   from neo4j import GraphDatabase
   
   driver = GraphDatabase.driver(
       "neo4j+s://your-uri",
       auth=("neo4j", "your-password")
   )
   driver.verify_connectivity()
   print("Connection OK!")
   ```

3. **Check Network:**
   - Firewall might block Neo4j port (7687)
   - Try from Neo4j Browser first

---

### 4. Google API Errors

**Symptoms:**
```
google.api_core.exceptions.Unauthorized: 401
InvalidArgument: API key not valid
```

**Solutions:**

1. **Verify API Key:**
   - Get from: https://makersuite.google.com/app/apikey
   - Copy entire key (starts with "AIza...")
   - Update in `.env`: `GOOGLE_API_KEY=AIza...`

2. **Check API Enabled:**
   - Go to Google Cloud Console
   - Enable "Generative Language API"

3. **Test API Key:**
   ```python
   import google.generativeai as genai
   genai.configure(api_key="your-key")
   model = genai.GenerativeModel('gemini-2.0-flash-exp')
   response = model.generate_content("Hello")
   print(response.text)
   ```

---

### 5. No Data Showing on Map

**Symptoms:**
- Map loads but no pins/markers
- Query executes but map is empty

**Solutions:**

1. **Check Browser Console:**
   - Open DevTools (F12)
   - Look for JavaScript errors
   - Check Network tab for failed requests

2. **Check /map-data Endpoint:**
   ```bash
   # In browser or curl:
   curl http://localhost:5000/map-data
   ```
   Should return JSON with `features` array.

3. **Verify Database Has Coordinates:**
   ```cypher
   MATCH (p:Place)
   WHERE p.latitude IS NOT NULL AND p.longitude IS NOT NULL
   RETURN count(p)
   ```

4. **Check Data Format:**
   - Open `app.py`, find `map_data()` function
   - Add debug prints to see what's being returned
   - Verify `features` list is populated

---

### 6. Flask/App Won't Start

**Symptoms:**
```
Address already in use
Port 5000 is already allocated
```

**Solutions:**

1. **Kill Existing Process:**
   ```bash
   # Linux/Mac:
   lsof -i :5000
   kill -9 <PID>
   
   # Windows:
   netstat -ano | findstr :5000
   taskkill /PID <PID> /F
   ```

2. **Use Different Port:**
   ```bash
   # In app.py, change:
   app.run(host="0.0.0.0", port=5001)
   
   # Or set environment variable:
   export PORT=5001  # Linux/Mac
   set PORT=5001     # Windows
   ```

---

### 7. Import Errors with Agents

**Symptoms:**
```
ImportError: cannot import name 'Neo4jAgent'
```

**Solutions:**

1. **Check __init__.py:**
   - Open `agents/__init__.py`
   - Verify imports are correct:
   ```python
   from .neo4j_agent import Neo4jAgent
   from .osm_agent import OSMAgent
   from .web_scraper_agent import WebScraperAgent
   ```

2. **Clear Python Cache:**
   ```bash
   find . -type d -name __pycache__ -exec rm -r {} +
   find . -type f -name "*.pyc" -delete
   ```

3. **Restart Python:**
   - Exit and restart Python interpreter
   - Or restart IDE/editor

---

### 8. Cypher Generation Issues

**Symptoms:**
- LLM generates invalid Cypher
- Cypher syntax errors
- Query returns no results

**Solutions:**

1. **Check Cypher Template:**
   - Verify schema in template matches actual database
   - Ensure relationship patterns are correct

2. **Add More Examples:**
   - Edit `CYPHER_GENERATION_TEMPLATE` in `neo4j_agent.py`
   - Add concrete query examples

3. **Use Fine-Tuned Model:**
   - Train model on your specific Cypher patterns
   - Update `GOOGLE_MODEL` in `.env`

4. **Enable Validation:**
   - Check `_validate_cypher_query()` in `neo4j_agent.py`
   - Add more forbidden patterns if needed

---

## Debug Mode

Enable detailed logging:

```python
# In app.py, set:
app.run(debug=True)

# Or in terminal:
export FLASK_DEBUG=1
python app.py
```

## Getting Help

If issues persist:

1. Check logs carefully - error messages usually indicate the problem
2. Test each component individually (database, API, LLM)
3. Use the setup script: `python setup.py`
4. Create an issue on GitHub with:
   - Error message
   - Steps to reproduce
   - Environment details (Python version, OS, etc.)
