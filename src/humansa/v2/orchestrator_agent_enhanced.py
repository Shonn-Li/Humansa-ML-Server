"""
Enhanced Humansa V2 Orchestrator Agent with detailed logging
This version provides comprehensive logging of:
- Agent thinking process
- Tool calls with parameters
- Agent reasoning
- Mem0 integration
"""

from typing import Dict, Any, List, Optional, AsyncGenerator
from llama_index.core.agent import ReActAgent
from llama_index.core.tools import FunctionTool
from llama_index.core.llms import LLM
from llama_index.core.callbacks import CallbackManager, LlamaDebugHandler, CBEventType
from llama_index.core.callbacks.base import BaseCallbackHandler
import logging
import json
import time
from datetime import datetime
import asyncio

# Agent imports will be simplified for now
from .memory.memory_manager import MemoryManager
from humansa.prompts.humansa_system_prompt_v2 import get_humansa_system_prompt_v2, HUMANSA_REACT_PROMPT_V2

logger = logging.getLogger(__name__)


class EnhancedLoggingHandler(BaseCallbackHandler):
    """Custom callback handler for enhanced logging"""
    
    def __init__(self, stream_callback=None):
        super().__init__(
            event_starts_to_ignore=[],
            event_ends_to_ignore=[]
        )
        self.stream_callback = stream_callback
        self.events = []
        
    async def _send_event(self, event_type: str, data: Dict[str, Any]):
        """Send event to stream if callback is provided"""
        event = {
            "type": event_type,
            "timestamp": time.time(),
            **data
        }
        self.events.append(event)
        
        if self.stream_callback:
            try:
                await self.stream_callback(event)
            except Exception as e:
                logger.error(f"Error in stream callback: {e}")
    
    def on_event_start(
        self,
        event_type: CBEventType,
        payload: Optional[Dict[str, Any]] = None,
        event_id: str = "",
        parent_id: str = "",
        **kwargs: Any,
    ) -> str:
        """Called at the start of an event"""
        if event_type == CBEventType.LLM:
            # LLM thinking/reasoning
            asyncio.create_task(self._send_event("thinking_start", {
                "event_id": event_id,
                "prompt": payload.get("messages", [])[-1].content if payload and "messages" in payload else ""
            }))
        elif event_type == CBEventType.FUNCTION_CALL:
            # Tool call
            asyncio.create_task(self._send_event("tool_call_start", {
                "event_id": event_id,
                "tool": payload.get("tool", {}).name if payload else "unknown",
                "input": payload.get("tool_input", {}) if payload else {}
            }))
        return event_id
    
    def on_event_end(
        self,
        event_type: CBEventType,
        payload: Optional[Dict[str, Any]] = None,
        event_id: str = "",
        **kwargs: Any,
    ) -> None:
        """Called at the end of an event"""
        if event_type == CBEventType.LLM:
            # LLM response
            response = payload.get("response", {}) if payload else {}
            content = response.message.content if hasattr(response, "message") else str(response)
            asyncio.create_task(self._send_event("thinking_end", {
                "event_id": event_id,
                "thought": content
            }))
        elif event_type == CBEventType.FUNCTION_CALL:
            # Tool result
            output = payload.get("function_output", "") if payload else ""
            asyncio.create_task(self._send_event("tool_call_end", {
                "event_id": event_id,
                "result": output
            }))
    
    def start_trace(self, trace_id: Optional[str] = None) -> None:
        """Start a trace - required by BaseCallbackHandler"""
        # Implementation for trace start
        if trace_id:
            logger.debug(f"Starting trace: {trace_id}")
    
    def end_trace(
        self,
        trace_id: Optional[str] = None,
        trace_map: Optional[Dict[str, List[str]]] = None,
    ) -> None:
        """End a trace - required by BaseCallbackHandler"""
        # Implementation for trace end
        if trace_id:
            logger.debug(f"Ending trace: {trace_id}")


