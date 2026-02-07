"""
Neo4j Agent - Handles database queries and natural language to Cypher conversion
"""
import os
import re
from typing import Dict, Any, List, Tuple
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from langchain_neo4j import Neo4jGraph
from langchain_core.prompts import PromptTemplate
from .base_agent import BaseAgent


CYPHER_GENERATION_TEMPLATE = """Task: Generate a Cypher statement to query a graph database.

Instructions:
- Use ONLY the relationship types and properties provided in the schema
- Do NOT use any other relationships or properties not listed
- Return ONLY the Cypher statement, no explanations or comments

Schema:
{schema}

Database Structure:
- Places connect to Categories through Place_Grade nodes: (Place)-[:HAS_GRADE]->(Place_Grade)-[:BELONGS_TO]->(Category)
- Category properties: category_id (integer 1-6), type (name), description
- Always use OPTIONAL MATCH for category relationships

Query Pattern Examples:
```
MATCH (p:places)
OPTIONAL MATCH (p)<-[:ASSOCIATED_WITH]-(pg:place_grades)-[:OF_CATEGORY]->(c:categories)
OPTIONAL MATCH (co:comments)-[:ABOUT]->(p)
WHERE p.latitude >= 48.1 AND p.latitude <= 48.3 
  AND p.longitude >= 16.2 AND p.longitude <= 16.5
RETURN DISTINCT p, c, pg, co
```

For Category Filtering - IMPORTANT:
When filtering by category, the WHERE clause MUST be placed BEFORE the OPTIONAL MATCH returns None values.
CORRECT pattern:
```
MATCH (p:places)<-[:ASSOCIATED_WITH]-(pg:place_grades)-[:OF_CATEGORY]->(c:categories)
WHERE p.latitude >= 48.1 AND p.latitude <= 48.3 
  AND p.longitude >= 16.2 AND p.longitude <= 16.5
  AND c.category_id = 1
OPTIONAL MATCH (co:comments)-[:ABOUT]->(p)
RETURN DISTINCT p, c, pg, co
```

WRONG pattern (this returns places where c is None):
```
MATCH (p:places)
OPTIONAL MATCH (p)<-[:ASSOCIATED_WITH]-(pg:place_grades)-[:OF_CATEGORY]->(c:categories)
WHERE c.category_id = 1  -- This filters AFTER optional match, keeping nulls!
```

CRITICAL RULES:
1. ALWAYS return individual place nodes (p) with their properties
2. NEVER use COUNT, GROUP BY, COLLECT, or any aggregation in RETURN
3. Each row must represent ONE place with its location data (lat/lon)
4. Return DISTINCT results to avoid duplicates
5. Include: p, c, pg, co (place, category, grade, comment nodes)
6. DETECT QUERY INTENT:
   - If asking about ONE specific place by name (e.g., "tell me about Stephansplatz", "what is Stephansplatz"): Use LIMIT 1
   - If asking about ONE specific point/coordinate: Use LIMIT 1
   - If asking about multiple places or a region (e.g., "places in Vienna", "show all"): Do NOT use LIMIT
   - Keywords indicating single place: "tell me about", "what is", "show me [specific name]", "information about"
   - Keywords indicating multiple: "places in", "locations in", "all", "find", "show all"

For Specific Coordinate Queries (e.g., "location at latitude X and longitude Y" or "what is at this point"):
- Match EXACT coordinates: WHERE p.latitude = X AND p.longitude = Y
- Or match nearby (within 0.0001 degrees): WHERE abs(p.latitude - X) < 0.0001 AND abs(p.longitude - Y) < 0.0001
- Return: RETURN p, c, pg, co
- ALWAYS use LIMIT 1 for exact coordinate queries to return only that specific point

For Single Place by Name (e.g., "tell me about Stephansplatz" or "show me Stephansplatz"):
- Use: WHERE toLower(p.location) CONTAINS toLower('Stephansplatz')
- Add LIMIT 1 to return only that specific place
- Return: RETURN p, c, pg, co LIMIT 1

For Named Location Queries (e.g., "places in Vienna" or "show Vienna locations"):
- Use: WHERE toLower(p.location) CONTAINS toLower('Vienna')
- Return ALL matching places, no LIMIT

For Bounded Region Queries (with North/South/East/West coordinates):
- Use: WHERE p.latitude >= south_value AND p.latitude <= north_value 
        AND p.longitude >= west_value AND p.longitude <= east_value
- Return ALL places in region, no LIMIT

For Category-Filtered Queries - USE MATCH NOT OPTIONAL MATCH:
When filtering by category, use MATCH (not OPTIONAL MATCH) for the category relationship:
```
MATCH (p:places)<-[:ASSOCIATED_WITH]-(pg:place_grades)-[:OF_CATEGORY]->(c:categories)
WHERE p.latitude >= south AND p.latitude <= north
  AND p.longitude >= west AND p.longitude <= east
  AND c.category_id = X
OPTIONAL MATCH (co:comments)-[:ABOUT]->(p)
RETURN DISTINCT p, c, pg, co
```
This ensures only places WITH that category are returned (not places where c is None).

User Question: {question}

Map Context: {map_bounds_info}

Generate the Cypher query now:"""

