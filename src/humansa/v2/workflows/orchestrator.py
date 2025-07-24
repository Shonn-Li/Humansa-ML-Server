from typing import Dict, Any, List, Optional, AsyncIterator
from llama_index.core.workflow import (
    Workflow,
    StartEvent,
    StopEvent,
    step
)
from llama_index.core.workflow.events import Event
from llama_index.core.llms import LLM
from dataclasses import dataclass
import asyncio
import logging
from ..agents.base_agent import BaseHumansaAgent
from ..memory.memory_manager import MemoryManager

logger = logging.getLogger(__name__)


@dataclass
class QueryEvent(Event):
    """Event for processing a user query."""
    query: str
    context: Dict[str, Any]
    user_id: str


@dataclass
class AgentResponseEvent(Event):
    """Event for agent responses."""
    agent_id: str
    response: str
    confidence: float
    metadata: Dict[str, Any]


@dataclass
class MemoryUpdateEvent(Event):
    """Event for memory updates."""
    user_id: str
    update_type: str
    data: Dict[str, Any]


class HumansaOrchestrator(Workflow):
    """Main orchestrator for the Humansa multi-agent system."""
    
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
        
    @step
    async def process_query(self, ev: StartEvent) -> QueryEvent:
        """Initial step to process incoming query."""
        query = ev.get("query")
        user_id = ev.get("user_id")
        
        # Load user context from memory
        context = await self.memory_manager.get_user_context(user_id)
        
        return QueryEvent(
            query=query,
            context=context,
            user_id=user_id
        )
    
    @step
    async def route_to_agents(self, ev: QueryEvent) -> List[AgentResponseEvent]:
        """Route query to appropriate agents."""
        # Determine which agents should handle this query
        agent_scores = await self._score_agents(ev.query, ev.context)
        
        # Select agents with confidence > threshold
        selected_agents = [
            agent_id for agent_id, score in agent_scores.items()
            if score > 0.5
        ]
        
        if not selected_agents:
            # Default to general medical agent
            selected_agents = ["general_medical"]
        
        # Process query with selected agents in parallel
        tasks = []
        for agent_id in selected_agents:
            if agent_id in self.agents:
                agent = self.agents[agent_id]
                tasks.append(self._process_with_agent(agent, ev.query, ev.context))
        
        responses = await asyncio.gather(*tasks)
        return responses
    
    @step
    async def synthesize_responses(self, ev: AgentResponseEvent) -> MemoryUpdateEvent:
        """Synthesize responses from multiple agents."""
        # Collect all agent response events
        events = [ev]  # In a real implementation, you'd collect multiple events
        
        if not events:
            return StopEvent(result={"error": "No agent responses received"})
        
        # Combine agent responses
        combined_response = await self._synthesize_agent_responses(events)
        
        # Update memory with conversation
        memory_update = MemoryUpdateEvent(
            user_id=events[0].metadata.get("user_id"),
            update_type="conversation",
            data={
                "query": events[0].metadata.get("query"),
                "response": combined_response,
                "agent_ids": [e.agent_id for e in events]
            }
        )
        
        return memory_update
    
    @step
    async def update_memory(self, ev: MemoryUpdateEvent) -> StopEvent:
        """Update user memory and return final response."""
        await self.memory_manager.update_conversation(
            user_id=ev.user_id,
            query=ev.data["query"],
            response=ev.data["response"],
            metadata={"agent_ids": ev.data["agent_ids"]}
        )
        
        return StopEvent(result={
            "response": ev.data["response"],
            "agents_used": ev.data["agent_ids"]
        })
    
    async def _score_agents(self, query: str, context: Dict[str, Any]) -> Dict[str, float]:
        """Score each agent's relevance to the query."""
        scores = {}
        
        for agent_id, agent in self.agents.items():
            score = agent.should_handle_query(query, context)
            scores[agent_id] = score
            
        return scores
    
    async def _process_with_agent(
        self,
        agent: BaseHumansaAgent,
        query: str,
        context: Dict[str, Any]
    ) -> AgentResponseEvent:
        """Process query with a specific agent."""
        try:
            response_parts = []
            async for chunk in agent.process_query(query, context, stream=True):
                if chunk.get("type") == "content":
                    response_parts.append(chunk.get("chunk", ""))
            
            full_response = "".join(response_parts)
            
            return AgentResponseEvent(
                agent_id=agent.agent_id,
                response=full_response,
                confidence=1.0,
                metadata={
                    "query": query,
                    "user_id": context.get("user_id")
                }
            )
        except Exception as e:
            logger.error(f"Error processing with agent {agent.agent_id}: {e}")
            return AgentResponseEvent(
                agent_id=agent.agent_id,
                response=f"Error: {str(e)}",
                confidence=0.0,
                metadata={"error": str(e)}
            )
    
    async def _synthesize_agent_responses(self, events: List[AgentResponseEvent]) -> str:
        """Synthesize multiple agent responses into a coherent answer."""
        if len(events) == 1:
            return events[0].response
        
        # Use router LLM to synthesize multiple responses
        synthesis_prompt = self._build_synthesis_prompt(events)
        response = await self.router_llm.acomplete(synthesis_prompt)
        
        return response.text
    
    def _build_synthesis_prompt(self, events: List[AgentResponseEvent]) -> str:
        """Build prompt for synthesizing multiple agent responses."""
        prompt = "Synthesize the following expert responses into a coherent medical consultation response:\n\n"
        
        for event in events:
            agent = self.agents.get(event.agent_id)
            agent_name = agent.agent_name if agent else event.agent_id
            prompt += f"**{agent_name}**: {event.response}\n\n"
        
        prompt += "Provide a unified response that combines the key insights from all agents."
        
        return prompt