class HumansaOrchestratorAgentEnhanced:
    """
    Enhanced Orchestrator with comprehensive logging
    """
    
    def __init__(
        self,
        llm: LLM,
        agents: List[Any] = None,
        memory_manager: Optional[MemoryManager] = None,
        debug: bool = True,
        enable_enhanced_logging: bool = True
    ):
        self.llm = llm
        self.memory_manager = memory_manager
        self.debug = debug
        self.enable_enhanced_logging = enable_enhanced_logging
        self.stream_callback = None
        
        # Initialize enhanced logging handler
        self.enhanced_handler = EnhancedLoggingHandler() if enable_enhanced_logging else None
        
        # Initialize debug handler if needed
        self.debug_handler = LlamaDebugHandler() if debug else None
        
        # Combine handlers
        handlers = []
        if self.enhanced_handler:
            handlers.append(self.enhanced_handler)
        if self.debug_handler:
            handlers.append(self.debug_handler)
            
        self.callback_manager = CallbackManager(handlers) if handlers else None
        
        # For now, we'll use simple agent functions instead of complex agent classes
        self.agents = {}
        
        # Create tools from agent functions
        self.tools = self._create_agent_tools()
        
        # Get system prompt with React format
        current_date = datetime.now().strftime('%Y-%m-%d')
        # Use the REACT prompt which includes proper identity
        orchestrator_prompt = HUMANSA_REACT_PROMPT_V2.format(current_date=current_date)
        
        # Create orchestrator agent using new API (llama-index 0.13.0)
        self.orchestrator = ReActAgent(
            name="HumansaV2EnhancedOrchestrator",
            description="Enhanced orchestrator for HUMANSA V2 medical consultation system",
            tools=self.tools,
            llm=self.llm,
            verbose=True,  # Always verbose for agent flow visibility
            system_prompt=orchestrator_prompt,
            callback_manager=self.callback_manager
        )
        
        logger.info(f"Initialized Enhanced HumansaOrchestratorAgent with {len(self.tools)} agent tools")
        
    def _create_agent_tools(self) -> List[FunctionTool]:
        """Create tools from agents for the orchestrator to use"""
        tools = []
        
        # General Medical Agent Tool
        def general_medical_agent(query: str) -> str:
            """处理一般健康咨询、健康建议、日常保健等问题"""
            logger.info(f"🏥 General Medical Agent called with: {query}")
            
            # Simulate agent processing
            if "身份" in query or "你是谁" in query:
                return "我是诺亚新舟健康医疗助理（小诺），是一个专业的医疗AI助手。我可以为您提供健康咨询、症状分析、用药指导、预约服务等多方面的医疗健康支持。"
            
            return f"关于您的健康咨询 '{query}'：建议保持良好的生活习惯，均衡饮食，适量运动。如有具体症状，请到我们的诺亚新舟诊所进行专业咨询。"
        
        # Diagnosis Agent Tool
        def diagnosis_agent(symptoms: str) -> str:
            """分析症状并提供初步诊断建议"""
            logger.info(f"🔍 Diagnosis Agent called with symptoms: {symptoms}")
            
            if "胸痛" in symptoms or "呼吸困难" in symptoms:
                return "⚠️ 紧急情况！您描述的症状可能是严重的心脏或呼吸系统问题。请立即拨打120急救电话！"
            
            return f"根据您描述的症状 '{symptoms}'：这可能需要专业医生的诊断。建议您预约我们诺亚新舟诊所的专家进行详细检查。我们有超过500位三甲主任级名医专家为您服务。"
        
        # Medication Agent Tool
        def medication_agent(query: str) -> str:
            """提供药物信息和用药指导"""
            logger.info(f"💊 Medication Agent called with: {query}")
            
            return f"关于您的用药咨询 '{query}'：用药需要在医生指导下进行。请携带您的用药记录到诺亚新舟诊所，我们的专业医生会为您提供个性化的用药指导。"
        
        # Emergency Triage Agent Tool
        def emergency_triage_agent(situation: str) -> str:
            """评估紧急情况并提供急救建议"""
            logger.info(f"🚨 Emergency Triage Agent called with: {situation}")
            
            if any(word in situation for word in ["胸痛", "呼吸困难", "昏迷", "大出血"]):
                return "🚨 紧急情况！请立即拨打120急救电话！在等待救护车期间，请保持冷静，不要移动患者。"
            
            return f"根据您描述的情况 '{situation}'：建议您尽快到诺亚新舟诊所就诊。如果症状加重，请立即就医。"
        
        # Appointment Agent Tool
        def appointment_agent(request: str) -> str:
            """处理预约请求和诊所导航"""
            logger.info(f"📅 Appointment Agent called with: {request}")
            
            return f"关于您的预约需求 '{request}'：诺亚新舟在全国有30+家高端综合名医诊所。您可以通过诺亚新舟医疗小程序进行实时预约，或拨打客服电话咨询最近的诊所。"
        
        # Memory Search Agent Tool
        async def memory_search_agent(query: str, user_id: str = "") -> str:
            """搜索用户历史记录和偏好"""
            logger.info(f"🧠 Memory Search Agent called for user {user_id} with query: {query}")
            
            if self.memory_manager and user_id:
                try:
                    # Log Mem0 integration attempt
                    if hasattr(self.memory_manager, 'mem0_manager'):
                        logger.info("Using Mem0 for memory search")
                        if self.stream_callback:
                            await self.stream_callback({
                                "type": "memory",
                                "status": "mem0_active",
                                "user_id": user_id
                            })
                    
                    # Search memories
                    memories = await self.memory_manager.search_memories(
                        user_id=user_id,
                        query=query,
                        limit=5
                    )
                    
                    if memories:
                        memory_text = "\n".join([m.get('content', '') for m in memories[:3]])
                        if self.stream_callback:
                            await self.stream_callback({
                                "type": "memory",
                                "data": memories,
                                "count": len(memories)
                            })
                        return f"根据您的历史记录：\n{memory_text}"
                    else:
                        return "没有找到相关的历史记录。"
                except Exception as e:
                    logger.error(f"Memory search error: {e}")
                    return "无法访问历史记录。"
            
            return "需要用户ID才能搜索历史记录。"
        
        # Create FunctionTools
        tools.append(FunctionTool.from_defaults(fn=general_medical_agent, name="general_medical_agent"))
        tools.append(FunctionTool.from_defaults(fn=diagnosis_agent, name="diagnosis_agent"))
        tools.append(FunctionTool.from_defaults(fn=medication_agent, name="medication_agent"))
        tools.append(FunctionTool.from_defaults(fn=emergency_triage_agent, name="emergency_triage_agent"))
        tools.append(FunctionTool.from_defaults(fn=appointment_agent, name="appointment_agent"))
        
        # Add memory search tool if memory manager is available
        if self.memory_manager:
            # Wrap async function for sync tool
            def memory_search_wrapper(query: str) -> str:
                """Wrapper for async memory search"""
                import asyncio
                loop = asyncio.get_event_loop()
                user_id = getattr(self, '_current_user_id', '')
                return loop.run_until_complete(memory_search_agent(query, user_id))
            
            tools.append(FunctionTool.from_defaults(
                fn=memory_search_wrapper,
                name="memory_search_agent",
                description="搜索用户的历史对话记录、偏好和医疗信息"
            ))
        
        return tools
    
    async def process_query(
        self,
        query: str,
        user_id: str,
        messages: List[Dict[str, Any]] = None,
        stream: bool = True
    ) -> Any:
        """Process a query through the orchestrator with enhanced logging"""
        
        # Store current user ID for memory search
        self._current_user_id = user_id
        
        # Set stream callback if enhanced logging is enabled
        if self.enable_enhanced_logging and self.enhanced_handler:
            self.enhanced_handler.stream_callback = self._create_stream_callback() if stream else None
        
        logger.info(f"Processing query for user {user_id}: {query[:100]}...")
        
        # Log initial event
        if stream and self.enhanced_handler and self.enhanced_handler.stream_callback:
            await self.enhanced_handler.stream_callback({
                "type": "process_start",
                "user_id": user_id,
                "query": query,
                "message_count": len(messages) if messages else 0
            })
        
        # Get memory context if available
        memory_context = {}
        if self.memory_manager:
            try:
                # Log Mem0 check
                if hasattr(self.memory_manager, 'mem0_manager'):
                    if stream and self.enhanced_handler and self.enhanced_handler.stream_callback:
                        await self.enhanced_handler.stream_callback({
                            "type": "mem0_check",
                            "initialized": self.memory_manager.mem0_manager.initialized
                        })
                
                # Get user context
                memory_context = await self.memory_manager.get_user_context(user_id)
                
                if memory_context and stream and self.enhanced_handler and self.enhanced_handler.stream_callback:
                    await self.enhanced_handler.stream_callback({
                        "type": "memory_context",
                        "context": memory_context
                    })
                    
            except Exception as e:
                logger.error(f"Error getting memory context: {e}")
        
        # Build conversation with memory context
        conversation = []
        if memory_context:
            context_prompt = f"用户历史信息：{json.dumps(memory_context, ensure_ascii=False)}"
            conversation.append({"role": "system", "content": context_prompt})
        
        if messages:
            conversation.extend(messages)
        else:
            conversation.append({"role": "user", "content": query})
        
        # Process through orchestrator
        try:
            if stream:
                return self._stream_response(query, user_id, conversation)
            else:
                # Non-streaming response
                # Use run method for new API
                response_handler = self.orchestrator.run(query)
                result = await response_handler
                
                # Extract response text
                if hasattr(result, 'response'):
                    response_text = str(result.response)
                else:
                    response_text = str(result)
                
                # Create a simple response object to match expected format
                response = type('Response', (), {'response': response_text})()
                
                # Save to memory
                if self.memory_manager:
                    await self.memory_manager.add_conversation(
                        user_id=user_id,
                        query=query,
                        response=str(response),
                        metadata={"agent": "orchestrator_v2"}
                    )
                
                return self._format_openai_response(str(response), query, user_id)
                
        except Exception as e:
            logger.error(f"Error in orchestrator processing: {e}")
            raise
    
    def _create_stream_callback(self):
        """Create a stream callback for enhanced logging"""
        async def callback(event: Dict[str, Any]):
            # Format event for streaming
            yield {
                "id": f"event-{int(time.time()*1000)}",
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": "gpt-4",
                "choices": [{
                    "index": 0,
                    "delta": {
                        "role": "assistant",
                        "content": f"\n[{event['type'].upper()}] {json.dumps(event, ensure_ascii=False)}\n"
                    },
                    "finish_reason": None
                }],
                "debug": event  # Include raw event in debug field
            }
        return callback
    
    async def _stream_response(
        self,
        query: str,
        user_id: str,
        conversation: List[Dict[str, Any]]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream response with enhanced logging"""
        try:
            # Create response stream
            # Use run method for new API (no true streaming yet)
            response_handler = self.orchestrator.run(query)
            result = await response_handler
            
            # Extract response text
            if hasattr(result, 'response'):
                response_text = str(result.response)
            else:
                response_text = str(result)
            
            # Create a simple response object to match expected format
            response = type('Response', (), {'response': response_text})()
            
            chunk_id = f"chatcmpl-{int(time.time())}"
            full_response = ""
            
            # Stream the response
            async for token in response.async_response_gen():
                full_response += token
                
                # Yield content chunk
                yield {
                    "id": chunk_id,
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": "gpt-4",
                    "choices": [{
                        "index": 0,
                        "delta": {
                            "content": token
                        },
                        "finish_reason": None
                    }]
                }
                
                # Also yield debug events if available
                if self.enhanced_handler and self.enhanced_handler.events:
                    for event in self.enhanced_handler.events:
                        yield {
                            "id": f"debug-{int(time.time()*1000)}",
                            "object": "debug.event",
                            "created": int(time.time()),
                            "type": "debug",
                            "event": event
                        }
                    self.enhanced_handler.events.clear()
            
            # Save conversation to memory
            if self.memory_manager and full_response:
                await self.memory_manager.add_conversation(
                    user_id=user_id,
                    query=query,
                    response=full_response,
                    metadata={
                        "agent": "orchestrator_v2_enhanced",
                        "streamed": True
                    }
                )
            
            # Send final chunk
            yield {
                "id": chunk_id,
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": "gpt-4",
                "choices": [{
                    "index": 0,
                    "delta": {},
                    "finish_reason": "stop"
                }]
            }
            
        except Exception as e:
            logger.error(f"Error in _stream_response: {e}")
            # Yield error chunk
            yield {
                "id": f"chatcmpl-{int(time.time())}",
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": "gpt-4",
                "choices": [{
                    "index": 0,
                    "delta": {
                        "content": f"\nError: {str(e)}"
                    },
                    "finish_reason": "stop"
                }],
                "error": str(e)
            }
    
    def _format_openai_response(
        self,
        content: str,
        query: str,
        user_id: str
    ) -> Dict[str, Any]:
        """Format response in OpenAI API format with debug info"""
        # Include debug events if available
        debug_info = {}
        if self.enhanced_handler and self.enhanced_handler.events:
            debug_info["events"] = self.enhanced_handler.events
            debug_info["agent_count"] = len([e for e in self.enhanced_handler.events if e["type"] == "tool_call_start"])
            debug_info["thinking_steps"] = len([e for e in self.enhanced_handler.events if e["type"] == "thinking_start"])
        
        # Estimate token usage (rough approximation)
        prompt_tokens = len(query.split()) * 2
        completion_tokens = len(content.split()) * 2
        
        response = {
            "id": f"chatcmpl-{int(time.time())}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": "gpt-4",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": content
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens
            },
            "system_fingerprint": f"humansa_v2_orchestrator_enhanced_{user_id}"
        }
        
        # Add debug info if available
        if debug_info:
            response["debug"] = debug_info
        
        return response