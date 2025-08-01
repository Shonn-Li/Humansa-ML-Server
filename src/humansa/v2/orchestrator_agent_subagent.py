"""
HUMANSA V2 Orchestrator with Sub-Agent Architecture
Uses specialized sub-agents as tools for the main orchestrator
"""

import os
import logging
import json
import time
import uuid
from typing import List, Dict, Any, Optional, AsyncGenerator
from datetime import datetime
import asyncio

# LlamaIndex imports
try:
    from llama_index.core.agent import ReActAgent
    from llama_index.core.tools import FunctionTool
    from llama_index.core.callbacks import CallbackManager, LlamaDebugHandler
    from llama_index.core import Settings
    from llama_index.core.callbacks.base import BaseCallbackHandler
    from llama_index.core.callbacks.schema import CBEventType
    
    LLAMAINDEX_AVAILABLE = True
except ImportError:
    LLAMAINDEX_AVAILABLE = False
    logging.warning("LlamaIndex not available - agent features disabled")

# Import agent tool wrapper - use absolute import to avoid issues
try:
    from .agent_tool_wrapper import create_subagent_tools
    from .response_agent import HumansaResponseAgent
except ImportError:
    # Try absolute import path
    from src.humansa.v2.agent_tool_wrapper import create_subagent_tools
    from src.humansa.v2.response_agent import HumansaResponseAgent

logger = logging.getLogger(__name__)


