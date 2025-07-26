"""
Simple debug version of HumansaOrchestrator
"""

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


class HumansaOrchestratorDebug(Workflow):
    """Debug version - single step workflow"""
    
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
        """
        Single step processing
        """
        logger.info("=== DEBUG: process_query step ===")
        query = ev.get("query")
        user_id = ev.get("user_id")
        logger.info(f"Query: {query}, User: {user_id}")
        
        try:
            # Simple LLM call
            response = await self.router_llm.acomplete(
                f"Answer this query briefly: {query}"
            )
            
            response_text = response.text
            logger.info(f"LLM response: {response_text[:100]}...")
            
        except Exception as e:
            logger.error(f"LLM error: {e}")
            response_text = "I encountered an error processing your request."
        
        # Return result
        return StopEvent(
            result={
                "response": response_text,
                "metadata": {
                    "user_id": user_id,
                    "orchestrator": "humansa_v2_debug",
                    "agents_consulted": []
                }
            }
        )