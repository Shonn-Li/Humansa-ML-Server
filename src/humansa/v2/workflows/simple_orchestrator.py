"""Simple orchestrator for testing"""

from typing import Dict, Any, List
from llama_index.core.workflow import (
    Workflow,
    StartEvent,
    StopEvent,
    step
)
from llama_index.core.llms import LLM
import logging

logger = logging.getLogger(__name__)


class SimpleHumansaOrchestrator(Workflow):
    """Simple orchestrator for debugging"""
    
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
        
    @step
    async def process_query(self, ev: StartEvent) -> StopEvent:
        """Simple single-step processing"""
        query = ev.get("query")
        user_id = ev.get("user_id")
        
        logger.info(f"Processing query: {query} for user: {user_id}")
        
        # Simple response
        response = {
            "response": f"I received your query: {query}",
            "metadata": {
                "user_id": user_id,
                "orchestrator": "simple",
                "agents_used": []
            }
        }
        
        return StopEvent(result=response)