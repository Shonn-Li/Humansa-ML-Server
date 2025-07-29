"""
HUMANSA V2 Orchestrator Agent with Consolidated Tools
Uses 7 core tools with dynamic loading based on query context
"""

import os
import logging
from typing import List, Dict, Any, Optional, AsyncGenerator
from datetime import datetime
import asyncio
import json

# LlamaIndex imports
try:
    from llama_index.core.agent import ReActAgent
    from llama_index.core.tools import FunctionTool
    from llama_index.core.callbacks import CallbackManager, LlamaDebugHandler
    from llama_index.core import Settings
    from llama_index.llms.openai import OpenAI
    
    LLAMAINDEX_AVAILABLE = True
except ImportError:
    LLAMAINDEX_AVAILABLE = False
    logging.warning("LlamaIndex not available - agent features disabled")

# Import consolidated tools
try:
    from humansa.tools.consolidated_tools import ConsolidatedHumansaTools, DynamicToolLoader
    CONSOLIDATED_TOOLS_AVAILABLE = True
except ImportError:
    CONSOLIDATED_TOOLS_AVAILABLE = False
    logging.warning("Consolidated tools not available")

logger = logging.getLogger(__name__)


class HumansaOrchestratorAgentConsolidated:
    """
    Orchestrator agent that uses consolidated tools with dynamic loading
    """
    
    def __init__(
        self,
        llm: Optional[Any] = None,
        memory_manager: Optional[Any] = None,
        debug: bool = False,
        use_real_tools: bool = True,
        db_config: Optional[Dict[str, Any]] = None
    ):
        """Initialize the orchestrator with consolidated tools"""
        
        if not LLAMAINDEX_AVAILABLE:
            raise ImportError("LlamaIndex is required for HumansaOrchestratorAgentConsolidated")
        
        self.llm = llm or Settings.llm
        self.memory_manager = memory_manager
        self.debug = debug
        self.use_real_tools = use_real_tools and CONSOLIDATED_TOOLS_AVAILABLE
        
        # Initialize debug handler if needed
        self.debug_handler = LlamaDebugHandler() if debug else None
        self.callback_manager = CallbackManager([self.debug_handler]) if self.debug_handler else None
        
        # Initialize consolidated tool manager
        self.tool_manager = None
        self.dynamic_loader = None
        if self.use_real_tools:
            try:
                self.tool_manager = ConsolidatedHumansaTools(memory_manager=memory_manager)
                self.dynamic_loader = DynamicToolLoader(self.tool_manager)
                logger.info("✅ Initialized consolidated tools (7 core functions)")
            except Exception as e:
                logger.error(f"❌ Failed to initialize consolidated tools: {e}")
                self.use_real_tools = False
        
        # Get current date
        current_date = datetime.now().strftime('%Y-%m-%d')
        
        # Use the official HUMANSA V2 system prompt
        from humansa.prompts.humansa_system_prompt_v2 import HUMANSA_REACT_PROMPT_V2
        
        # Get the complete system prompt with React format
        orchestrator_prompt = HUMANSA_REACT_PROMPT_V2.format(current_date=current_date)
        
        # Create base agent with minimal tools (will be updated per query)
        base_tools = self._get_base_tools()
        self.base_agent = ReActAgent.from_tools(
            tools=base_tools,
            llm=self.llm,
            verbose=self.debug,
            system_prompt=orchestrator_prompt,
            callback_manager=self.callback_manager,
            max_iterations=10
        )
        
        logger.info(f"✅ HumansaOrchestratorAgentConsolidated initialized with dynamic tool loading")
    
    def _get_base_tools(self) -> List[FunctionTool]:
        """Get minimal base tools for initialization"""
        if self.use_real_tools and self.tool_manager:
            # Just return search and memory tools for base
            all_tools = self.tool_manager.get_llamaindex_tools()
            base_tool_names = ['unified_search', 'conversation_memory']
            return [t for t in all_tools if t.name in base_tool_names]
        else:
            # Fallback to simple tools
            return self._create_simple_tools()
    
    def _create_simple_tools(self) -> List[FunctionTool]:
        """Create simple fallback tools"""
        async def simple_search(query: str) -> str:
            return f"搜索结果：{query}（模拟模式）"
        
        return [
            FunctionTool.from_defaults(
                fn=simple_search,
                name="simple_search",
                description="简单搜索工具"
            )
        ]
    
    def _create_agent_for_query(self, query: str) -> ReActAgent:
        """Create an agent with dynamically selected tools based on query"""
        if self.use_real_tools and self.dynamic_loader:
            # Select tools based on query context
            selected_tools = self.dynamic_loader.select_tools_for_query(query)
            logger.info(f"🎯 Selected {len(selected_tools)} tools for query: {[t.name for t in selected_tools]}")
        else:
            selected_tools = self._get_base_tools()
        
        # Get current date
        current_date = datetime.now().strftime('%Y-%m-%d')
        
        # Use the official prompt
        from humansa.prompts.humansa_system_prompt_v2 import HUMANSA_REACT_PROMPT_V2
        orchestrator_prompt = HUMANSA_REACT_PROMPT_V2.format(current_date=current_date)
        
        # Create agent with selected tools
        return ReActAgent.from_tools(
            tools=selected_tools,
            llm=self.llm,
            verbose=self.debug,
            system_prompt=orchestrator_prompt,
            callback_manager=self.callback_manager,
            max_iterations=10
        )
    
    async def process_query(
        self,
        query: str,
        user_id: Optional[str] = None,
        messages: Optional[List[Dict[str, str]]] = None,
        stream: bool = False
    ) -> Any:
        """Process a query with dynamically selected tools"""
        
        logger.info(f"🎯 Processing query with consolidated tools: {query[:100]}...")
        
        # Create agent with tools selected for this specific query
        agent = self._create_agent_for_query(query)
        
        # Load relevant memories if available
        context = ""
        if self.memory_manager and user_id:
            try:
                # Use conversation_memory tool to get context
                memory_result = await self.tool_manager.conversation_memory(
                    action="retrieve",
                    user_id=user_id,
                    memory_type="general",
                    time_range="recent"
                )
                if memory_result.get("success") and memory_result.get("memories"):
                    context = f"用户历史记忆：{json.dumps(memory_result['memories'], ensure_ascii=False)}\n\n"
            except Exception as e:
                logger.warning(f"Failed to load memories: {e}")
        
        # Add message history to context
        if messages:
            context += "对话历史：\n"
            for msg in messages[-6:]:  # Last 6 messages
                role = "用户" if msg["role"] == "user" else "助手"
                context += f"{role}: {msg['content']}\n"
            context += "\n"
        
        # Combine context with query
        full_query = f"{context}当前查询：{query}" if context else query
        
        try:
            if stream:
                # Stream response
                return await self._stream_response(agent, full_query, user_id)
            else:
                # Get complete response
                response = await asyncio.to_thread(agent.chat, full_query)
                
                # Save important information to memory if available
                if self.memory_manager and user_id:
                    await self._save_to_memory(user_id, query, str(response))
                
                # Extract tools used
                tools_used = []
                if hasattr(response, 'sources') and response.sources:
                    for source in response.sources:
                        if hasattr(source, 'tool_name'):
                            tools_used.append(source.tool_name)
                
                return {
                    "response": str(response),
                    "tools_used": list(set(tools_used)),
                    "tool_selection_strategy": "dynamic",
                    "total_tools_available": 7,
                    "tools_loaded": len(agent.tools)
                }
                
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return {
                "response": f"抱歉，处理您的请求时遇到了问题：{str(e)}",
                "error": str(e),
                "tools_used": []
            }
    
    async def _stream_response(
        self,
        agent: ReActAgent,
        query: str,
        user_id: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream response from agent"""
        try:
            # Use agent's stream_chat method
            streaming_response = agent.stream_chat(query)
            
            accumulated_response = ""
            tools_used = []
            
            async for chunk in streaming_response.async_response_gen():
                # Track accumulated response
                accumulated_response += chunk
                
                # Yield chunk in OpenAI format
                yield {
                    "choices": [{
                        "delta": {"content": chunk},
                        "index": 0
                    }]
                }
            
            # After streaming completes, save to memory
            if self.memory_manager and user_id and accumulated_response:
                await self._save_to_memory(user_id, query, accumulated_response)
            
            # Extract tools used from the response
            if hasattr(streaming_response, 'sources') and streaming_response.sources:
                for source in streaming_response.sources:
                    if hasattr(source, 'tool_name'):
                        tools_used.append(source.tool_name)
            
            # Send final metadata
            yield {
                "choices": [{
                    "delta": {},
                    "finish_reason": "stop",
                    "index": 0
                }],
                "tools_used": list(set(tools_used))
            }
            
        except Exception as e:
            logger.error(f"Error in stream response: {e}")
            yield {
                "choices": [{
                    "delta": {"content": f"\n\n错误：{str(e)}"},
                    "finish_reason": "error",
                    "index": 0
                }]
            }
    
    async def _save_to_memory(self, user_id: str, query: str, response: str):
        """Save important information from conversation to memory"""
        try:
            # Extract key information
            important_keywords = ['预约', '过敏', '病史', '用药', '诊断', '建议']
            is_important = any(keyword in query or keyword in response for keyword in important_keywords)
            
            if is_important:
                content = {
                    "query": query,
                    "response": response,
                    "timestamp": datetime.now().isoformat(),
                    "importance": "high"
                }
                
                await self.tool_manager.conversation_memory(
                    action="save",
                    user_id=user_id,
                    memory_type="medical_history" if any(k in query for k in ['病史', '过敏', '用药']) else "general",
                    content=content
                )
                logger.info(f"💾 Saved important information to memory for user {user_id}")
                
        except Exception as e:
            logger.warning(f"Failed to save to memory: {e}")
    
    def get_tool_statistics(self) -> Dict[str, Any]:
        """Get statistics about tool usage"""
        if self.tool_manager:
            all_tools = self.tool_manager.get_llamaindex_tools()
            return {
                "total_tools": 7,
                "tool_names": [t.name for t in all_tools],
                "dynamic_loading": True,
                "context_aware": True
            }
        else:
            return {
                "total_tools": 0,
                "tool_names": [],
                "dynamic_loading": False,
                "context_aware": False
            }