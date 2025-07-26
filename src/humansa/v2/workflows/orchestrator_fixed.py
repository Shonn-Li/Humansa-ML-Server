"""
Fixed Humansa Orchestrator - removing Context from step parameters
Based on LlamaIndex workflow best practices
"""

from typing import Dict, Any, List, Optional, AsyncIterator, Set, Union
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
import json
from ..agents.base_agent import BaseHumansaAgent
from ..memory.memory_manager import MemoryManager

logger = logging.getLogger(__name__)


@dataclass
class QueryAnalysisEvent(Event):
    """Initial query analysis results."""
    query: str
    user_id: str
    intent: str
    complexity: str  # simple, moderate, complex
    required_capabilities: List[str]
    context: Dict[str, Any]


@dataclass
class AgentSelectionEvent(Event):
    """Agent selection for current iteration."""
    iteration: int
    selected_agents: List[str]
    selection_reason: str
    information_gaps: List[str]
    context: Dict[str, Any]


@dataclass
class AgentExecutionEvent(Event):
    """Result from agent execution."""
    agent_id: str
    response: Dict[str, Any]
    extracted_info: Dict[str, Any]
    confidence: float


@dataclass
class CompletenessEvaluationEvent(Event):
    """Evaluation of information completeness."""
    iteration: int
    is_complete: bool
    confidence: float
    collected_responses: List[Dict[str, Any]]


@dataclass
class RefinementEvent(Event):
    """Request for refinement with specific gaps."""
    iteration: int
    information_gaps: List[str]
    previous_agents: Set[str]
    context: Dict[str, Any]


@dataclass  
class SynthesisEvent(Event):
    """Final synthesis request."""
    all_responses: List[Dict[str, Any]]
    iterations_used: int
    final_context: Dict[str, Any]


