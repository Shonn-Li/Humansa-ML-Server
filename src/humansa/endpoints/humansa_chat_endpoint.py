"""
Humansa AI-Agent Chat Endpoint - Fully Agentic Architecture

This endpoint provides AI-agent functionality with structured tool calling.
ALL tool selection and argument extraction is performed by the LLM agent using
structured schemas, with NO heuristic/regex-based fallbacks.

Key Features:
- LLM-only tool selection and argument parsing
- Structured schemas for all tool arguments
- Business/safety rules enforced in system prompt and post-processing
- Observable tool calls via LlamaIndex CallbackManager
- No fallback/direct tool execution (fail fast if agent unhealthy)

A/B Testing Support:
- Toggle between O3 Demo and Regular Humansa implementations
- Easy switching via USE_O3_DEMO flag in handle_chat_request method
- Both implementations emit the same canonical streaming format
"""

from ..streaming.comprehensive_response_streaming_handler_fixed import convert_agent_response_to_comprehensive_stream
from ..agent.humansa_agent import HumansaAgenticAgent
from ..tools.humansa_tools import HumansaAgenticToolManager
from ..prompts.appointment_booking_prompt import build_intelligent_system_prompt
from ..prompts.humansa_react_system_header import get_humansa_react_system_prompt
from ..prompts.intelligent_prompt_selector import intelligent_prompt_selector
from chat.query.query_transformer import QueryTransformer
from chat.streaming.streaming_response_generator import StreamingResponseGenerator
from chat.citation import CitationEngine, StreamingCitationEngine
from chat.provider.llm_provider import LLMProviderSelector
from chat.rag.rag_processor import RAGProcessor
from chat.attachment.file_attachment_manager import file_attachment_manager
from chat.websearch.web_search_processor import web_search_processor
import os
import logging
import time
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
import requests
import json
from ..prompts.appointment_booking_prompt import APPOINTMENT_BOOKING_PROMPT

# Import existing modules for reuse
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

# Import OpenAI v1 streaming handler

# Import humansa-specific agentic modules (now using main module names)

logger = logging.getLogger(__name__)


