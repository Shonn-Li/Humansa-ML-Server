"""
Improved Humansa Orchestrator with Iterative Multi-Agent Pattern
Based on LlamaIndex workflow best practices
"""

from typing import Dict, Any, List, Optional, AsyncIterator, Set, Union
from llama_index.core.workflow import (
    Workflow,
    StartEvent,
    StopEvent,
    step,
    Context
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
    response: str
    confidence: float
    extracted_info: Dict[str, Any]
    needs_clarification: List[str]
    metadata: Dict[str, Any]


@dataclass
class CompletenessEvaluationEvent(Event):
    """Evaluation of response completeness."""
    iteration: int
    is_complete: bool
    confidence: float
    missing_information: List[str]
    contradictions: List[str]
    collected_responses: List[AgentExecutionEvent]


@dataclass
class RefinementEvent(Event):
    """Request for additional information."""
    iteration: int
    gaps_to_fill: List[str]
    previous_agents: Set[str]
    context: Dict[str, Any]


@dataclass
class SynthesisEvent(Event):
    """Final synthesis request."""
    all_responses: List[AgentExecutionEvent]
    iterations_used: int
    final_context: Dict[str, Any]


class ImprovedHumansaOrchestrator(Workflow):
    """
    Improved orchestrator implementing true iterative multi-agent pattern.
    
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
        
    @step
    async def analyze_query(self, ctx: Context, ev: StartEvent) -> QueryAnalysisEvent:
        """
        Step 1: Analyze the query to understand intent and complexity.
        """
        query = ev.get("query")
        user_id = ev.get("user_id")
        
        # Load user context from memory
        user_context = await self.memory_manager.get_user_context(user_id)
        
        # Store in workflow context for access across steps
        ctx.set("user_context", user_context)
        ctx.set("query", query)
        ctx.set("user_id", user_id)
        ctx.set("iteration_count", 0)
        ctx.set("used_agents", set())
        ctx.set("all_responses", [])
        
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
        ctx: Context, 
        ev: Union[QueryAnalysisEvent, RefinementEvent]
    ) -> AgentSelectionEvent:
        """
        Step 2: Select appropriate agents based on current needs.
        Handles both initial selection and refinement selections.
        """
        iteration = ctx.get("iteration_count", 0) + 1
        ctx.set("iteration_count", iteration)
        
        used_agents = ctx.get("used_agents", set())
        all_responses = ctx.get("all_responses", [])
        
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
            Consider which agents can work in parallel vs sequentially.
            
            Respond in JSON:
            {{
                "selected_agents": ["agent_id1", "agent_id2"],
                "selection_reason": "...",
                "information_gaps": ["what we need to know"]
            }}
            """
        else:  # RefinementEvent
            # Select additional agents to fill gaps
            selection_prompt = f"""
            We need additional information to complete the response.
            
            Information gaps: {ev.gaps_to_fill}
            Previously used agents: {list(ev.previous_agents)}
            
            Available Agents:
            {self._get_agent_descriptions()}
            
            Select agents that can provide the missing information.
            Avoid agents already used unless they can provide new insights.
            
            Respond in JSON:
            {{
                "selected_agents": ["agent_id1", "agent_id2"],
                "selection_reason": "...",
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
            used_agents.add(agent_id)
        ctx.set("used_agents", used_agents)
        
        return AgentSelectionEvent(
            iteration=iteration,
            selected_agents=selection["selected_agents"],
            selection_reason=selection["selection_reason"],
            information_gaps=selection["information_gaps"],
            context=ctx.get("user_context", {})
        )
    
    @step
    async def execute_agents(
        self,
        ctx: Context,
        ev: AgentSelectionEvent
    ) -> List[AgentExecutionEvent]:
        """
        Step 3: Execute selected agents (in parallel where possible).
        """
        if not ev.selected_agents:
            # No agents selected, trigger evaluation
            await ctx.send_event(CompletenessEvaluationEvent(
                iteration=ev.iteration,
                is_complete=True,  # Force completion
                confidence=1.0,
                missing_information=[],
                contradictions=[],
                collected_responses=ctx.get("all_responses", [])
            ))
            return []
        
        # Execute agents in parallel
        tasks = []
        for agent_id in ev.selected_agents:
            if agent_id in self.agents:
                agent = self.agents[agent_id]
                task = self._execute_single_agent(
                    agent,
                    ctx.get("query"),
                    ev.context
                )
                tasks.append(task)
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process responses
        execution_events = []
        for i, response in enumerate(responses):
            if isinstance(response, Exception):
                logger.error(f"Agent execution failed: {response}")
                continue
            
            execution_events.append(response)
            
        # Store responses in context
        all_responses = ctx.get("all_responses", [])
        all_responses.extend(execution_events)
        ctx.set("all_responses", all_responses)
        
        # Send each event separately for proper workflow handling
        for event in execution_events:
            await ctx.send_event(event)
        
        # Trigger evaluation after all agents complete
        if execution_events:
            await ctx.send_event(CompletenessEvaluationEvent(
                iteration=ev.iteration,
                is_complete=False,  # To be determined
                confidence=0.0,
                missing_information=[],
                contradictions=[],
                collected_responses=all_responses
            ))
        
        return execution_events
    
    @step
    async def evaluate_completeness(
        self,
        ctx: Context,
        ev: CompletenessEvaluationEvent
    ) -> Union[RefinementEvent, SynthesisEvent]:
        """
        Step 4: Evaluate if we have complete information.
        """
        iteration = ctx.get("iteration_count", 0)
        
        # Check iteration limit
        if iteration >= self.max_iterations:
            logger.info(f"Reached max iterations ({self.max_iterations}), proceeding to synthesis")
            return SynthesisEvent(
                all_responses=ev.collected_responses,
                iterations_used=iteration,
                final_context=ctx.get("user_context", {})
            )
        
        # Use LLM to evaluate completeness
        evaluation_prompt = f"""
        Evaluate if we have sufficient information to answer the query completely.
        
        Original Query: {ctx.get("query")}
        
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
                "confidence": 0.7,
                "missing_information": [],
                "contradictions": []
            }
        
        # Check if we should continue or synthesize
        if evaluation["is_complete"] or evaluation["confidence"] >= self.completeness_threshold:
            return SynthesisEvent(
                all_responses=ev.collected_responses,
                iterations_used=iteration,
                final_context=ctx.get("user_context", {})
            )
        else:
            # Need more information
            return RefinementEvent(
                iteration=iteration,
                gaps_to_fill=evaluation["missing_information"],
                previous_agents=ctx.get("used_agents", set()),
                context=ctx.get("user_context", {})
            )
    
    @step
    async def synthesize_response(
        self,
        ctx: Context,
        ev: SynthesisEvent
    ) -> StopEvent:
        """
        Step 5: Synthesize all agent responses into final answer.
        """
        # Build comprehensive synthesis prompt
        synthesis_prompt = f"""
        Synthesize all expert responses into a comprehensive medical consultation response.
        
        Original Query: {ctx.get("query")}
        Iterations Used: {ev.iterations_used}
        
        Expert Responses:
        {self._format_responses(ev.all_responses)}
        
        Patient Context:
        {json.dumps(ev.final_context, indent=2)}
        
        Create a unified, coherent response that:
        1. Addresses all aspects of the query
        2. Integrates insights from all agents
        3. Resolves any contradictions
        4. Provides clear, actionable advice
        5. Acknowledges any limitations or areas needing follow-up
        """
        
        response = await self.router_llm.acomplete(synthesis_prompt)
        final_response = response.text
        
        # Update memory with the conversation
        user_id = ctx.get("user_id")
        await self.memory_manager.update_conversation(
            user_id=user_id,
            query=ctx.get("query"),
            response=final_response,
            metadata={
                "iterations": ev.iterations_used,
                "agents_used": list(ctx.get("used_agents", set())),
                "confidence": ctx.get("final_confidence", 0.85)
            }
        )
        
        # Return final result
        return StopEvent(result={
            "response": final_response,
            "metadata": {
                "iterations": ev.iterations_used,
                "agents_consulted": list(ctx.get("used_agents", set())),
                "total_responses": len(ev.all_responses)
            }
        })
    
    async def _execute_single_agent(
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
                    "medications": ["..."],
                    "warnings": ["..."]
                }},
                "needs_clarification": ["..."],
                "confidence": 0.8
            }}
            """
            
            extraction_response = await self.router_llm.acomplete(extraction_prompt)
            
            try:
                extraction = json.loads(extraction_response.text)
            except:
                extraction = {
                    "extracted_info": {},
                    "needs_clarification": [],
                    "confidence": 0.7
                }
            
            return AgentExecutionEvent(
                agent_id=agent.agent_id,
                response=full_response,
                confidence=extraction.get("confidence", 0.7),
                extracted_info=extraction.get("extracted_info", {}),
                needs_clarification=extraction.get("needs_clarification", []),
                metadata={"agent_name": getattr(agent, "agent_name", agent.agent_id)}
            )
            
        except Exception as e:
            logger.error(f"Error executing agent {agent.agent_id}: {e}")
            return AgentExecutionEvent(
                agent_id=agent.agent_id,
                response=f"Error: {str(e)}",
                confidence=0.0,
                extracted_info={},
                needs_clarification=[],
                metadata={"error": str(e)}
            )
    
    def _get_agent_descriptions(self) -> str:
        """Get formatted descriptions of available agents."""
        descriptions = []
        for agent_id, agent in self.agents.items():
            desc = f"- {agent_id}: {getattr(agent, 'description', 'Medical expert agent')}"
            descriptions.append(desc)
        return "\n".join(descriptions)
    
    def _format_responses(self, responses: List[AgentExecutionEvent]) -> str:
        """Format agent responses for LLM consumption."""
        formatted = []
        for resp in responses:
            formatted.append(f"""
Agent: {resp.metadata.get('agent_name', resp.agent_id)}
Response: {resp.response}
Confidence: {resp.confidence}
Key Info: {json.dumps(resp.extracted_info, indent=2)}
Needs Clarification: {resp.needs_clarification}
---""")
        return "\n".join(formatted)