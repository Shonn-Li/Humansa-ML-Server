"""
Base Agent Class for Multi-Agent System

This module defines the abstract base class for all agents in the system.
All agents must inherit from BaseAgent and implement the required methods.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, AsyncGenerator
import logging

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Enhanced base class for streaming-capable agents"""
    
    def __init__(self):
        super().__init__()
        self.supports_streaming = False
    
    @abstractmethod
    async def run(self, request: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the agent's main logic (non-streaming).
        
        Args:
            request: The incoming request with messages, user_id, model, etc.
            context: Shared context between agents containing results from previous agents
            
        Returns:
            Dict containing the agent's results to be added to context
        """
        pass
    
    async def stream(self, request: Dict[str, Any], context: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Execute the agent's logic with streaming support.
        
        Default implementation yields the full result at once.
        Override this method in agents that support true streaming.
        
        Args:
            request: The incoming request
            context: Shared context between agents
            
        Yields:
            Dict containing streaming chunks or full result
        """
        result = await self.run(request, context)
        yield result