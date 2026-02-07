# LLM System Documentation

## Overview

The **Location Agent** uses Large Language Models (LLMs) to convert natural language queries into structured database queries (Cypher) and generate user-friendly responses. The system supports multiple LLM providers and handles complex multi-dataset analysis.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    User Query (Natural Language)            │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              Chat History & Context Enhancement             │
│  - Previous Q&A pairs                                       │
│  - Map bounds (North/South/East/West)                       │
│  - Category filter                                          │
│  - External datasets (Weather, Transport, Vegetation)       │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    LLM PHASE 1: Query Generation            │
│  Input: Enhanced query + Schema + Context                   │
│  Output: Cypher query for Neo4j database                    │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              Cypher Validation & Execution                  │
│  - Safety checks (no DELETE/DROP/CREATE)                    │
│  - Pattern validation                                       │
│  - Execute on Neo4j database                                │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              Context Aggregation & Formatting               │
│  - Prepare database results                                 │
│  - Aggregate external datasets                              │
│  - Format for LLM consumption                               │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    LLM PHASE 2: Answer Generation           │
│  Input: Original question + Formatted context               │
│  Output: User-friendly markdown response                    │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              Frontend Display (Markdown Rendered)           │
│  - Formatted headings, tables, lists                        │
│  - Statistics and highlights                                │
│  - Interactive visualization triggers                       │
└─────────────────────────────────────────────────────────────┘
```

---

## Supported LLM Providers

### 1. **Google Gemini** (Recommended)
- **Provider**: Google Generative AI
- **Framework**: `langchain_google_genai.ChatGoogleGenerativeAI`
- **Default Model**: `gemini-flash-latest`
- **Recommended Model**: `gemini-2.0-flash-exp`
- **Configuration**:
  - Environment variable: `LLM_PROVIDER=google`
  - Model selection: `GOOGLE_MODEL=gemini-2.0-flash-exp`
  - API key: `GOOGLE_API_KEY=your_key_here`

**Advantages**:
- ✅ Fast response times (flash variant)
- ✅ Strong reasoning capabilities
- ✅ Excellent Cypher query generation
- ✅ Reliable structured output handling
- ✅ Supports system message conversion

### 2. **Ollama** (Local/Self-Hosted)
- **Provider**: Ollama
- **Framework**: `langchain_ollama.ChatOllama`
- **Default Model**: `llama3.1`
- **Configuration**:
  - Environment variable: `LLM_PROVIDER=ollama`
  - Base URL: `OLLAMA_BASE_URL=http://localhost:11434`
  - Model selection: `OLLAMA_MODEL=llama3.1`

**Advantages**:
- ✅ Privacy (runs locally)
- ✅ No API costs
- ✅ Customizable models
- ⚠️ Requires local setup and resources

---

## Model Parameters

### Temperature
- **Value**: `0` (deterministic)
- **Purpose**: Ensures consistent, predictable outputs
- **Use case**: Critical for Cypher query generation where syntax precision is required

### Context Limitations
- **CityLayers records**: Limited to 50 records for LLM context (full dataset stored separately)
- **Weather data**: Summarized with avg/min/max aggregation
- **Transport data**: Limited to 30 stations with type aggregation
- **Vegetation data**: Top species summarized
- **Chat history**: Last 2 Q&A pairs included for continuity

---

## System Prompt Breakdown

The system uses **two specialized prompts**:

### Phase 1: Cypher Query Generation (`CYPHER_GENERATION_TEMPLATE`)

**Purpose**: Convert natural language → Cypher query

**Key Instructions**:
1. **Schema Awareness**
   - Use ONLY provided relationships and properties
   - Follow graph structure: `(Place)-[:HAS_GRADE]->(Place_Grade)-[:BELONGS_TO]->(Category)`

2. **Query Patterns**
   ```cypher
   MATCH (p:places)
   OPTIONAL MATCH (p)<-[:ASSOCIATED_WITH]-(pg:place_grades)-[:OF_CATEGORY]->(c:categories)
   OPTIONAL MATCH (co:comments)-[:ABOUT]->(p)
   WHERE p.latitude >= south AND p.latitude <= north 
     AND p.longitude >= west AND p.longitude <= east
   RETURN DISTINCT p, c, pg, co
   ```

