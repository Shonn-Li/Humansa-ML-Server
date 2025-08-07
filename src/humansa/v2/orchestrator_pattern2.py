"""
HUMANSA V2 Orchestrator - LlamaIndex Pattern 2 Implementation
Uses FunctionAgent with sub-agents as tools and shared Context
Provides full reasoning visibility and state management
"""

import logging
import json
import asyncio
from typing import Dict, Any, Optional, List, AsyncGenerator
from datetime import datetime
from dataclasses import dataclass, field

from llama_index.core.agent.workflow import FunctionAgent
from llama_index.core.workflow import Context
from llama_index.core.llms import LLM
from llama_index.core.callbacks import CallbackManager

from .context_manager import UnifiedContext, ContextManager
from .memory.memory_manager import MemoryManager

logger = logging.getLogger(__name__)


@dataclass
class WorkflowState:
    """State that persists across agent tool calls"""
    # Workflow metadata
    workflow_id: str = ""
    conversation_id: str = ""
    user_id: str = ""
    start_time: datetime = field(default_factory=datetime.now)
    
    # Patient context (loaded from memory)
    patient_profile: Dict[str, Any] = field(default_factory=dict)
    medical_history: List[Dict[str, Any]] = field(default_factory=list)
    current_medications: List[Dict[str, Any]] = field(default_factory=list)
    allergies: List[str] = field(default_factory=list)
    appointment_preferences: Dict[str, Any] = field(default_factory=dict)
    
    # Workflow execution state
    research_notes: List[Dict[str, Any]] = field(default_factory=list)
    diagnosis_findings: List[Dict[str, Any]] = field(default_factory=list)
    product_recommendations: List[Dict[str, Any]] = field(default_factory=list)
    appointment_options: List[Dict[str, Any]] = field(default_factory=list)
    medication_checks: List[Dict[str, Any]] = field(default_factory=list)
    
    # Agent coordination
    agents_called: List[str] = field(default_factory=list)
    agent_outputs: Dict[str, Any] = field(default_factory=dict)
    reasoning_chain: List[str] = field(default_factory=list)
    
    # Final outputs
    final_recommendations: Dict[str, Any] = field(default_factory=dict)
    follow_up_actions: List[str] = field(default_factory=list)
    emergency_flags: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "workflow_id": self.workflow_id,
            "conversation_id": self.conversation_id,
            "user_id": self.user_id,
            "start_time": self.start_time.isoformat(),
            "patient_profile": self.patient_profile,
            "medical_history": self.medical_history,
            "current_medications": self.current_medications,
            "allergies": self.allergies,
            "appointment_preferences": self.appointment_preferences,
            "research_notes": self.research_notes,
            "diagnosis_findings": self.diagnosis_findings,
            "product_recommendations": self.product_recommendations,
            "appointment_options": self.appointment_options,
            "medication_checks": self.medication_checks,
            "agents_called": self.agents_called,
            "agent_outputs": self.agent_outputs,
            "reasoning_chain": self.reasoning_chain,
            "final_recommendations": self.final_recommendations,
            "follow_up_actions": self.follow_up_actions,
            "emergency_flags": self.emergency_flags
        }