class HumansaChatEndpoint:
    """
    Humansa AI-Agent Chat Endpoint - Fully Agentic Architecture

    Provides AI-agent functionality where ALL tool calls are made by the LLM agent
    using structured schemas. No heuristic tool selection or argument extraction.
    """

    def __init__(self, db_config: Optional[Dict] = None):
        """Initialize the agentic endpoint with required components."""
        self.rag_processor = RAGProcessor()
        self.llm_provider = LLMProviderSelector()
        self.citation_engine = CitationEngine()
        self.streaming_citation_engine = StreamingCitationEngine()
        self.streaming_generator = StreamingResponseGenerator(
            self.rag_processor,
            file_attachment_manager,
            web_search_processor
        )

        # Skip IntelligentRouter for basic functionality
        try:
            logger.info(
                "ℹ️ Skipping IntelligentRouter initialization (not needed for basic functionality)")
            self.router = None
        except Exception as e:
            logger.warning(f"⚠️ IntelligentRouter initialization failed: {e}")
            self.router = None

        # Initialize query transformer
        try:
            self.query_transformer = QueryTransformer(self.llm_provider)
            logger.info("✅ QueryTransformer initialized successfully")
        except Exception as e:
            logger.warning(f"⚠️ QueryTransformer initialization failed: {e}")
            self.query_transformer = None

        # Initialize AGENTIC tool manager
        self.tool_manager = HumansaAgenticToolManager(db_config)

        # Initialize memory manager (Mem0 if available)
        self.memory_manager = None
        try:
            # Try to use Mem0 if available
            from humansa.memory.mem0_manager import Mem0Manager
            from humansa.v2.memory.mem0_integration import Mem0MemoryManagerAdapter
            
            mem0 = Mem0Manager.get_instance()
            if mem0.initialized:
                # Create a mock db_pool for compatibility
                class MockDBPool:
                    pass
                self.memory_manager = Mem0MemoryManagerAdapter(MockDBPool(), mem0)
                logger.info("✅ Mem0 memory manager initialized for V1")
            else:
                logger.info("ℹ️ Mem0 not available, continuing without memory")
        except Exception as e:
            logger.warning(f"Failed to initialize memory manager: {e}")

        # Initialize AGENTIC agent with memory support
        self.agent = HumansaAgenticAgent(
            llm=self.tool_manager.llm,
            tools=self.tool_manager.get_llamaindex_tools(),
            callback_manager=self.tool_manager.callback_manager,
            memory_manager=self.memory_manager
        )

        logger.info("🤖 HumansaChatEndpoint initialized - FULLY AGENTIC")

    async def handle_chat_request(self, request_data: Dict[str, Any]):
        """
        Handle incoming chat requests with fully agentic capabilities.

        ALL tool selection and argument extraction is performed by the LLM agent.
        NO heuristic fallbacks or regex-based tool selection.

        Args:
            request_data: The incoming chat request data

        Returns:
            Async generator for streaming responses or dict for non-streaming
        """
        start_time = time.time()

        # 🔄 A/B TESTING: Toggle between O3 Demo and Regular Humansa Implementation
        #
        # For A/B testing and comparison:
        # - Set use_o3_demo = True  in request_data to use O3 demo endpoint (wraps OpenAI O3)
        # - Set use_o3_demo = False in request_data to use regular Humansa agentic implementation
        #
        # This allows dynamic switching between implementations based on request parameters
        # Default to regular Humansa implementation
        USE_O3_DEMO = request_data.get('use_o3_demo', False)

        if USE_O3_DEMO:
            logger.info("🚀 A/B TEST MODE: Using O3 Demo Implementation")
            try:
                from .o3_demo_endpoint import o3_demo_endpoint
                return await o3_demo_endpoint.handle_demo_request(request_data)
            except Exception as e:
                logger.error(f"❌ O3 demo failed, falling back to Humansa: {e}")
                # Fall through to regular Humansa implementation

        # 🤖 Regular Humansa Agentic Implementation starts here
        logger.info(
            "🚀 A/B TEST MODE: Using Regular Humansa Agentic Implementation")
        try:
            logger.info("🚀 Starting AGENTIC Humansa chat request processing")

            # Extract basic parameters
            messages = request_data.get('messages', [])
            model = request_data.get('model', 'gpt-4.1-nano')
            stream = request_data.get('stream', False)
            user_id = request_data.get('user_id')

            # Validate required parameters
            if not messages:
                raise ValueError("Messages are required")
            if not user_id:
                raise ValueError("User ID is required")

            # FAIL FAST: Ensure agent is healthy (no fallbacks)
            if not self.agent.is_healthy():
                raise RuntimeError(
                    "Agent is not healthy - failing fast (no fallbacks in agentic mode)")

            logger.info(
                f"📊 Request params: model={model}, stream={stream}, user_id={user_id}")

            # Phase 1: Query Transformation (reuse existing module)
            logger.info("🔄 Phase 1: Query transformation")
            last_user_message = next((m for m in reversed(
                messages) if m.get('role') == 'user'), None)
            if not last_user_message:
                raise ValueError("No user message found")

            original_query = last_user_message.get('content', '')
            if isinstance(original_query, list):
                # Handle multi-part content
                text_parts = [
                    part.get('text', '') for part in original_query if part.get('type') == 'text']
                original_query = ' '.join(text_parts)

            # Transform query with conversation context
            if self.query_transformer:
                try:
                    condensed_query = await self.query_transformer.transform_query(
                        original_query,
                        messages[-3:] if len(messages) > 3 else messages
                    )
                except Exception as e:
                    logger.warning(f"⚠️ Query transformation failed: {e}")
                    condensed_query = original_query
            else:
                logger.warning(
                    "⚠️ QueryTransformer not available, using original query")
                condensed_query = original_query

            # Ensure condensed_query is a string
            if not isinstance(condensed_query, str):
                if isinstance(condensed_query, dict) and 'condensed_query' in condensed_query:
                    condensed_query = condensed_query['condensed_query']
                else:
                    condensed_query = str(
                        condensed_query) if condensed_query else original_query

            logger.info(
                f"📝 Query transformation: '{str(original_query)[:100]}...' → '{str(condensed_query)[:100]}...'")

            # Phase 2: Context retrieval (reuse existing modules)
            logger.info("📚 Phase 2: Context retrieval")
            context_tasks = []

            # RAG context
            if request_data.get('enable_rag', True):
                rag_context = request_data.get('context', {})
                if rag_context:
                    context_tasks.append(
                        self.rag_processor.process_rag_context(
                            condensed_query, rag_context, user_id
                        )
                    )

            # File attachments
            attachments = request_data.get('attachments', [])
            if attachments:
                context_tasks.append(
                    file_attachment_manager.process_attachments(
                        attachments, condensed_query, user_id
                    )
                )

            # Web search
            if request_data.get('enable_web_search', False):
                context_tasks.append(
                    web_search_processor.search_web_content(condensed_query)
                )

            # Execute context retrieval in parallel
            context_results = []
            if context_tasks:
                context_results = await asyncio.gather(*context_tasks, return_exceptions=True)
                logger.info(
                    f"📊 Context retrieval completed: {len(context_results)} sources")

            # Phase 3: AGENTIC Tool Execution
            logger.info(
                "🤖 Phase 3: AGENTIC tool execution - LLM decides ALL tools and arguments")

            # Set up streaming callback for web search if streaming is enabled
            streaming_data = []  # Collect streaming data for later inclusion in agent trace
            if stream and hasattr(self.tool_manager, 'set_stream_callback'):
                # Create a streaming callback that forwards web search results
                def streaming_callback(step_data):
                    logger.info(f"🔍 Streaming callback received: {step_data}")
                    streaming_data.append(step_data)
                    # This data will be included in the agent_trace for streaming to frontend

                self.tool_manager.set_stream_callback(streaming_callback)
                logger.info(
                    "✅ Set streaming callback on tool manager for web search")

            # The agent decides which tools to call and with what arguments
            # NO heuristic tool selection - agent has full autonomy

            # Build Humansa system prompt for the agent using intelligent selector
            humansa_system_prompt = await self._build_humansa_system_prompt(condensed_query, messages)
            logger.info(
                f"🤖 Built Humansa system prompt: {len(humansa_system_prompt)} chars")
            logger.info(
                f"🔍 System prompt preview: {humansa_system_prompt[:200]}...")

            # Prepare enhanced messages with system prompt for the agent
            agent_messages = messages.copy()
            agent_messages.insert(0, {
                'role': 'system',
                'content': humansa_system_prompt
            })
            logger.info(
                f"📝 Agent will receive {len(agent_messages)} messages (including system prompt)")

            agent_response = await self.agent.execute_with_tools(
                query=condensed_query,
                conversation_history=agent_messages,  # Pass messages with system prompt
                context_results=context_results,
                user_id=user_id
            )

            # 🔍 HUMANSA DEBUG - Log agent response structure
            logger.info(f"🔍 HUMANSA DEBUG - Agent response structure:")
            logger.info(
                f"  agent_trace: {len(agent_response.get('agent_trace', ''))} chars")
            logger.info(
                f"  agent_response: {len(agent_response.get('agent_response', ''))} chars")
            logger.info(
                f"  tool_calls_observed: {len(agent_response.get('tool_calls_observed', []))}")
            logger.info(
                f"  reasoning: {len(agent_response.get('reasoning', ''))} chars")
            logger.info(
                f"  agent_trace content: {agent_response.get('agent_trace', '')}")
            logger.info(
                f"  agent_response content: {agent_response.get('agent_response', '')}")
            logger.info(
                f"  reasoning content: {agent_response.get('reasoning', '')}")

            # Extract tool results from agent response
            tool_results = agent_response.get('tool_results', [])
            logger.info(f"🛠️ Agent executed {len(tool_results)} tools")

            # Phase 4: Response Generation (Direct from Agent)
            logger.info("🤖 Phase 4: Direct agent response generation")

            # Build enhanced context with tool results and streaming data for metadata
            enhanced_context = self._build_enhanced_context(
                context_results,
                tool_results,
                agent_response,
                streaming_data
            )

            # Generate response directly from agent (no additional LLM processing)
            if stream:
                return self._generate_streaming_response_from_agent(
                    agent_response, enhanced_context, model
                )
            else:
                return self._generate_non_streaming_response_from_agent(
                    agent_response, enhanced_context, model
                )

        except Exception as e:
            logger.error(f"❌ Agentic chat request failed: {e}")
            import traceback
            traceback.print_exc()

            error_response = {
                "error": str(e),
                "status": "error",
                "timestamp": time.time(),
                "processing_time": time.time() - start_time,
                "agentic_mode": True
            }

            if stream:
                async def error_stream():
                    yield error_response
                return error_stream()
            else:
                return error_response

    def _build_enhanced_context(self, context_results: List, tool_results: List, agent_response: Dict, streaming_data: List = None) -> Dict:
        """Build enhanced context combining regular context with tool results, agent reasoning, and streaming data."""
        enhanced_context = {
            'agent_reasoning': agent_response.get('reasoning', ''),
            # Full ReAct reasoning chain from trace handler
            'agent_trace': agent_response.get('agent_trace', ''),
            'confidence': agent_response.get('confidence', 1.0),
            'context_sources': [],
            'tool_results': tool_results,
            'tool_calls_observed': agent_response.get('tool_calls_observed', []),
            # Include streaming data from web search
            'streaming_data': streaming_data or [],
            'metadata': {
                'agentic_mode': True,
                'tools_used': [t.get('tool') for t in tool_results if t.get('success', False)],
                'agent_confidence': agent_response.get('confidence', 1.0),
                'callback_events': len(agent_response.get('tool_calls_observed', [])),
                'streaming_steps': len(streaming_data) if streaming_data else 0
            }
        }

        # Process regular context results
        for result in context_results:
            if isinstance(result, Exception):
                logger.error(f"Context retrieval error: {result}")
                continue

            if isinstance(result, dict):
                enhanced_context['context_sources'].append(result)

        return enhanced_context

    async def _build_humansa_system_prompt(self, query: str, conversation_history: List[Dict] = None) -> str:
        """Use streamlined v2 system prompt without tables."""
        try:
            logger.info(
                f"🧠 Building Humansa v2 system prompt for query: {query[:100]}...")

            # Use v2 system prompt without tables
            from ..prompts.humansa_system_prompt_v2 import get_humansa_system_prompt_v2
            current_date = datetime.now().strftime('%Y-%m-%d')
            system_prompt = get_humansa_system_prompt_v2(current_date)

            logger.info(
                f"🎯 Built Humansa v2 system prompt")
            logger.info(f"📝 System prompt length: {len(system_prompt)} chars")

            return system_prompt

        except Exception as e:
            logger.error(f"❌ V2 system prompt generation failed: {e}")
            # Fallback to full prompt
            from ..prompts.appointment_booking_prompt import get_full_humansa_system_prompt
            logger.warning("⚠️ Using fallback full system prompt")
            return get_full_humansa_system_prompt()

    async def _generate_streaming_response_from_agent(self, agent_response: Dict, enhanced_context: Dict, model: str):
        """Generate OpenAI v1-compatible streaming response directly from agent results."""
        try:
            logger.info("🌊 Generating streaming response directly from agent")

            # Prepare agent response data for streaming
            agent_response_data = {
                'agent_trace': agent_response.get('agent_trace', ''),
                'tool_calls_observed': agent_response.get('tool_calls_observed', []),
                'reasoning': agent_response.get('reasoning', ''),
                'agent_response': agent_response.get('agent_response', ''),
                'tool_results': agent_response.get('tool_results', []),
                'streaming_data': enhanced_context.get('streaming_data', [])
            }

            # Ensure we have agent response content
            if not agent_response_data['agent_response']:
                logger.warning("⚠️ No agent response content available")
                agent_response_data['agent_response'] = "抱歉，我无法处理您的请求。请稍后再试。"

            logger.info(f"🔍 Streaming agent data:")
            logger.info(
                f"  agent_trace: {len(agent_response_data['agent_trace'])} chars")
            logger.info(
                f"  agent_response: {len(agent_response_data['agent_response'])} chars")
            logger.info(
                f"  tool_results: {len(agent_response_data['tool_results'])}")

            # Stream agent response with comprehensive format
            async for event in convert_agent_response_to_comprehensive_stream(agent_response_data):
                # Add agentic metadata
                event['agentic_mode'] = True
                if enhanced_context.get('metadata'):
                    event['agentic_metadata'] = enhanced_context['metadata']
                yield event

        except Exception as e:
            logger.error(f"❌ Agent streaming failed: {e}")
            import traceback
            traceback.print_exc()

            # Stream error response
            error_event = {
                "event": "response.output_text.delta",
                "data": {"delta": f"处理请求时出现错误: {str(e)}"}
            }
            yield error_event

            yield {
                "event": "response.output_text.done",
                "data": {}
            }

    def _generate_non_streaming_response_from_agent(self, agent_response: Dict, enhanced_context: Dict, model: str):
        """Generate non-streaming response directly from agent results."""
        try:
            logger.info(
                "🤖 Generating non-streaming response directly from agent")

            # Extract the agent's final response
            agent_content = agent_response.get('agent_response', '')

            if not agent_content:
                logger.warning("⚠️ No agent response content available")
                agent_content = "抱歉，我无法处理您的请求。请稍后再试。"

            logger.info(
                f"📝 Agent response content: {len(agent_content)} chars")

            # Return the agent response directly in OpenAI format
            return {
                "id": f"resp_{int(time.time())}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": agent_content,
                        },
                        "finish_reason": "stop"
                    }
                ],
                "usage": {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0
                },
                "agentic_mode": True,
                "agent_trace": agent_response.get('agent_trace', ''),
                "tool_calls_observed": agent_response.get('tool_calls_observed', []),
                "metadata": enhanced_context.get('metadata', {})
            }

        except Exception as e:
            logger.error(f"❌ Non-streaming agent response failed: {e}")
            import traceback
            traceback.print_exc()

            return {
                "error": str(e),
                "message": "处理请求时出现错误",
                "agentic_mode": True
            }
