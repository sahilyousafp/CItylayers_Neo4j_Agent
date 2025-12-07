import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import re

# Add parent directory to path to import agents
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.neo4j_agent import Neo4jAgent

class TestNeo4jAgentPatterns(unittest.TestCase):
    def setUp(self):
        self.mock_graph = MagicMock()
        self.mock_llm = MagicMock()
        
        self.graph_patcher = patch('agents.neo4j_agent.Neo4jGraph', return_value=self.mock_graph)
        self.llm_patcher = patch('agents.neo4j_agent.ChatGoogleGenerativeAI', return_value=self.mock_llm)
        
        self.graph_patcher.start()
        self.llm_patcher.start()
        
        self.agent = Neo4jAgent()
        self.agent.llm = self.mock_llm
        self.agent.graph = self.mock_graph

    def tearDown(self):
        self.graph_patcher.stop()
        self.llm_patcher.stop()

    def test_map_bounds_prompt_structure(self):
        # Test that _get_map_bounds_prompt returns the correct pattern
        map_context = {
            "bounds": {"south": 10, "north": 20, "west": 30, "east": 40}
        }
        
        # Test WITH category filter
        prompt_with_cat = self.agent._get_map_bounds_prompt(map_context, category_filter="1")
        self.assertIn("MATCH (pg:place_grades)-[:ASSOCIATED_WITH]->(pl:places)", prompt_with_cat)
        self.assertIn("MATCH (pg)-[:OF_CATEGORY]->(cat:categories)", prompt_with_cat)
        self.assertIn("cat.category_id = 1", prompt_with_cat)
        
        # Test WITHOUT category filter (should still use the pattern as per user request "Always places are connected...")
        # Wait, if no category filter, do we still enforce it? 
        # The user said "Always places are connected to categories with place grades. So when filtering with category sirch through place grades and places."
        # But even without filter, it's good to show categories.
        # My update to the code changed the "WITHOUT category filter" block to also use this pattern.
        prompt_no_cat = self.agent._get_map_bounds_prompt(map_context, category_filter=None)
        self.assertIn("MATCH (pg:place_grades)-[:ASSOCIATED_WITH]->(pl:places)", prompt_no_cat)
        self.assertIn("MATCH (pg)-[:OF_CATEGORY]->(cat:categories)", prompt_no_cat)

if __name__ == '__main__':
    unittest.main()