class HumansaOrchestratorPattern2:
    """
    LlamaIndex Pattern 2 Orchestrator for HUMANSA V2
    Sub-agents are exposed as tools with shared workflow context
    """
    
    def __init__(
        self,
        llm: LLM,
        agents: Dict[str, Any],
        memory_manager: Optional[MemoryManager] = None,
        context_manager: Optional[ContextManager] = None,
        callback_manager: Optional[CallbackManager] = None,
        debug: bool = False
    ):
        self.llm = llm
        self.agents = agents
        self.memory_manager = memory_manager
        self.context_manager = context_manager or ContextManager()
        self.callback_manager = callback_manager
        self.debug = debug
        
        # Create orchestrator tools from sub-agents
        self.orchestrator_tools = self._create_agent_tools()
        
        # Initialize FunctionAgent orchestrator
        self.orchestrator = FunctionAgent(
            name="HumansaV2Orchestrator",
            description="Main orchestrator for HUMANSA medical consultation system",
            system_prompt=self._get_orchestrator_prompt(),
            llm=self.llm,
            tools=self.orchestrator_tools,
            callback_manager=self.callback_manager,
            initial_state=WorkflowState().to_dict(),
            verbose=debug
        )
        
        logger.info(f"✅ Initialized Pattern 2 Orchestrator with {len(self.orchestrator_tools)} agent tools")
    
    def _create_agent_tools(self) -> List[Any]:
        """Create tools from sub-agents that use shared context"""
        tools = []
        
        # Product Agent Tool
        async def call_product_agent(ctx: Context, query: str) -> str:
            """Search and recommend health products based on symptoms or needs"""
            logger.info(f"🛍️ ProductAgent called with: {query}")
            
            # Record agent call
            async with ctx.store.edit_state() as state:
                state["agents_called"].append("ProductAgent")
                state["reasoning_chain"].append(f"Searching for products related to: {query}")
            
            # Get patient context
            async with ctx.store.get_state() as state:
                patient_profile = state.get("patient_profile", {})
                allergies = state.get("allergies", [])
            
            # Check if agent exists
            if agent := self.agents.get("ProductAgent"):
                try:
                    # Run the agent
                    result_parts = []
                    async for chunk in agent.process_query(
                        query=query,
                        context={
                            "patient_profile": patient_profile,
                            "allergies": allergies
                        },
                        stream=True
                    ):
                        if chunk.get('type') == 'content' and chunk.get('chunk'):
                            result_parts.append(chunk['chunk'])
                    
                    result = ''.join(result_parts)
                    
                    # Store product recommendations
                    async with ctx.store.edit_state() as state:
                        state["product_recommendations"].append({
                            "query": query,
                            "results": result,
                            "timestamp": datetime.now().isoformat()
                        })
                        state["agent_outputs"]["ProductAgent"] = result
                    
                    return result
                    
                except Exception as e:
                    logger.error(f"ProductAgent error: {e}")
                    return f"产品搜索时出现错误: {str(e)}"
            else:
                return "产品推荐服务暂时不可用"
        
        # Appointment Agent Tool
        async def call_appointment_agent(ctx: Context, request: str) -> str:
            """Book or manage medical appointments"""
            logger.info(f"📅 AppointmentAgent called with: {request}")
            
            # Record agent call
            async with ctx.store.edit_state() as state:
                state["agents_called"].append("AppointmentAgent")
                state["reasoning_chain"].append(f"Processing appointment request: {request}")
            
            # Get context
            async with ctx.store.get_state() as state:
                patient_profile = state.get("patient_profile", {})
                preferences = state.get("appointment_preferences", {})
                diagnosis = state.get("diagnosis_findings", [])
            
            if agent := self.agents.get("AppointmentAgent"):
                try:
                    # Enhance request with diagnosis if available
                    enhanced_request = request
                    if diagnosis:
                        latest_diagnosis = diagnosis[-1]
                        if dept := latest_diagnosis.get("recommended_department"):
                            enhanced_request = f"{request} (建议科室: {dept})"
                    
                    # Run the agent
                    result_parts = []
                    async for chunk in agent.process_query(
                        query=enhanced_request,
                        context={
                            "patient_profile": patient_profile,
                            "preferences": preferences
                        },
                        stream=True
                    ):
                        if chunk.get('type') == 'content' and chunk.get('chunk'):
                            result_parts.append(chunk['chunk'])
                    
                    result = ''.join(result_parts)
                    
                    # Store appointment details
                    async with ctx.store.edit_state() as state:
                        state["appointment_options"].append({
                            "request": request,
                            "response": result,
                            "timestamp": datetime.now().isoformat()
                        })
                        state["agent_outputs"]["AppointmentAgent"] = result
                        
                        # Add follow-up if appointment was booked
                        if "预约成功" in result or "已确认" in result:
                            state["follow_up_actions"].append("发送预约确认短信")
                            state["follow_up_actions"].append("就诊前一天提醒")
                    
                    return result
                    
                except Exception as e:
                    logger.error(f"AppointmentAgent error: {e}")
                    return f"预约服务暂时不可用: {str(e)}"
            else:
                return "预约服务暂时不可用"
        
        # Diagnosis Agent Tool
        async def call_diagnosis_agent(ctx: Context, symptoms: str) -> str:
            """Analyze symptoms and provide initial medical assessment"""
            logger.info(f"🔍 DiagnosisAgent called with: {symptoms}")
            
            # Record agent call
            async with ctx.store.edit_state() as state:
                state["agents_called"].append("DiagnosisAgent")
                state["reasoning_chain"].append(f"Analyzing symptoms: {symptoms}")
            
            # Get medical history
            async with ctx.store.get_state() as state:
                medical_history = state.get("medical_history", [])
                current_medications = state.get("current_medications", [])
                patient_profile = state.get("patient_profile", {})
            
            if agent := self.agents.get("DiagnosisAgent", self.agents.get("ClinicalAgent")):
                try:
                    # Run the agent
                    result_parts = []
                    async for chunk in agent.process_query(
                        query=symptoms,
                        context={
                            "medical_history": medical_history,
                            "current_medications": current_medications,
                            "patient_profile": patient_profile
                        },
                        stream=True
                    ):
                        if chunk.get('type') == 'content' and chunk.get('chunk'):
                            result_parts.append(chunk['chunk'])
                    
                    result = ''.join(result_parts)
                    
                    # Store diagnosis findings
                    async with ctx.store.edit_state() as state:
                        findings = {
                            "symptoms": symptoms,
                            "assessment": result,
                            "timestamp": datetime.now().isoformat()
                        }
                        
                        # Check for emergency keywords
                        emergency_keywords = ["紧急", "急诊", "立即", "120", "危险", "严重"]
                        if any(keyword in result for keyword in emergency_keywords):
                            findings["severity"] = "emergency"
                            state["emergency_flags"].append({
                                "type": "medical_emergency",
                                "details": result,
                                "timestamp": datetime.now().isoformat()
                            })
                            state["follow_up_actions"].append("立即联系急救服务")
                        
                        # Extract recommended department if mentioned
                        dept_keywords = {
                            "心内科": ["心脏", "心血管", "心悸"],
                            "呼吸科": ["呼吸", "咳嗽", "哮喘"],
                            "消化科": ["胃", "腹痛", "消化"],
                            "神经内科": ["头痛", "头晕", "神经"]
                        }
                        
                        for dept, keywords in dept_keywords.items():
                            if any(kw in symptoms or kw in result for kw in keywords):
                                findings["recommended_department"] = dept
                                break
                        
                        state["diagnosis_findings"].append(findings)
                        state["agent_outputs"]["DiagnosisAgent"] = result
                    
                    return result
                    
                except Exception as e:
                    logger.error(f"DiagnosisAgent error: {e}")
                    return f"症状分析服务暂时不可用: {str(e)}"
            else:
                return "症状分析服务暂时不可用"
        
        # Medication Agent Tool
        async def call_medication_agent(ctx: Context, medication_query: str) -> str:
            """Check drug interactions and provide medication guidance"""
            logger.info(f"💊 MedicationAgent called with: {medication_query}")
            
            # Record agent call
            async with ctx.store.edit_state() as state:
                state["agents_called"].append("MedicationAgent")
                state["reasoning_chain"].append(f"Checking medications: {medication_query}")
            
            # Get current medications and allergies
            async with ctx.store.get_state() as state:
                current_meds = state.get("current_medications", [])
                allergies = state.get("allergies", [])
                diagnosis = state.get("diagnosis_findings", [])
            
            if agent := self.agents.get("MedicationAgent"):
                try:
                    # Run the agent
                    result_parts = []
                    async for chunk in agent.process_query(
                        query=medication_query,
                        context={
                            "current_medications": current_meds,
                            "allergies": allergies,
                            "recent_diagnosis": diagnosis[-1] if diagnosis else None
                        },
                        stream=True
                    ):
                        if chunk.get('type') == 'content' and chunk.get('chunk'):
                            result_parts.append(chunk['chunk'])
                    
                    result = ''.join(result_parts)
                    
                    # Store medication checks
                    async with ctx.store.edit_state() as state:
                        check_result = {
                            "query": medication_query,
                            "guidance": result,
                            "timestamp": datetime.now().isoformat()
                        }
                        
                        # Check for contraindications
                        if "禁忌" in result or "不建议" in result or "相互作用" in result:
                            check_result["has_warnings"] = True
                            state["follow_up_actions"].append("咨询医生确认用药安全")
                        
                        state["medication_checks"].append(check_result)
                        state["agent_outputs"]["MedicationAgent"] = result
                    
                    return result
                    
                except Exception as e:
                    logger.error(f"MedicationAgent error: {e}")
                    return f"用药指导服务暂时不可用: {str(e)}"
            else:
                return "用药指导服务暂时不可用"
        
        # General Medical Agent Tool
        async def call_general_agent(ctx: Context, question: str) -> str:
            """Answer general medical questions and provide health advice"""
            logger.info(f"🏥 GeneralAgent called with: {question}")
            
            # Record agent call
            async with ctx.store.edit_state() as state:
                state["agents_called"].append("GeneralAgent")
                state["reasoning_chain"].append(f"Answering general question: {question}")
            
            # Get full context for general questions
            async with ctx.store.get_state() as state:
                full_context = {
                    "patient_profile": state.get("patient_profile", {}),
                    "recent_diagnosis": state.get("diagnosis_findings", [])[-1] if state.get("diagnosis_findings") else None,
                    "current_concerns": [d["symptoms"] for d in state.get("diagnosis_findings", [])]
                }
            
            if agent := self.agents.get("GeneralAgent", self.agents.get("GeneralMedicalAgent")):
                try:
                    # Run the agent
                    result_parts = []
                    async for chunk in agent.process_query(
                        query=question,
                        context=full_context,
                        stream=True
                    ):
                        if chunk.get('type') == 'content' and chunk.get('chunk'):
                            result_parts.append(chunk['chunk'])
                    
                    result = ''.join(result_parts)
                    
                    # Store general consultation
                    async with ctx.store.edit_state() as state:
                        state["research_notes"].append({
                            "question": question,
                            "answer": result,
                            "timestamp": datetime.now().isoformat()
                        })
                        state["agent_outputs"]["GeneralAgent"] = result
                    
                    return result
                    
                except Exception as e:
                    logger.error(f"GeneralAgent error: {e}")
                    return f"医疗咨询服务暂时不可用: {str(e)}"
            else:
                return "医疗咨询服务暂时不可用"
        
        # Create tool list
        tools.append(call_product_agent)
        tools.append(call_appointment_agent)
        tools.append(call_diagnosis_agent)
        tools.append(call_medication_agent)
        tools.append(call_general_agent)
        
        return tools
    
    def _get_orchestrator_prompt(self) -> str:
        """System prompt for the orchestrator"""
        return f"""你是诺亚新舟健康医疗助理的主协调器（使用LlamaIndex Pattern 2架构）。

今天是{datetime.now().strftime('%Y-%m-%d')}。

你的职责是：
1. 理解患者需求并协调专业代理
2. 维护对话上下文和状态
3. 确保医疗安全和全面护理
4. 整合所有代理的输出提供完整答案

可用的专业代理工具：
- call_product_agent: 健康产品推荐（保健品、医疗器械）
- call_appointment_agent: 预约挂号和排班查询
- call_diagnosis_agent: 症状分析和初步评估（医疗问题必须首先使用）
- call_medication_agent: 用药指导和相互作用检查
- call_general_agent: 一般医疗咨询和健康建议

重要指导原则：
1. **医疗安全第一**：
   - 症状相关问题必须先调用 call_diagnosis_agent
   - 紧急情况立即识别并提醒
   - 用药前检查相互作用

2. **智能协调**：
   - 根据诊断结果推荐合适的科室预约
   - 产品推荐要考虑过敏史和禁忌
   - 多个代理的结果要整合成连贯的回答

3. **上下文感知**：
   - 利用患者历史信息提供个性化建议
   - 记住之前的对话内容
   - 跟踪已执行的操作避免重复

4. **完整服务**：
   - 不仅回答问题，还要提供后续建议
   - 主动识别潜在需求
   - 确保患者得到全面的医疗指导

工作流状态会在所有工具调用间自动共享和更新。
请基于收集到的所有信息提供专业、准确、有帮助的医疗建议。"""
    
    async def process_query(
        self,
        query: str,
        user_id: str,
        messages: List[Dict[str, Any]] = None,
        stream: bool = True,
        session_id: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Process query through Pattern 2 orchestrator with streaming support
        """
        try:
            # Create or get conversation context
            conversation_id = session_id or f"conv_{datetime.now().timestamp()}"
            
            # Create UnifiedContext
            unified_context = self.context_manager.create_context(
                user_id=user_id,
                query=query,
                conversation_id=conversation_id
            )
            
            # Load patient memory
            if self.memory_manager:
                try:
                    patient_memory = await self.memory_manager.get_user_context(user_id)
                    if patient_memory:
                        unified_context.patient_profile = patient_memory.get("profile", {})
                        unified_context.medical_history = patient_memory.get("medical_history", [])
                        unified_context.current_medications = patient_memory.get("medications", [])
                        unified_context.allergies = patient_memory.get("allergies", [])
                        logger.info(f"Loaded patient memory for {user_id}")
                except Exception as e:
                    logger.warning(f"Failed to load patient memory: {e}")
            
            # Initialize orchestrator state with patient context
            initial_state = WorkflowState(
                workflow_id=f"wf_{datetime.now().timestamp()}",
                conversation_id=conversation_id,
                user_id=user_id,
                patient_profile=unified_context.patient_profile,
                medical_history=unified_context.medical_history,
                current_medications=unified_context.current_medications,
                allergies=unified_context.allergies,
                appointment_preferences=unified_context.appointment_preferences
            )
            
            # Update orchestrator initial state
            self.orchestrator.initial_state = initial_state.to_dict()
            
            # Build enhanced query with conversation history
            enhanced_query = self._build_enhanced_query(query, unified_context, messages)
            
            if stream:
                # Stream the response with reasoning visibility
                async for event in self._stream_orchestrator_response(
                    enhanced_query, unified_context
                ):
                    yield event
            else:
                # Non-streaming response
                result = await self._process_non_streaming(
                    enhanced_query, unified_context
                )
                yield result
            
            # Store conversation in memory
            if self.memory_manager:
                await self._store_conversation(unified_context)
                
        except Exception as e:
            logger.error(f"Error in Pattern 2 orchestrator: {e}")
            import traceback
            traceback.print_exc()
            
            yield {
                "error": {
                    "message": str(e),
                    "type": "orchestrator_error"
                }
            }
    
    async def _stream_orchestrator_response(
        self,
        query: str,
        unified_context: UnifiedContext
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream orchestrator response with reasoning visibility"""
        
        stream_id = f"chatcmpl-{unified_context.conversation_id}"
        created_time = int(datetime.now().timestamp())
        sequence_num = 0
        
        # Start response
        yield {
            "type": "response.created",
            "sequence_number": sequence_num,
            "response": {
                "id": stream_id,
                "object": "chat.completion",
                "created_at": created_time,
                "status": "in_progress",
                "model": "humansa-v2-pattern2",
                "output": []
            }
        }
        sequence_num += 1
        
        try:
            # Run orchestrator and collect response
            logger.info(f"Running Pattern 2 orchestrator with query: {query[:100]}...")
            response = await self.orchestrator.run(user_msg=query)
            
            # Get final state
            final_state = self.orchestrator.state
            
            # Log final context for debugging
            logger.info("="*60)
            logger.info("PATTERN 2 FINAL CONTEXT")
            logger.info("="*60)
            logger.info(f"Workflow ID: {final_state.get('workflow_id', 'N/A')}")
            logger.info(f"User ID: {final_state.get('user_id', 'N/A')}")
            logger.info(f"Agents Called: {final_state.get('agents_called', [])}")
            logger.info(f"Reasoning Chain: {final_state.get('reasoning_chain', [])}")
            
            # Log agent outputs summary
            agent_outputs = final_state.get('agent_outputs', {})
            if agent_outputs:
                logger.info("Agent Outputs:")
                for agent, output in agent_outputs.items():
                    logger.info(f"  - {agent}: {output[:200]}..." if len(output) > 200 else f"  - {agent}: {output}")
            
            # Log emergency flags and follow-up actions
            if emergency_flags := final_state.get('emergency_flags', []):
                logger.warning(f"Emergency Flags: {emergency_flags}")
            
            if follow_up_actions := final_state.get('follow_up_actions', []):
                logger.info(f"Follow-up Actions: {follow_up_actions}")
            
            logger.info("="*60)
            
            # Extract response text
            response_text = str(response)
            
            # Update UnifiedContext with results
            unified_context.agents_invoked = final_state.get("agents_called", [])
            unified_context.agent_responses = final_state.get("agent_outputs", {})
            
            # Create message item
            message_item = {
                "id": f"msg_{sequence_num}",
                "type": "message",
                "role": "assistant",
                "status": "completed",
                "content": [
                    {
                        "type": "output_text",
                        "text": response_text
                    }
                ],
                "created_at": datetime.now().isoformat() + "Z",
                "completed_at": datetime.now().isoformat() + "Z",
                "output_index": 0
            }
            
            # Add message item
            yield {
                "type": "response.output_item.added",
                "sequence_number": sequence_num,
                "output_index": 0,
                "item": message_item
            }
            sequence_num += 1
            
            # Add reasoning chain if available
            if reasoning_chain := final_state.get("reasoning_chain", []):
                yield {
                    "type": "response.reasoning",
                    "sequence_number": sequence_num,
                    "reasoning": reasoning_chain
                }
                sequence_num += 1
            
            # Add usage metadata
            yield {
                "type": "response.usage",
                "sequence_number": sequence_num,
                "usage": {
                    "agents_used": final_state.get("agents_called", []),
                    "total_agents": len(final_state.get("agents_called", [])),
                    "workflow_id": final_state.get("workflow_id", ""),
                    "emergency_flags": final_state.get("emergency_flags", []),
                    "follow_up_actions": final_state.get("follow_up_actions", [])
                }
            }
            sequence_num += 1
            
            # Complete response
            yield {
                "type": "response.completed",
                "sequence_number": sequence_num,
                "response": {
                    "id": stream_id,
                    "status": "completed",
                    "object": "chat.completion",
                    "output": [message_item]
                }
            }
            
        except Exception as e:
            logger.error(f"Error in orchestrator streaming: {e}")
            
            error_item = {
                "id": f"msg_error_{sequence_num}",
                "type": "message",
                "role": "assistant",
                "status": "completed",
                "content": [{
                    "type": "output_text",
                    "text": f"处理请求时出现错误: {str(e)}"
                }],
                "created_at": datetime.now().isoformat() + "Z",
                "output_index": 0
            }
            
            yield {
                "type": "response.output_item.added",
                "sequence_number": sequence_num,
                "output_index": 0,
                "item": error_item
            }
    
    async def _process_non_streaming(
        self,
        query: str,
        unified_context: UnifiedContext
    ) -> Dict[str, Any]:
        """Process without streaming"""
        try:
            # Run orchestrator
            logger.info(f"Running Pattern 2 orchestrator (non-streaming) with query: {query[:100]}...")
            response = await self.orchestrator.run(user_msg=query)
            
            # Get final state
            final_state = self.orchestrator.state
            
            # Log final context for debugging
            logger.info("="*60)
            logger.info("PATTERN 2 FINAL CONTEXT (Non-Streaming)")
            logger.info("="*60)
            logger.info(f"Workflow ID: {final_state.get('workflow_id', 'N/A')}")
            logger.info(f"User ID: {final_state.get('user_id', 'N/A')}")
            logger.info(f"Agents Called: {final_state.get('agents_called', [])}")
            
            # Log agent outputs summary
            agent_outputs = final_state.get('agent_outputs', {})
            if agent_outputs:
                logger.info("Agent Outputs Summary:")
                for agent, output in agent_outputs.items():
                    logger.info(f"  - {agent}: {len(output)} chars")
            
            logger.info("="*60)
            
            # Update UnifiedContext
            unified_context.agents_invoked = final_state.get("agents_called", [])
            unified_context.agent_responses = final_state.get("agent_outputs", {})
            
            return {
                "id": f"chatcmpl-{unified_context.conversation_id}",
                "object": "chat.completion",
                "created": int(datetime.now().timestamp()),
                "model": "humansa-v2-pattern2",
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": str(response)
                    },
                    "finish_reason": "stop"
                }],
                "usage": {
                    "agents_used": final_state.get("agents_called", []),
                    "total_agents": len(final_state.get("agents_called", [])),
                    "workflow_state": final_state
                }
            }
            
        except Exception as e:
            logger.error(f"Error in non-streaming processing: {e}")
            return {
                "id": f"chatcmpl-error",
                "object": "chat.completion",
                "created": int(datetime.now().timestamp()),
                "model": "humansa-v2-pattern2",
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": f"处理请求时出现错误: {str(e)}"
                    },
                    "finish_reason": "error"
                }],
                "error": {
                    "message": str(e),
                    "type": "processing_error"
                }
            }
    
    def _build_enhanced_query(
        self,
        query: str,
        context: UnifiedContext,
        messages: List[Dict[str, Any]] = None
    ) -> str:
        """Build enhanced query with context"""
        parts = []
        
        # Add patient context if available
        if context.patient_profile:
            parts.append(f"患者信息: {json.dumps(context.patient_profile, ensure_ascii=False)}")
        
        # Add recent medical context
        if medical_context := context.get_relevant_medical_context():
            parts.append(f"医疗背景:\n{medical_context}")
        
        # Add conversation history
        if messages and len(messages) > 1:
            recent = messages[-3:-1] if len(messages) > 3 else messages[:-1]
            history = []
            for msg in recent:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                history.append(f"{role}: {content}")
            if history:
                parts.append(f"近期对话:\n" + "\n".join(history))
        
        # Add current query
        parts.append(f"当前问题: {query}")
        
        return "\n\n".join(parts)
    
    async def _store_conversation(self, context: UnifiedContext):
        """Store conversation in memory"""
        if not self.memory_manager:
            return
            
        try:
            # Store conversation
            await self.memory_manager.add_conversation(
                user_id=context.user_id,
                messages=[{
                    "role": "user",
                    "content": context.query
                }],
                metadata={
                    "conversation_id": context.conversation_id,
                    "agents_used": context.agents_invoked,
                    "timestamp": context.timestamp.isoformat()
                }
            )
            
            # Extract and store important information
            if context.current_symptoms:
                await self.memory_manager.add_memory(
                    user_id=context.user_id,
                    content=f"Patient reported symptoms: {', '.join(context.current_symptoms)}",
                    metadata={"type": "symptoms", "date": context.timestamp.isoformat()}
                )
            
            # Store any emergency flags
            final_state = self.orchestrator.state
            if emergency_flags := final_state.get("emergency_flags", []):
                for flag in emergency_flags:
                    await self.memory_manager.add_memory(
                        user_id=context.user_id,
                        content=f"Emergency flag: {flag['details']}",
                        metadata={"type": "emergency", "severity": "high"}
                    )
                    
        except Exception as e:
            logger.error(f"Failed to store conversation: {e}")


# Factory function
def create_pattern2_orchestrator(
    llm: LLM,
    agents: Dict[str, Any],
    memory_manager: Optional[MemoryManager] = None,
    debug: bool = False
) -> HumansaOrchestratorPattern2:
    """
    Create a Pattern 2 orchestrator instance
    
    Args:
        llm: Language model
        agents: Dictionary of initialized sub-agents
        memory_manager: Memory manager for persistence
        debug: Enable debug logging
        
    Returns:
        HumansaOrchestratorPattern2 instance
    """
    return HumansaOrchestratorPattern2(
        llm=llm,
        agents=agents,
        memory_manager=memory_manager,
        debug=debug
    )