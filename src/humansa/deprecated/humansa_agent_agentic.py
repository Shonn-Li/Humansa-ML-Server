"""
Humansa Agentic Agent - Fully LLM-Driven Tool Selection

This agent operates in fully agentic mode where ALL tool selection and argument
extraction is performed by the LLM using structured schemas. NO heuristic patterns
or regex-based tool selection.

Key Features:
- LLM-only tool selection via LlamaIndex ReActAgent
- Structured Pydantic schemas for all tool arguments  
- Observable tool calls via CallbackManager
- Fail-fast if agent is unhealthy (no fallbacks)
- Business/safety rules enforced in system prompt only
"""

import logging
from typing import Dict, Any, List, Optional
import json
from datetime import datetime

logger = logging.getLogger(__name__)

# LlamaIndex imports for agentic functionality
try:
    from llama_index.core.agent import ReActAgent, AgentRunner
    from llama_index.core.llms import LLM
    from llama_index.core.tools import BaseTool
    from llama_index.core.callbacks import CallbackManager
    from llama_index.core.memory import ChatMemoryBuffer
    from llama_index.core.chat_engine.types import ChatMode
    LLAMAINDEX_AVAILABLE = True
except ImportError as e:
    logger.warning(f"LlamaIndex not fully available for agentic agent: {e}")
    LLAMAINDEX_AVAILABLE = False


