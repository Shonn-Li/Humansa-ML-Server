"""
Enhanced Humansa Agentic Agent with Strict Tool Routing
"""

import logging
from typing import Dict, Any, List, Optional
import json
from datetime import datetime
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

logger = logging.getLogger(__name__)

# Import the enhanced system prompt
from humansa_agent_system_prompt import HUMANSA_REACT_SYSTEM_PROMPT, get_tool_for_query, validate_tool_choice

# LlamaIndex imports for agentic functionality
try:
    from llama_index.core.agent import ReActAgent, AgentRunner
    from llama_index.core.llms import LLM
    from llama_index.core.tools import BaseTool
    from llama_index.core.callbacks import CallbackManager
    from llama_index.core.memory import ChatMemoryBuffer
    from llama_index.core.chat_engine.types import ChatMode
    from llama_index.core import PromptTemplate
    LLAMAINDEX_AVAILABLE = True
except ImportError as e:
    logger.warning(f"LlamaIndex not fully available for agentic agent: {e}")
    LLAMAINDEX_AVAILABLE = False


class HumansaAgenticAgentEnhanced:
    """
    Enhanced Humansa AI Agent with strict tool routing and ReAct format enforcement.
    """

    def __init__(self, llm: Optional[LLM] = None, tools: Optional[List[BaseTool]] = None,
                 callback_manager: Optional[CallbackManager] = None):
        """Initialize the enhanced agent with tool filtering."""
        self.llm = llm
        self.tools = tools or []
        self.callback_manager = callback_manager
        self.agent = None
        self.memory = None
        
        # Filter out search_web tool if present
        self.tools = [tool for tool in self.tools if tool.metadata.name != "search_web"]
        logger.info(f"🚫 Filtered out search_web tool. Available tools: {[t.metadata.name for t in self.tools]}")

        # Initialize ReAct agent if LlamaIndex is available
        if LLAMAINDEX_AVAILABLE and self.llm and self.tools:
            self._initialize_react_agent()

        logger.info(f"🤖 HumansaAgenticAgentEnhanced initialized with {len(self.tools)} tools")

    def _initialize_react_agent(self):
        """Initialize LlamaIndex ReAct agent with enhanced system prompt."""
        try:
            # Initialize chat memory for conversation context
            self.memory = ChatMemoryBuffer.from_defaults(token_limit=4000)

            # Create the enhanced system prompt template
            react_system_header = PromptTemplate(HUMANSA_REACT_SYSTEM_PROMPT)

            # Create ReAct agent with tools and custom prompt
            self.agent = ReActAgent.from_tools(
                tools=self.tools,
                llm=self.llm,
                memory=self.memory,
                callback_manager=self.callback_manager,
                verbose=True,
                max_iterations=30,
                react_chat_formatter=react_system_header
            )

            logger.info("🧠 ReAct agent initialized with enhanced Humansa system prompt")

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
        return healthy

    async def execute_with_tools(self, query: str, conversation_history: List[Dict],
                                 context_results: List, user_id: str) -> Dict[str, Any]:
        """
        Execute query with enhanced tool routing and ReAct format.
        """
        start_time = datetime.now()

        try:
            logger.info(f"🚀 ENHANCED AGENTIC EXECUTION for: '{query[:100]}...'")

            # Fail fast if agent is not healthy
            if not self.is_healthy():
                raise RuntimeError("Agent is not healthy - cannot execute")

            # Check if query requires specific tool routing
            suggested_tool = get_tool_for_query(query)
            if suggested_tool:
                logger.info(f"📌 Suggested tool for query: {suggested_tool}")

            # Prepare enhanced query
            enhanced_query = self._prepare_enhanced_query(
                query, conversation_history, context_results, user_id, suggested_tool
            )

            # Execute with ReAct agent
            agent_response = await self._execute_with_react_agent(enhanced_query)

            # Extract and validate tool calls
            tool_calls_observed = []
            full_trace = ""
            
            if self.callback_manager:
                for handler in self.callback_manager.handlers:
                    if hasattr(handler, 'get_trace'):
                        full_trace = handler.get_trace()
                    if hasattr(handler, 'get_tool_calls'):
                        tool_calls_observed.extend(handler.get_tool_calls())

            # Validate tool choices
            for tool_call in tool_calls_observed:
                tool_name = tool_call.get('tool_name', '')
                if not validate_tool_choice(query, tool_name):
                    logger.warning(f"⚠️ Invalid tool choice '{tool_name}' for query")

            execution_time = (datetime.now() - start_time).total_seconds()

            result = {
                'agent_response': agent_response,
                'agent_trace': full_trace,
                'tool_results': self._extract_tool_results(agent_response, tool_calls_observed),
                'tool_calls_observed': tool_calls_observed,
                'reasoning': f"Enhanced agent executed {len(tool_calls_observed)} tool calls",
                'confidence': 1.0,
                'execution_time': execution_time,
                'mode': 'enhanced_agentic',
                'query': query,
                'user_id': user_id
            }

            logger.info(f"✅ ENHANCED EXECUTION completed in {execution_time:.2f}s")
            return result

        except Exception as e:
            logger.error(f"❌ Enhanced execution failed: {e}")
            import traceback
            traceback.print_exc()

            return {
                'error': str(e),
                'tool_results': [],
                'tool_calls_observed': [],
                'reasoning': f'Enhanced execution failed: {str(e)}',
                'confidence': 0.0,
                'mode': 'failed',
                'query': query,
                'user_id': user_id
            }

    def _prepare_enhanced_query(self, query: str, conversation_history: List[Dict],
                                context_results: List, user_id: str, suggested_tool: str = None) -> str:
        """Prepare enhanced query with tool routing hints."""
        
        # Build conversation context
        conversation_context = ""
        if len(conversation_history) > 1:
            recent_messages = conversation_history[-3:]
            conversation_context = "\n\nRecent Conversation:"
            for msg in recent_messages:
                role = msg.get('role', 'unknown')
                content = str(msg.get('content', ''))[:200]
                conversation_context += f"\n{role}: {content}"

        # Add tool routing hint if applicable
        tool_hint = ""
        if suggested_tool:
            tool_hint = f"\n\nIMPORTANT: Based on the query, you should use the '{suggested_tool}' tool."

        enhanced_query = f"""User Query: {query}
User ID: {user_id}
Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{conversation_context}
{tool_hint}

Remember to follow the strict ReAct format:
1. Thought: Analyze what the user needs
2. Action: Choose the appropriate tool
3. Action Input: Provide exact parameters
4. Observation: Review the tool output
5. Answer: Provide the final response

NEVER use search_web for Humansa internal data."""

        return enhanced_query

    async def _execute_with_react_agent(self, enhanced_query: str) -> str:
        """Execute with enhanced ReAct agent."""
        try:
            if hasattr(self.agent, 'achat'):
                response = await self.agent.achat(enhanced_query)
            else:
                response = self.agent.chat(enhanced_query)

            # Extract response
            final_answer = str(response.response) if hasattr(response, 'response') else str(response)
            
            # Try to get full reasoning chain from memory
            if hasattr(self.agent, 'memory') and self.agent.memory:
                try:
                    chat_history = self.agent.memory.get_all()
                    reasoning_chain = []
                    
                    for msg in chat_history:
                        content = str(msg.content) if hasattr(msg, 'content') else str(msg)
                        if any(pattern in content for pattern in ["Thought:", "Action:", "Observation:", "Answer:"]):
                            reasoning_chain.append(content)
                    
                    if reasoning_chain:
                        return "\n".join(reasoning_chain)
                except Exception as e:
                    logger.warning(f"Could not extract reasoning chain: {e}")

            return final_answer

        except Exception as e:
            logger.error(f"ReAct agent execution failed: {e}")
            raise

    def _extract_tool_results(self, agent_response: str, tool_calls: List[Dict]) -> List[Dict]:
        """Extract tool results with validation."""
        tool_results = []
        
        for tool_call in tool_calls:
            tool_name = tool_call.get('tool_name', '')
            result = tool_call.get('result', '')
            
            tool_results.append({
                'tool': tool_name,
                'result': result,
                'success': bool(result),
                'method': 'enhanced_agentic'
            })
        
        return tool_results