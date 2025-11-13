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
        qa_template = """You are a helpful assistant answering questions about places in a database.

Question: {question}

Database results:
{context}

Provide a clear, concise answer based on the results. Extract specific information requested.

Answer:"""
        qa_prompt = PromptTemplate(
            input_variables=["question", "context"],
            template=qa_template,
        )
        return GraphCypherQAChain.from_llm(
            llm=self.llm,
            graph=self.graph,
            qa_prompt=qa_prompt,
            allow_dangerous_requests=True,
            verbose=True,
            return_intermediate_steps=True,
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
        Format raw database results into a readable string.
        
        Args:
            context: List of database records
            
        Returns:
            Formatted string representation of results
        """
        if not context:
            return "No results found."
        output_lines: List[str] = [f"Found {len(context)} results:"]
        count = 0
        for record in context:
            count += 1
            if "p" in record:
                place = record["p"]
                location = place.get("location", "Unknown")
                lat = place.get("latitude")
                lon = place.get("longitude")
                pid = place.get("place_id")
                output_lines.append(f"{count}. {location} (ID: {pid}, Coords: {lat}, {lon})")
        return "\n".join(output_lines)

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