QA_TEMPLATE = """You are a helpful location assistant providing information about places from a database. Your responses should be **easy to understand** for the **general public** with clear formatting and helpful context.

Question: {question}

Database Results:
{context}

**Response Guidelines:**

1. **For Region/Area Queries** (questions with map bounds or asking about an area):
   - Format: "### 📍 [Location/Region Name]"
   - **One-sentence summary** of the area in plain language
   - **Statistics table** using markdown:
   
   | Metric | Value |
   |--------|-------|
   | **Total Locations** | XXX |
   | **Most Common** | Category name (XXX locations, YY%) |
   | **Average Rating** | X.X out of 10 ⭐ |
   | **Highest Rated** | Location name (X.X/10) |
   
   - **Key Highlights:** 3-4 bullet points with interesting findings
   - **Top 5 Relevant Comments from this Region:** (if available)
     - Show comments that best match the context of the user's question
     - Do NOT sort by rating - show contextually relevant comments
     - Format: "Comment text" - *Location Name*
   - Keep under 250 words total
   - Use **bold** for important numbers, ratings, and category names

2. **For Specific Location Queries** (asking about one place by name or coordinates):
   - Format: "### 📍 [Location Name]"
   - **Quick Facts Table:**
   
   | Property | Details |
   |----------|---------|
   | 📍 **Location** | Full address |
   | 🏷️ **Category** | Category name |
   | ⭐ **Rating** | XX out of 100 |
   | 📝 **What it's about** | Brief description in simple terms |
   
   - **About this location:** 1-2 sentences explaining what makes it special
   
   - **💬 Top 5 Relevant Visitor Comments:** (if comments available)
     1. "Comment text" - *Context or Detail*
     2. "Comment text" - *Context or Detail*
     3. ...
     
   - **What makes it special:**  
     - 3-4 bullet points highlighting unique features
   
   - Keep simple and scannable
   - Use emojis sparingly for visual hierarchy

3. **Comment Selection - IMPORTANT:**
   - Show comments that are RELEVANT to the user's question context
   - If the user asks about "beauty", prioritize comments mentioning aesthetics, views, architecture
   - If asking about "transport", prioritize comments about accessibility, transit connections
   - If asking about "safety", prioritize comments mentioning security, crime, lighting
   - Do NOT just show highest-rated location comments
   - Do NOT mention ratings or scores in comment display
   - Focus on comments that answer the user's specific interest

4. **General Style:**
- Always include **Top 5 Relevant Comments** when available
- Focus on "what" and "why" - help people understand what they're looking at
- Add context: explain what categories mean, why ratings matter
- Use simple words: "places" not "locations", "rating" not "grade"
- If showing comments, include location name for context
- DO NOT mention map UI interactions or technical database terms
- If no results: suggest alternatives in a helpful, friendly way
- Keep your response focused on the DATABASE RESULTS provided
- DO NOT make up information about specific places - stick to the data
- Additional context about landmarks may be provided separately

**Example Output (Area Query):**
```
### 📍 Vienna District 1

This central historic district offers **exceptional urban quality** with beautiful architecture, excellent transit, and vibrant public spaces.

| Metric | Value |
|--------|-------|
| **Total Places** | **523** locations 🌟 |
| **Most Common** | Movement (**156** places, 30%) |
| **Average Rating** | **7.8** out of 10 ⭐ |
| **Highest Rated** | **Stephansplatz** (9.2/10) 🏆 |

**Key Highlights:**
- **Movement** and **Beauty** are the strongest categories here
- Over **200 places** rated above **8.0** - great quality overall!
- The historic core has the **highest concentration** of top-rated spots
- **Protection** ratings range from 5.2 to 9.8, showing variety in safety perceptions

**Top 5 Relevant Comments from this Region:**
1. "Absolutely stunning architecture and atmosphere!" - *Stephansplatz*
2. "Great public transport connections, very easy to get around" - *Karlsplatz*
3. "Beautiful pedestrian areas with lots of cafes" - *Graben Street*
4. "Can get crowded with tourists during summer" - *Stephansplatz*
5. "Well-maintained parks and green spaces" - *Stadtpark*
```

**Example 2 (Specific Location):**
```
### 📍 Stephansplatz

| Property | Details |
|----------|---------|
| 📍 **Location** | Stephansplatz 3, 1010 Vienna, Austria |
| 🏷️ **Category** | **Beauty** |
| ⭐ **Rating** | **9.2** out of 10 |
| 📝 **What it's about** | Vienna's most famous public square with stunning Gothic cathedral |

**About this location:**
**Stephansplatz** is the heart of Vienna's historic center, featuring the magnificent **St. Stephen's Cathedral**. This medieval square attracts visitors from around the world and consistently ranks as one of **Vienna's most beautiful** locations.

**💬 Top 5 Relevant Visitor Comments:**
1. "Absolutely breathtaking architecture, especially the cathedral!"
2. "Perfect central meeting point with amazing atmosphere"
3. "Best at night when the cathedral is lit up"
4. "Can be very crowded, but worth visiting early morning"
5. "Great street performers and energy, very photogenic"

**What makes it special:**
- **Gothic cathedral** dating back to the 12th century
- **Bustling pedestrian zone** with street performers daily
- Central **meeting point** and top tourist destination
- Surrounded by **luxury shops** and historic buildings
- **Excellent transit access** (U1, U3 metro lines)
```

Now provide your answer based on the database results above:
     1. "Comment text" - *Date or Context*
     2. "Comment text" - *Date or Context*
     3. (etc.)
   - Keep thorough but readable (250-350 words max)
   - Use **bold** for key features and important details

3. **For Multiple Specific Places** (list of named places):
   - **For 1-20 places:** Create easy-to-read table:
   
   | Location | What it is | Rating ⭐ | Why visit |
   |----------|------------|----------|-----------|
   
   - **For 21+ places:** 
     - Summary statistics with **bold** numbers
     - **Top 5 Highest Rated** locations in table format
     - **Top 5 Comments Across All Locations:**
       1. "Comment text" - *Location Name* (Rating)
   - ALWAYS show location names in **bold**, NEVER show place IDs
   - Use simple language for categories

4. **For Category-Specific Queries** (e.g., "show me beauty locations"):
   - Format: "### 🏷️ [Category Name]"
   - One sentence explaining what this category means in everyday terms
   - **Statistics:**
   
   | What we found | Details |
   |---------------|---------|
   | **Total Locations** | XXX places |
   | **Average Rating** | X.X out of 10 ⭐ |
   | **Rating Range** | From X.X to X.X |
   | **Best Rated** | Location name (X.X/10) |
   
   - **Top 5 Rated Locations:** Table with names, ratings, and brief descriptions
   - **Top 5 Comments for this Category:**
     1. "Comment text" - *Location Name* (Rating: X.X/10)
   - Keep under 300 words

**Formatting Rules for Better Readability:**
- Use ### for main headers only
- Use #### for subsections sparingly
- Use tables for all structured data
- Use **bold** for ALL important words: numbers, ratings, place names, category names, key facts
- Use emojis liberally: 📍🏷️⭐📝💬🌟🏆👍
- Use "out of 10" instead of "/10" for clarity
- Return ONLY markdown - no JSON, no code blocks
- Break up long paragraphs - use bullet points

**Content Requirements:**
- Write like you're talking to a friend - avoid technical jargon
- **Bold** all numbers, ratings, and important terms
- Always include **Top 5 Comments** when available (prioritize highest-rated locations)
- Focus on "what" and "why" - help people understand what they're looking at
- Add context: explain what categories mean, why ratings matter
- Use simple words: "places" not "locations", "rating" not "grade"
- If showing comments, include location name and rating for context
- DO NOT mention map UI interactions or technical database terms
- If no results: suggest alternatives in a helpful, friendly way
- Keep your response focused on the DATABASE RESULTS provided
- DO NOT make up information about specific places - stick to the data
- Additional context about landmarks may be provided separately

**Example Output (Area Query):**
```
### 📍 Vienna District 1

This central historic district offers **exceptional urban quality** with beautiful architecture, excellent transit, and vibrant public spaces.

| Metric | Value |
|--------|-------|
| **Total Places** | **523** locations 🌟 |
| **Most Common** | Movement (**156** places, 30%) |
| **Average Rating** | **7.8** out of 10 ⭐ |
| **Highest Rated** | **Stephansplatz** (9.2/10) 🏆 |

**Key Highlights:**
- **Movement** and **Beauty** are the strongest categories here
- Over **200 places** rated above **8.0** - great quality overall!
- The historic core has the **highest concentration** of top-rated spots
- **Protection** ratings range from 5.2 to 9.8, showing variety in safety perceptions

**Top 5 Comments from this Region:**
1. "Absolutely stunning architecture and atmosphere!" - *Stephansplatz* (**9.2**/10) ⭐
2. "Great public transport connections, very easy to get around" - *Karlsplatz* (**8.9**/10)
3. "Beautiful pedestrian areas with lots of cafes" - *Graben Street* (**8.7**/10)
4. "Can get crowded with tourists during summer" - *Stephansplatz* (**9.2**/10)
5. "Well-maintained parks and green spaces" - *Stadtpark* (**8.5**/10)
```

**Example 2 (Specific Location):**
```
### 📍 Stephansplatz

| Property | Details |
|----------|---------|
| 📍 **Location** | Stephansplatz 3, 1010 Vienna, Austria |
| 🏷️ **Category** | **Beauty** |
| ⭐ **Rating** | **9.2** out of 10 |
| 📝 **What it's about** | Vienna's most famous public square with stunning Gothic cathedral |

**About this location:**
**Stephansplatz** is the heart of Vienna's historic center, featuring the magnificent **St. Stephen's Cathedral**. This medieval square attracts visitors from around the world and consistently ranks as one of **Vienna's most beautiful** locations.

**💬 Top 5 Visitor Comments:**
1. "Absolutely breathtaking architecture, especially the cathedral!" - *December 2023*
2. "Perfect central meeting point with amazing atmosphere" - *November 2023*
3. "Best at night when the cathedral is lit up" - *October 2023*
4. "Can be very crowded, but worth visiting early morning" - *September 2023*
5. "Great street performers and energy, very photogenic" - *August 2023*

**What makes it special:**
- **Gothic cathedral** dating back to the 12th century
- **Bustling pedestrian zone** with street performers daily
- Central **meeting point** and top tourist destination
- Surrounded by **luxury shops** and historic buildings
- **Excellent transit access** (U1, U3 metro lines)
```

Now provide your answer based on the database results above:"""