class HumansaAgenticAgent:
    """
    Fully Agentic Humansa AI Agent.
    
    ALL tool selection and argument extraction is performed by the LLM agent
    using structured schemas. NO heuristic patterns or fallback logic.
    """

    def __init__(self, llm: Optional[LLM] = None, tools: Optional[List[BaseTool]] = None, 
                 callback_manager: Optional[CallbackManager] = None):
        """Initialize the fully agentic agent."""
        self.llm = llm
        self.tools = tools or []
        self.callback_manager = callback_manager
        self.agent = None
        self.memory = None
        
        # Initialize ReAct agent if LlamaIndex is available
        if LLAMAINDEX_AVAILABLE and self.llm and self.tools:
            self._initialize_react_agent()
        
        logger.info(f"🤖 HumansaAgenticAgent initialized with {len(self.tools)} tools")
        if self.agent:
            logger.info("✅ ReAct agent successfully initialized - FULLY AGENTIC MODE")
        else:
            logger.warning("❌ ReAct agent initialization failed - agent will be unhealthy")

    def _initialize_react_agent(self):
        """Initialize LlamaIndex ReAct agent with tools and memory."""
        try:
            # Initialize chat memory for conversation context
            self.memory = ChatMemoryBuffer.from_defaults(token_limit=4000)
            
            # Create ReAct agent with tools
            self.agent = ReActAgent.from_tools(
                tools=self.tools,
                llm=self.llm,
                memory=self.memory,
                callback_manager=self.callback_manager,
                verbose=True,
                max_iterations=8  # Limit iterations to prevent loops
            )
            
            logger.info("🧠 ReAct agent initialized with structured tool calling")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize ReAct agent: {e}")
            self.agent = None

    def is_healthy(self) -> bool:
        """Check if the agent is healthy and ready for operation."""
        healthy = (
            LLAMAINDEX_AVAILABLE and 
            self.llm is not None and 
            self.agent is not None and
            len(self.tools) > 0
        )
        
        if not healthy:
            logger.warning("⚠️ Agent health check failed")
            if not LLAMAINDEX_AVAILABLE:
                logger.warning("  - LlamaIndex not available")
            if self.llm is None:
                logger.warning("  - No LLM configured")
            if self.agent is None:
                logger.warning("  - ReAct agent not initialized")
            if len(self.tools) == 0:
                logger.warning("  - No tools available")
        
        return healthy

    async def execute_with_tools(self, query: str, conversation_history: List[Dict], 
                                context_results: List, user_id: str) -> Dict[str, Any]:
        """
        Execute query with full agentic tool calling.
        
        The LLM agent decides which tools to call and with what arguments.
        NO heuristic tool selection or argument extraction.
        
        Args:
            query: The user query
            conversation_history: Full conversation history for context
            context_results: Retrieved context from RAG/attachments/web
            user_id: User identifier
            
        Returns:
            Dict containing agent response and tool results
        """
        start_time = datetime.now()
        
        try:
            logger.info(f"🚀 AGENTIC EXECUTION started for query: '{query[:100]}...'")
            
            # Fail fast if agent is not healthy
            if not self.is_healthy():
                raise RuntimeError("Agent is not healthy - cannot execute in agentic mode")
            
            # Prepare enhanced query with context
            enhanced_query = self._prepare_enhanced_query(
                query, conversation_history, context_results, user_id
            )
            
            logger.info(f"📝 Enhanced query prepared: {len(enhanced_query)} characters")
            
            # Execute with ReAct agent - LLM decides all tool calls
            logger.info("🤖 Executing with ReAct agent - LLM controls all tool selection")
            agent_response = await self._execute_with_react_agent(enhanced_query)
            
            # Extract tool calls from callback manager
            tool_calls_observed = []
            if self.callback_manager:
                # Get tool calls from callback handler
                for handler in self.callback_manager.handlers:
                    if hasattr(handler, 'get_tool_calls'):
                        tool_calls_observed.extend(handler.get_tool_calls())
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            result = {
                'agent_response': agent_response,
                'tool_results': self._extract_tool_results_from_response(agent_response),
                'tool_calls_observed': tool_calls_observed,
                'reasoning': f"Agent executed {len(tool_calls_observed)} tool calls autonomously",
                'confidence': 1.0,  # High confidence in agentic mode
                'execution_time': execution_time,
                'mode': 'fully_agentic',
                'query': query,
                'user_id': user_id
            }
            
            logger.info(f"✅ AGENTIC EXECUTION completed in {execution_time:.2f}s")
            logger.info(f"📊 Tools observed: {len(tool_calls_observed)}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Agentic execution failed: {e}")
            import traceback
            traceback.print_exc()
            
            return {
                'error': str(e),
                'tool_results': [],
                'tool_calls_observed': [],
                'reasoning': f'Agentic execution failed: {str(e)}',
                'confidence': 0.0,
                'mode': 'failed',
                'query': query,
                'user_id': user_id
            }

    def _prepare_enhanced_query(self, query: str, conversation_history: List[Dict], 
                               context_results: List, user_id: str) -> str:
        """Prepare enhanced query with conversation context and available information."""
        
        # Build context summary
        context_summary = ""
        if context_results:
            context_summary = f"\\n\\nAvailable Context: {len(context_results)} sources retrieved."
        
        # Build conversation context
        conversation_context = ""
        if len(conversation_history) > 1:
            recent_messages = conversation_history[-3:]  # Last 3 messages for context
            conversation_context = "\\n\\nRecent Conversation:"
            for msg in recent_messages:
                role = msg.get('role', 'unknown')
                content = str(msg.get('content', ''))[:200]  # Truncate long messages
                conversation_context += f"\\n{role}: {content}"
        
        enhanced_query = f"""User Query: {query}
User ID: {user_id}
Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{conversation_context}
{context_summary}

Please process this query using the appropriate tools. Call tools with structured arguments only."""
        
        return enhanced_query

    async def _execute_with_react_agent(self, enhanced_query: str) -> str:
        """Execute the query with ReAct agent."""
        try:
            # Use async chat if available, otherwise sync
            if hasattr(self.agent, 'achat'):
                response = await self.agent.achat(enhanced_query)
            else:
                # Fallback to sync chat
                response = self.agent.chat(enhanced_query)
            
            # Extract response text
            if hasattr(response, 'response'):
                return str(response.response)
            else:
                return str(response)
                
        except Exception as e:
            logger.error(f"❌ ReAct agent execution failed: {e}")
            raise

    def _extract_tool_results_from_response(self, agent_response: str) -> List[Dict]:
        """Extract tool execution results from agent response."""
        # This is a simplified extraction - in a real implementation,
        # tool results would be captured more systematically via callbacks
        tool_results = []
        
        # Try to extract any tool execution information from the response
        if "tool" in agent_response.lower() or "function" in agent_response.lower():
            tool_results.append({
                'tool': 'agent_executed_tools',
                'result': 'Tools were executed by the agent',
                'success': True,
                'method': 'agentic'
            })
        
        return tool_results

    def get_agent_memory(self) -> Optional[Dict]:
        """Get the current agent memory/conversation state."""
        if self.memory:
            try:
                # Get chat history from memory
                chat_history = self.memory.get_all()
                return {
                    'messages': [str(msg) for msg in chat_history],
                    'token_count': len(str(chat_history)),
                    'memory_type': 'ChatMemoryBuffer'
                }
            except Exception as e:
                logger.warning(f"Failed to extract agent memory: {e}")
        
        return None

    def reset_agent_memory(self):
        """Reset the agent's conversation memory."""
        if self.memory:
            try:
                self.memory.reset()
                logger.info("🧠 Agent memory reset")
            except Exception as e:
                logger.warning(f"Failed to reset agent memory: {e}")

    def get_available_tools(self) -> List[Dict]:
        """Get information about available tools."""
        tools_info = []
        for tool in self.tools:
            tool_info = {
                'name': getattr(tool, 'metadata', {}).get('name', 'unknown'),
                'description': getattr(tool, 'metadata', {}).get('description', 'No description'),
                'schema': getattr(tool, 'fn_schema', None)
            }
            tools_info.append(tool_info)
        
        return tools_info

    def validate_tool_arguments(self, tool_name: str, arguments: Dict) -> Dict[str, Any]:
        """Validate tool arguments against schemas (for debugging)."""
        for tool in self.tools:
            if getattr(tool, 'metadata', {}).get('name') == tool_name:
                if hasattr(tool, 'fn_schema') and tool.fn_schema:
                    try:
                        # Validate arguments against Pydantic schema
                        validated = tool.fn_schema(**arguments)
                        return {
                            'valid': True,
                            'validated_args': validated.dict(),
                            'tool_name': tool_name
                        }
                    except Exception as e:
                        return {
                            'valid': False,
                            'error': str(e),
                            'tool_name': tool_name,
                            'provided_args': arguments
                        }
        
        return {
            'valid': False,
            'error': f'Tool {tool_name} not found',
            'tool_name': tool_name,
            'provided_args': arguments
        }