3. **Critical Rules**
   - ✅ ALWAYS return individual place nodes
   - ❌ NEVER use COUNT, GROUP BY, COLLECT, or aggregations
   - ✅ Each row = ONE place with location data
   - ✅ Use DISTINCT to avoid duplicates
   - ✅ Include: `p, c, pg, co` (place, category, grade, comment)

4. **Intent Detection**
   - **Single place**: "tell me about X" → Use `LIMIT 1`
   - **Multiple places**: "places in X" → No LIMIT
   - **Exact coordinates**: Match exact lat/lon → `LIMIT 1`
   - **Region/bounds**: Match range → No LIMIT

5. **Category Filtering**
   ```cypher
   -- CORRECT: Use MATCH for category filter (not OPTIONAL)
   MATCH (p:places)<-[:ASSOCIATED_WITH]-(pg:place_grades)-[:OF_CATEGORY]->(c:categories)
   WHERE c.category_id = X
   OPTIONAL MATCH (co:comments)-[:ABOUT]->(p)
   RETURN DISTINCT p, c, pg, co
   
   -- WRONG: OPTIONAL MATCH with WHERE on category returns nulls
   ```

6. **Location Matching**
   - Named location: `WHERE toLower(p.location) CONTAINS toLower('Vienna')`
   - Exact point: `WHERE p.latitude = X AND p.longitude = Y`
   - Nearby: `WHERE abs(p.latitude - X) < 0.0001 AND abs(p.longitude - Y) < 0.0001`

7. **Safety Validation**
   - ❌ Blocked operations: DELETE, DETACH, CREATE, SET, REMOVE, MERGE
   - ✅ Allowed operations: MATCH, OPTIONAL MATCH, WHERE, RETURN

---

### Phase 2: Answer Generation (`QA_TEMPLATE`)

**Purpose**: Convert database results → User-friendly response

**Response Guidelines**:

#### For Region/Area Queries
Format:
```markdown
### 📍 [Location/Region Name]

One-sentence summary of the area in plain language

| Metric | Value |
|--------|-------|
| **Total Locations** | XXX |
| **Most Common** | Category name (XXX locations, YY%) |
| **Average Rating** | X.X out of 10 ⭐ |
| **Highest Rated** | Location name (X.X/10) |

**Key Highlights:**
- Highlight 1 with interesting finding
- Highlight 2 with contextual insight
- Highlight 3 with meaningful pattern
- Highlight 4 if relevant

**Top 5 Relevant Comments from this Region:**
- "Comment text" - *Location Name*
- "Comment text" - *Location Name*
...

(Keep under 250 words total)
```

#### For Specific Location Queries
Format:
```markdown
### 📍 [Location Name]

**Category**: Category name
**Rating**: X.X out of 10 ⭐
**Location**: Address/coordinates

**Description**: Brief description of the place

**User Comments:**
- "Comment text"
- "Comment text"

(Keep under 200 words)
```

#### For Multi-Dataset Queries
When external datasets are available (Weather, Transport, Vegetation):
```markdown
### 📊 Analysis: [Query Topic]

**Dataset Integration:**
- **CityLayers**: X locations found
- **Weather**: Avg temp, wind conditions
- **Transport**: Y stations nearby
- **Vegetation**: Z trees analyzed

**Key Insights:**
- Insight connecting datasets
- Pattern or correlation found
- Recommendation based on combined data

(Smart dataset selection based on query relevance)
```

**Formatting Rules**:
- ✅ Use markdown (headings, bold, tables, lists)
- ✅ Use emojis strategically (📍, ⭐, 📊, 🌡️, 🚇, 🌳)
- ✅ Bold important numbers and categories
- ✅ Keep concise (200-250 words)
- ❌ No raw data dumps
- ❌ No technical database terminology
- ❌ No "based on the database results" phrases
- ❌ No sorting comments by rating (show contextually relevant ones)

---

## Technical Implementation

