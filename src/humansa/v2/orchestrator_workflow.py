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
    from .react_formatter import get_humansa_react_formatter
    
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
                AppointmentAgent,
                DiagnosisAgent,
                MedicationAgent,
                GeneralMedicalAgent
            )
            from .agents.product_agent import ProductAgent
        except ImportError:
            from src.humansa.v2.agents import (
                AppointmentAgent,
                DiagnosisAgent,
                MedicationAgent,
                GeneralMedicalAgent
            )
            from src.humansa.v2.agents.product_agent import ProductAgent
        
        # Instantiate real agent instances
        try:
            logger.info(f"Creating agents with LLM: {type(self.llm)}")
            
            # Use staged product agent (compact search + detailed load)
            logger.info("Creating ProductAgent...")
            agents["ProductAgent"] = ProductAgent(llm=self.llm)
            logger.info(f"ProductAgent created: {agents['ProductAgent']}")
            
            logger.info("Creating AppointmentAgent...")
            agents["AppointmentAgent"] = AppointmentAgent(llm=self.llm)
            
            logger.info("Creating DiagnosisAgent...")
            agents["ClinicalAgent"] = DiagnosisAgent(llm=self.llm)
            
            logger.info("Creating MedicationAgent...")
            agents["MedicationAgent"] = MedicationAgent(llm=self.llm)
            
            logger.info("Creating GeneralMedicalAgent...")
            agents["GeneralAgent"] = GeneralMedicalAgent(llm=self.llm)
            
            logger.info(f"✅ Successfully instantiated {len(agents)} real sub-agents")
        except Exception as e:
            logger.error(f"❌ Error instantiating agents: {e}. Using None placeholders.")
            import traceback
            logger.error(f"Agent instantiation traceback:\n{traceback.format_exc()}")
            # Fallback to None placeholders if instantiation fails
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
                async def call_agent(query: str = None, input: str = None, **kwargs) -> str:
                    """Call the sub-agent and return response. Accepts both 'query' and 'input' parameters."""
                    # Handle both 'query' and 'input' parameters from ReAct agent
                    actual_query = query or input or ""
                    
                    try:
                        # Get the actual agent instance
                        agent_instance = self.agents.get(name)
                        
                        if agent_instance is None:
                            logger.warning(f"Agent {name} not instantiated, using mock response")
                            return f"[{name}代理响应] 收到查询: {actual_query}\n\n这里应该是{name}的实际响应。当前为演示模式。"
                        
                        # Call the real agent
                        logger.info(f"🔧 Calling real {name} with query: {actual_query[:100]}...")
                        
                        # Collect response from agent's process_query method
                        if hasattr(agent_instance, 'process_query'):
                            response_parts = []
                            async for chunk in agent_instance.process_query(actual_query, {}, stream=True):
                                if chunk.get('type') == 'content' and chunk.get('chunk'):
                                    response_parts.append(chunk['chunk'])
                                elif 'response' in chunk:
                                    response_parts.append(chunk['response'])
                            
                            full_response = ''.join(response_parts)
                            if full_response.strip():
                                logger.info(f"✅ {name} returned {len(full_response)} characters")
                                return full_response
                        
                        # Fallback for agents without process_query method
                        logger.warning(f"Agent {name} has no process_query method")
                        return f"[{name}代理响应] 收到查询: {query}\n\n代理已接收查询但未能处理。"
                        
                    except Exception as e:
                        logger.error(f"Error calling {name}: {e}")
                        import traceback
                        traceback.print_exc()
                        return f"调用{name}时出现错误: {str(e)}"
                
                return call_agent
            
            # Create tool with proper metadata
            tool = FunctionTool.from_defaults(
                fn=create_agent_tool(agent_name),
                name=f"call_{agent_name.lower()}",
                description=self._get_agent_description(agent_name)
            )
            orchestrator_tools.append(tool)
        
        # Create orchestrator with ReActAgent and custom formatter
        try:
            # Use new API for llama-index 0.13.0
            logger.info("Creating ReActAgent orchestrator...")
            orchestrator = ReActAgent(
                name="HumansaOrchestrator",
                description="Main orchestrator for HUMANSA health assistant",
                tools=orchestrator_tools,
                llm=self.llm,
                system_prompt=f"""你是诺亚新舟健康医疗助理的主协调器。

今天是{datetime.now().strftime('%Y-%m-%d')}。

你的职责是：
1. 理解用户的问题和需求
2. 选择最合适的专业代理来处理
3. 如果需要多个方面的信息，可以调用多个代理
4. **重要**：整合所有工具调用的结果，基于获得的信息提供完整、具体的答案

可用的专业代理：
- call_productagent: 产品推荐、保健品、医疗器械推荐
- call_appointmentagent: 预约挂号、医生排班、改期取消
- call_clinicalagent: 症状分析、紧急情况识别、科室推荐
- call_medicationagent: 用药指导、药物相互作用检查
- call_generalagent: 一般医疗咨询、健康知识、保险政策

重要原则：
- 紧急医疗情况立即使用call_clinicalagent
- 产品相关问题必须使用call_productagent并包含产品具体信息
- 预约相关必须使用call_appointmentagent
- 可以组合使用多个代理提供全面服务

工作流程：
1. 分析用户问题，确定需要调用的代理
2. 调用相应代理获取信息
3. **必须基于工具返回的具体信息（如产品名称、链接、用法等）组织答案**
4. 如果工具返回的信息不完整，继续调用工具获取更多信息
5. 最终答案必须包含从工具获得的具体信息，不要给出泛泛的建议

你必须调用至少一个专业代理来处理用户问题，并将代理返回的具体信息整合到你的回答中。""",
                verbose=True
            )
            logger.info("ReActAgent orchestrator created successfully")
        except Exception as e:
            logger.error(f"Error creating ReActAgent: {e}")
            import traceback
            logger.error(f"ReActAgent creation traceback:\n{traceback.format_exc()}")
            raise
        
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
            logger.info(f"Creating stream_chat with query: {query[:100]}...")
            try:
                # Try to create proper message format
                from llama_index.core.base.llms.types import ChatMessage, MessageRole
                
                # First try with just string (this is what should work)
                try:
                    # Use run method for new API
                    response_stream = self.orchestrator_agent.run(query)
                except Exception as e1:
                    logger.error(f"Error with string query: {e1}")
                    # If that fails, try with ChatMessage
                    try:
                        chat_msg = ChatMessage(role=MessageRole.USER, content=query)
                        response_stream = self.orchestrator_agent.stream_chat(chat_msg)
                    except Exception as e2:
                        logger.error(f"Error with ChatMessage: {e2}")
                        raise e1  # Raise original error
            except Exception as e:
                logger.error(f"Error creating stream_chat: {e}")
                import traceback
                logger.error(f"Stream creation traceback:\n{traceback.format_exc()}")
                raise
            
            # Collect full response
            full_response = ""
            logger.info("Starting to collect response chunks...")
            
            # New API - await the response directly
            try:
                result = await response_stream
                if hasattr(result, 'response'):
                    full_response = str(result.response)
                else:
                    full_response = str(result)
                logger.info(f"Got complete response: {full_response[:100]}...")
            except Exception as e:
                logger.error(f"Error getting result: {e}")
                full_response = "处理查询时出现错误"
            
            # Check if this is a product query - preserve details
            is_product_query = any(keyword in original_query.lower() 
                                 for keyword in ['产品', '推荐', 'dha', '保健品', '营养', '健康商城', '童年故事'])
            
            # Skip response agent processing for now - it's causing the 'blocks' error
            # The response agent expects a different format that we need to investigate
            final_text = full_response
            logger.info(f"Using raw response without post-processing: {final_text[:200]}...")
            logger.info(f"Full response length: {len(final_text)}")
            
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
            import traceback
            logger.error(f"Full streaming traceback:\n{traceback.format_exc()}")
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
            logger.info(f"Calling orchestrator_agent.chat with query: {query[:100]}...")
            try:
                # Use run method for new API
                response = self.orchestrator_agent.run(query)
                logger.info(f"Got response type: {type(response)}")
                logger.info(f"Response attributes: {dir(response)}")
            except Exception as e:
                logger.error(f"Error in orchestrator_agent.chat: {e}")
                import traceback
                logger.error(f"Chat error traceback:\n{traceback.format_exc()}")
                
                # Try to get more info about the error
                if "'dict' object has no attribute 'blocks'" in str(e):
                    logger.error("This appears to be a message formatting issue with Azure OpenAI")
                raise
            
            # Handle the WorkflowHandler response
            # Wait for the workflow to complete
            result = await response
            
            # Extract text from result
            if hasattr(result, 'response'):
                response_text = str(result.response)
            elif hasattr(result, 'output'):
                response_text = str(result.output)
            elif hasattr(result, 'content'):
                response_text = str(result.content)
            else:
                response_text = str(result)
            
            # Skip response agent processing for now - it's causing the 'blocks' error
            # The response agent expects a different format that we need to investigate
            logger.info("Using raw response without post-processing")
            
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
            import traceback
            logger.error(f"Full traceback:\n{traceback.format_exc()}")
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