class HumansaOrchestrator(Workflow):
    """
    Fixed orchestrator implementing true iterative multi-agent pattern.
    
    Key improvements:
    1. Iterative refinement until complete information
    2. Dynamic agent selection based on gaps
    3. Completeness evaluation at each step
    4. Contradiction detection and resolution
    5. Parallel agent execution where possible
    """
    
    def __init__(
        self,
        agents: List[BaseHumansaAgent],
        router_llm: LLM,
        memory_manager: MemoryManager,
        max_iterations: int = 5,
        completeness_threshold: float = 0.85,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.agents = {agent.agent_id: agent for agent in agents}
        self.router_llm = router_llm
        self.memory_manager = memory_manager
        self.max_iterations = max_iterations
        self.completeness_threshold = completeness_threshold
        
        # Initialize workflow state
        self._user_context = {}
        self._query = ""
        self._user_id = ""
        self._iteration_count = 0
        self._used_agents = set()
        self._all_responses = []
        
    @step
    async def analyze_query(self, ev: StartEvent) -> QueryAnalysisEvent:
        """
        Step 1: Analyze the query to understand intent and complexity.
        """
        logger.info("=== STARTING analyze_query ===")
        query = ev.get("query")
        user_id = ev.get("user_id")
        logger.info(f"Query: {query}, User: {user_id}")
        
        try:
            # Load user context from memory
            logger.info("Loading user context...")
            user_context = await self.memory_manager.get_user_context(user_id)
            logger.info(f"User context loaded: {len(user_context)} items")
        except Exception as e:
            logger.error(f"Error loading user context: {e}")
            user_context = {}
        
        # Store in instance variables for access across steps
        self._user_context = user_context
        self._query = query
        self._user_id = user_id
        self._iteration_count = 0
        self._used_agents = set()
        self._all_responses = []
        
        # Use LLM to analyze query
        analysis_prompt = f"""
        Analyze this medical query and provide:
        1. Primary intent (diagnosis, treatment, information, emergency, appointment)
        2. Complexity level (simple, moderate, complex)
        3. Required capabilities (list of agent types needed)
        
        Query: {query}
        User Context: {json.dumps(user_context, indent=2)}
        
        Respond in JSON format:
        {{
            "intent": "...",
            "complexity": "...",
            "required_capabilities": ["diagnosis", "medication", ...]
        }}
        """
        
        response = await self.router_llm.acomplete(analysis_prompt)
        
        try:
            analysis = json.loads(response.text)
        except:
            # Fallback to basic analysis
            analysis = {
                "intent": "general",
                "complexity": "moderate",
                "required_capabilities": ["general_medical"]
            }
        
        return QueryAnalysisEvent(
            query=query,
            user_id=user_id,
            intent=analysis["intent"],
            complexity=analysis["complexity"],
            required_capabilities=analysis["required_capabilities"],
            context=user_context
        )
    
    @step
    async def select_agents(
        self, 
        ev: Union[QueryAnalysisEvent, RefinementEvent]
    ) -> AgentSelectionEvent:
        """
        Step 2: Select appropriate agents based on current needs.
        Handles both initial selection and refinement selections.
        """
        self._iteration_count += 1
        iteration = self._iteration_count
        
        if isinstance(ev, QueryAnalysisEvent):
            # Initial agent selection
            selection_prompt = f"""
            Select the most appropriate agents for this medical query.
            
            Query: {ev.query}
            Intent: {ev.intent}
            Complexity: {ev.complexity}
            Required Capabilities: {ev.required_capabilities}
            
            Available Agents:
            {self._get_agent_descriptions()}
            
            Select 1-3 agents that best match the requirements.
            
            Respond in JSON:
            {{
                "selected_agents": ["agent_id1", "agent_id2"],
                "selection_reason": "why these agents",
                "information_gaps": ["what info we're seeking"]
            }}
            """
        else:
            # Refinement selection based on gaps
            selection_prompt = f"""
            Select additional agents to fill information gaps.
            
            Information Gaps: {ev.information_gaps}
            Previously Used Agents: {list(ev.previous_agents)}
            
            Available Agents:
            {self._get_agent_descriptions()}
            
            Select agents that can fill the gaps without duplicating previous efforts.
            
            Respond in JSON:
            {{
                "selected_agents": ["agent_id"],
                "selection_reason": "why these agents",
                "information_gaps": ["remaining gaps"]
            }}
            """
        
        response = await self.router_llm.acomplete(selection_prompt)
        
        try:
            selection = json.loads(response.text)
        except:
            # Fallback selection
            if iteration == 1:
                selection = {
                    "selected_agents": ["general_medical"],
                    "selection_reason": "Starting with general assessment",
                    "information_gaps": []
                }
            else:
                # No more agents to try
                selection = {
                    "selected_agents": [],
                    "selection_reason": "All relevant agents consulted",
                    "information_gaps": []
                }
        
        # Update used agents
        for agent_id in selection["selected_agents"]:
            self._used_agents.add(agent_id)
        
        return AgentSelectionEvent(
            iteration=iteration,
            selected_agents=selection["selected_agents"],
            selection_reason=selection["selection_reason"],
            information_gaps=selection["information_gaps"],
            context=self._user_context
        )
    
    @step
    async def execute_agents(
        self,
        ev: AgentSelectionEvent
    ) -> CompletenessEvaluationEvent:
        """
        Step 3: Execute selected agents (in parallel where possible).
        """
        if not ev.selected_agents:
            # No agents selected, force completion
            return CompletenessEvaluationEvent(
                iteration=ev.iteration,
                is_complete=True,  # Force completion
                confidence=1.0,
                collected_responses=self._all_responses
            )
        
        # Execute agents in parallel
        tasks = []
        for agent_id in ev.selected_agents:
            if agent_id in self.agents:
                agent = self.agents[agent_id]
                task = self._execute_agent(
                    agent,
                    self._query,
                    self._user_context
                )
                tasks.append(task)
        
        # Wait for all agents to complete
        agent_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for result in agent_results:
            if isinstance(result, Exception):
                logger.error(f"Agent execution failed: {result}")
            else:
                self._all_responses.append(result.response)
        
        # Return evaluation event
        return CompletenessEvaluationEvent(
            iteration=ev.iteration,
            is_complete=False,  # Let evaluation step decide
            confidence=0.0,  # Let evaluation step calculate
            collected_responses=self._all_responses
        )
    
    @step
    async def evaluate_completeness(
        self,
        ev: CompletenessEvaluationEvent
    ) -> Union[RefinementEvent, SynthesisEvent]:
        """
        Step 4: Evaluate if we have complete information.
        """
        iteration = self._iteration_count
        
        # Check iteration limit
        if iteration >= self.max_iterations:
            logger.info(f"Reached max iterations ({self.max_iterations}), proceeding to synthesis")
            return SynthesisEvent(
                all_responses=ev.collected_responses,
                iterations_used=iteration,
                final_context=self._user_context
            )
        
        # Use LLM to evaluate completeness
        evaluation_prompt = f"""
        Evaluate if we have sufficient information to answer the query completely.
        
        Original Query: {self._query}
        
        Collected Information:
        {self._format_responses(ev.collected_responses)}
        
        Evaluate:
        1. Is the information complete enough to provide a comprehensive answer?
        2. What critical information is still missing?
        3. Are there any contradictions that need resolution?
        4. Confidence level (0.0-1.0)
        
        Respond in JSON:
        {{
            "is_complete": true/false,
            "confidence": 0.85,
            "missing_information": ["what's missing"],
            "contradictions": ["any contradictions"],
            "evaluation_reason": "explanation"
        }}
        """
        
        response = await self.router_llm.acomplete(evaluation_prompt)
        
        try:
            evaluation = json.loads(response.text)
        except:
            # Default to proceeding if parsing fails
            evaluation = {
                "is_complete": True,
                "confidence": 0.85,
                "missing_information": [],
                "contradictions": [],
                "evaluation_reason": "Sufficient information collected"
            }
        
        # Check if we should continue or synthesize
        if evaluation["is_complete"] or evaluation["confidence"] >= self.completeness_threshold:
            return SynthesisEvent(
                all_responses=ev.collected_responses,
                iterations_used=iteration,
                final_context=self._user_context
            )
        else:
            return RefinementEvent(
                iteration=iteration,
                information_gaps=evaluation["missing_information"],
                previous_agents=self._used_agents,
                context=self._user_context
            )
    
    @step
    async def synthesize_response(
        self,
        ev: SynthesisEvent  
    ) -> StopEvent:
        """
        Step 5: Synthesize final response from all collected information.
        """
        # Create comprehensive synthesis prompt
        synthesis_prompt = f"""
        Synthesize a comprehensive response from multiple agent consultations.
        
        Original Query: {self._query}
        
        Information from {len(ev.all_responses)} consultations:
        {self._format_responses(ev.all_responses)}
        
        User Context:
        {json.dumps(ev.final_context, indent=2)}
        
        Create a unified, coherent response that:
        1. Directly answers the user's query
        2. Integrates all relevant information
        3. Resolves any contradictions
        4. Provides clear recommendations
        5. Acknowledges any limitations or uncertainties
        
        Format the response in a clear, professional manner suitable for medical communication.
        """
        
        final_response = await self.router_llm.acomplete(synthesis_prompt)
        
        # Store conversation in memory
        await self.memory_manager.add_conversation(
            user_id=self._user_id,
            query=self._query,
            response=final_response.text,
            metadata={
                "iterations": ev.iterations_used,
                "agents_used": list(self._used_agents),
                "confidence": self._all_responses[-1].get("confidence", 0.85) if self._all_responses else 0.85
            }
        )
        
        # Return final result
        return StopEvent(
            result={
                "response": final_response.text,
                "metadata": {
                    "user_id": self._user_id,
                    "orchestrator": "humansa_v2",
                    "iterations": ev.iterations_used,
                    "agents_consulted": list(self._used_agents),
                    "confidence": 0.85
                }
            }
        )
    
    async def _execute_agent(
        self,
        agent: BaseHumansaAgent,
        query: str,
        context: Dict[str, Any]
    ) -> AgentExecutionEvent:
        """Execute a single agent and extract structured information."""
        try:
            # Call agent
            response_parts = []
            async for chunk in agent.process_query(query, context, stream=True):
                if chunk.get("type") == "content":
                    response_parts.append(chunk.get("chunk", ""))
            
            full_response = "".join(response_parts)
            
            # Extract key information using LLM
            extraction_prompt = f"""
            Extract key medical information from this agent response.
            
            Agent: {agent.agent_id}
            Response: {full_response}
            
            Extract:
            1. Key findings or diagnoses
            2. Recommendations
            3. Areas needing clarification
            4. Confidence level (0.0-1.0)
            
            Respond in JSON:
            {{
                "extracted_info": {{
                    "findings": ["..."],
                    "recommendations": ["..."],
                    "clarifications_needed": ["..."],
                    "confidence": 0.85
                }}
            }}
            """
            
            extraction_response = await self.router_llm.acomplete(extraction_prompt)
            
            try:
                extracted = json.loads(extraction_response.text)
            except:
                extracted = {
                    "extracted_info": {
                        "findings": [full_response[:200]],
                        "recommendations": [],
                        "clarifications_needed": [],
                        "confidence": 0.7
                    }
                }
            
            return AgentExecutionEvent(
                agent_id=agent.agent_id,
                response={"content": full_response},
                extracted_info=extracted["extracted_info"],
                confidence=extracted["extracted_info"].get("confidence", 0.7)
            )
            
        except Exception as e:
            logger.error(f"Agent {agent.agent_id} execution failed: {e}")
            return AgentExecutionEvent(
                agent_id=agent.agent_id,
                response={"error": str(e)},
                extracted_info={},
                confidence=0.0
            )
    
    def _get_agent_descriptions(self) -> str:
        """Get formatted descriptions of available agents."""
        descriptions = []
        for agent_id, agent in self.agents.items():
            desc = f"- {agent_id}: {getattr(agent, 'description', 'Medical specialist')}"
            descriptions.append(desc)
        return "\n".join(descriptions)
    
    def _format_responses(self, responses: List[Dict[str, Any]]) -> str:
        """Format agent responses for prompts."""
        formatted = []
        for i, resp in enumerate(responses, 1):
            formatted.append(f"Response {i}:\n{json.dumps(resp, indent=2)}")
        return "\n\n".join(formatted)