### Initialization (`_init_llm()`)
```python
def _init_llm(self):
    llm_provider = self.config.get("llm_provider", "ollama")
    
    if llm_provider == "ollama":
        model_name = self.config.get("ollama_model", "llama3.1")
        base_url = self.config.get("ollama_base_url", "http://localhost:11434")
        return ChatOllama(
            model=model_name,
            base_url=base_url,
            temperature=0,
        )
    else:  # google
        model_name = self.config.get("google_model", "gemini-flash-latest")
        return ChatGoogleGenerativeAI(
            model=model_name,
            temperature=0,
            convert_system_message_to_human=True,
        )
```

### Query Processing Flow (`process()`)
```python
def process(query, chat_history, map_context, category_filter):
    # 1. Enhance query with chat history
    enhanced_query = _enhance_query_with_history(query, chat_history)
    
    # 2. Prepare map bounds info
    map_bounds_info = _get_map_bounds_prompt(map_context, category_filter)
    
    # 3. Generate Cypher query (LLM Phase 1)
    llm_response = self.llm.invoke(formatted_prompt)
    generated_cypher = llm_response.content
    
    # 4. Handle structured response formats
    if isinstance(generated_cypher, dict):
        generated_cypher = generated_cypher.get('text', str(generated_cypher))
    if isinstance(generated_cypher, list):
        generated_cypher = " ".join(item.get('text', str(item)) for item in generated_cypher)
    
    # 5. Clean Cypher (remove markdown blocks)
    generated_cypher = re.sub(r'```cypher', '', generated_cypher, flags=re.IGNORECASE)
    generated_cypher = re.sub(r'```', '', generated_cypher).strip()
    
    # 6. Validate Cypher safety
    _validate_cypher_query(generated_cypher)
    
    # 7. Execute query on Neo4j
    context_records = self.graph.query(generated_cypher)
    
    # 8. Prepare context summary
    context_summary = _prepare_context_summary(context_records, category_filter)
    
    # 9. Generate answer (LLM Phase 2)
    answer_response = self.llm.invoke(formatted_qa_prompt)
    answer = answer_response.content
    
    # 10. Return results
    return {
        "answer": answer,
        "context_records": context_records,
        "intermediate_steps": [generated_cypher]
    }
```

### Multi-Dataset Integration (`process_with_aggregated_context()`)
```python
def process_with_aggregated_context(query, chat_history, aggregated_context):
    # Combines multiple data sources
    context_parts = []
    
    # 1. CityLayers data
    if aggregated_context.get("citylayers"):
        context_parts.append(_format_citylayers_context(...))
    
    # 2. Weather data
    if aggregated_context.get("weather"):
        weather_summary = {
            "avg_temp": mean(temps),
            "min_temp": min(temps),
            "max_temp": max(temps)
        }
        context_parts.append(_format_weather_context(weather_summary))
    
    # 3. Transport data
    if aggregated_context.get("transport"):
        transport_summary = {
            "total_stations": len(stations),
            "by_type": group_by_type(stations)
        }
        context_parts.append(_format_transport_context(transport_summary))
    
    # 4. Vegetation data
    if aggregated_context.get("vegetation"):
        veg_summary = {
            "total_trees": len(trees),
            "top_species": get_top_species(trees)
        }
        context_parts.append(_format_vegetation_context(veg_summary))
    
    # Combine and send to LLM
    combined_context = "\n\n".join(context_parts)
    llm_response = self.llm.invoke(qa_prompt.format(
        question=query,
        context=combined_context
    ))
    return llm_response.content
```

---

## Response Format Handling

The system handles multiple response formats from different LLM providers:

### 1. String Response (Simple)
```python
llm_response.content = "MATCH (p:places) RETURN p"
```

### 2. Dictionary Response
```python
llm_response.content = {"type": "text", "text": "MATCH (p:places) RETURN p"}
# Extraction: content.get('text')
```

### 3. List Response
```python
llm_response.content = [
    {"type": "text", "text": "MATCH (p:places)"},
    {"type": "text", "text": "RETURN p"}
]
# Extraction: " ".join(item.get('text') for item in content)
```

### 4. JSON String Response
```python
llm_response.content = '{"text": "MATCH (p:places) RETURN p"}'
# Extraction: json.loads(content).get('text')
```

**Robust Extraction Logic**:
```python
# Handle dict
if isinstance(content, dict):
    content = content.get('text', str(content))