class Neo4jAgent(BaseAgent):
    """
    Agent responsible for connecting to Neo4j database and executing
    natural language queries using LangChain's GraphCypherQAChain.
    """

    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize Neo4j Agent with database and LLM configuration.
        
        Args:
            config: Optional configuration dictionary with keys:
                - uri: Neo4j connection URI
                - username: Database username
                - password: Database password
                - model: Google Generative AI model name
                - temperature: LLM temperature setting
        """
        super().__init__(config)
        # If config is provided, use it, otherwise fall back to defaults (which might come from env vars in base_agent or here)
        self.config = config or {}
        self.graph = self._connect_to_neo4j()
        self.llm = self._init_llm()
        # self.chain = self._build_chain() # Deprecated in favor of manual control

    def _connect_to_neo4j(self) -> Neo4jGraph:
        """
        Establish connection to Neo4j database.
        
        Returns:
            Neo4jGraph instance connected to the database
        """
        return Neo4jGraph(
            url=self.config.get("uri", os.environ.get("NEO4J_URI", "neo4j+s://02f54a39.databases.neo4j.io")),
            username=self.config.get("username", os.environ.get("NEO4J_USERNAME", "neo4j")),
            password=self.config.get("password", os.environ.get("NEO4J_PASSWORD", "U9WSV67C8evx4nWCk48n3M0o7dX79T2XQ3cU1OJfP9c")),
        )

    def _init_llm(self):
        """
        Initialize the LLM based on configured provider.
        Supports Ollama (default) or Google Generative AI.
        
        Returns:
            Configured LLM instance (ChatOllama or ChatGoogleGenerativeAI)
        """
        llm_provider = self.config.get("llm_provider", os.environ.get("LLM_PROVIDER", "ollama"))
        
        if llm_provider == "ollama":
            model_name = self.config.get("ollama_model", os.environ.get("OLLAMA_MODEL", "llama3.1"))
            base_url = self.config.get("ollama_base_url", os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"))
            print(f"INFO: Initializing Neo4jAgent with Ollama model: {model_name} at {base_url}")
            return ChatOllama(
                model=model_name,
                base_url=base_url,
                temperature=self.config.get("temperature", 0),
            )
        else:  # google
            model_name = self.config.get("google_model", os.environ.get("GOOGLE_MODEL", "gemini-flash-latest"))
            print(f"INFO: Initializing Neo4jAgent with Google model: {model_name}")
            return ChatGoogleGenerativeAI(
                model=model_name,
                temperature=self.config.get("temperature", 0),
                convert_system_message_to_human=True,
            )

    def update_model(self, model_name: str) -> None:
        """
        Update the LLM model used by the agent.
        Useful for switching to a fine-tuned model at runtime.
        
        Args:
            model_name: Name of the new model (e.g., 'gemini-pro' or 'tunedModels/my-model')
        """
        print(f"INFO: Switching Neo4jAgent model to: {model_name}")
        self.config["model"] = model_name
        self.llm = self._init_llm()
        # Rebuild chain with new LLM
        # self.chain = self._build_chain()

    def _validate_cypher_query(self, query: str) -> None:
        """
        Validates that the Cypher query is safe and read-only.
        Raises ValueError if destructive patterns are found.
        """
        forbidden_patterns = [
            r'\bDELETE\b', r'\bDETACH\b', r'\bDROP\b', 
            r'\bCREATE\b', r'\bMERGE\b', r'\bSET\b', 
            r'\bREMOVE\b', r'\bCALL\s+apoc\.periodic\.iterate\b'
        ]
        
        upper_query = query.upper()
        for pattern in forbidden_patterns:
            if re.search(pattern, upper_query):
                raise ValueError(f"Destructive Cypher query detected and blocked: {pattern}")

    def process(self, query: str, chat_history: List[Tuple[str, str]] = None, map_context: Dict[str, Any] = None, category_filter: str = None) -> Dict[str, Any]:
        """
        Process a natural language query and return results from Neo4j.
        
        Args:
            query: Natural language question about places
            chat_history: Optional list of (question, answer) tuples for context
            map_context: Optional map state (bounds, center) for filtering
            category_filter: Optional category ID to filter results (e.g., "1" for Beauty)
            
        Returns:
            Dictionary containing:
                - answer: Text answer to the query
                - context_records: Raw database records (ALL results from DB)
                - intermediate_steps: Query execution details
        """
        # Enhance question with chat history context
        enhanced_query = self._enhance_query_with_history(query, chat_history)

        # Prepare map bounds info for the prompt
        map_bounds_info = self._get_map_bounds_prompt(map_context, category_filter)

        try:
            # 1. Generate Cypher
            schema = self.graph.get_schema
            cypher_prompt = PromptTemplate(
                input_variables=["schema", "question", "map_bounds_info"],
                template=CYPHER_GENERATION_TEMPLATE,
            )
            formatted_prompt = cypher_prompt.format(
                schema=schema,
                question=enhanced_query,
                map_bounds_info=map_bounds_info
            )
            
            print(f"DEBUG: Generating Cypher...")
            llm_response = self.llm.invoke(formatted_prompt)
            generated_cypher = llm_response.content
            
            # Handle case where content is a dict or JSON structure
            if isinstance(generated_cypher, dict):
                # Extract from {'type': 'text', 'text': '...'}  structure
                if 'text' in generated_cypher:
                    generated_cypher = generated_cypher['text']
                else:
                    generated_cypher = str(generated_cypher)
            
            # Handle case where content is a list (some models return list of content blocks)
            if isinstance(generated_cypher, list):
                # Check if list contains dicts with 'text' key
                if generated_cypher and isinstance(generated_cypher[0], dict) and 'text' in generated_cypher[0]:
                    generated_cypher = " ".join(item.get('text', str(item)) for item in generated_cypher)
                else:
                    generated_cypher = " ".join(str(item) for item in generated_cypher) if generated_cypher else ""
            
            # Convert to string if not already
            generated_cypher = str(generated_cypher)
            
            # Try to parse as JSON if it looks like a JSON string
            if generated_cypher.startswith('{') and '"text"' in generated_cypher:
                try:
                    import json
                    parsed = json.loads(generated_cypher)
                    if isinstance(parsed, dict) and 'text' in parsed:
                        generated_cypher = parsed['text']
                except (json.JSONDecodeError, ValueError):
                    pass
            
            # Clean Cypher (remove markdown blocks)
            generated_cypher = re.sub(r'```cypher', '', generated_cypher, flags=re.IGNORECASE)
            generated_cypher = re.sub(r'```', '', generated_cypher).strip()
            
            print(f"⚡ GENERATED CYPHER:\n{generated_cypher}")

            # 2. Validate Cypher
            self._validate_cypher_query(generated_cypher)

            # 3. Execute Cypher
            print(f"DEBUG: Executing Cypher...")
            context_records = self.graph.query(generated_cypher)
            print(f"📊 OUTPUT RECORDS: {len(context_records)} records found")

            # 4. Prepare context summary for LLM
            context_summary = self._prepare_context_summary(context_records, category_filter)

            # 5. Generate Answer
            qa_prompt = PromptTemplate(
                input_variables=["question", "context"],
                template=QA_TEMPLATE,
            )
            formatted_qa_prompt = qa_prompt.format(
                question=enhanced_query,
                context=context_summary
            )
            
            print(f"DEBUG: Generating Answer...")
            answer_response = self.llm.invoke(formatted_qa_prompt)
            answer = answer_response.content
            
            # Handle case where content is a list (some models return list of content blocks)
            if isinstance(answer, list):
                # Extract text from list items
                text_parts = []
                for item in answer:
                    if isinstance(item, dict) and 'text' in item:
                        text_parts.append(item['text'])
                    elif isinstance(item, str):
                        text_parts.append(item)
                    else:
                        text_parts.append(str(item))
                answer = " ".join(text_parts) if text_parts else ""
            
            # Clean up answer - remove extras/signature fields if it's a dict
            if isinstance(answer, dict):
                answer = answer.get('text', str(answer))
            
            # Additional cleanup for dict-like strings
            if isinstance(answer, str):
                # Check if answer looks like a dict representation
                if answer.strip().startswith("{'type':") or answer.strip().startswith('{"type":'):
                    try:
                        import ast
                        parsed = ast.literal_eval(answer)
                        if isinstance(parsed, dict) and 'text' in parsed:
                            answer = parsed['text']
                    except:
                        # Try regex extraction as fallback
                        match = re.search(r"'text':\s*'(.*?)'(?:,\s*'extras'|$)", answer, re.DOTALL)
                        if match:
                            answer = match.group(1)
                        else:
                            match = re.search(r'"text":\s*"(.*?)"(?:,\s*"extras"|$)', answer, re.DOTALL)
                            if match:
                                answer = match.group(1)
            
            # Remove generic/unwanted phrases
            unwanted_patterns = [
                r'\.\s*\n\n.*?All locations shown on map\. Click pins for details\.',
                r'💡 All locations shown on map\. Click pins for details\.',
                r'Showing \w+ locations\.',
                r'\n\nShowing \w+ locations\.\n\n.*?Click pins for details\.',
                r"'extras':\s*\{[^}]*\}",  # Remove extras dict
                r"'signature':\s*'[^']*'",  # Remove signature
            ]
            
            for pattern in unwanted_patterns:
                answer = re.sub(pattern, '', answer, flags=re.IGNORECASE | re.DOTALL)
            
            # Clean up extra newlines and whitespace
            answer = re.sub(r'\n{3,}', '\n\n', answer).strip()
            answer = re.sub(r'\s+\.', '.', answer)  # Remove space before periods

            # --- LOGGING FOR USER MONITORING ---
            print("\n" + "="*60)
            print(f"🤖 INPUT QUERY: {enhanced_query}")
            if category_filter:
                print(f"🏷️ CATEGORY FILTER: {category_filter}")
            print("-" * 60)
            print(f"⚡ GENERATED CYPHER:\n{generated_cypher}")
            print("-" * 60)
            print(f"📊 OUTPUT RECORDS: {len(context_records)} records found")
            print("="*60 + "\n")
            # -----------------------------------

            # If we have a Cypher query and limited results, fetch ALL results for the map
            all_records = self._fetch_full_results(context_records, generated_cypher, category_filter)

            # If AI doesn't know, format results
            if "don't know" in answer.lower():
                answer = self._format_results(all_records)
            
            # For regional queries, ensure we mention all points are on the map
            is_regional_query = self._is_regional_query(query)
            if is_regional_query and len(all_records) > 10:
                if "map" not in answer.lower():
                    answer = answer + f"\n\n💡 All {len(all_records)} locations are displayed on the map. Click any pin for detailed information."
            
            # For large result sets, enhance the answer with total count
            if len(all_records) > 50 and not is_regional_query:
                if not any(str(len(all_records)) in answer for _ in [1]):
                    answer = f"**Found {len(all_records)} locations total.** All locations will be shown on the map.\n\n" + answer

            return {
                "ok": True,
                "answer": answer,
                "context_records": all_records,
                "intermediate_steps": [{"query": generated_cypher, "context": context_records}],
            }
        except Exception as e:
            print(f"ERROR: {e}")
            return {
                "ok": False,
                "error": str(e),
                "context_records": [],
            }

    def process_multi_dataset(
        self,
        query: str,
        aggregated_context: Dict[str, Any],
        chat_history: List[Tuple[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Process a query that involves multiple datasets (CityLayers + external sources).
        Enhances the answer with cross-dataset insights.
        
        Args:
            query: Natural language question
            aggregated_context: Context from multiple data sources
            chat_history: Optional conversation history
            
        Returns:
            Dictionary with enhanced answer considering all datasets
        """
        try:
            # Enhanced QA template for multi-dataset analysis
            enhanced_template = """You are a helpful location assistant analyzing data from multiple sources. You have access to:

**Available Data Sources:**
{data_sources_summary}

**User Question:** {question}

**Data from All Sources:**
{context}

**Response Guidelines:**
1. **Identify Relevant Datasets**: Determine which datasets are most relevant to the user's question
2. **Cross-Dataset Insights**: When multiple datasets are relevant, provide insights that connect them
   - Example: "Beautiful places near transport stations"
   - Example: "Parks with good weather conditions"
   - Example: "Areas with many trees and high beauty ratings"
3. **Clear Source Attribution**: When mentioning data, indicate which source it comes from
4. **Prioritize User Intent**: Focus on what the user is actually asking for
5. **Be Concise**: Don't overload with irrelevant data from unused sources

**Formatting:**
- Use markdown for structure (headers, tables, bullet points)
- Include relevant statistics from each dataset
- Highlight cross-dataset correlations when meaningful
- Keep tone friendly and accessible for general public

Now provide your analysis:"""

            # Format the prompt
            formatted_prompt = enhanced_template.format(
                data_sources_summary=self._format_data_sources_summary(aggregated_context),
                question=query,
                context=self._format_multi_dataset_context(aggregated_context)
            )
            
            print(f"DEBUG: Processing multi-dataset query with {len([s for s in aggregated_context.values() if s['enabled']])} enabled sources")
            
            # Invoke LLM
            llm_response = self.llm.invoke(formatted_prompt)
            answer = llm_response.content if hasattr(llm_response, 'content') else str(llm_response)
            
            # Clean up answer
            if isinstance(answer, dict) and 'text' in answer:
                answer = answer['text']
            elif isinstance(answer, str) and answer.startswith('{'):
                try:
                    import json
                    parsed = json.loads(answer)
                    if isinstance(parsed, dict) and 'text' in parsed:
                        answer = parsed['text']
                except:
                    pass
            
            answer = str(answer).strip()
            
            print(f"✅ Multi-dataset analysis complete")
            
            return {
                "ok": True,
                "answer": answer
            }
            
        except Exception as e:
            print(f"ERROR in multi-dataset processing: {e}")
            return {
                "ok": False,
                "error": str(e)
            }

    def _format_data_sources_summary(self, aggregated_context: Dict[str, Any]) -> str:
        """Format a summary of available data sources."""
        summary_lines = []
        for source, info in aggregated_context.items():
            if info["enabled"]:
                source_name = source.capitalize()
                count = info["count"]
                summary_lines.append(f"- **{source_name}**: {count} records available")
        return "\n".join(summary_lines) if summary_lines else "No data sources enabled"

    def _format_multi_dataset_context(self, aggregated_context: Dict[str, Any]) -> str:
        """Format the aggregated context for LLM consumption."""
        context_parts = []
        
        # CityLayers data
        if aggregated_context["citylayers"]["enabled"] and aggregated_context["citylayers"]["count"] > 0:
            citylayers_data = aggregated_context["citylayers"]["data"]
            context_parts.append(f"### CityLayers Database ({len(citylayers_data)} locations)")
            context_parts.append(self._summarize_citylayers_data(citylayers_data))
        
        # Weather data
        if aggregated_context["weather"]["enabled"] and aggregated_context["weather"]["count"] > 0:
            weather_data = aggregated_context["weather"]["data"]
            if isinstance(weather_data, dict) and "summary" in weather_data:
                summary = weather_data["summary"]
                context_parts.append(f"\n### Weather Data")
                context_parts.append(f"- Average Temperature: {summary.get('avg_temperature', 'N/A'):.1f}°C")
                context_parts.append(f"- Temperature Range: {summary.get('min_temperature', 'N/A'):.1f}°C to {summary.get('max_temperature', 'N/A'):.1f}°C")
                context_parts.append(f"- Average Wind Speed: {summary.get('avg_wind_speed', 'N/A'):.1f} m/s")
        
        # Transport data
        if aggregated_context["transport"]["enabled"] and aggregated_context["transport"]["count"] > 0:
            transport_data = aggregated_context["transport"]["data"]
            context_parts.append(f"\n### Transport Stations ({len(transport_data)} stations)")
            # Group by type
            by_type = {}
            for station in transport_data:
                station_type = station.get("type", "Unknown")
                by_type[station_type] = by_type.get(station_type, 0) + 1
            for stype, count in sorted(by_type.items()):
                context_parts.append(f"- {stype.capitalize()}: {count} stations")
        
        # Vegetation data
        if aggregated_context["vegetation"]["enabled"] and aggregated_context["vegetation"]["count"] > 0:
            veg_data = aggregated_context["vegetation"]["data"]
            if isinstance(veg_data, dict) and "summary" in veg_data:
                summary = veg_data["summary"]
                context_parts.append(f"\n### Vegetation Data")
                context_parts.append(f"- Total Trees: {summary.get('total_trees', 0)}")
                context_parts.append(f"- Species Diversity: {summary.get('species_diversity', 0)} different species")
                if "top_species" in summary:
                    context_parts.append("- Most Common Species:")
                    for species, count in summary["top_species"][:5]:
                        context_parts.append(f"  - {species}: {count} trees")
        
        return "\n".join(context_parts) if context_parts else "No data available"

    def _summarize_citylayers_data(self, data: List[Dict]) -> str:
        """Create a concise summary of CityLayers data."""
        if not data:
            return "No locations found"
        
        # Extract key info
        locations = []
        categories = {}
        grades = []
        
        for record in data[:50]:  # Limit to first 50 for summary
            if "p" in record:
                place = record["p"]
                loc = place.get("location", "Unknown")
                locations.append(loc)
                
                if "grade" in place:
                    try:
                        grades.append(float(place["grade"]))
                    except:
                        pass
            
            if "c" in record and record["c"]:
                cat = record["c"].get("type", record["c"].get("name", "Unknown"))
                categories[cat] = categories.get(cat, 0) + 1
        
        # Build summary
        summary_parts = []
        if grades:
            avg_grade = sum(grades) / len(grades)
            summary_parts.append(f"- Average Grade: {avg_grade:.1f}/100")
        
        if categories:
            summary_parts.append("- Categories:")
            for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True)[:5]:
                summary_parts.append(f"  - {cat}: {count} locations")
        
        if locations:
            summary_parts.append(f"- Sample Locations: {', '.join(locations[:5])}")
        
        return "\n".join(summary_parts) if summary_parts else "Data available"

    def _enhance_query_with_history(self, query: str, chat_history: List[Tuple[str, str]]) -> str:
        if chat_history:
            context_text = "\n".join(
                [f"Previous Q: {q}\nPrevious A: {a}" for q, a in chat_history[-2:]]
            )
            return f"{context_text}\n\nCurrent question: {query}"
        return query

    def _get_map_bounds_prompt(self, map_context: Dict[str, Any], category_filter: str = None) -> str:
        prompt_parts = []
        
        # Category ID to Name mapping
        CATEGORY_ID_MAPPING = {
            '1': 'Beauty',
            '2': 'Sound',
            '3': 'Movement',
            '4': 'Protection',
            '5': 'Climate Comfort',
            '6': 'Activities'
        }
        
        # Check if this is a single point query
        is_single_point = False
        if map_context and "clickedPoint" in map_context:
            clicked = map_context["clickedPoint"]
            if clicked and "lat" in clicked and "lng" in clicked:
                is_single_point = True
                prompt_parts.append(f"""
USER CLICKED ON A SPECIFIC POINT:
Latitude: {clicked['lat']}
Longitude: {clicked['lng']}

CRITICAL: This is a query about ONE SPECIFIC LOCATION at these exact coordinates.
Use this pattern:
```
MATCH (p:places)
WHERE abs(p.latitude - {clicked['lat']}) < 0.0001 AND abs(p.longitude - {clicked['lng']}) < 0.0001
OPTIONAL MATCH (p)<-[:ASSOCIATED_WITH]-(pg:place_grades)-[:OF_CATEGORY]->(c:categories)
OPTIONAL MATCH (co:comments)-[:ABOUT]->(p)
RETURN DISTINCT p, c, pg, co
LIMIT 1
```
Return ONLY this one place, not nearby places.
""")
        
        if category_filter and category_filter != 'all':
            category_name = CATEGORY_ID_MAPPING.get(category_filter, f"Category ID {category_filter}")
            if is_single_point:
                # For single point with category filter
                prompt_parts.append(f"""
Category filter active: {category_name} (ID: {category_filter})
Filter the single point result by this category if applicable.
""")
            else:
                # For area queries with category filter
                prompt_parts.append(f"""
CATEGORY FILTER ACTIVE: User has selected "{category_name}" category (ID: {category_filter}).

CRITICAL: Use MATCH (not OPTIONAL MATCH) for category relationships when filtering:

CORRECT PATTERN:
```
MATCH (p:places)<-[:ASSOCIATED_WITH]-(pg:place_grades)-[:OF_CATEGORY]->(c:categories)
WHERE c.category_id = {category_filter}
  AND p.latitude >= south AND p.latitude <= north
  AND p.longitude >= west AND p.longitude <= east
OPTIONAL MATCH (co:comments)-[:ABOUT]->(p)
RETURN DISTINCT p, c, pg, co
```

WRONG PATTERN (returns nulls):
```
MATCH (p:places)
OPTIONAL MATCH (p)<-[:ASSOCIATED_WITH]-(pg:place_grades)-[:OF_CATEGORY]->(c:categories)
WHERE c.category_id = {category_filter}  -- This is too late!
```

Category IDs: 1=Beauty, 2=Sound, 3=Movement, 4=Protection, 5=Climate Comfort, 6=Activities

Return ALL places with this category. Do NOT use LIMIT.
""")
        
        if map_context and "bounds" in map_context and not is_single_point:
            b = map_context["bounds"]
            north = b.get('north')
            south = b.get('south')
            east = b.get('east')
            west = b.get('west')
            
            # Only add bounds if all values are present
            if all(v is not None for v in [north, south, east, west]):
                bounds_clause = f"""
MAP BOUNDS PROVIDED:
North: {north}
South: {south}
East: {east}
West: {west}

INSTRUCTION: Unless the question explicitly mentions a different location (e.g. "in Paris"), 
restrict the query to these bounds using:
WHERE p.latitude >= {south} AND p.latitude <= {north} 
AND p.longitude >= {west} AND p.longitude <= {east}
"""
                prompt_parts.append(bounds_clause)
        
        if not prompt_parts:
            return "No specific map bounds or category filter provided. Query the entire database."
        
        return "\n".join(prompt_parts)

    def _fetch_full_results(self, context_records: List[Dict], cypher_query: str, category_filter: str = None) -> List[Dict]:
        if cypher_query and len(context_records) >= 200:
            try:
                full_query = re.sub(r'\s+LIMIT\s+\d+', '', cypher_query, flags=re.IGNORECASE)
                
                # If category filter is applied and not already in the query, add it
                if category_filter and category_filter != 'all' and 'c.category_id' not in full_query:
                    # Try to add category filter to WHERE clause
                    if 'WHERE' in full_query.upper():
                        # Add to existing WHERE clause
                        full_query = re.sub(
                            r'(WHERE\s+)',
                            rf'\1exists((p)-[:BELONGS_TO]->(c:Category)) AND c.category_id = {category_filter} AND ',
                            full_query,
                            count=1,
                            flags=re.IGNORECASE
                        )
                    else:
                        # Add new WHERE clause before RETURN
                        full_query = re.sub(
                            r'(\s+RETURN\s+)',
                            rf' WHERE exists((p)-[:BELONGS_TO]->(c:Category)) AND c.category_id = {category_filter}\1',
                            full_query,
                            count=1,
                            flags=re.IGNORECASE
                        )
                    print(f"INFO: Added category filter {category_filter} to full query")
                
                all_records = self.graph.query(full_query)
                print(f"INFO: Retrieved {len(all_records)} total records (was limited to {len(context_records)} for LLM)")
                return all_records
            except Exception as e:
                print(f"WARN: Could not fetch full results: {e}")
        return context_records

    def _prepare_context_summary(self, records: List[Dict], category_filter: str = None) -> str:
        """
        Prepare a well-formatted context summary from database records for the LLM.
        
        Args:
            records: Raw database records from Neo4j
            category_filter: Optional category ID if filtering
            
        Returns:
            Formatted string with relevant information for LLM
        """
        if not records:
            return "No locations found in the database for this query."
        
        # Category mapping
        CATEGORY_NAMES = {
            1: "Beauty", 2: "Sound", 3: "Movement", 
            4: "Protection", 5: "Climate Comfort", 6: "Activities"
        }
        
        total_count = len(records)
        
        # Collect statistics
        category_counts = {}
        locations = []
        
        for record in records[:100]:  # Process up to 100 for detailed info
            p = record.get('p', {})
            c = record.get('c', {})
            pg = record.get('pg', {})
            
            if not p:
                continue
            
            # Use precise address if available (from Mapbox), fallback to DB location
            location_name = record.get('precise_address') or p.get('location', 'Unknown Location')
            lat = p.get('latitude')
            lon = p.get('longitude')
            
            # Extract category info
            category_id = c.get('category_id') if c else None
            category_name = CATEGORY_NAMES.get(category_id, 'Uncategorized') if category_id else 'Uncategorized'
            
            # Track category counts
            if category_name not in category_counts:
                category_counts[category_name] = 0
            category_counts[category_name] += 1
            
            # Extract grade
            grade = None
            if pg:
                grade = pg.get('grade') or pg.get('value')
            
            # Extract comments (if available)
            comments = []
            co = record.get('co')
            if co:
                # Handle comment data structure
                if isinstance(co, list):
                    # List of comments
                    for comment in co[:5]:  # Take top 5 comments
                        comment_text = comment.get('text') or comment.get('content') or comment.get('comment_text', '')
                        if comment_text:
                            comments.append(comment_text)
                elif isinstance(co, dict):
                    # Single comment
                    comment_text = co.get('text') or co.get('content') or co.get('comment_text', '')
                    if comment_text:
                        comments.append(comment_text)
                elif isinstance(co, str):
                    # Direct comment string
                    comments.append(co)
            
            # Build location entry
            location_info = {
                'name': location_name,
                'category': category_name,
                'grade': grade,
                'coordinates': f"({lat}, {lon})" if lat and lon else None,
                'comments': comments if comments else None
            }
            locations.append(location_info)
        
        # Build context summary
        summary_parts = []
        
        # 1. Overview
        summary_parts.append(f"Total Locations: {total_count}")
        
        if category_filter:
            filter_name = CATEGORY_NAMES.get(int(category_filter), f"Category {category_filter}")
            summary_parts.append(f"Filtered by: {filter_name}")
        
        # 2. Category breakdown
        if category_counts:
            summary_parts.append("\nCategory Distribution:")
            for cat, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
                summary_parts.append(f"  - {cat}: {count} locations")
        
        # 3. Sample locations (first 30)
        if locations:
            summary_parts.append(f"\nSample Locations (showing {min(30, len(locations))} of {total_count}):")
            for i, loc in enumerate(locations[:30], 1):
                loc_str = f"{i}. {loc['name']} - Category: {loc['category']}"
                if loc['grade']:
                    loc_str += f", Grade: {loc['grade']}"
                if loc.get('comments'):
                    loc_str += f"\n   💬 Top Comments:"
                    for j, comment in enumerate(loc['comments'], 1):
                        # Truncate long comments
                        comment_preview = comment[:150] + '...' if len(comment) > 150 else comment
                        loc_str += f"\n      {j}. \"{comment_preview}\""
                summary_parts.append(loc_str)
        
        return "\n".join(summary_parts)

    def _is_regional_query(self, query: str) -> bool:
        return any(keyword in query.lower() for keyword in [
            'region', 'area', 'north', 'south', 'east', 'west', 
            'bound', 'rectangle', 'box', 'zone', 'in the region'
        ])

    def _format_results(self, context: List[Dict[str, Any]]) -> str:
        """
        Format raw database results into markdown.
        Shows only first 10 results as preview for chat output.
        
        Args:
            context: List of database records
            
        Returns:
            Markdown-formatted string representation of results
        """
        if not context:
            return "**No results found.**"
        
        total_count = len(context)
        output = []
        
        # Show only first 10 for chat preview
        preview_count = min(10, total_count)
        
        # Header with count
        if preview_count < total_count:
            output.append(f"### {total_count} locations (showing first {preview_count})\n")
        else:
            output.append(f"### {total_count} locations\n")
        
        # Create markdown table with locations and categories
        output.append("| # | Location | Category |")
        output.append("|---|----------|----------|")
        
        for i, record in enumerate(context[:preview_count], 1):
            if "p" in record:
                place = record["p"]
                location = place.get("location", "Unknown")
                
                # Get category - prioritize c.name over c.description, then p.category
                category = "N/A"
                if "c" in record and record["c"]:
                    # Try c.name first (category name), fallback to c.description
                    category = record["c"].get("name", record["c"].get("description", "N/A"))
                elif "category" in place:
                    category = place.get("category", "N/A")
                elif "p" in record and record["p"] and "category" in record["p"]:
                    category = record["p"].get("category", "N/A")
                
                output.append(f"| {i} | **{location}** | {category} |")
        
        # Add footer if there are more results
        if total_count > preview_count:
            output.append("")
            output.append(f"_... and {total_count - preview_count} more_")
        
        return "\n".join(output)

    def get_info(self) -> Dict[str, Any]:
        """
        Return information about the Neo4j agent.
        
        Returns:
            Dictionary with agent capabilities and configuration
        """
        return {
            "name": "Neo4j Agent",
            "description": "Handles natural language queries to Neo4j database using LangChain",
            "capabilities": [
                "Natural language to Cypher conversion",
                "Place search and retrieval",
                "Context-aware query enhancement",
            ],
            "model": self.config.get("google_model", "gemini-flash-latest"),
            "database": "Neo4j Graph Database",
        }
