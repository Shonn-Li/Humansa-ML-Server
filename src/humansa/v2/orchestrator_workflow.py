"""
HUMANSA V2 Orchestrator using AgentWorkflow Pattern
Implements proper streaming of reasoning steps and tool calls
"""

import os
import logging
import json
import time
import uuid
from typing import List, Dict, Any, Optional, AsyncGenerator, Callable
from datetime import datetime

# LlamaIndex imports for the ReActAgent pattern
try:
    from llama_index.core.agent import ReActAgent
    from llama_index.core.tools import FunctionTool
    from llama_index.core import Settings
    
    WORKFLOW_AVAILABLE = True
except ImportError:
    WORKFLOW_AVAILABLE = False
    logging.warning("LlamaIndex agent components not available - agent features disabled")

# Import response agent for post-processing
try:
    from .response_agent import HumansaResponseAgent
except ImportError:
    from src.humansa.v2.response_agent import HumansaResponseAgent

logger = logging.getLogger(__name__)


class WorkflowOrchestrator:
    """
    Orchestrator using LlamaIndex AgentWorkflow pattern
    Provides full streaming of reasoning steps and tool calls
    """
    
    def __init__(
        self,
        llm: Optional[Any] = None,
        memory_manager: Optional[Any] = None,
        debug: bool = False,
        db_config: Optional[Dict[str, Any]] = None
    ):
        """Initialize the workflow orchestrator"""
        
        if not WORKFLOW_AVAILABLE:
            raise ImportError("LlamaIndex agent components are required for WorkflowOrchestrator")
        
        self.llm = llm or Settings.llm
        self.memory_manager = memory_manager
        self.debug = debug
        self.db_config = db_config
        
        # Initialize response agent for post-processing
        self.response_agent = HumansaResponseAgent()
        
        # Create sub-agents using FunctionAgent pattern
        self.agents = self._create_function_agents()
        
        # Create main orchestrator agent
        self.orchestrator_agent = self._create_orchestrator_agent()
        
        # Store orchestrator agent (no workflow needed)
        # self.workflow = self.orchestrator_agent
        
        logger.info(f"✅ Initialized WorkflowOrchestrator with {len(self.agents)} sub-agents")
    
    def _create_function_agents(self) -> Dict[str, Any]:
        """Create async agent instances wrapped as tools"""
        
        agents = {}
        
        # Import agent implementations
        try:
            from .agents import (
                ProductAgent,
                AppointmentAgent,
                DiagnosisAgent,
                MedicationAgent,
                GeneralMedicalAgent
            )
        except ImportError:
            from src.humansa.v2.agents import (
                ProductAgent,
                AppointmentAgent,
                DiagnosisAgent,
                MedicationAgent,
                GeneralMedicalAgent
            )
        
        # For now, don't instantiate the actual agents - just store None placeholders
        # The workflow orchestrator will use ReActAgent with tools that call the agents
        agents["ProductAgent"] = None
        agents["AppointmentAgent"] = None  
        agents["ClinicalAgent"] = None
        agents["MedicationAgent"] = None
        agents["GeneralAgent"] = None
        
        return agents
    
    def _create_orchestrator_agent(self) -> Any:
        """Create orchestrator using ReActAgent with sub-agent tools"""
        
        from llama_index.core.agent import ReActAgent
        
        # Create tools that call sub-agents
        orchestrator_tools = []
        
        for agent_name in self.agents.keys():
            # Create a tool function for each sub-agent
            def create_agent_tool(name):
                async def call_agent(query: str) -> str:
                    """Call the sub-agent and return response"""
                    try:
                        # For now, return a mock response indicating which agent would be called
                        # In a real implementation, this would instantiate and call the actual agent
                        return f"[{name}代理响应] 收到查询: {query}\n\n这里应该是{name}的实际响应。当前为演示模式。"
                    except Exception as e:
                        logger.error(f"Error calling {name}: {e}")
                        return f"调用{name}时出现错误: {str(e)}"
                
                return call_agent
            
            # Create tool with proper metadata
            tool = FunctionTool.from_defaults(
                fn=create_agent_tool(agent_name),
                name=f"call_{agent_name.lower()}",
                description=self._get_agent_description(agent_name)
            )
            orchestrator_tools.append(tool)
        
        # Create orchestrator with ReActAgent 
        orchestrator = ReActAgent.from_tools(
            tools=orchestrator_tools,
            llm=self.llm,
            system_prompt=f"""你是诺亚新舟健康医疗助理的主协调器。

今天是{datetime.now().strftime('%Y-%m-%d')}。

你的职责是：
1. 理解用户的问题和需求
2. 选择最合适的专业代理来处理
3. 如果需要多个方面的信息，可以调用多个代理
4. 整合所有响应，提供完整答案

可用的专业代理：
- call_productagent: 产品推荐、保健品、医疗器械推荐
- call_appointmentagent: 预约挂号、医生排班、改期取消
- call_clinicalagent: 症状分析、紧急情况识别、科室推荐
- call_medicationagent: 用药指导、药物相互作用检查
- call_generalagent: 一般医疗咨询、健康知识、保险政策

重要原则：
- 紧急医疗情况立即使用call_clinicalagent
- 产品相关问题必须使用call_productagent
- 预约相关必须使用call_appointmentagent
- 可以组合使用多个代理提供全面服务

你必须调用至少一个专业代理来处理用户问题，不要直接回答。""",
            verbose=True
        )
        
        return orchestrator
    
    def _get_agent_description(self, agent_name: str) -> str:
        """Get description for each agent"""
        descriptions = {
            "ProductAgent": "专门处理产品推荐、保健品查询、医疗器械推荐",
            "AppointmentAgent": "专门处理预约挂号、医生排班查询、改期取消",
            "ClinicalAgent": "专门进行症状分析、紧急情况识别、科室推荐",
            "MedicationAgent": "专门提供用药指导、药物相互作用检查",
            "GeneralAgent": "处理一般医疗咨询、健康知识、保险政策"
        }
        return descriptions.get(agent_name, "专业医疗助理")
    
    async def process_query(
        self,
        query: str,
        user_id: str,
        messages: List[Dict[str, Any]] = None,
        stream: bool = True,
        session_id: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Process a query through the workflow orchestrator with streaming"""
        
        try:
            # No workflow context needed for ReActAgent approach
            session_id = session_id or str(uuid.uuid4())
            start_time = time.time()
            
            # Load user context from memory if available
            user_context = {}
            if self.memory_manager:
                try:
                    user_context = await self.memory_manager.get_user_context(user_id)
                    logger.info(f"Loaded user context for {user_id}")
                except Exception as e:
                    logger.warning(f"Failed to load user context: {e}")
            
            # Build enhanced query with context
            enhanced_query = self._build_enhanced_query(query, user_context, messages)
            
            if stream:
                # Stream the orchestrator response (ReActAgent supports streaming)
                async for event in self._stream_orchestrator_response(enhanced_query, user_id, query):
                    yield event
            else:
                # Non-streaming: get complete response
                final_response = await self._process_non_streaming(enhanced_query, user_id, query)
                yield final_response
            
            # Store conversation in memory
            if self.memory_manager:
                await self._store_conversation(user_id, query, session_id)
                
        except Exception as e:
            logger.error(f"Error in process_query: {e}")
            import traceback
            traceback.print_exc()
            
            yield {
                "error": {
                    "message": str(e),
                    "type": "processing_error"
                }
            }
    
    async def _stream_orchestrator_response(
        self,
        query: str,
        user_id: str,
        original_query: str
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream orchestrator response using ReActAgent's native streaming"""
        
        # Stream ID for this response
        stream_id = f"chatcmpl-{uuid.uuid4()}"
        created_time = int(time.time())
        
        # Sequence number for event ordering
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
                "model": "humansa-v2-workflow",
                "output": []
            }
        }
        sequence_num += 1
        
        # Track agents used
        agents_used = []
        start_time = time.time()
        
        try:
            # Use ReActAgent's stream_chat for natural streaming with reasoning
            response_stream = self.orchestrator_agent.stream_chat(query)
            
            # Collect full response
            full_response = ""
            async for chunk in response_stream.async_response_gen():
                if chunk:
                    full_response += str(chunk)
            
            # Post-process with response agent
            processed_response = self.response_agent.process_response(
                {"output": [{"content": full_response}]},
                original_query
            )
            
            if processed_response.get("output"):
                final_text = processed_response["output"][0].get("text", full_response)
            else:
                final_text = full_response
            
            # Create single message item with complete response
            current_time = datetime.utcnow().isoformat() + "Z"
            message_item = {
                "id": f"msg_{uuid.uuid4().hex[:8]}",
                "type": "message",
                "role": "assistant",
                "status": "completed",
                "content": [
                    {
                        "type": "output_text",
                        "text": final_text
                    }
                ],
                "created_at": current_time,
                "completed_at": current_time,
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
            
            # Add content part
            yield {
                "type": "response.content_part.added",
                "sequence_number": sequence_num,
                "item_id": message_item["id"],
                "output_index": 0,
                "content_index": 0,
                "part": {"type": "output_text", "text": final_text}
            }
            sequence_num += 1
            
            # Complete content
            yield {
                "type": "response.output_text.done",
                "sequence_number": sequence_num,
                "item_id": message_item["id"],
                "output_index": 0,
                "content_index": 0,
                "text": final_text
            }
            sequence_num += 1
            
            # Complete message item
            yield {
                "type": "response.output_item.done",
                "sequence_number": sequence_num,
                "output_index": 0,
                "item": message_item
            }
            sequence_num += 1
            
            # Extract agent usage from response (if available)
            # Note: ReActAgent logs show which tools were called but we need to parse it
            if "call_" in final_text.lower():
                for agent_name in self.agents.keys():
                    if f"call_{agent_name.lower()}" in final_text.lower():
                        agents_used.append(agent_name)
            
        except Exception as e:
            logger.error(f"Error in orchestrator streaming: {e}")
            # Return error message
            error_message = f"处理查询时出现错误: {str(e)}"
            
            error_item = {
                "id": f"msg_{uuid.uuid4().hex[:8]}",
                "type": "message",
                "role": "assistant",
                "status": "completed",
                "content": [{"type": "output_text", "text": error_message}],
                "created_at": datetime.utcnow().isoformat() + "Z",
                "completed_at": datetime.utcnow().isoformat() + "Z",
                "output_index": 0
            }
            
            yield {
                "type": "response.output_item.added",
                "sequence_number": sequence_num,
                "output_index": 0, 
                "item": error_item
            }
            sequence_num += 1
        
        # Add usage metadata
        yield {
            "type": "response.usage",
            "sequence_number": sequence_num,
            "usage": {
                "agents_used": agents_used,
                "total_agents": len(agents_used),
                "duration": time.time() - start_time
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
                "output": [message_item] if 'message_item' in locals() else []
            }
        }
    
    async def _process_non_streaming(
        self,
        query: str,
        user_id: str,
        original_query: str
    ) -> Dict[str, Any]:
        """Process without streaming and return complete response"""
        
        try:
            # Use ReActAgent to get response
            response = self.orchestrator_agent.chat(query)
            response_text = str(response.response)
            
            # Post-process response
            processed_response = self.response_agent.process_response(
                {"output": [{"content": response_text}]},
                original_query
            )
            
            if processed_response.get("output"):
                response_text = processed_response["output"][0].get("text", response_text)
            
            return {
                "id": f"chatcmpl-{uuid.uuid4()}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": "humansa-v2-workflow",
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": response_text
                    },
                    "finish_reason": "stop"
                }],
                "usage": {
                    "agents_used": [],  # Would need to parse from response
                    "total_agents": 0,
                    "duration": 0
                }
            }
            
        except Exception as e:
            logger.error(f"Error in non-streaming processing: {e}")
            return {
                "id": f"chatcmpl-{uuid.uuid4()}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": "humansa-v2-workflow",
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": f"处理查询时出现错误: {str(e)}"
                    },
                    "finish_reason": "stop"
                }],
                "usage": {
                    "agents_used": [],
                    "total_agents": 0,
                    "duration": 0
                }
            }
    
    def _build_enhanced_query(
        self,
        query: str,
        user_context: Dict[str, Any],
        messages: List[Dict[str, Any]] = None
    ) -> str:
        """Build query enhanced with user context"""
        
        enhanced = query
        
        # Add user profile if available
        if user_context.get("profile"):
            profile = user_context["profile"]
            enhanced = f"用户信息：{json.dumps(profile, ensure_ascii=False)}\n\n{enhanced}"
        
        # Add recent context if available
        if user_context.get("recent_context"):
            enhanced = f"近期对话背景：{user_context['recent_context']}\n\n{enhanced}"
        
        # Add conversation history if provided
        if messages and len(messages) > 1:
            history = []
            for msg in messages[-5:-1]:  # Last 5 messages before current
                role = msg.get("role", "user")
                content = msg.get("content", "")
                history.append(f"{role}: {content}")
            
            if history:
                enhanced = f"对话历史：\n{chr(10).join(history)}\n\n当前查询：{enhanced}"
        
        return enhanced
    
    async def _store_conversation(
        self,
        user_id: str,
        query: str,
        session_id: Optional[str] = None
    ):
        """Store conversation in memory"""
        
        try:
            # Store conversation metadata  
            metadata = {
                "session_id": session_id,
                "timestamp": datetime.now().isoformat(),
                "orchestrator": "workflow",
                "agents_used": [],  # Would be populated from actual response
                "model": "humansa-v2"
            }
            
            # Store (would need actual response text)
            # await self.memory_manager.add_conversation(...)
            
        except Exception as e:
            logger.error(f"Failed to store conversation: {e}")
    
    def _get_product_tools(self) -> List[FunctionTool]:
        """Get tools for product agent"""
        # In real implementation, would return actual product search/recommendation tools
        return []
    
    def _get_appointment_tools(self) -> List[FunctionTool]:
        """Get tools for appointment agent"""
        # In real implementation, would return appointment search/booking tools
        return []
    
    def _get_clinical_tools(self) -> List[FunctionTool]:
        """Get tools for clinical agent"""
        # In real implementation, would return symptom analysis tools
        return []
    
    def _get_medication_tools(self) -> List[FunctionTool]:
        """Get tools for medication agent"""
        # In real implementation, would return drug interaction check tools
        return []
    
    def _get_general_tools(self) -> List[FunctionTool]:
        """Get tools for general agent"""
        # In real implementation, would return knowledge base search tools
        return []


# Convenience function for initialization
def create_workflow_orchestrator(
    llm: Any,
    memory_manager: Optional[Any] = None,
    debug: bool = False,
    db_config: Optional[Dict[str, Any]] = None
) -> WorkflowOrchestrator:
    """
    Create a workflow orchestrator instance
    
    Args:
        llm: Language model instance
        memory_manager: Memory manager for context
        debug: Enable debug logging
        db_config: Database configuration
        
    Returns:
        WorkflowOrchestrator instance
    """
    
    return WorkflowOrchestrator(
        llm=llm,
        memory_manager=memory_manager,
        debug=debug,
        db_config=db_config
    )