# Handle list
if isinstance(content, list):
    if content and isinstance(content[0], dict) and 'text' in content[0]:
        content = " ".join(item.get('text', str(item)) for item in content)
    else:
        content = " ".join(str(item) for item in content)

# Handle JSON string
if content.startswith('{') and '"text"' in content:
    try:
        parsed = json.loads(content)
        content = parsed.get('text', content)
    except json.JSONDecodeError:
        pass

# Clean markdown blocks
content = re.sub(r'```cypher', '', content, flags=re.IGNORECASE)
content = re.sub(r'```', '', content).strip()
```

---

## Capabilities

### 1. Natural Language Query Understanding
- ✅ Convert questions to precise Cypher queries
- ✅ Detect query intent (single place vs. multiple places)
- ✅ Handle location names, coordinates, and regions
- ✅ Understand category filters and context

### 2. Context-Aware Responses
- ✅ Maintain chat history (last 2 Q&A pairs)
- ✅ Consider map bounds for geographic filtering
- ✅ Apply category filters dynamically
- ✅ Integrate external datasets intelligently

### 3. Multi-Dataset Analysis
- ✅ CityLayers (places, ratings, comments)
- ✅ Weather (temperature, wind, conditions)
- ✅ Transport (stations, routes, accessibility)
- ✅ Vegetation (trees, species, green coverage)

### 4. Smart Data Aggregation
- ✅ Summarizes large datasets for LLM efficiency
- ✅ Preserves full data for visualization
- ✅ Provides statistical summaries
- ✅ Highlights top/relevant items

### 5. Safety & Validation
- ✅ Blocks destructive database operations
- ✅ Validates Cypher query patterns
- ✅ Prevents SQL injection-like attacks
- ✅ Enforces read-only access

### 6. User-Friendly Output
- ✅ Markdown-formatted responses
- ✅ Tables, headings, and lists
- ✅ Emoji indicators for clarity
- ✅ Concise summaries (200-250 words)
- ✅ Context-relevant comments
- ✅ No technical jargon

---

## Configuration Reference

### Environment Variables
```bash
# LLM Provider Selection
LLM_PROVIDER=google  # or "ollama"

# Google Gemini
GOOGLE_API_KEY=your_api_key_here
GOOGLE_MODEL=gemini-2.0-flash-exp  # Recommended

# Ollama (Local)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1

# Neo4j Database
NEO4J_URI=neo4j+s://your_instance.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password_here
```

### Python Configuration (`config.py`)
```python
class Config:
    LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "ollama")
    
    # Ollama
    OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1")
    
    # Google Gemini
    GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
    GOOGLE_MODEL = os.environ.get("GOOGLE_MODEL", "gemini-flash-latest")
    
    AGENTS = {
        "neo4j": {
            "llm_provider": LLM_PROVIDER,
            "ollama_base_url": OLLAMA_BASE_URL,
            "ollama_model": OLLAMA_MODEL,
            "google_model": GOOGLE_MODEL,
            "temperature": 0
        }
    }
