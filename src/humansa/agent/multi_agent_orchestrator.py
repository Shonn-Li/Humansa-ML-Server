"""
Multi-Agent Orchestrator for Humansa V1
Enhances the V1 agent with multi-agent capabilities while maintaining tool compatibility
"""

import logging
from typing import Dict, Any, List, Optional
import json
from ..v2.agents import (
    GeneralMedicalAgent,
    DiagnosisAgent,
    MedicationAgent,
    EmergencyTriageAgent,
    AppointmentAgent
)
from llama_index.core.llms import LLM

logger = logging.getLogger(__name__)


class MultiAgentOrchestrator:
    """
    Orchestrates multiple specialized agents for Humansa V1.
    Maintains compatibility with existing tool-calling interface.
    """
    
    def __init__(self, llm: LLM, tools: List[Any], memory_manager=None):
        """Initialize orchestrator with agents."""
        self.llm = llm
        self.tools = tools
        self.memory_manager = memory_manager
        
        # Initialize specialized agents
        self.agents = {
            "general_medical": GeneralMedicalAgent(llm=llm),
            "diagnosis": DiagnosisAgent(llm=llm),
            "medication": MedicationAgent(llm=llm),
            "emergency_triage": EmergencyTriageAgent(llm=llm),
            "appointment": AppointmentAgent(llm=llm)
        }
        
        # Map tools to agent capabilities
        self.tool_to_agent_map = {
            "find_doctor_info": ["appointment", "general_medical"],
            "find_doctor_availability": ["appointment"],
            "book_appointment": ["appointment"],
            "book_appointment_confirmation": ["appointment"],
            "prepare_booking_confirmation": ["appointment"],
            "search_clinics": ["general_medical", "appointment"],
            "get_pricing": ["general_medical"],
            "recommend_product": ["general_medical", "medication"],
            "place_call": ["emergency_triage"],
            "search_web": ["general_medical"]
        }
        
        logger.info(f"🎭 Multi-Agent Orchestrator initialized with {len(self.agents)} agents")
    
    async def analyze_query(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze query to determine intent and required agents."""
        analysis_prompt = f"""
        Analyze this medical query and determine:
        1. Primary intent (appointment, diagnosis, medication, emergency, general)
        2. Required tool types
        3. Urgency level
        
        Query: {query}
        Context: {json.dumps(context, ensure_ascii=False)}
        
        Respond in JSON format:
        {{
            "intent": "...",
            "urgency": "normal|urgent|emergency",
            "required_tools": ["tool1", "tool2"],
            "recommended_agents": ["agent1", "agent2"]
        }}
        """
        
        try:
            response = await self.llm.acomplete(analysis_prompt)
            analysis = json.loads(response.text)
            
            # If emergency detected, prioritize emergency agent
            if analysis.get("urgency") == "emergency" or "胸痛" in query or "呼吸困难" in query:
                analysis["recommended_agents"] = ["emergency_triage"]
                analysis["urgency"] = "emergency"
            
            return analysis
        except Exception as e:
            logger.warning(f"Query analysis failed: {e}")
            return {
                "intent": "general",
                "urgency": "normal",
                "required_tools": [],
                "recommended_agents": ["general_medical"]
            }
    
    async def route_to_agents(self, query: str, analysis: Dict[str, Any], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Route query to appropriate agents and collect responses."""
        agent_responses = []
        recommended_agents = analysis.get("recommended_agents", ["general_medical"])
        
        for agent_name in recommended_agents:
            if agent_name not in self.agents:
                continue
                
            agent = self.agents[agent_name]
            try:
                # Process through specialized agent
                response_parts = []
                async for chunk in agent.process_query(query, context, stream=True):
                    if chunk.get("type") == "content":
                        response_parts.append(chunk.get("chunk", ""))
                
                full_response = "".join(response_parts)
                
                # Extract any tool recommendations from agent response
                tool_recommendations = self._extract_tool_recommendations(full_response, agent_name)
                
                agent_responses.append({
                    "agent": agent_name,
                    "response": full_response,
                    "tool_recommendations": tool_recommendations
                })
                
                logger.info(f"✅ Agent {agent_name} provided response with {len(tool_recommendations)} tool recommendations")
                
            except Exception as e:
                logger.error(f"Agent {agent_name} failed: {e}")
                agent_responses.append({
                    "agent": agent_name,
                    "response": f"Error: {str(e)}",
                    "tool_recommendations": []
                })
        
        return agent_responses
    
    def _extract_tool_recommendations(self, response: str, agent_name: str) -> List[Dict[str, Any]]:
        """Extract tool recommendations from agent response."""
        recommendations = []
        
        # Map agent specialties to likely tools
        if agent_name == "appointment":
            if "医生" in response or "预约" in response:
                recommendations.append({
                    "tool": "find_doctor_info",
                    "reason": "User needs doctor information"
                })
            if "时间" in response or "排班" in response:
                recommendations.append({
                    "tool": "find_doctor_availability",
                    "reason": "User asking about availability"
                })
        elif agent_name == "emergency_triage":
            if "紧急" in response or "急诊" in response:
                recommendations.append({
                    "tool": "place_call",
                    "reason": "Emergency situation detected"
                })
        
        return recommendations
    
    async def synthesize_for_tools(self, query: str, agent_responses: List[Dict[str, Any]], available_tools: List[str]) -> Dict[str, Any]:
        """
        Synthesize agent responses into tool-calling recommendations.
        This maintains compatibility with V1's tool-calling interface.
        """
        # Collect all tool recommendations
        all_recommendations = []
        for response in agent_responses:
            all_recommendations.extend(response.get("tool_recommendations", []))
        
        # Build synthesis that guides tool selection
        synthesis_prompt = f"""
        Based on the analysis from specialized agents, synthesize a response that:
        1. Identifies which tools should be called
        2. Provides reasoning for tool selection
        3. Maintains Humansa's medical expertise
        
        Query: {query}
        
        Agent Analyses:
        {json.dumps(agent_responses, ensure_ascii=False, indent=2)}
        
        Available Tools: {available_tools}
        
        Provide a response that guides the ReAct agent to call appropriate tools.
        Focus on the user's specific needs.
        """
        
        response = await self.llm.acomplete(synthesis_prompt)
        
        return {
            "synthesis": response.text,
            "recommended_tools": [r["tool"] for r in all_recommendations],
            "agent_responses": agent_responses
        }
    
    async def enhance_with_memory(self, query: str, user_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance context with memory if available."""
        if self.memory_manager:
            try:
                # Get user memories
                memories = await self.memory_manager.get_user_context(user_id)
                context["user_memories"] = memories
                
                # Search for relevant memories
                relevant = await self.memory_manager.search_memories(
                    user_id=user_id,
                    query=query,
                    limit=5
                )
                context["relevant_memories"] = relevant
                
                logger.info(f"📚 Enhanced context with {len(memories)} memories")
            except Exception as e:
                logger.warning(f"Memory enhancement failed: {e}")
        
        return context