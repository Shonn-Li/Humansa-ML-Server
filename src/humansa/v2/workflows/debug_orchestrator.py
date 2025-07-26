"""
Debug version of HumansaOrchestrator to identify recursion issue
"""

from typing import Dict, Any, List, Optional, Union
from llama_index.core.workflow import (
    Workflow,
    StartEvent,
    StopEvent,
    step
)
from llama_index.core.workflow.events import Event
from llama_index.core.llms import LLM
from dataclasses import dataclass
import logging
import json

logger = logging.getLogger(__name__)


@dataclass
class QueryAnalysisEvent(Event):
    """Initial query analysis results."""
    query: str
    user_id: str
    intent: str
    

@dataclass
class ProcessingEvent(Event):
    """Processing event."""
    data: Dict[str, Any]


class DebugHumansaOrchestrator(Workflow):
    """Debug orchestrator - minimal implementation"""
    
    def __init__(
        self,
        agents: List[Any],
        router_llm: LLM,
        memory_manager: Any,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.agents = {agent.agent_id: agent for agent in agents}
        self.router_llm = router_llm
        self.memory_manager = memory_manager
        self._context_data = {}  # Use instance variable instead of Context
        
    @step
    async def analyze_query(self, ev: StartEvent) -> QueryAnalysisEvent:
        """
        Step 1: Analyze the query - NO Context parameter
        """
        logger.info("=== DEBUG: analyze_query step ===")
        query = ev.get("query")
        user_id = ev.get("user_id")
        logger.info(f"Query: {query}, User: {user_id}")
        
        # Store in instance variable instead of Context
        self._context_data["query"] = query
        self._context_data["user_id"] = user_id
        
        return QueryAnalysisEvent(
            query=query,
            user_id=user_id,
            intent="general"
        )
    
    @step
    async def process_query(self, ev: QueryAnalysisEvent) -> ProcessingEvent:
        """
        Step 2: Process - NO Context parameter
        """
        logger.info("=== DEBUG: process_query step ===")
        
        # Simple processing
        result_data = {
            "query": ev.query,
            "user_id": ev.user_id,
            "intent": ev.intent,
            "response": f"Processing query: {ev.query}"
        }
        
        return ProcessingEvent(data=result_data)
    
    @step
    async def finalize(self, ev: ProcessingEvent) -> StopEvent:
        """
        Step 3: Finalize - NO Context parameter
        """
        logger.info("=== DEBUG: finalize step ===")
        
        response = {
            "response": ev.data.get("response", "No response"),
            "metadata": {
                "user_id": ev.data.get("user_id"),
                "orchestrator": "debug",
                "intent": ev.data.get("intent")
            }
        }
        
        return StopEvent(result=response)