"""
Humansa AI-Agent Chat Endpoint - Fully Agentic Architecture

This endpoint provides AI-agent functionality with structured tool calling.
ALL tool selection and argument extraction is performed by the LLM agent using
structured schemas, with NO heuristic/regex-based fallbacks.

Key Features:
- LLM-only tool selection and argument parsing
- Structured        # Add agent reasoning trace if available
        agent_trace = enhanced_context.get('agent_trace', '')
        logger.info(f"🔍 Agent trace length: {len(agent_trace)} chars")
        logger.info(f"🔍 Agent trace preview: {agent_trace[:200]}...")
        
        if agent_trace and agent_trace.strip():
            system_content += f"\n🧠 AGENT REASONING CHAIN:\n{agent_trace}\n"
            logger.info("✅ Added agent reasoning trace to system content")
        else:
            logger.warning("⚠️ No agent reasoning trace available")schemas for all tool arguments
- Business/safety rules enforced in system prompt and post-processing
- Observable tool calls via LlamaIndex CallbackManager
- No fallback/direct tool execution (fail fast if agent unhealthy)
"""

from ..streaming.comprehensive_response_streaming_handler_fixed import convert_agent_response_to_comprehensive_stream
from ..agent.humansa_agent import HumansaAgenticAgent
from ..tools.humansa_tools import HumansaAgenticToolManager
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

        # Initialize AGENTIC agent
        self.agent = HumansaAgenticAgent(
            llm=self.tool_manager.llm,
            tools=self.tool_manager.get_llamaindex_tools(),
            callback_manager=self.tool_manager.callback_manager
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
            agent_response = await self.agent.execute_with_tools(
                query=condensed_query,
                conversation_history=messages,
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

            # Phase 4: LLM Response Generation
            logger.info("🤖 Phase 4: LLM response generation")

            # Build enhanced context with tool results and streaming data
            enhanced_context = self._build_enhanced_context(
                context_results,
                tool_results,
                agent_response,
                streaming_data
            )

            # Prepare messages with enhanced context
            enhanced_messages = self._prepare_enhanced_messages(
                messages,
                enhanced_context,
                condensed_query
            )

            # Select LLM provider
            provider_enum, llm_provider = self.llm_provider.select_provider_and_model(
                None, model)

            # Generate response
            if stream:
                return self._generate_streaming_response(
                    llm_provider, enhanced_messages, model, enhanced_context
                )
            else:
                return await self._generate_non_streaming_response_with_agent(
                    llm_provider, enhanced_messages, model, enhanced_context
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

    def _prepare_enhanced_messages(self, messages: List, enhanced_context: Dict, query: str) -> List:
        """Prepare messages with enhanced context and comprehensive agentic system prompt."""
        enhanced_messages = messages.copy()

        # Get current date for system prompt
        current_date = datetime.now().strftime("%Y-%m-%d")

        # Create comprehensive agentic system prompt
        system_content = f"""### <AGENTIC_POLICY v2.0 ({current_date})>
Current date: {current_date}
Locale: zh-CN

You are **Humansa Health-Assist**, an AI concierge for high-end clinics operating in FULLY AGENTIC mode.

🎯 SUCCESS METRICS:
1️⃣   Grow official-account reads & video plays  
2️⃣   Maximise completed medical appointments  
3️⃣   Increase in-app store conversions  
4️⃣   Keep every interaction clinically safe & HIPAA-compliant  

🛠️ AGENTIC TOOL CALLING:
You have access to structured tools with Pydantic schemas. All tools have intelligent fuzzy matching and fallbacks:
• find_doctor_info(name: str, specialty: str, city: str) - Always returns 5 relevant doctors from our network
• find_doctor_availability(doctor_name: str, start_date: str, end_date: str, days_ahead: int) - Flexible date ranges up to 30 days, suggests alternatives
• search_clinics(clinic_name: str, city: str, specialty: str) - Always returns 5 relevant clinics with fuzzy matching  
• search_services(service_name: str, specialty: str, clinic_name: str) - Always returns 5 relevant services with pricing
• get_pricing(service_type: str, clinic_name: str, specialty: str) - Pricing with intelligent fallbacks
• book_appointment(doctor_name: str, date_iso: str, time_hhdd: str, patient_name: str, phone: str, service_type: str)
• place_call(phone_number: str, purpose: str, urgency: str)
• recommend_product(product_category: str, reason: str, price_range: str)
• push_content(content_type: str, topic: str, target_audience: str)
• search_web(query: str, language: str) - ONLY for external news/research, NOT for Humansa services

🏥 DOCTOR NAME REQUIREMENTS:
• **CRITICAL**: For all doctor search tools (find_doctor_info, find_doctor_availability, book_appointment), always use ONLY the actual Chinese family name or personal name (e.g., "张", "王", "李明")
• **NEVER** include titles like "医生", "主任", "Dr.", "医师", "教授" etc. in doctor_name parameters
• If user says "张医生", extract only "张" for the search
• If user says "Dr. Wang", extract only "Wang" for the search
• The system supports fuzzy/partial matching - even single characters like "张" will find relevant doctors
• If search fails, ask user for more specific name details or suggest they provide specialty/city to narrow results

🔍 ENHANCED SEARCH CAPABILITIES:
• **ALL tools have intelligent fallbacks** - they always return 5 useful results even if exact search fails
• **Date range flexibility** - availability tool supports "next week" (7 days), "this month" (30 days), specific ranges
• **Fuzzy matching everywhere** - partial names, service types, clinic names all work with intelligent matching
• **Smart suggestions** - if exact doctor not found, tools suggest similar doctors with availability
• **Context-aware responses** - tools explain search method and provide helpful alternatives

🎯 INTELLIGENT SEARCH BEHAVIOR:
• **ALWAYS use Humansa internal tools first** for doctors, clinics, services, pricing
• **NEVER use web search for Humansa services** - web search is ONLY for external news, research, health education
• **Trust the fallback results** - our tools always return helpful alternatives when exact matches aren't found
• **Explain search results** - tell users when we're showing alternatives vs exact matches
• **Use date ranges wisely** - when users ask "this week" or "next month", use the days_ahead parameter

🚨 SAFETY & BUSINESS RULES (enforced here, not in code):
• Emergency symptoms (胸痛、呼吸困难、昏迷等) → **DO NOT book** → "请立即拨打 120 / call 911"
• No medical diagnosis - only information and booking assistance
• Always quote prices in "¥" and name the clinic
• Verify patient details before booking: name, phone, preferred date/time
• When recommending products, explain WHY they help the upcoming service
• Language: Respond in user's language (Chinese/English)
• Tone: Concise, warm, professional
• Always end with a short next-step sentence

🎯 AGENT BEHAVIOR:
• Make ≤ 8 tool calls per user turn
• If arguments are missing: ask clarifying questions
• **DOCTOR NAME PROCESSING**: Always strip titles (医生, 主任, Dr., etc.) from doctor names before tool calls
• **ALWAYS try internal Humansa tools first** - our tools have intelligent fallbacks with 5 relevant alternatives
• **NEVER use web search for Humansa services** - only for external news, research, health information
• If internal tools return alternatives, present them to user as helpful suggestions
• Be autonomous in tool selection - no heuristics needed
• Use structured schemas for all tool arguments
• All tool calls and arguments will be observed and logged        ### <DYNAMIC_CONTEXT>"""

        # Add agent chain of thought if available
        agent_chain_of_thought = enhanced_context.get(
            'agent_trace', '')  # Use agent_trace instead
        logger.info(
            f"🔍 Agent chain of thought length: {len(agent_chain_of_thought)} chars")
        logger.info(
            f"🔍 Agent chain of thought preview: {agent_chain_of_thought[:200]}...")

        if agent_chain_of_thought and agent_chain_of_thought.strip():
            system_content += f"\n🧠 AGENT REASONING CHAIN:\n{agent_chain_of_thought}\n"
            logger.info("✅ Added agent reasoning chain to system content")
        else:
            logger.warning("⚠️ No agent chain of thought available")

        # Add tool execution results if available
        if enhanced_context.get('tool_results'):
            logger.info(
                f"🔍 Tool results count: {len(enhanced_context['tool_results'])}")
            system_content += f"\n✅ Tool Results Available: {len(enhanced_context['tool_results'])} tools executed."
            for tool_result in enhanced_context['tool_results']:
                if tool_result.get('success', False):
                    tool_name = tool_result.get('tool')
                    result_summary = str(tool_result.get('result', ''))[:150]
                    system_content += f"\n• {tool_name}: {result_summary}..."
                    logger.info(f"🔍 Added tool result: {tool_name}")

        # Add callback observation info
        if enhanced_context.get('tool_calls_observed'):
            system_content += f"\n📊 Observed {len(enhanced_context['tool_calls_observed'])} tool call events via CallbackManager"
            logger.info(
                f"🔍 Tool calls observed: {len(enhanced_context['tool_calls_observed'])}")

        # Add context sources summary
        context_sources = enhanced_context.get('context_sources', [])
        if context_sources:
            system_content += f"\n📚 Available Context: {len(context_sources)} sources"
            logger.info(f"🔍 Context sources: {len(context_sources)}")

        system_content += "\n</DYNAMIC_CONTEXT>"

        # 🔍 FULL SYSTEM MESSAGE LOGGING
        logger.info(
            "🔍 ======================== FULL SYSTEM MESSAGE START ========================")
        logger.info(system_content)
        logger.info(
            "🔍 ======================== FULL SYSTEM MESSAGE END ==========================")

        system_message = {
            'role': 'system',
            'content': system_content
        }

        # Insert system message at the beginning
        enhanced_messages.insert(0, system_message)

        return enhanced_messages

    async def _generate_streaming_response(self, llm_provider, messages: List, model: str, context: Dict):
        """Generate OpenAI v1-compatible streaming response for agent reasoning and tool calls."""
        try:
            logger.info(
                "🌊 Generating OpenAI v1-compatible agentic streaming response")

            # Check if we have agent response data for streaming
            agent_response_data = {
                'agent_trace': context.get('agent_trace', ''),
                'tool_calls_observed': context.get('tool_calls_observed', []),
                'reasoning': context.get('agent_reasoning', ''),
                'agent_response': context.get('agent_response', ''),
                'tool_results': context.get('tool_results', []),
                # Include streaming data
                'streaming_data': context.get('streaming_data', [])
            }

            # If we have agent data, use custom response streaming
            if (agent_response_data['agent_trace'] or
                agent_response_data['tool_calls_observed'] or
                    agent_response_data['reasoning']):

                logger.info(
                    "🤖 Streaming agent reasoning using custom response format")

                # 🔍 HUMANSA DEBUG - Log what we're sending to streaming handler
                logger.info(
                    f"🔍 HUMANSA DEBUG - Sending to response streaming handler:")
                logger.info(
                    f"  agent_trace: {len(agent_response_data['agent_trace'])} chars")
                logger.info(
                    f"  tool_calls_observed: {len(agent_response_data['tool_calls_observed'])}")
                logger.info(
                    f"  reasoning: {len(agent_response_data['reasoning'])} chars")
                logger.info(
                    f"  agent_response: {len(agent_response_data['agent_response'])} chars")
                logger.info(
                    f"  tool_results: {len(agent_response_data['tool_results'])}")
                logger.info(
                    f"  streaming_data: {len(agent_response_data['streaming_data'])} items")

                # Stream agent reasoning with comprehensive response format
                async for event in convert_agent_response_to_comprehensive_stream(agent_response_data):
                    # Add agentic metadata
                    event['agentic_mode'] = True
                    if context.get('metadata'):
                        event['agentic_metadata'] = context['metadata']
                    yield event

                # DON'T generate additional LLM response - the agent already provided the final answer

            else:
                # Fallback to regular streaming if no agent data
                logger.info(
                    "🌊 No agent data available, using regular streaming")
                async for event in self._stream_regular_response(llm_provider, messages, model, context):
                    yield event

        except Exception as e:
            logger.error(f"❌ Agentic streaming failed: {e}")
            import traceback
            traceback.print_exc()

            # Stream error response in custom response format
            error_event = {
                "event": "response.output_text.delta",
                "data": {"delta": f"Error in agentic processing: {str(e)}"}
            }
            yield error_event

            yield {
                "event": "response.output_text.done",
                "data": {}
            }

            # Final error chunk
            final_chunk = {
                "id": f"chatcmpl-error-{int(time.time())}",
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": model,
                "choices": [{
                    "index": 0,
                    "delta": {},
                    "finish_reason": "stop"
                }]
            }
            yield final_chunk

    async def _stream_final_llm_response(self, llm_provider, messages: List, model: str, context: Dict):
        """Stream final LLM response after agent reasoning in OpenAI v1 format."""
        try:
            # Add a final user message to get LLM response
            enhanced_messages = messages.copy()

            # Add system context if available
            if context.get('tool_results'):
                tool_summary = f"Based on the tool results: {len(context['tool_results'])} tools were executed."
                enhanced_messages.append({
                    'role': 'system',
                    'content': f"{tool_summary} Please provide a final response to the user."
                })

            # Generate final response with regular streaming
            async for event in self._stream_regular_response(llm_provider, enhanced_messages, model, context):
                # Don't mark regular LLM content with reasoning type - let it be treated as normal chat content
                yield event

        except Exception as e:
            logger.error(f"❌ Final LLM response streaming failed: {e}")

    async def _stream_regular_response(self, llm_provider, messages: List, model: str, context: Dict):
        """Stream regular response using existing streaming generator and convert to new event format."""
        try:
            # Prepare request data for the streaming generator
            request_data = {
                'messages': messages,
                'model': model,
                'stream': True
            }

            # Extract context components
            rag_context = None
            attachment_context = None
            websearch_context = None

            context_sources = context.get('context_sources', [])
            for source in context_sources:
                if isinstance(source, dict):
                    if 'rag_context' in source or 'chunks' in source:
                        rag_context = source
                    elif 'attachments' in source or 'attachment_context' in source:
                        attachment_context = source
                    elif 'web_search' in source or 'search_results' in source:
                        websearch_context = source

            # Use default provider enum
            from chat.provider.llm_provider import LLMProvider
            provider_enum = LLMProvider.AZURE_INFERENCE

            # Use the streaming response generator and convert OpenAI chunks to events
            async for chunk in self.streaming_generator.generate_streaming_response(
                request_data=request_data,
                rag_context=rag_context,
                attachment_context=attachment_context,
                websearch_context=websearch_context,
                llm=llm_provider,
                provider_enum=provider_enum,
                model=model,
                enable_citations=True,
                router_decision=None,
                generate_title=False
            ):
                # Convert OpenAI chunk format to our new event format
                if isinstance(chunk, dict) and 'choices' in chunk:
                    choice = chunk['choices'][0] if chunk['choices'] else {}
                    delta = choice.get('delta', {})
                    content = delta.get('content', '')
                    finish_reason = choice.get('finish_reason')

                    if content:
                        # Stream content as output text delta
                        yield {
                            "event": "response.output_text.delta",
                            "data": {"delta": content}
                        }

                    if finish_reason == "stop":
                        # Signal output is done
                        yield {
                            "event": "response.output_text.done",
                            "data": {}
                        }
                else:
                    # Pass through other formats as-is for now
                    yield chunk

        except Exception as e:
            logger.error(f"❌ Regular streaming failed: {e}")
            # Stream error as output text
            yield {
                "event": "response.output_text.delta",
                "data": {"delta": f"Error: {str(e)}"}
            }
            yield {
                "event": "response.output_text.done",
                "data": {}
            }

    async def _generate_non_streaming_response_with_agent(self, llm_provider, messages: List, model: str, context: Dict):
        """Generate non-streaming response using traditional agent execution."""
        try:
            logger.info("🤖 Generating non-streaming agentic response")

            # Extract context for agent
            user_query = messages[-1]['content'] if messages else ""
            conversation_history = messages[:-1] if len(messages) > 1 else []
            context_results = context.get('context_results', [])
            user_id = context.get('user_id', 'unknown')

            # Execute agent traditionally (non-streaming)
            agent_response = await self.agent.execute_with_tools(
                query=user_query,
                conversation_history=conversation_history,
                context_results=context_results,
                user_id=user_id
            )

            # Return the agent response directly
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
                            "content": agent_response.get('agent_response', 'No response generated'),
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
                "tool_calls_observed": agent_response.get('tool_calls_observed', [])
            }

        except Exception as e:
            logger.error(f"❌ Non-streaming agentic response failed: {e}")
            import traceback
            traceback.print_exc()

            return {
                "error": str(e),
                "message": "Failed to generate non-streaming agentic response"
            }
