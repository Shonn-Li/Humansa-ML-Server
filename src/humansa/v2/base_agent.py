"""
Base agent class for all specialized medical agents in the Humansa system.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from llama_index.core.base.agent.base import BaseAgent
from llama_index.core.tools import BaseTool
from llama_index.core.llms import LLM


class HumansaBaseAgent(ABC):
    """
    Abstract base class for all Humansa medical agents.
    Provides common functionality and interface for specialized agents.
    """
    
    def __init__(
        self,
        name: str,
        description: str,
        llm: LLM,
        tools: Optional[List[BaseTool]] = None,
        system_prompt: Optional[str] = None,
    ):
        """
        Initialize the base agent.
        
        Args:
            name: Agent name (e.g., "DiagnosisAgent", "TreatmentAgent")
            description: Agent description and capabilities
            llm: Language model instance
            tools: List of tools available to this agent
            system_prompt: Custom system prompt for the agent
        """
        self.name = name
        self.description = description
        self.llm = llm
        self.tools = tools or []
        self.system_prompt = system_prompt or self._get_default_system_prompt()
        self.memory = {}  # Agent-specific memory
        
    @abstractmethod
    def _get_default_system_prompt(self) -> str:
        """
        Get the default system prompt for this agent type.
        Must be implemented by subclasses.
        """
        pass
        
    @abstractmethod
    async def process(
        self,
        query: str,
        context: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """
        Process a query with the given context.
        
        Args:
            query: User query or task
            context: Shared context including patient info, history, etc.
            **kwargs: Additional agent-specific parameters
            
        Returns:
            Dictionary containing results and any updates to context
        """
        pass
        
    async def pre_process(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Pre-processing hook. Can be overridden by subclasses.
        """
        return context
        
    async def post_process(
        self,
        result: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Post-processing hook. Can be overridden by subclasses.
        """
        return result
        
    def add_tool(self, tool: BaseTool) -> None:
        """Add a tool to the agent's toolkit."""
        self.tools.append(tool)
        
    def get_capabilities(self) -> Dict[str, Any]:
        """
        Return agent capabilities for the orchestrator.
        """
        return {
            "name": self.name,
            "description": self.description,
            "tools": [tool.metadata.name for tool in self.tools],
            "specializations": self._get_specializations()
        }
        
    def _get_specializations(self) -> List[str]:
        """
        Return list of medical specializations this agent handles.
        Can be overridden by subclasses.
        """
        return []