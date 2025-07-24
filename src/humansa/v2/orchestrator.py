"""
Main workflow orchestrator for the Humansa multi-agent system.
Manages agent coordination and workflow execution.
"""

from typing import Any, Dict, List, Optional, Set
from llama_index.core.workflow import (
    Context,
    Workflow,
    StartEvent,
    StopEvent,
    step,
)
from llama_index.core.llms import LLM
import logging

from .base_agent import HumansaBaseAgent
from .memory_manager import MemoryManager
from .context_manager import ContextManager


logger = logging.getLogger(__name__)


class AgentSelectionEvent:
    """Event for agent selection results."""
    def __init__(self, selected_agents: List[str], query: str, context: Dict[str, Any]):
        self.selected_agents = selected_agents
        self.query = query
        self.context = context


class AgentExecutionEvent:
    """Event for agent execution results."""
    def __init__(self, agent_name: str, result: Dict[str, Any], context: Dict[str, Any]):
        self.agent_name = agent_name
        self.result = result
        self.context = context


class HumansaOrchestrator(Workflow):
    """
    Main orchestrator for the Humansa multi-agent medical system.
    Coordinates multiple specialized agents using LlamaIndex workflows.
    """
    
    def __init__(
        self,
        llm: LLM,
        agents: List[HumansaBaseAgent],
        memory_manager: MemoryManager,
        context_manager: ContextManager,
        max_iterations: int = 3,
    ):
        """
        Initialize the orchestrator.
        
        Args:
            llm: Language model for orchestration decisions
            agents: List of available agents
            memory_manager: Patient memory management system
            context_manager: Unified context management
            max_iterations: Maximum workflow iterations
        """
        super().__init__()
        self.llm = llm
        self.agents = {agent.name: agent for agent in agents}
        self.memory_manager = memory_manager
        self.context_manager = context_manager
        self.max_iterations = max_iterations
        
    @step
    async def route_query(self, ctx: Context, ev: StartEvent) -> AgentSelectionEvent:
        """
        Initial step: Analyze query and select appropriate agents.
        """
        query = ev.query
        patient_id = ev.get("patient_id")
        
        # Initialize context
        context = await self.context_manager.initialize_context(
            query=query,
            patient_id=patient_id,
            initial_data=ev.get("initial_data", {})
        )
        
        # Load patient memory if available
        if patient_id:
            patient_memory = await self.memory_manager.get_patient_memory(patient_id)
            context["patient_memory"] = patient_memory
            
        # Analyze query and select agents
        selected_agents = await self._select_agents(query, context)
        
        logger.info(f"Selected agents for query: {selected_agents}")
        
        return AgentSelectionEvent(
            selected_agents=selected_agents,
            query=query,
            context=context
        )
        
    @step
    async def execute_agents(
        self,
        ctx: Context,
        ev: AgentSelectionEvent
    ) -> List[AgentExecutionEvent]:
        """
        Execute selected agents in parallel or sequence based on dependencies.
        """
        results = []
        context = ev.context
        
        # Group agents by execution order
        agent_groups = self._group_agents_by_dependencies(ev.selected_agents)
        
        for group in agent_groups:
            # Execute agents in the same group in parallel
            group_results = await self._execute_agent_group(
                agents=group,
                query=ev.query,
                context=context
            )
            
            # Update context with results
            for agent_name, result in group_results.items():
                context = await self.context_manager.update_context(
                    context=context,
                    agent_name=agent_name,
                    result=result
                )
                
                results.append(AgentExecutionEvent(
                    agent_name=agent_name,
                    result=result,
                    context=context
                ))
                
        return results
        
    @step
    async def synthesize_results(
        self,
        ctx: Context,
        events: List[AgentExecutionEvent]
    ) -> StopEvent:
        """
        Final step: Synthesize results from all agents.
        """
        if not events:
            return StopEvent(result={"error": "No agent results to synthesize"})
            
        # Get the latest context
        final_context = events[-1].context if events else {}
        
        # Collect all agent results
        agent_results = {
            event.agent_name: event.result
            for event in events
        }
        
        # Synthesize final response
        synthesis = await self._synthesize_agent_results(
            results=agent_results,
            context=final_context
        )
        
        # Update patient memory if applicable
        patient_id = final_context.get("patient_id")
        if patient_id:
            await self.memory_manager.update_patient_memory(
                patient_id=patient_id,
                interaction_data={
                    "query": final_context.get("original_query"),
                    "agent_results": agent_results,
                    "synthesis": synthesis
                }
            )
            
        return StopEvent(result={
            "synthesis": synthesis,
            "agent_results": agent_results,
            "context": final_context
        })
        
    async def _select_agents(
        self,
        query: str,
        context: Dict[str, Any]
    ) -> List[str]:
        """
        Select appropriate agents based on query and context.
        """
        # Get agent capabilities
        capabilities = {
            name: agent.get_capabilities()
            for name, agent in self.agents.items()
        }
        
        # Use LLM to select appropriate agents
        prompt = f"""
        Given the following medical query and available agents, select the most appropriate agents to handle this request.
        
        Query: {query}
        
        Available Agents:
        {capabilities}
        
        Patient Context: {context.get('patient_summary', 'No patient context available')}
        
        Return a list of agent names that should be invoked, in order of execution.
        Consider dependencies between agents.
        """
        
        # TODO: Implement proper LLM-based agent selection
        # For now, return a simple selection based on keywords
        selected = []
        query_lower = query.lower()
        
        if any(word in query_lower for word in ["diagnose", "diagnosis", "symptoms"]):
            selected.append("DiagnosisAgent")
        if any(word in query_lower for word in ["treatment", "medication", "therapy"]):
            selected.append("TreatmentAgent")
        if any(word in query_lower for word in ["research", "evidence", "studies"]):
            selected.append("ResearchAgent")
            
        return selected or ["GeneralMedicalAgent"]
        
    def _group_agents_by_dependencies(
        self,
        agent_names: List[str]
    ) -> List[List[str]]:
        """
        Group agents by execution dependencies.
        Agents in the same group can run in parallel.
        """
        # TODO: Implement dependency analysis
        # For now, execute sequentially
        return [[name] for name in agent_names]
        
    async def _execute_agent_group(
        self,
        agents: List[str],
        query: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a group of agents (potentially in parallel).
        """
        results = {}
        
        for agent_name in agents:
            if agent_name in self.agents:
                agent = self.agents[agent_name]
                try:
                    result = await agent.process(query=query, context=context)
                    results[agent_name] = result
                except Exception as e:
                    logger.error(f"Error executing agent {agent_name}: {e}")
                    results[agent_name] = {"error": str(e)}
                    
        return results
        
    async def _synthesize_agent_results(
        self,
        results: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Synthesize results from multiple agents into a coherent response.
        """
        # TODO: Implement sophisticated synthesis using LLM
        synthesis = {
            "summary": "Combined analysis from multiple medical agents",
            "key_findings": [],
            "recommendations": [],
            "confidence_level": "moderate"
        }
        
        # Extract key information from each agent
        for agent_name, result in results.items():
            if "error" not in result:
                if "findings" in result:
                    synthesis["key_findings"].extend(result["findings"])
                if "recommendations" in result:
                    synthesis["recommendations"].extend(result["recommendations"])
                    
        return synthesis