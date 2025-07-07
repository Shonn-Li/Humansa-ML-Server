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

        logger.info(
            f"🤖 HumansaAgenticAgent initialized with {len(self.tools)} tools")
        if self.agent:
            logger.info(
                "✅ ReAct agent successfully initialized - FULLY AGENTIC MODE")
        else:
            logger.warning(
                "❌ ReAct agent initialization failed - agent will be unhealthy")

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
                max_iterations=30  # Increased to allow more complex reasoning
            )

            logger.info(
                "🧠 ReAct agent initialized with structured tool calling")

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
            logger.info(
                f"🚀 AGENTIC EXECUTION started for query: '{query[:100]}...'")

            # Fail fast if agent is not healthy
            if not self.is_healthy():
                raise RuntimeError(
                    "Agent is not healthy - cannot execute in agentic mode")

            # Prepare enhanced query with context
            enhanced_query = self._prepare_enhanced_query(
                query, conversation_history, context_results, user_id
            )

            logger.info(
                f"📝 Enhanced query prepared: {len(enhanced_query)} characters")

            # Execute with ReAct agent - LLM decides all tool calls
            logger.info(
                "🤖 Executing with ReAct agent - LLM controls all tool selection")
            agent_response = await self._execute_with_react_agent(enhanced_query)

            # Extract tool calls from callback manager and build complete reasoning chain
            tool_calls_observed = []
            full_trace = ""
            react_trace_handler = None
            humansa_callback_handler = None

            if self.callback_manager:
                # Get tool calls and trace from callback handlers
                for handler in self.callback_manager.handlers:
                    if hasattr(handler, 'get_trace'):  # ReActTraceHandler
                        react_trace_handler = handler
                        full_trace = handler.get_trace()
                        logger.info(
                            f"🧠 CAPTURED FULL TRACE: {len(full_trace)} characters")
                    if hasattr(handler, 'get_tool_calls'):  # HumansaCallbackHandler
                        humansa_callback_handler = handler
                        tool_calls_observed.extend(handler.get_tool_calls())

            # Merge tool results into the trace to create complete ReAct chain
            if react_trace_handler and humansa_callback_handler:
                enhanced_trace = self._merge_trace_with_tool_results(
                    full_trace, humansa_callback_handler.get_tool_calls()
                )
                if enhanced_trace != full_trace:
                    full_trace = enhanced_trace
                    logger.info(
                        f"✅ ENHANCED TRACE with tool results: {len(full_trace)} characters")

            # Use the full trace if available, otherwise use the agent response
            final_agent_response = full_trace if full_trace and full_trace.strip() else agent_response
            logger.info(
                f"🔗 Using {'full trace' if full_trace else 'agent response'}: {len(final_agent_response)} chars")

            execution_time = (datetime.now() - start_time).total_seconds()

            result = {
                'agent_response': final_agent_response,
                'agent_trace': full_trace,  # NEW: Include the full trace separately
                'tool_results': self._extract_tool_results_from_response(agent_response),
                'tool_calls_observed': tool_calls_observed,
                'reasoning': f"Agent executed {len(tool_calls_observed)} tool calls autonomously",
                'confidence': 1.0,  # High confidence in agentic mode
                'execution_time': execution_time,
                'mode': 'fully_agentic',
                'query': query,
                'user_id': user_id
            }

            logger.info(
                f"✅ AGENTIC EXECUTION completed in {execution_time:.2f}s")
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
            # Last 3 messages for context
            recent_messages = conversation_history[-3:]
            conversation_context = "\\n\\nRecent Conversation:"
            for msg in recent_messages:
                role = msg.get('role', 'unknown')
                content = str(msg.get('content', ''))[
                    :200]  # Truncate long messages
                conversation_context += f"\\n{role}: {content}"

        enhanced_query = f"""User Query: {query}
User ID: {user_id}
Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{conversation_context}
{context_summary}

Please process this query using the appropriate tools. Call tools with structured arguments only."""

        return enhanced_query

    async def _execute_with_react_agent(self, enhanced_query: str) -> str:
        """Execute the query with ReAct agent and capture full reasoning chain."""
        try:
            # Use async chat if available, otherwise sync
            if hasattr(self.agent, 'achat'):
                response = await self.agent.achat(enhanced_query)
            else:
                # Fallback to sync chat
                response = self.agent.chat(enhanced_query)

            # Debug: Log all available attributes on the response
            logger.info(f"🔍 Agent response type: {type(response)}")
            logger.info(f"🔍 Agent response attributes: {dir(response)}")

            # Try to capture the full reasoning chain from agent memory
            full_reasoning_chain = ""

            # Method 1: Check agent memory for chat history
            if hasattr(self.agent, 'memory') and self.agent.memory:
                logger.info("🔍 Accessing agent memory for reasoning chain")
                try:
                    chat_history = self.agent.memory.get_all()
                    logger.info(
                        f"🔍 Chat history length: {len(chat_history)} messages")

                    # Build the reasoning chain from chat history
                    reasoning_steps = []
                    for msg in chat_history:
                        content = str(msg.content) if hasattr(
                            msg, 'content') else str(msg)
                        logger.info(
                            f"🔍 Chat message preview: {content[:100]}...")

                        # Look for ReAct pattern (Thought:, Action:, Observation:)
                        if any(pattern in content for pattern in ["Thought:", "Action:", "Observation:", "> Running step"]):
                            reasoning_steps.append(content)

                    if reasoning_steps:
                        full_reasoning_chain = "\n".join(reasoning_steps)
                        logger.info(
                            f"🔍 Captured reasoning chain from memory: {len(full_reasoning_chain)} chars")
                except Exception as e:
                    logger.warning(f"🔍 Could not access agent memory: {e}")

            # Method 2: Check if agent has chat store/history
            if not full_reasoning_chain and hasattr(self.agent, 'chat_history'):
                logger.info("🔍 Accessing agent chat_history")
                try:
                    history = self.agent.chat_history
                    logger.info(f"🔍 Chat history type: {type(history)}")
                    full_reasoning_chain = str(history)
                except Exception as e:
                    logger.warning(f"🔍 Could not access chat history: {e}")

            # Method 3: Check response sources for reasoning
            if not full_reasoning_chain and hasattr(response, 'source_nodes') and response.source_nodes:
                logger.info(
                    f"🔍 Checking {len(response.source_nodes)} source nodes for reasoning")
                reasoning_parts = []
                for i, node in enumerate(response.source_nodes):
                    node_content = str(node)
                    logger.info(f"🔍 Source node {i}: {node_content[:100]}...")
                    if any(pattern in node_content for pattern in ["Thought:", "Action:", "Observation:"]):
                        reasoning_parts.append(node_content)

                if reasoning_parts:
                    full_reasoning_chain = "\n".join(reasoning_parts)
                    logger.info(
                        f"🔍 Captured reasoning from source nodes: {len(full_reasoning_chain)} chars")

            # Extract final answer
            final_answer = str(response.response) if hasattr(
                response, 'response') else str(response)
            logger.info(f"🔍 Final answer: {final_answer[:100]}...")

            # Return the full reasoning chain if available, otherwise final answer
            if full_reasoning_chain and len(full_reasoning_chain) > len(final_answer):
                logger.info(
                    f"✅ Using full reasoning chain ({len(full_reasoning_chain)} chars)")
                return full_reasoning_chain
            else:
                logger.info(
                    f"⚠️ Using final answer only ({len(final_answer)} chars)")
                return final_answer

        except Exception as e:
            logger.error(f"❌ ReAct agent execution failed: {e}")
            raise

    def _merge_trace_with_tool_results(self, original_trace: str, tool_calls: List[Dict]) -> str:
        """
        Merge the ReAct trace with actual tool results to create complete 
        Thought/Action/Observation/Answer chains.

        Args:
            original_trace: The original trace from ReActTraceHandler
            tool_calls: Tool calls with results from HumansaCallbackHandler

        Returns:
            Enhanced trace with complete ReAct chains
        """
        if not original_trace or not tool_calls:
            return original_trace

        try:
            lines = original_trace.split('\n')
            enhanced_lines = []
            tool_call_index = 0

            for line in lines:
                enhanced_lines.append(line)

                # If this line contains an Action Input, add the corresponding Observation
                if "Action Input:" in line and tool_call_index < len(tool_calls):
                    tool_call = tool_calls[tool_call_index]
                    if 'result' in tool_call:
                        observation = f"Observation: {tool_call['result']}"
                        enhanced_lines.append(observation)
                        logger.info(
                            f"🔗 Added observation for tool {tool_call.get('tool_name', 'unknown')}")
                    tool_call_index += 1

            enhanced_trace = '\n'.join(enhanced_lines)
            return enhanced_trace

        except Exception as e:
            logger.warning(f"⚠️ Failed to merge trace with tool results: {e}")
            return original_trace

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

    async def stream_chat(self, query: str, conversation_history: List[Dict],
                          context_results: List, user_id: str):
        """
        Stream agent chat responses with tool execution and real-time thoughts.

        This method streams the agent's reasoning process in real-time, including:
        - Thoughts as the agent reasons
        - Actions as tools are selected  
        - Observations as tool results come in
        - Final answers

        Args:
            query: The user query
            conversation_history: Full conversation history for context  
            context_results: Retrieved context from RAG/attachments/web
            user_id: User identifier

        Yields:
            Dict chunks containing streaming response data
        """
        start_time = datetime.now()

        try:
            logger.info(
                f"🌊 AGENT STREAMING started for query: '{query[:100]}...'")

            # Fail fast if agent is not healthy
            if not self.is_healthy():
                error_chunk = {
                    'choices': [{
                        'delta': {
                            'content': 'Agent is not healthy - cannot execute in agentic mode',
                            'role': 'assistant'
                        },
                        'index': 0,
                        'finish_reason': 'stop'
                    }],
                    'object': 'chat.completion.chunk',
                    'reasoning': 'error',
                    'timestamp': datetime.now().isoformat()
                }
                yield error_chunk
                return

            # Prepare enhanced query with context
            enhanced_query = self._prepare_enhanced_query(
                query, conversation_history, context_results, user_id
            )

            # Yield initial progress in v1 format using regular content for progress
            yield {
                'choices': [{
                    'delta': {
                        'content': 'Agent processing query...',
                        'role': 'assistant'
                    },
                    'index': 0,
                    'finish_reason': None
                }],
                'object': 'chat.completion.chunk',
                'reasoning': 'progress',
                'stage': 'agent_initialization',
                'timestamp': datetime.now().isoformat()
            }

            # Create a queue to collect streaming chunks from callback
            import asyncio
            streaming_queue = asyncio.Queue()

            # Create streaming callback function
            def stream_callback(chunk):
                """Callback function to receive streaming chunks from agent"""
                try:
                    streaming_queue.put_nowait(chunk)
                except Exception as e:
                    logger.warning(f"⚠️ Failed to queue streaming chunk: {e}")

            # Define streaming handler locally to avoid import issues
            try:
                # Import required types
                from llama_index.core.callbacks.base import BaseCallbackHandler
                from llama_index.core.callbacks.schema import CBEventType

                class LocalStreamingReActHandler(BaseCallbackHandler):
                    """Local streaming callback handler that emits thoughts, actions, and observations in real-time."""

                    def __init__(self, stream_callback=None):
                        super().__init__([], [])
                        self.stream_callback = stream_callback
                        self.current_step = 0

                    def on_event_start(self, event_type: CBEventType, payload: Optional[Dict[str, Any]] = None, **kwargs) -> str:
                        """Capture start events for streaming"""
                        event_id = kwargs.get(
                            'event_id', f"stream_event_{self.current_step}")

                        if event_type == CBEventType.AGENT_STEP:
                            self.current_step += 1

                        return event_id

                    def on_event_end(self, event_type: CBEventType, payload: Optional[Dict[str, Any]] = None, **kwargs) -> None:
                        """Stream thoughts, actions, and observations in OpenAI v1 completion format"""
                        if not self.stream_callback:
                            return

                        if event_type == CBEventType.LLM:
                            # Stream LLM responses (thoughts, actions)
                            txt = payload.get(
                                "response", "") if payload else ""
                            if hasattr(txt, 'message') and hasattr(txt.message, 'content'):
                                txt = txt.message.content
                            elif hasattr(txt, 'content'):
                                txt = txt.content
                            else:
                                txt = str(txt)

                            logger.info(
                                f"🔍 LocalStreamingReActHandler received LLM response: {txt[:200]}...")

                            # Parse and stream different parts of ReAct pattern
                            if "Thought:" in txt:
                                # Extract thought content and stream multiple thoughts
                                thought_parts = txt.split("Thought:")
                                for i, thought in enumerate(thought_parts[1:], 1):
                                    # Extract content before next "Action:" or end
                                    thought_content = thought.split("Action:")[
                                        0].strip()
                                    if thought_content:
                                        logger.info(
                                            f"🧠 Streaming thought #{i}: {thought_content[:100]}...")
                                        # Use v1 completion format with reasoning_content field for thoughts
                                        self.stream_callback({
                                            'choices': [{
                                                'delta': {
                                                    'reasoning_content': thought_content,
                                                    'role': 'assistant'
                                                },
                                                'index': 0,
                                                'finish_reason': None
                                            }],
                                            'object': 'chat.completion.chunk',
                                            'reasoning': 'thought',  # Custom field to indicate this is reasoning
                                            'step': self.current_step
                                        })

                            if "Action:" in txt:
                                # Extract action content and stream as tool calls
                                action_parts = txt.split("Action:")
                                for i, action in enumerate(action_parts[1:], 1):
                                    # Get action name before "Action Input:"
                                    action_content = action.split(
                                        "Action Input:")[0].strip()
                                    if action_content:
                                        logger.info(
                                            f"⚡ Streaming action #{i}: {action_content}")
                                        # ✅ NEW: Check if this is a web search action
                                        if "search_web" in action_content.lower() or "web" in action_content.lower():
                                            # Stream as web search tool call with special handling
                                            self.stream_callback({
                                                'choices': [{
                                                    'delta': {
                                                        'tool_calls': [{
                                                            'id': f'call_{self.current_step}_{i}',
                                                            'type': 'function',
                                                            'function': {
                                                                'name': 'search_web',
                                                                'arguments': ''  # Will be filled in next chunk
                                                            }
                                                        }],
                                                        'role': 'assistant'
                                                    },
                                                    'index': 0,
                                                    'finish_reason': None
                                                }],
                                                'object': 'chat.completion.chunk',
                                                'reasoning': 'web_search_start',  # Special reasoning type for web search
                                                'step': self.current_step
                                            })
                                        else:
                                            # Regular tool call
                                            self.stream_callback({
                                                'choices': [{
                                                    'delta': {
                                                        'tool_calls': [{
                                                            'id': f'call_{self.current_step}_{i}',
                                                            'type': 'function',
                                                            'function': {
                                                                'name': action_content,
                                                                'arguments': ''  # Will be filled in next chunk
                                                            }
                                                        }],
                                                        'role': 'assistant'
                                                    },
                                                    'index': 0,
                                                    'finish_reason': None
                                                }],
                                                'object': 'chat.completion.chunk',
                                                'reasoning': 'action',
                                                'step': self.current_step
                                            })

                            if "Answer:" in txt:
                                # Extract final answer and stream as regular content
                                answer_parts = txt.split("Answer:")
                                for i, answer in enumerate(answer_parts[1:], 1):
                                    answer_content = answer.strip()
                                    if answer_content:
                                        logger.info(
                                            f"✅ Streaming answer #{i}: {answer_content[:100]}...")
                                        # Stream final answer as reasoning_content for consistency
                                        self.stream_callback({
                                            'choices': [{
                                                'delta': {
                                                    'reasoning_content': answer_content,
                                                    'role': 'assistant'
                                                },
                                                'index': 0,
                                                'finish_reason': 'stop'
                                            }],
                                            'object': 'chat.completion.chunk',
                                            'reasoning': 'answer',
                                            'step': self.current_step
                                        })

                        elif event_type == CBEventType.FUNCTION_CALL and self.stream_callback:
                            # Stream tool execution results in v1 completion format
                            if payload:
                                tool_name = payload.get("function_call", {}).get(
                                    "name", "unknown_tool")
                                tool_result = payload.get(
                                    "function_call_response", "")

                                logger.info(
                                    f"👁️ Streaming observation for tool {tool_name}: {str(tool_result)[:100]}...")

                                # ✅ NEW: Special handling for web search results
                                if tool_name == "search_web" and isinstance(tool_result, dict):
                                    if tool_result.get("success") and tool_result.get("results"):
                                        # Stream web search results as individual link discoveries
                                        results = tool_result["results"]
                                        for i, result in enumerate(results):
                                            self.stream_callback({
                                                'choices': [{
                                                    'delta': {
                                                        'reasoning_content': f"Found: {result.get('title', 'Web result')} - {result.get('url', '')}",
                                                        'role': 'assistant'
                                                    },
                                                    'index': 0,
                                                    'finish_reason': None
                                                }],
                                                'object': 'chat.completion.chunk',
                                                'reasoning': 'web_search_result',
                                                'tool_name': tool_name,
                                                'web_result': result,  # Include the full result
                                                'result_index': i + 1,
                                                'total_results': len(results),
                                                'step': self.current_step
                                            })

                                        # Final web search summary
                                        self.stream_callback({
                                            'choices': [{
                                                'delta': {
                                                    'reasoning_content': f"Web search completed - found {len(results)} results",
                                                    'role': 'assistant'
                                                },
                                                'index': 0,
                                                'finish_reason': None
                                            }],
                                            'object': 'chat.completion.chunk',
                                            'reasoning': 'web_search_complete',
                                            'tool_name': tool_name,
                                            'web_results_summary': {
                                                'total_found': len(results),
                                                'query': tool_result.get('query', ''),
                                                'search_type': tool_result.get('search_type', 'web_search')
                                            },
                                            'step': self.current_step
                                        })
                                    else:
                                        # Web search failed or no results
                                        self.stream_callback({
                                            'choices': [{
                                                'delta': {
                                                    'reasoning_content': f"Web search completed - {tool_result.get('message', 'no results found')}",
                                                    'role': 'assistant'
                                                },
                                                'index': 0,
                                                'finish_reason': None
                                            }],
                                            'object': 'chat.completion.chunk',
                                            'reasoning': 'web_search_complete',
                                            'tool_name': tool_name,
                                            'step': self.current_step
                                        })
                                else:
                                    # Regular tool result
                                    # Stream tool result as reasoning_content with special reasoning marker
                                    self.stream_callback({
                                        'choices': [{
                                            'delta': {
                                                'reasoning_content': f"Tool {tool_name} executed successfully",
                                                'role': 'assistant'
                                            },
                                            'index': 0,
                                            'finish_reason': None
                                        }],
                                        'object': 'chat.completion.chunk',
                                        'reasoning': 'observation',
                                        'tool_name': tool_name,
                                        # Truncate for efficiency
                                        'tool_result': str(tool_result)[:500],
                                        'step': self.current_step
                                    })

                    def start_trace(self, trace_id: Optional[str] = None) -> None:
                        """Start streaming trace"""
                        if self.stream_callback:
                            self.stream_callback({
                                'type': 'trace_start',
                                'message': 'Agent reasoning started...',
                                'timestamp': datetime.now().isoformat()
                            })

                    def end_trace(self, trace_id: Optional[str] = None, trace_map: Optional[Dict[str, List[str]]] = None) -> None:
                        """End streaming trace"""
                        if self.stream_callback:
                            self.stream_callback({
                                'type': 'trace_end',
                                'message': f'Agent reasoning completed after {self.current_step} steps',
                                'total_steps': self.current_step,
                                'timestamp': datetime.now().isoformat()
                            })

                # Create streaming callback handler
                streaming_handler = LocalStreamingReActHandler(
                    stream_callback=stream_callback)

                # Add streaming handler to existing callback manager instead of replacing
                if self.callback_manager:
                    # Add our streaming handler to the existing manager
                    self.callback_manager.add_handler(streaming_handler)
                    logger.info(
                        "🌊 Added local streaming handler to existing callback manager")
                else:
                    # Create new callback manager with streaming handler
                    from llama_index.core.callbacks import CallbackManager
                    temp_callback_manager = CallbackManager(
                        [streaming_handler])
                    self.agent.callback_manager = temp_callback_manager
                    logger.info(
                        "🌊 Created new callback manager with local streaming handler")

                logger.info(
                    "🌊 Using local streaming callback handler for real-time thoughts")

            except Exception as e:
                logger.warning(
                    f"⚠️ Could not set up local streaming handler: {e}")
                import traceback
                traceback.print_exc()
                streaming_handler = None

            # Start agent execution in background task
            async def execute_agent():
                try:
                    if hasattr(self.agent, 'achat'):
                        response = await self.agent.achat(enhanced_query)
                    else:
                        # Run sync method in thread pool
                        import asyncio
                        loop = asyncio.get_event_loop()
                        response = await loop.run_in_executor(None, self.agent.chat, enhanced_query)

                    # Signal completion
                    streaming_queue.put_nowait({
                        'type': 'agent_complete',
                        'response': str(response),
                        'timestamp': datetime.now().isoformat()
                    })

                except Exception as e:
                    logger.error(f"❌ Agent execution failed: {e}")
                    streaming_queue.put_nowait({
                        'type': 'error',
                        'error': str(e),
                        'timestamp': datetime.now().isoformat()
                    })

            # Start agent execution
            agent_task = asyncio.create_task(execute_agent())

            # Stream chunks as they come from the callback
            agent_completed = False
            final_response_parts = []

            while not agent_completed:
                try:
                    # Wait for chunks with timeout
                    chunk = await asyncio.wait_for(streaming_queue.get(), timeout=1.0)

                    # Handle both v1 completion format and legacy format chunks
                    if isinstance(chunk, dict):
                        # Check if this is a v1 completion format chunk
                        if 'choices' in chunk and 'object' in chunk:
                            # v1 completion format - yield directly
                            yield chunk

                            # Track completion
                            choice = chunk['choices'][0] if chunk['choices'] else {
                            }
                            if choice.get('finish_reason') == 'stop':
                                agent_completed = True

                            # Collect content for final response (check both content and reasoning_content)
                            delta = choice.get('delta', {})
                            content = delta.get('content', '') or delta.get(
                                'reasoning_content', '')
                            if content:
                                final_response_parts.append(content)

                        # Legacy format processing (for backward compatibility)
                        elif chunk.get('type') == 'agent_complete':
                            # Agent finished - stream final response if not already streamed
                            agent_completed = True
                            final_response = chunk['response']

                            # If we haven't streamed much content yet, stream the final response in v1 format
                            if len(final_response_parts) < 10:  # Arbitrary threshold
                                chunk_size = 50
                                for i in range(0, len(final_response), chunk_size):
                                    chunk_text = final_response[i:i + chunk_size]
                                    yield {
                                        'choices': [{
                                            'delta': {
                                                'reasoning_content': chunk_text,
                                                'role': 'assistant'
                                            },
                                            'index': 0,
                                            'finish_reason': None
                                        }],
                                        'object': 'chat.completion.chunk',
                                        'reasoning': 'response'
                                    }
                                    final_response_parts.append(chunk_text)

                        elif chunk.get('type') == 'error':
                            # Convert error to v1 format using regular content for errors
                            yield {
                                'choices': [{
                                    'delta': {
                                        'content': f"Error: {chunk.get('error', 'Unknown error')}",
                                        'role': 'assistant'
                                    },
                                    'index': 0,
                                    'finish_reason': 'stop'
                                }],
                                'object': 'chat.completion.chunk',
                                'reasoning': 'error'
                            }
                            agent_completed = True

                        elif chunk.get('type') in ['agent_thought', 'agent_action', 'agent_observation', 'agent_answer']:
                            # Legacy format - convert to v1 format
                            chunk_type = chunk.get('type', '')
                            content = chunk.get('content', '')

                            if chunk_type == 'agent_thought':
                                reasoning = 'thought'
                            elif chunk_type == 'agent_action':
                                reasoning = 'action'
                            elif chunk_type == 'agent_observation':
                                reasoning = 'observation'
                            elif chunk_type == 'agent_answer':
                                reasoning = 'answer'
                            else:
                                reasoning = 'unknown'

                            # Convert to v1 format using reasoning_content for reasoning chunks
                            delta_field = 'reasoning_content' if reasoning in [
                                'thought', 'observation', 'answer'] else 'content'
                            yield {
                                'choices': [{
                                    'delta': {
                                        delta_field: content,
                                        'role': 'assistant'
                                    },
                                    'index': 0,
                                    'finish_reason': None
                                }],
                                'object': 'chat.completion.chunk',
                                'reasoning': reasoning
                            }

                            # For answers, also add to response parts
                            if chunk_type == 'agent_answer':
                                final_response_parts.append(content)

                        elif chunk.get('type') in ['trace_start', 'trace_end', 'agent_step_start', 'agent_step_end']:
                            # Internal trace events - convert to v1 format progress
                            yield {
                                'choices': [{
                                    'delta': {
                                        'content': chunk.get('message', ''),
                                        'role': 'assistant'
                                    },
                                    'index': 0,
                                    'finish_reason': None
                                }],
                                'object': 'chat.completion.chunk',
                                'reasoning': 'progress',
                                'step': chunk.get('step'),
                                'trace_event': chunk.get('type')
                            }

                        else:
                            # Unknown chunk type - stream as generic content in v1 format
                            yield {
                                'choices': [{
                                    'delta': {
                                        'content': str(chunk.get('content', chunk)),
                                        'role': 'assistant'
                                    },
                                    'index': 0,
                                    'finish_reason': None
                                }],
                                'object': 'chat.completion.chunk',
                                'reasoning': 'unknown'
                            }

                except asyncio.TimeoutError:
                    # Check if agent task is still running
                    if agent_task.done():
                        agent_completed = True
                    # Continue waiting for more chunks
                    continue
                except Exception as e:
                    logger.error(f"❌ Error processing streaming chunk: {e}")
                    break

            # Clean up - remove streaming handler from callback manager
            if streaming_handler and self.callback_manager:
                try:
                    # Remove the streaming handler
                    if hasattr(self.callback_manager, 'handlers') and streaming_handler in self.callback_manager.handlers:
                        self.callback_manager.handlers.remove(
                            streaming_handler)
                        logger.info(
                            "🧹 Removed streaming handler from callback manager")
                except Exception as e:
                    logger.warning(
                        f"⚠️ Could not remove streaming handler: {e}")

            # Wait for agent task to complete
            try:
                await agent_task
            except Exception as e:
                logger.error(f"❌ Agent task completion error: {e}")

            # Final completion chunk in v1 format
            execution_time = (datetime.now() - start_time).total_seconds()
            yield {
                'choices': [{
                    'delta': {},
                    'index': 0,
                    'finish_reason': 'stop'
                }],
                'object': 'chat.completion.chunk',
                'reasoning': 'completion',
                'execution_time': execution_time,
                'mode': 'fully_agentic_streaming',
                'total_response_parts': len(final_response_parts),
                'timestamp': datetime.now().isoformat()
            }

            logger.info(
                f"✅ AGENT STREAMING completed in {execution_time:.2f}s")

        except Exception as e:
            logger.error(f"❌ Agent streaming failed: {e}")
            import traceback
            traceback.print_exc()

            error_chunk = {
                'choices': [{
                    'delta': {
                        'content': f'Error: {str(e)}',
                        'role': 'assistant'
                    },
                    'index': 0,
                    'finish_reason': 'stop'
                }],
                'object': 'chat.completion.chunk',
                'reasoning': 'error',
                'timestamp': datetime.now().isoformat()
            }
            yield error_chunk
