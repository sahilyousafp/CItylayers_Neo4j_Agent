import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add parent directory to path to import agents
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.neo4j_agent import Neo4jAgent

class TestNeo4jAgentSafety(unittest.TestCase):
    def setUp(self):
        # Mock dependencies
        self.mock_graph = MagicMock()
        self.mock_llm = MagicMock()
        
        # Patch the classes used in Neo4jAgent
        self.graph_patcher = patch('agents.neo4j_agent.Neo4jGraph', return_value=self.mock_graph)
        self.llm_patcher = patch('agents.neo4j_agent.ChatGoogleGenerativeAI', return_value=self.mock_llm)
        
        self.graph_patcher.start()
        self.llm_patcher.start()
        
        # Initialize agent
        self.agent = Neo4jAgent()
        # Replace the internal LLM with our mock
        self.agent.llm = self.mock_llm
        self.agent.graph = self.mock_graph

    def tearDown(self):
        self.graph_patcher.stop()
        self.llm_patcher.stop()

    def test_destructive_query_blocked(self):
        # Mock LLM to return a destructive query
        destructive_cypher = "MATCH (n) DETACH DELETE n"
        self.mock_llm.invoke.return_value.content = destructive_cypher
        
        # Call process
        result = self.agent.process("Delete everything")
        
        # Verify result indicates error
        self.assertFalse(result["ok"])
        self.assertIn("Destructive Cypher query detected", result["error"])
        
        # Verify graph.query was NOT called with the destructive query
        # (It might be called for get_schema or other things, but not the destructive one)
        # Actually, get_schema is a property or method called earlier.
        # We want to ensure query() wasn't called with the delete command.
        for call in self.mock_graph.query.call_args_list:
            args, _ = call
            if args:
                self.assertNotIn("DELETE", args[0])
                self.assertNotIn("DETACH", args[0])

    def test_safe_query_allowed(self):
        # Mock LLM to return a safe query
        safe_cypher = "MATCH (n:Place) RETURN n LIMIT 10"
        
        # Setup mock responses
        # First invoke is for Cypher generation
        # Second invoke is for Answer generation
        self.mock_llm.invoke.side_effect = [
            MagicMock(content=safe_cypher), # Cypher generation
            MagicMock(content="Here are the places.") # Answer generation
        ]
        
        self.mock_graph.query.return_value = [{"n": {"name": "Test Place"}}]
        
        # Call process
        result = self.agent.process("Show me places")
        
        # Verify success
        self.assertTrue(result["ok"])
        self.assertEqual(result["answer"], "Here are the places.")
        
        # Verify graph.query WAS called with the safe query
        self.mock_graph.query.assert_any_call(safe_cypher)

if __name__ == '__main__':
    unittest.main()
