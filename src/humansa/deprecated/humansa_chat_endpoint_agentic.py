"""
Humansa AI-Agent Chat Endpoint - Fully Agentic Architecture

This endpoint provides AI-agent functionality with structured tool calling.
ALL tool selection and argument extraction is performed by the LLM agent using
structured schemas, with NO heuristic/regex-based fallbacks.

Key Features:
- LLM-only tool selection and argument parsing
- Structured Pydantic schemas for all tool arguments
- Business/safety rules enforced in system prompt and post-processing
- Observable tool calls via LlamaIndex CallbackManager
- No fallback/direct tool execution (fail fast if agent unhealthy)
"""

import os
import json
import logging
import time
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

# Import existing modules for reuse
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from chat.websearch.web_search_processor import web_search_processor
from chat.attachment.file_attachment_manager import file_attachment_manager
from chat.embedding.embedding_manager import embedding_manager
from chat.rag.rag_processor import RAGProcessor
from chat.provider.llm_provider import LLMProviderSelector
from chat.citation import CitationEngine, StreamingCitationEngine
from chat.streaming.streaming_response_generator import StreamingResponseGenerator
from chat.router.intelligent_router import IntelligentRouter
from chat.title.title_generator import title_generator
from chat.query.query_transformer import QueryTransformer

# Import humansa-specific modules
from ..tools.humansa_tools_agentic import HumansaAgenticToolManager
from ..agent.humansa_agent_agentic import HumansaAgenticAgent

logger = logging.getLogger(__name__)