class SubAgentOrchestrator:
    """
    Orchestrator that uses specialized sub-agents as tools
    Implements LlamaIndex Pattern 2: Agents as Tools
    """
    
    def __init__(
        self,
        llm: Optional[Any] = None,
        memory_manager: Optional[Any] = None,
        debug: bool = False,
        db_config: Optional[Dict[str, Any]] = None
    ):
        """Initialize the sub-agent orchestrator"""
        
        if not LLAMAINDEX_AVAILABLE:
            raise ImportError("LlamaIndex is required for SubAgentOrchestrator")
        
        self.llm = llm or Settings.llm
        self.memory_manager = memory_manager
        self.debug = debug
        self.db_config = db_config
        
        # Initialize debug handler if needed
        self.debug_handler = LlamaDebugHandler() if debug else None
        
        # Create callback manager
        handlers = []
        if self.debug_handler:
            handlers.append(self.debug_handler)
        self.callback_manager = CallbackManager(handlers) if handlers else None
        
        # Initialize response agent for post-processing
        self.response_agent = HumansaResponseAgent()
        
        # Create sub-agent tools
        self.agent_tools = create_subagent_tools(
            llm=self.llm,
            memory_manager=memory_manager,
            db_config=db_config
        )
        
        # Get current date
        current_date = datetime.now().strftime('%Y-%m-%d')
        
        # Create system prompt for orchestrator
        self.system_prompt = f"""你是诺亚新舟健康医疗助理的主协调器。

今天是{current_date}。

你的职责是：
1. 理解用户的问题和需求
2. 选择合适的专业子代理来处理用户请求
3. 协调多个子代理的响应（如果需要）
4. 确保响应的连贯性和完整性

可用的专业子代理：

1. **产品推荐代理 (product_recommendation_agent)**
   - 处理所有产品相关查询
   - 保健品、医疗器械推荐
   - 价格和优惠信息
   - 健康商城购物指导

2. **预约挂号代理 (appointment_booking_agent)**
   - 医生预约和排班查询
   - 预约、改期、取消操作
   - 就诊准备指导

3. **临床分析代理 (clinical_analysis_agent)**
   - 症状分析和评估
   - 紧急情况识别（120急救）
   - 科室推荐
   - 疾病风险评估

4. **用药指导代理 (medication_guidance_agent)**
   - 药物使用指导
   - 药物相互作用检查
   - 用药注意事项

5. **综合医疗代理 (general_medical_agent)**
   - 一般健康咨询
   - 保险政策信息
   - 诊所位置查询
   - 健康知识科普

工作流程：
1. 分析用户查询，确定需求类型
2. 选择最合适的子代理处理
3. 如果需要多个方面的信息，可以调用多个子代理
4. 整合所有响应，提供完整答案

重要原则：
- 紧急医疗情况立即使用临床分析代理
- 产品相关问题必须使用产品推荐代理
- 预约相关必须使用预约挂号代理
- 可以组合使用多个代理提供全面服务

记住：你是协调器，不直接回答医疗问题，而是通过调用合适的子代理来获取专业答案。"""
        
        # Create main orchestrator agent with sub-agents as tools
        self.agent = self._create_orchestrator_agent()
        
        logger.info(f"✅ Initialized SubAgentOrchestrator with {len(self.agent_tools)} sub-agent tools")
        
    def _create_orchestrator_agent(self) -> ReActAgent:
        """Create the main orchestrator ReAct agent"""
        
        return ReActAgent.from_tools(
            tools=self.agent_tools,
            llm=self.llm,
            verbose=self.debug,
            system_prompt=self.system_prompt,
            callback_manager=self.callback_manager,
            max_iterations=10
        )
    
    async def process_query(
        self,
        query: str,
        user_id: str,
        messages: List[Dict[str, Any]] = None,
        stream: bool = True,
        session_id: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Process a query through the sub-agent orchestrator"""
        
        try:
            # Load user context from memory
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
                # Stream response
                async for chunk in self._process_streaming(enhanced_query, user_id, session_id):
                    yield chunk
            else:
                # Non-streaming response
                response = await self.agent.achat(enhanced_query)
                
                # Post-process with response agent
                # Response agent expects a dict with 'output' key
                response_dict = {
                    "output": [{"content": response.response}]
                }
                final_response = self.response_agent.process_response(
                    response_dict,
                    query
                )
                
                yield {
                    "id": f"chatcmpl-{uuid.uuid4()}",
                    "object": "chat.completion",
                    "created": int(time.time()),
                    "model": "humansa-v2-subagent",
                    "choices": [{
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": final_response
                        },
                        "finish_reason": "stop"
                    }]
                }
                
                # Store conversation if memory manager available
                if self.memory_manager:
                    await self._store_conversation(user_id, query, final_response, session_id)
                    
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
    
    async def _process_streaming(
        self,
        query: str,
        user_id: str,
        session_id: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Process query with streaming response"""
        
        try:
            # Get streaming response from agent
            response = await self.agent.astream_chat(query)
            
            # Stream ID for this response
            stream_id = f"chatcmpl-{uuid.uuid4()}"
            
            # Collect full response for storage
            full_response = []
            
            # Stream chunks
            async for chunk in response.async_response_gen():
                if chunk:
                    full_response.append(chunk)
                    
                    # Create OpenAI-compatible chunk
                    yield {
                        "id": stream_id,
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": "humansa-v2-subagent",
                        "choices": [{
                            "index": 0,
                            "delta": {
                                "content": chunk
                            },
                            "finish_reason": None
                        }]
                    }
            
            # Send finish chunk
            yield {
                "id": stream_id,
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": "humansa-v2-subagent",
                "choices": [{
                    "index": 0,
                    "delta": {},
                    "finish_reason": "stop"
                }]
            }
            
            # Post-process full response
            complete_response = ''.join(full_response)
            final_response = self.response_agent.process_response(
                complete_response,
                {"query": query}
            )
            
            # Store conversation
            if self.memory_manager:
                await self._store_conversation(user_id, query, final_response, session_id)
                
        except Exception as e:
            logger.error(f"Error in streaming: {e}")
            yield {
                "error": {
                    "message": str(e),
                    "type": "streaming_error"
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
        response: str,
        session_id: Optional[str] = None
    ):
        """Store conversation in memory"""
        
        try:
            metadata = {
                "session_id": session_id or str(uuid.uuid4()),
                "timestamp": datetime.now().isoformat(),
                "orchestrator": "subagent",
                "model": "humansa-v2"
            }
            
            await self.memory_manager.add_conversation(
                user_id=user_id,
                query=query,
                response=response,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Failed to store conversation: {e}")


# Convenience function for initialization
def create_subagent_orchestrator(
    llm: Any,
    memory_manager: Optional[Any] = None,
    debug: bool = False,
    db_config: Optional[Dict[str, Any]] = None
) -> SubAgentOrchestrator:
    """
    Create a sub-agent orchestrator instance
    
    Args:
        llm: Language model instance
        memory_manager: Memory manager for context
        debug: Enable debug logging
        db_config: Database configuration
        
    Returns:
        SubAgentOrchestrator instance
    """
    
    return SubAgentOrchestrator(
        llm=llm,
        memory_manager=memory_manager,
        debug=debug,
        db_config=db_config
    )