"""
HumansaOrchestrator with workaround for llama-index-workflows Event bug
"""

from typing import Dict, Any, List, Optional, Set, Union
from llama_index.core.workflow import (
    Workflow,
    StartEvent,
    StopEvent,
    step,
    Event
)
from llama_index.core.llms import LLM
import asyncio
import logging
import json
from ..agents.base_agent import BaseHumansaAgent
from ..memory.memory_manager import MemoryManager

logger = logging.getLogger(__name__)


# Workaround: Create events without @dataclass to avoid recursion bug
class QueryAnalysisEvent(Event):
    """Initial query analysis results."""
    def __init__(self, **kwargs):
        super().__init__()
        self.query = kwargs.get('query', '')
        self.user_id = kwargs.get('user_id', '')
        self.intent = kwargs.get('intent', '')
        self.complexity = kwargs.get('complexity', '')
        self.required_capabilities = kwargs.get('required_capabilities', [])
        self.context = kwargs.get('context', {})


class HumansaOrchestrator(Workflow):
    """
    Simplified orchestrator with workaround for event recursion bug.
    Uses instance variables instead of complex event passing.
    """
    
    def __init__(
        self,
        agents: List[BaseHumansaAgent],
        router_llm: LLM,
        memory_manager: MemoryManager,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.agents = {agent.agent_id: agent for agent in agents}
        self.router_llm = router_llm
        self.memory_manager = memory_manager
        
        # Store workflow state in instance variables
        self._query = ""
        self._user_id = ""
        self._user_context = {}
        self._agent_responses = []
        
    @step
    async def process_query(self, ev: StartEvent) -> StopEvent:
        """
        Single-step processing to avoid multi-step event issues.
        """
        logger.info("=== Processing query ===")
        self._query = ev.get("query")
        self._user_id = ev.get("user_id")
        logger.info(f"Query: {self._query}, User: {self._user_id}")
        
        try:
            # Load user context
            self._user_context = await self.memory_manager.get_user_context(self._user_id)
            logger.info(f"User context loaded: {len(self._user_context)} items")
        except Exception as e:
            logger.error(f"Error loading user context: {e}")
            self._user_context = {}
        
        # Analyze query
        analysis = await self._analyze_query()
        
        # Select and execute agents
        selected_agents = await self._select_agents(analysis)
        agent_responses = await self._execute_agents(selected_agents)
        
        # Synthesize response
        final_response = await self._synthesize_response(agent_responses)
        
        # Store conversation
        await self.memory_manager.add_conversation(
            user_id=self._user_id,
            query=self._query,
            response=final_response,
            metadata={
                "agents_used": selected_agents,
                "intent": analysis.get("intent", "general")
            }
        )
        
        return StopEvent(
            result={
                "response": final_response,
                "metadata": {
                    "user_id": self._user_id,
                    "orchestrator": "humansa_v2",
                    "agents_consulted": selected_agents,
                    "intent": analysis.get("intent", "general")
                }
            }
        )
    
    async def _analyze_query(self) -> Dict[str, Any]:
        """Analyze the query to understand intent."""
        analysis_prompt = f"""
        Analyze this medical query and provide:
        1. Primary intent (diagnosis, treatment, information, emergency, appointment)
        2. Complexity level (simple, moderate, complex)
        3. Required agent types
        
        Query: {self._query}
        User Context: {json.dumps(self._user_context, indent=2)}
        
        Respond in JSON format:
        {{
            "intent": "...",
            "complexity": "...",
            "required_agents": ["general_medical", ...]
        }}
        """
        
        response = await self.router_llm.acomplete(analysis_prompt)
        
        try:
            return json.loads(response.text)
        except:
            return {
                "intent": "general",
                "complexity": "moderate",
                "required_agents": ["general_medical"]
            }
    
    async def _select_agents(self, analysis: Dict[str, Any]) -> List[str]:
        """Select appropriate agents based on analysis."""
        required_agents = analysis.get("required_agents", ["general_medical"])
        selected = []
        
        for agent_type in required_agents:
            # Map agent types to actual agent IDs
            if agent_type in self.agents:
                selected.append(agent_type)
            elif "general_medical" in self.agents:
                selected.append("general_medical")
        
        # Ensure at least one agent is selected
        if not selected and self.agents:
            selected.append(list(self.agents.keys())[0])
        
        logger.info(f"Selected agents: {selected}")
        return selected
    
    async def _execute_agents(self, agent_ids: List[str]) -> List[Dict[str, Any]]:
        """Execute selected agents."""
        responses = []
        
        for agent_id in agent_ids:
            if agent_id not in self.agents:
                continue
                
            agent = self.agents[agent_id]
            try:
                # Collect response from agent
                response_parts = []
                async for chunk in agent.process_query(
                    self._query, 
                    self._user_context, 
                    stream=True
                ):
                    if chunk.get("type") == "content":
                        response_parts.append(chunk.get("chunk", ""))
                
                full_response = "".join(response_parts)
                responses.append({
                    "agent_id": agent_id,
                    "response": full_response
                })
                logger.info(f"Agent {agent_id} responded")
                
            except Exception as e:
                logger.error(f"Agent {agent_id} failed: {e}")
                responses.append({
                    "agent_id": agent_id,
                    "response": f"Error: {str(e)}"
                })
        
        return responses
    
    async def _synthesize_response(self, agent_responses: List[Dict[str, Any]]) -> str:
        """Synthesize final response from agent responses."""
        if not agent_responses:
            return "I apologize, but I couldn't process your request at this time."
        
        # If only one agent responded, return its response
        if len(agent_responses) == 1:
            return agent_responses[0]["response"]
        
        # Multiple agents - synthesize
        synthesis_prompt = f"""
        Synthesize a coherent response from multiple agent consultations.
        
        Original Query: {self._query}
        
        Agent Responses:
        {json.dumps(agent_responses, indent=2)}
        
        Create a unified response that:
        1. Directly answers the user's query
        2. Integrates information from all agents
        3. Provides clear recommendations
        """
        
        response = await self.router_llm.acomplete(synthesis_prompt)
        return response.text