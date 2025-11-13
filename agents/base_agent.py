"""
Base Agent class for all agents
"""
from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseAgent(ABC):
    """
    Abstract base class for all agents.
    Each agent should implement its own logic for processing queries.
    """

    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the agent with optional configuration.
        
        Args:
            config: Dictionary containing agent-specific configuration
        """
        self.config = config or {}

    @abstractmethod
    def process(self, *args, **kwargs) -> Any:
        """
        Process the input and return results.
        This method must be implemented by all agents.
        """
        pass

    @abstractmethod
    def get_info(self) -> Dict[str, Any]:
        """
        Return information about the agent's capabilities and configuration.
        """
        pass