class HumansaAgenticChatEndpoint:
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
            logger.info("ℹ️ Skipping IntelligentRouter initialization (not needed for basic functionality)")
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
        
        logger.info("🤖 HumansaAgenticChatEndpoint initialized - FULLY AGENTIC")
    
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
                raise RuntimeError("Agent is not healthy - failing fast (no fallbacks in agentic mode)")
            
            logger.info(f"📊 Request params: model={model}, stream={stream}, user_id={user_id}")
            
            # Phase 1: Query Transformation (reuse existing module)
            logger.info("🔄 Phase 1: Query transformation")
            last_user_message = next((m for m in reversed(messages) if m.get('role') == 'user'), None)
            if not last_user_message:
                raise ValueError("No user message found")
            
            original_query = last_user_message.get('content', '')
            if isinstance(original_query, list):
                # Handle multi-part content
                text_parts = [part.get('text', '') for part in original_query if part.get('type') == 'text']
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
                logger.warning("⚠️ QueryTransformer not available, using original query")
                condensed_query = original_query
            
            # Ensure condensed_query is a string
            if not isinstance(condensed_query, str):
                if isinstance(condensed_query, dict) and 'condensed_query' in condensed_query:
                    condensed_query = condensed_query['condensed_query']
                else:
                    condensed_query = str(condensed_query) if condensed_query else original_query
            
            logger.info(f"📝 Query transformation: '{str(original_query)[:100]}...' → '{str(condensed_query)[:100]}...'")
            
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
                logger.info(f"📊 Context retrieval completed: {len(context_results)} sources")
            
            # Phase 3: AGENTIC Tool Execution
            logger.info("🤖 Phase 3: AGENTIC tool execution - LLM decides ALL tools and arguments")
            
            # The agent decides which tools to call and with what arguments
            # NO heuristic tool selection - agent has full autonomy
            agent_response = await self.agent.execute_with_tools(
                query=condensed_query,
                conversation_history=messages,
                context_results=context_results,
                user_id=user_id
            )
            
            # Extract tool results from agent response
            tool_results = agent_response.get('tool_results', [])
            logger.info(f"🛠️ Agent executed {len(tool_results)} tools")
            
            # Phase 4: LLM Response Generation
            logger.info("🤖 Phase 4: LLM response generation")
            
            # Build enhanced context with tool results
            enhanced_context = self._build_enhanced_context(
                context_results, 
                tool_results, 
                agent_response
            )
            
            # Prepare messages with enhanced context
            enhanced_messages = self._prepare_enhanced_messages(
                messages, 
                enhanced_context, 
                condensed_query
            )
            
            # Select LLM provider
            provider_enum, llm_provider = self.llm_provider.select_provider_and_model(None, model)
            
            # Generate response
            if stream:
                return self._generate_streaming_response(
                    llm_provider, enhanced_messages, model, enhanced_context
                )
            else:
                return await self._generate_non_streaming_response(
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
    
    def _build_enhanced_context(self, context_results: List, tool_results: List, agent_response: Dict) -> Dict:
        """Build enhanced context combining regular context with tool results."""
        enhanced_context = {
            'agent_reasoning': agent_response.get('reasoning', ''),
            'confidence': agent_response.get('confidence', 1.0),
            'context_sources': [],
            'tool_results': tool_results,
            'tool_calls_observed': agent_response.get('tool_calls_observed', []),
            'metadata': {
                'agentic_mode': True,
                'tools_used': [t.get('tool') for t in tool_results if t.get('success', False)],
                'agent_confidence': agent_response.get('confidence', 1.0),
                'callback_events': len(agent_response.get('tool_calls_observed', []))
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
You have access to structured tools with Pydantic schemas. Call tools using JSON with properly typed arguments:
• find_doctor_info(name: str, specialty: str, city: str)
• find_doctor_availability(doctor_name: str, date_iso: str, specialty: str)
• get_pricing(service_type: str, clinic_name: str, specialty: str)
• book_appointment(doctor_name: str, date_iso: str, time_hhdd: str, patient_name: str, phone: str, service_type: str)
• place_call(phone_number: str, purpose: str, urgency: str)
• recommend_product(product_category: str, reason: str, price_range: str)
• push_content(content_type: str, topic: str, target_audience: str)
• search_notes(query: str, category: str)
• search_web(query: str, language: str)
• get_current_date()

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
• Be autonomous in tool selection - no heuristics needed
• Use structured schemas for all tool arguments
• All tool calls and arguments will be observed and logged

### <DYNAMIC_CONTEXT>"""

        # Add tool execution results if available
        if enhanced_context.get('tool_results'):
            system_content += f"\n✅ Tool Results Available: {len(enhanced_context['tool_results'])} tools executed."
            for tool_result in enhanced_context['tool_results']:
                if tool_result.get('success', False):
                    tool_name = tool_result.get('tool')
                    result_summary = str(tool_result.get('result', ''))[:150]
                    system_content += f"\n• {tool_name}: {result_summary}..."
        
        # Add callback observation info
        if enhanced_context.get('tool_calls_observed'):
            system_content += f"\n📊 Observed {len(enhanced_context['tool_calls_observed'])} tool call events via CallbackManager"
        
        # Add context sources summary
        context_sources = enhanced_context.get('context_sources', [])
        if context_sources:
            system_content += f"\n📚 Available Context: {len(context_sources)} sources"
        
        system_content += "\n</DYNAMIC_CONTEXT>"
        
        system_message = {
            'role': 'system',
            'content': system_content
        }
        
        # Insert system message at the beginning
        enhanced_messages.insert(0, system_message)
        
        return enhanced_messages
    
    async def _generate_streaming_response(self, llm_provider, messages: List, model: str, context: Dict):
        """Generate streaming response with citations."""
        try:
            logger.info("🌊 Generating AGENTIC streaming response")
            
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
            
            # Use the streaming response generator with agentic enhancements
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
                # Add agentic metadata to each chunk
                if isinstance(chunk, dict):
                    chunk['agentic_mode'] = True
                    if context.get('metadata'):
                        chunk['agentic_metadata'] = context['metadata']
                    
                    # Add tool execution results to progress
                    if context.get('tool_results') and chunk.get('progress'):
                        chunk['progress']['agentic_tools'] = {
                            'tools_executed': len(context['tool_results']),
                            'successful_tools': len([t for t in context['tool_results'] if t.get('success', False)]),
                            'callback_events': context['metadata'].get('callback_events', 0)
                        }
                
                yield chunk
                
        except Exception as e:
            logger.error(f"❌ Agentic streaming response generation failed: {e}")
            import traceback
            traceback.print_exc()
            
            # Yield error chunk
            error_chunk = {
                'error': str(e),
                'agentic_mode': True,
                'timestamp': time.time()
            }
            yield error_chunk
    
    async def _generate_non_streaming_response(self, llm_provider, messages: List, model: str, context: Dict):
        """Generate non-streaming response."""
        try:
            logger.info("📝 Generating AGENTIC non-streaming response")
            
            # Use LLM provider directly for non-streaming
            response = await llm_provider.agenerate_chat(messages)
            
            return {
                'response': response.message.content,
                'status': 'success',
                'agentic_mode': True,
                'metadata': context.get('metadata', {}),
                'tool_results': context.get('tool_results', []),
                'timestamp': time.time()
            }
            
        except Exception as e:
            logger.error(f"❌ Agentic non-streaming response generation failed: {e}")
            return {
                'error': str(e),
                'status': 'error',
                'agentic_mode': True,
                'timestamp': time.time()
            }
