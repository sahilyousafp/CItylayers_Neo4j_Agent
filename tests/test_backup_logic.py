import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add parent directory to path to import agents
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.neo4j_agent import Neo4jAgent

class TestBackupLogic(unittest.TestCase):
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

    def test_format_results_backup_logic(self):
        # Test that _format_results handles the 'p' and 'c' structure from backup
        mock_records = [
            {
                "p": {"location": "Test Place 1", "category": "Old Category"},
                "c": {"name": "New Category", "description": "Desc"}
            },
            {
                "p": {"location": "Test Place 2"},
                # No 'c' here
            }
        ]
        
        formatted = self.agent._format_results(mock_records)
        
        self.assertIn("Test Place 1", formatted)
        self.assertIn("New Category", formatted) # Should prioritize c.name
        self.assertIn("Test Place 2", formatted)
        self.assertIn("| Location | Category |", formatted)

    def test_map_bounds_prompt_backup_logic(self):
        # Test _get_map_bounds_prompt uses the backup pattern
        map_context = {"bounds": {"north": 1, "south": 0, "east": 1, "west": 0}}
        prompt = self.agent._get_map_bounds_prompt(map_context, category_filter="1")
        
        self.assertIn("CATEGORY FILTER ACTIVE", prompt)
        self.assertIn("OPTIONAL MATCH (p)-[:HAS_GRADE]->(pg:Place_Grade)-[:BELONGS_TO]->(c:Category)", prompt)
        self.assertIn("WHERE c.category_id = 1", prompt)

if __name__ == '__main__':
    unittest.main()
