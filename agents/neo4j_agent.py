"""
Neo4j Agent - Handles database queries and natural language to Cypher conversion
"""
import os
from typing import Dict, Any, List, Tuple
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_neo4j import Neo4jGraph, GraphCypherQAChain
from langchain_core.prompts import PromptTemplate
from .base_agent import BaseAgent


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
                - neo4j_uri: Neo4j connection URI
                - neo4j_username: Database username
                - neo4j_password: Database password
                - google_model: Google Generative AI model name
                - temperature: LLM temperature setting
        """
        super().__init__(config)
        self.graph = self._connect_to_neo4j()
        self.llm = self._init_llm()
        self.chain = self._build_chain()

    def _connect_to_neo4j(self) -> Neo4jGraph:
        """
        Establish connection to Neo4j database.
        
        Returns:
            Neo4jGraph instance connected to the database
        """
        return Neo4jGraph(
            url=self.config.get("neo4j_uri", os.environ.get("NEO4J_URI", "neo4j+s://02f54a39.databases.neo4j.io")),
            username=self.config.get("neo4j_username", os.environ.get("NEO4J_USERNAME", "neo4j")),
            password=self.config.get("neo4j_password", os.environ.get("NEO4J_PASSWORD", "U9WSV67C8evx4nWCk48n3M0o7dX79T2XQ3cU1OJfP9c")),
        )

    def _init_llm(self) -> ChatGoogleGenerativeAI:
        """
        Initialize the Google Generative AI LLM.
        
        Returns:
            Configured ChatGoogleGenerativeAI instance
        """
        return ChatGoogleGenerativeAI(
            model=self.config.get("google_model", os.environ.get("GOOGLE_MODEL", "gemini-flash-latest")),
            temperature=self.config.get("temperature", 0),
            convert_system_message_to_human=True,
        )

    def _build_chain(self) -> GraphCypherQAChain:
        """
        Build the LangChain GraphCypherQAChain for natural language to Cypher conversion.
        
        Returns:
            Configured GraphCypherQAChain instance
        """
        # Enhanced Cypher generation prompt
        cypher_generation_template = """Task: Generate Cypher statement to query a graph database.
Instructions:
Use only the provided relationship types and properties in the schema.
Do not use any other relationship types or properties that are not provided.

Schema:
{schema}

Note: Do not include any explanations or apologies in your responses.
Do not respond to any questions that might ask anything else than for you to construct a Cypher statement.
Do not include any text except the generated Cypher statement.

IMPORTANT: Always return comprehensive information about places:
- Return the place node (p) with ALL its properties
- Return related category nodes (c) with their descriptions
- Return subcategory information if available
- Return comments, grades, ratings, and reviews if they exist
- Use OPTIONAL MATCH for relationships that might not exist

For queries about specific locations with coordinates:
- Use WHERE clauses to filter by exact coordinates or nearby coordinates
- Example: WHERE p.latitude = lat AND p.longitude = lon
- Or for nearby: WHERE abs(p.latitude - lat) < 0.001 AND abs(p.longitude - lon) < 0.001
- Return all properties: category, subcategory, comments, grade, rating, etc.

For geographic/region queries with coordinate bounds (North, South, East, West):
- Use WHERE clauses to filter by latitude and longitude ranges
- Example: WHERE p.latitude >= south AND p.latitude <= north AND p.longitude >= west AND p.longitude <= east

The question is:
{question}"""

        cypher_prompt = PromptTemplate(
            input_variables=["schema", "question"],
            template=cypher_generation_template,
        )
        
        qa_template = """You are a helpful assistant providing comprehensive information about locations in a database.

Question: {question}

Database results:
{context}

IMPORTANT Instructions:
1. When asked about a SPECIFIC location (with or without coordinates):
   - Provide ALL available information about that location
   - Include category, subcategory, comments/description, and grade/rating
   - List all attributes systematically
   - Format with proper sections using markdown
   - Be thorough and informative

2. When listing MULTIPLE places:
   - Keep it concise
   - Always include coordinates with place IDs
   - Format: place_id: ChIJxxx (lat, lon)

Use proper markdown syntax:
- Use ### for main headers, #### for subheaders
- Use **text** for bold emphasis on important information
- Use - or * for bullet lists  
- Use tables with | pipes for structured data when comparing multiple items
- Use `text` for code/IDs
- Use proper line breaks between sections
- Use > for highlighting key information

Structure for single location queries:
### 📍 [Location Name]

**Description/Comments:** [Detailed description or comments if available]

#### 📂 Classification
- **Category:** [main category]
- **Subcategory:** [subcategory if available]
- **Type:** [type if available]

#### ⭐ Rating & Quality
- **Grade:** [grade/rating if available]
- **Reviews:** [review information if available]

#### 📋 Basic Information
- **Coordinates:** (lat, lon)
- **Address:** [address if available]

#### 🔑 Identifiers
- **Place ID:** `place_id`
[other IDs if available]

#### 📝 Additional Details
[Any other relevant information such as opening hours, contact info, etc.]

Answer:"""
        qa_prompt = PromptTemplate(
            input_variables=["question", "context"],
            template=qa_template,
        )
        return GraphCypherQAChain.from_llm(
            llm=self.llm,
            graph=self.graph,
            cypher_prompt=cypher_prompt,
            qa_prompt=qa_prompt,
            allow_dangerous_requests=True,
            verbose=True,
            return_intermediate_steps=True,
            top_k=10000,
        )

    def process(self, query: str, chat_history: List[Tuple[str, str]] = None) -> Dict[str, Any]:
        """
        Process a natural language query and return results from Neo4j.
        
        Args:
            query: Natural language question about places
            chat_history: Optional list of (question, answer) tuples for context
            
        Returns:
            Dictionary containing:
                - answer: Text answer to the query
                - context_records: Raw database records
                - intermediate_steps: Query execution details
        """
        # Enhance question with chat history context
        if chat_history:
            context_text = "\n".join(
                [f"Previous Q: {q}\nPrevious A: {a}" for q, a in chat_history[-2:]]
            )
            enhanced_query = f"{context_text}\n\nCurrent question: {query}"
        else:
            enhanced_query = query

        try:
            result = self.chain.invoke({"query": enhanced_query})
            answer = result.get("result", "")
            
            # Extract context records
            context_records = []
            intermediate_steps = result.get("intermediate_steps", [])
            for step in intermediate_steps:
                step_context = step.get("context")
                if step_context:
                    context_records = step_context

            # If AI doesn't know, format results
            if "don't know" in answer.lower():
                answer = self._format_results(context_records)

            return {
                "ok": True,
                "answer": answer,
                "context_records": context_records,
                "intermediate_steps": intermediate_steps,
            }
        except Exception as e:
            return {
                "ok": False,
                "error": str(e),
                "context_records": [],
            }

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
        
        # Create markdown table with coordinates always included
        output.append("| # | Location | Place ID (Coordinates) |")
        output.append("|---|----------|------------------------|")
        
        for i, record in enumerate(context[:preview_count], 1):
            if "p" in record:
                place = record["p"]
                location = place.get("location", "Unknown")
                lat = place.get("latitude", "N/A")
                lon = place.get("longitude", "N/A")
                pid = place.get("place_id", "N/A")
                
                # Format with coordinates
                if lat != "N/A" and lon != "N/A":
                    pid_coords = f"`{pid}` ({lat:.6f}, {lon:.6f})"
                else:
                    pid_coords = f"`{pid}` (N/A)"
                
                output.append(f"| {i} | **{location}** | {pid_coords} |")
        
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