```

---

## Performance Considerations

### Context Window Management
- **Database records**: Limited to 50 places (prevents context overflow)
- **Weather points**: Aggregated to avg/min/max (400 points → 3 values)
- **Transport stations**: Limited to 30 stations (grouped by type)
- **Chat history**: Last 2 exchanges only (maintains continuity without bloat)

### Response Time Optimization
- **Deterministic temperature (0)**: Reduces generation time variability
- **Gemini Flash model**: Optimized for speed
- **Single-pass generation**: No iterative refinement
- **Cached schema**: Schema retrieved once, reused for all queries

### Token Efficiency
- **Structured prompts**: Clear instructions reduce token waste
- **Markdown output**: Natural format for LLM, no post-processing
- **Context summarization**: Aggregated data uses fewer tokens
- **Focused questions**: Enhanced queries reduce ambiguity

---

## Troubleshooting

### Issue: LLM not querying properly
**Symptoms**: Returns COUNT/GROUP BY instead of individual places

**Solutions**:
1. Verify model: Use `gemini-2.0-flash-exp`
2. Check prompt template is applied correctly
3. Ensure temperature = 0
4. Validate Cypher extraction logic

### Issue: Malformed Cypher output
**Symptoms**: Cypher wrapped in dict/JSON structure

**Solutions**:
1. Response handling logic extracts text correctly
2. Markdown code blocks are removed
3. Check LLM provider response format

### Issue: Missing context in responses
**Symptoms**: LLM doesn't see external datasets

**Solutions**:
1. Verify `aggregated_context` is passed correctly
2. Check dataset formatting in `_format_*_context()` methods
3. Ensure datasets are enabled on frontend

### Issue: Slow response times
**Symptoms**: Queries take >5 seconds

**Solutions**:
1. Use Gemini Flash (not Pro)
2. Reduce context window (limit records to 50)
3. Check network latency to API
4. Consider switching to local Ollama for privacy/speed trade-off

---

## Model Recommendations

### Production (Recommended)
- **Model**: `gemini-2.0-flash-exp`
- **Provider**: Google Generative AI
- **Reason**: Best balance of speed, accuracy, and cost

### Development/Testing
- **Model**: `gemini-flash-latest`
- **Provider**: Google Generative AI
- **Reason**: Stable, well-tested

### Privacy-Focused/Local
- **Model**: `llama3.1` or `llama3.2`
- **Provider**: Ollama
- **Reason**: Runs locally, no data leaves your infrastructure

### Fine-Tuning Candidates
- Start with `gemini-2.0-flash-exp`
- Fine-tune on your specific Cypher patterns
- Train with examples of successful query generations
- Use `update_model()` method to switch at runtime

---

## API Usage Example

### Direct Agent Usage
```python
from agents.neo4j_agent import Neo4jAgent
from config import Config

# Initialize agent
agent = Neo4jAgent(Config.AGENTS["neo4j"])

# Simple query
result = agent.process(
    query="Show me parks in Vienna",
    chat_history=[],
    map_context={"bounds": {"north": 48.3, "south": 48.1, "east": 16.5, "west": 16.2}},
    category_filter=None
)

print(result["answer"])  # Markdown response
print(len(result["context_records"]))  # Raw database records
```

### Multi-Dataset Query
```python
# Prepare aggregated context
aggregated_context = {
    "citylayers": {"data": places, "count": 120},
    "weather": {"data": weather_points, "count": 400},
    "transport": {"data": stations, "count": 85}
}

# Process with multiple datasets
result = agent.process_with_aggregated_context(
    query="Find parks with good weather and nearby transport",
    chat_history=[],
    aggregated_context=aggregated_context
)

print(result)  # Integrated multi-dataset response
```

### Switch Model at Runtime
```python
# Start with default model
agent = Neo4jAgent(Config.AGENTS["neo4j"])

# Switch to fine-tuned model
agent.update_model("tunedModels/my-custom-model-xyz123")

# Continue using agent with new model
result = agent.process("Show me restaurants")
```

---

## Summary

The Location Agent's LLM system is a sophisticated two-phase pipeline:

1. **Phase 1**: Natural language → Cypher query (structured data extraction)
2. **Phase 2**: Database results → User-friendly response (natural language generation)

**Key Strengths**:
- ✅ Dual LLM provider support (Google Gemini / Ollama)
- ✅ Robust response format handling
- ✅ Multi-dataset integration
- ✅ Context-aware query enhancement
- ✅ Safety validation
- ✅ User-friendly markdown output

**Production Ready**:
- ✅ Temperature = 0 for consistency
- ✅ Context window optimization
- ✅ Token-efficient prompts
- ✅ Error handling and validation
- ✅ Modular architecture

For further details, see:
- `agents/neo4j_agent.py` - Core implementation
- `config.py` - Configuration management
- `app.py` - API endpoints (`/chat`)
