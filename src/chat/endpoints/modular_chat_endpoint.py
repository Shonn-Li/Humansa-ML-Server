"""
New Modular Chat Endpoint - Integration with existing system

This endpoint demonstrates the new modular architecture working with
the existing enhanced_chat_bot.py implementation for comparison and gradual migration.
"""

from chat.websearch.web_search_processor import web_search_processor
from chat.attachment.file_attachment_manager import file_attachment_manager
from chat.embedding.embedding_manager import embedding_manager
from chat.rag.rag_processor import RAGProcessor
from chat.provider.llm_provider import LLMProviderSelector
from chat.citation import CitationEngine, StreamingCitationEngine
from chat.router.intelligent_router import IntelligentRouter
from chat.title.title_generator import title_generator
from chat.query.query_transformer import QueryTransformer
from chat.streaming.streaming_response_generator import StreamingResponseGenerator
import os
import json
import logging
import time
import asyncio
from typing import Dict, Any, List, Optional

# Import our new modular system - fix paths
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))


logger = logging.getLogger(__name__)


def configure_azure_logging():
    """Configure Azure logging to reduce verbosity - call after imports"""
    azure_loggers = [
        'azure.core.pipeline.policies.http_logging_policy',
        'azure.ai.inference',
        'azure.core.pipeline',
        'azure.identity',
        'azure.core',
        'asyncio'
    ]

    for logger_name in azure_loggers:
        azure_logger = logging.getLogger(logger_name)
        azure_logger.setLevel(logging.WARNING)
        # Prevent propagation to root logger
        azure_logger.propagate = False

    # Specifically suppress asyncio ResourceWarnings about unclosed sessions
    import warnings
    warnings.filterwarnings(
        "ignore", message=".*unclosed.*", category=ResourceWarning)
    warnings.filterwarnings("ignore", message=".*Unclosed client session.*")
    warnings.filterwarnings("ignore", message=".*Unclosed connector.*")

    # Override asyncio logger to suppress specific error messages
    asyncio_logger = logging.getLogger('asyncio')
    asyncio_logger.addFilter(AsyncioFilter())

    logger.info("🔇 Azure logging configured - reduced verbosity")


class AsyncioFilter(logging.Filter):
    """Filter to suppress specific asyncio error messages"""

    def filter(self, record):
        # Suppress unclosed client session messages
        message = record.getMessage()
        if any(phrase in message.lower() for phrase in [
            'unclosed client session',
            'unclosed connector',
            'source_traceback',
            'client_session:',
            'connector:'
        ]):
            return False
        return True


def cleanup_azure_clients():
    """Enhanced cleanup for Azure client sessions with better error suppression"""
    try:
        import gc
        import asyncio
        import warnings
        import os

        # Suppress warnings during cleanup
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", ResourceWarning)
            warnings.simplefilter("ignore")

            # Force garbage collection to clean up unclosed sessions
            gc.collect()

            # Get current event loop and cancel pending tasks if possible
            try:
                loop = asyncio.get_event_loop()

                # Override the exception handler temporarily to suppress unclosed session warnings
                original_handler = loop.get_exception_handler()

                def silent_handler(loop, context):
                    # Silently ignore unclosed session warnings
                    message = context.get('message', '')
                    if not any(phrase in message.lower() for phrase in [
                        'unclosed client session',
                        'unclosed connector',
                        'unclosed ssl transport'
                    ]):
                        # Only log non-session-related exceptions
                        if original_handler:
                            original_handler(loop, context)
                        else:
                            logger.debug(f"Asyncio: {message}")

                loop.set_exception_handler(silent_handler)

                # Schedule restoration of original handler
                def restore_handler():
                    try:
                        loop.set_exception_handler(original_handler)
                    except:
                        pass

                loop.call_later(1.0, restore_handler)

            except:
                pass  # Not critical if this fails

    except Exception as e:
        # Don't log cleanup errors unless in debug mode
        if os.getenv('DEBUG_AZURE_CLEANUP'):
            logger.debug(f"Client cleanup note: {e}")


def log_azure_request(model: str, endpoint: str):
    """Clean logging for Azure requests - only what we care about"""
    logger.info(
        f"🔗 Azure AI Request: {model} -> {endpoint.split('/')[-3] if '/' in endpoint else endpoint}")


def log_llm_completion_start(provider: str, model: str, prompt_length: int):
    """Log the start of LLM completion with essential info"""
    logger.info(
        f"🤖 {provider.upper()} completion starting: {model} (prompt: {prompt_length} chars)")


class ModularChatEndpoint:
    """
    New modular chat endpoint that can be added to main.py
    Demonstrates clean separation of concerns
    """

    def __init__(self):
        self.provider_selector = LLMProviderSelector()
        self.rag_processor = RAGProcessor()
        self.citation_engine = CitationEngine()
        self.streaming_citation_engine = StreamingCitationEngine()
        self.router = None  # Will be initialized when needed
        self.query_transformer = QueryTransformer(
            self.provider_selector)  # NEW: Query transformer

        # NEW: Initialize streaming response generator
        self.streaming_generator = StreamingResponseGenerator(
            self.rag_processor,
            file_attachment_manager,
            web_search_processor
        )

        # Configure Azure logging to reduce verbosity
        configure_azure_logging()

        logger.info(
            "ModularChatEndpoint initialized with citation engines, router retriever support, query transformer, and streaming generator")

    async def handle_chat_request(self, request_data: Dict[str, Any]):
        """
        Handle chat request using new modular architecture

        Request format (same as existing but cleaner processing):
        {
            "messages": [...],
            "user_id": 123,
            "enable_rag": true,
            "enable_citations": false,
            "enable_web_search": true,
            "enable_router_retriever": true,  // NEW: Use intelligent routing (default: true)
            "generate_title": false,  // NEW: Generate conversation title (default: false)
            "enable_title_generation": false,  // Alternative parameter name for title generation
            "search_query": "optional custom search query",
            "stream": false,
            "note_ids": [1, 2, 3],
            "folder_ids": [10, 11],
            "conversation_ids": [100, 101],
            "attachments": [
                {"url": "https://example.com/file1.pdf"},
                {"url": "https://example.com/file2.jpg"}
            ],
            "provider": "openai",
            "model": "gpt-4.1-nano",
            "temperature": 0.7,
            "max_tokens": 1000
        }
        """

        # Extract parameters
        messages = request_data.get("messages", [])
        user_id = request_data.get("user_id")

        # Convert user_id to integer for database compatibility
        if user_id is not None:
            try:
                user_id = int(user_id)
            except (ValueError, TypeError):
                return {
                    "error": f"user_id must be a valid integer, got: {user_id}",
                    "status": "error"
                }
        enable_rag = request_data.get("enable_rag", True)
        enable_citations = request_data.get("enable_citations", False)
        enable_web_search = request_data.get("enable_web_search", False)
        enable_router_retriever = request_data.get(
            "enable_router_retriever", True)  # Default True
        # Support both parameter names for title generation
        generate_title = request_data.get("generate_title", False) or request_data.get(
            "enable_title_generation", False)
        # Optional custom search query
        search_query = request_data.get("search_query")
        stream = request_data.get("stream", False)  # Stream parameter
        note_ids = request_data.get("note_ids")
        folder_ids = request_data.get("folder_ids")
        conversation_ids = request_data.get("conversation_ids")
        attachments = request_data.get("attachments", [])  # File attachments
        provider = request_data.get("provider")
        model = request_data.get("model")
        temperature = request_data.get("temperature")
        max_tokens = request_data.get("max_tokens")

        # Validate required parameters
        if not user_id:
            return {
                "error": "user_id is required",
                "status": "error"
            }

        if not messages:
            return {
                "error": "messages are required",
                "status": "error"
            }

        logger.info(f"=== NEW MODULAR CHAT REQUEST ===")
        logger.info(
            f"User: {user_id}, RAG: {enable_rag}, Citations: {enable_citations}, WebSearch: {enable_web_search}, Stream: {stream}")
        logger.info(
            f"Router Retriever: {enable_router_retriever}, Generate Title: {generate_title}")
        logger.info(f"Provider: {provider}, Model: {model}")
        logger.info(f"Attachments: {len(attachments)} files")

        try:
            # Phase 1: Provider Selection - Prefer Azure Inference for cost savings
            if not provider:
                # Default to Azure Inference for cost savings
                provider = "azure_inference"
                if not model:
                    model = "gpt-4.1-nano"  # Cost-effective default
                logger.info(
                    f"💰 Defaulting to Azure Inference for cost savings: {provider} with {model}")

            provider_enum, llm = self.provider_selector.select_provider_and_model(
                provider, model)

            # Configure LLM parameters
            if temperature is not None:
                llm.temperature = temperature
            if max_tokens is not None:
                llm.max_tokens = max_tokens

            logger.info(f"✅ Selected: {provider_enum.value}")

            # Phase 1.5: Query Transformation - NEW STEP!
            logger.info("🔄 STARTING QUERY TRANSFORMATION...")
            original_query = self._extract_last_user_message(messages)

            try:
                transformation_result = await self.query_transformer.transform_query(
                    original_query=original_query,
                    messages=messages
                )

                condensed_query = transformation_result["condensed_query"]
                transformation_success = transformation_result["transformation_success"]
                context_messages_used = transformation_result["context_messages_used"]

                if transformation_success:
                    logger.info(
                        f"✅ Query transformation successful using {context_messages_used} context messages")
                    logger.info(f"Original: {original_query[:100]}...")
                    logger.info(f"Condensed: {condensed_query[:100]}...")
                    query = condensed_query  # Use the enriched query for everything
                else:
                    logger.info(
                        f"⚠️ Query transformation failed, using original query: {transformation_result.get('fallback_reason', 'unknown')}")
                    query = original_query

            except Exception as e:
                logger.error(f"❌ Query transformation error: {e}")
                logger.info("Using original query as fallback")
                query = original_query

            # Initialize Pure Decision Router - MUST WORK!
            if enable_router_retriever and not self.router:
                try:
                    self.router = IntelligentRouter()
                    logger.info(
                        "🎯 Pure Decision Router initialized successfully")
                except RuntimeError as e:
                    logger.error(
                        f"🚨 CRITICAL: RouterQueryEngine failed to initialize: {e}")
                    logger.error(
                        "🔧 Disabling router and using original enable flags...")
                    enable_router_retriever = False
                    self.router = None

            # Phase 2: Context Retrieval Strategy
            rag_context = None
            attachment_context = None
            websearch_context = None
            router_decision = None
            search_type = "mixed"  # Default search type when router is not used

            # Determine which sources are enabled
            available_sources = {
                "rag": enable_rag,
                "attachments": bool(attachments),
                "web_search": enable_web_search
            }

            # Router-based decision vs parallel processing
            if enable_router_retriever and self.router:
                logger.info(
                    "🎯 USING INTELLIGENT ROUTER FOR DECISION-MAKING WITH CONDENSED QUERY...")

                try:
                    # Get pure routing decision using CONDENSED QUERY (no retrieval yet)
                    router_decision = await self.router.route_query(
                        query=query,  # Using condensed query for better routing decisions
                        user_id=user_id,
                        # Last 6 messages for context
                        conversation_history=messages[-6:] if len(
                            messages) > 6 else messages
                    )

                    # Map router decision to enable flags
                    search_type = router_decision.search_type

                    # Set enable flags based on search type
                    if search_type == "none":
                        enable_rag = False
                        enable_web_search = False
                        enable_attachments = False
                    elif search_type == "web":
                        enable_rag = False
                        enable_web_search = True
                        enable_attachments = False
                    elif search_type == "attachments":
                        enable_rag = False
                        enable_web_search = False
                        enable_attachments = True
                    else:  # notes, conversations, mixed
                        enable_rag = True
                        enable_web_search = False
                        enable_attachments = False

                    logger.info(
                        f"🎯 Router decision: RAG={enable_rag}, Web={enable_web_search}, Attachments={enable_attachments}")
                    logger.info(
                        f"🧠 Router reasoning: {router_decision.reasoning}")
                    logger.info(
                        f"🔍 Search type: {search_type}")

                except RuntimeError as e:
                    logger.error(
                        f"🚨 CRITICAL: RouterQueryEngine decision failed: {e}")
                    logger.error(
                        "🔧 This must be fixed - RouterQueryEngine is essential!")
                    logger.error(
                        "🔄 Disabling router for this request and using original flags...")
                    enable_router_retriever = False
                    router_decision = None

            # Process contexts based on final enable flags (router or original)
            logger.info("⚡ PROCESSING ENABLED SOURCES...")

            # Create tasks for parallel execution
            tasks = []

            # RAG Processing Task (if enabled)
            if enable_rag:
                logger.info(
                    f"🔍 STARTING RAG WITH CONDENSED QUERY (search_type: {search_type})...")
                rag_task = self.rag_processor.process_rag_request(
                    messages=messages,
                    user_id=user_id,
                    note_ids=note_ids,
                    folder_ids=folder_ids,
                    conversation_ids=conversation_ids,
                    top_k=20,
                    custom_query=query,  # Use condensed query for better RAG results
                    search_type=search_type  # Pass search type from router
                )
                tasks.append(("rag", rag_task))

            # File Attachment Processing Task (if attachments provided)
            if attachments:
                logger.info(
                    f"📎 STARTING FILE ATTACHMENT PROCESSING: {len(attachments)} files")
                attachment_task = file_attachment_manager.process_attachments(
                    attachments=attachments,
                    query=query,
                    user_id=user_id,
                    top_k=8
                )
                tasks.append(("attachments", attachment_task))

            # Web Search Processing Task (if enabled)
            if enable_web_search:
                logger.info("🌐 STARTING WEB SEARCH WITH CONDENSED QUERY...")
                # Use condensed query for better web search results, fallback to custom search_query if provided
                # Use condensed query instead of extracting from messages
                search_query_to_use = search_query or query
                websearch_task = web_search_processor.search_web_content(
                    query=search_query_to_use,
                    num_results=5
                )
                tasks.append(("websearch", websearch_task))

            # Execute tasks in parallel
            if tasks:
                import asyncio
                task_results = await asyncio.gather(
                    *[task[1] for task in tasks],
                    return_exceptions=True
                )

                # Process results
                for i, (task_type, _) in enumerate(tasks):
                    result = task_results[i]

                    if isinstance(result, Exception):
                        logger.error(
                            f"❌ {task_type.upper()} processing failed: {result}")
                        continue

                    if task_type == "rag":
                        rag_context = result
                        logger.info(
                            f"🧠 RAG COMPLETE: {rag_context.total_chunks} chunks found")
                    elif task_type == "attachments":
                        attachment_context = result
                        logger.info(
                            f"📎 ATTACHMENTS COMPLETE: {attachment_context.total_chunks} chunks found")
                    elif task_type == "websearch":
                        websearch_context = result
                        cache_status = "cache hit" if websearch_context.cache_hit else "fresh search"
                        logger.info(
                            f"🌐 WEB SEARCH COMPLETE: {websearch_context.total_results} results found ({cache_status})")
            else:
                logger.info(
                    "⚡ No RAG, attachment, or web search processing needed")

            # Phase 3: Response Generation - Stream vs Non-Stream
            if stream:
                # Streaming response - return async generator
                logger.info(
                    "🌊 STREAMING MODE: Using modular streaming generator")
                return self.streaming_generator.generate_streaming_response(
                    request_data=request_data,
                    rag_context=rag_context,
                    attachment_context=attachment_context,
                    websearch_context=websearch_context,
                    llm=llm,
                    provider_enum=provider_enum,
                    model=model,
                    enable_citations=enable_citations,
                    router_decision=router_decision,
                    generate_title=generate_title
                )
            else:
                # Non-streaming response - return complete response
                logger.info(
                    "💬 NON-STREAMING MODE: Generating complete response")
                if enable_citations and ((rag_context and rag_context.chunks) or (attachment_context and attachment_context.chunks) or (websearch_context and websearch_context.results)):
                    response_data = await self._generate_with_citations(rag_context, attachment_context, websearch_context, llm)
                else:
                    response_data = await self._generate_direct_response(rag_context, attachment_context, websearch_context, messages, llm)

                # Generate conversation title if requested
                generated_title = None
                if generate_title:
                    try:
                        generated_title = await self._generate_conversation_title(messages, llm)
                    except Exception as e:
                        logger.error(f"Failed to generate title: {e}")
                        generated_title = "New Conversation"

                # Convert to OpenAI format with choices array
                openai_response = self._format_as_openai_response(
                    response_data,
                    model,
                    llm,
                    provider_enum,
                    enable_rag,
                    enable_citations,
                    enable_web_search,
                    rag_context,
                    attachment_context,
                    websearch_context,
                    len(attachments),
                    router_decision,
                    generated_title
                )

                return openai_response

        except Exception as e:
            logger.error(f"❌ Modular chat processing failed: {e}")
            return {
                "error": f"Processing failed: {str(e)}",
                "status": "error"
            }

    async def _generate_with_citations(self, rag_context, attachment_context, websearch_context, llm) -> Dict[str, Any]:
        """Generate response with citations using new citation engine"""
        logger.info("🎯 Citation mode - using new citation engine")

        try:
            # Use the new citation engine to generate response with citations
            citation_result = await self.citation_engine.generate_citation_response(
                rag_context=rag_context,
                attachment_context=attachment_context,
                websearch_context=websearch_context,
                llm=llm
            )

            return {
                "content": citation_result.response,
                "citations": citation_result.sources,
                "context_used": True,
                "context_sources": {
                    "rag_chunks": len(rag_context.chunks) if rag_context else 0,
                    "attachment_chunks": len(attachment_context.chunks) if attachment_context else 0,
                    "attachment_image_chunks": len(attachment_context.image_chunks) if attachment_context else 0,
                    "websearch_chunks": len(websearch_context.results) if websearch_context else 0,
                    "total_citations": len(citation_result.sources)
                },
                "status": "success"
            }

        except Exception as e:
            logger.error(f"❌ Citation engine failed: {e}")
            logger.info("🔄 Falling back to direct response")
            # Fall back to direct response without citations
            return await self._generate_direct_response(rag_context, attachment_context, websearch_context, None, llm)

    async def _generate_direct_response(self, rag_context, attachment_context, websearch_context, messages, llm) -> Dict[str, Any]:
        """Generate response with direct context injection"""

        has_context = False
        context_parts = []
        query = None

        logger.info("🔧 === CONTEXT BUILDING STAGE ===")

        # Add RAG context
        if rag_context and rag_context.chunks:
            has_context = True
            rag_context_text = self.rag_processor.chunks_to_context_text(
                rag_context.chunks)
            context_parts.append(f"KNOWLEDGE BASE:\n{rag_context_text}")
            query = rag_context.query_used
            logger.info(
                f"📚 RAG CONTEXT ADDED: {len(rag_context.chunks)} chunks")
            logger.info(f"📚 RAG Context preview: {rag_context_text[:200]}..." if len(
                rag_context_text) > 200 else f"📚 RAG Context: {rag_context_text}")

        # Add attachment context - PRIORITY: File attachments come first
        if attachment_context and (attachment_context.chunks or attachment_context.image_chunks):
            has_context = True
            attachment_context_text = file_attachment_manager.chunks_to_context_text(
                attachment_context.chunks, attachment_context.image_chunks)
            # INSERT AT BEGINNING
            context_parts.insert(
                0, f"FILE ATTACHMENTS:\n{attachment_context_text}")
            if not query:  # Use attachment query if no RAG query
                query = attachment_context.query_used

            logger.info(
                f"📎 ATTACHMENT CONTEXT ADDED (PRIORITY - INSERTED AT BEGINNING):")
            logger.info(
                f"📎 - Text chunks: {len(attachment_context.chunks) if attachment_context.chunks else 0}")
            logger.info(
                f"📎 - Image chunks: {len(attachment_context.image_chunks) if attachment_context.image_chunks else 0}")
            logger.info(f"📎 Attachment context preview: {attachment_context_text[:300]}..." if len(
                attachment_context_text) > 300 else f"📎 Attachment context: {attachment_context_text}")

        # Add web search context
        if websearch_context and websearch_context.results:
            has_context = True
            websearch_context_text = web_search_processor.results_to_context_text(
                websearch_context.results)
            context_parts.append(
                f"WEB SEARCH RESULTS:\n{websearch_context_text}")
            if not query:  # Use web search query if no other query
                query = websearch_context.query_used
            logger.info(
                f"🌐 WEB SEARCH CONTEXT ADDED: {len(websearch_context.results)} results")
            logger.info(f"🌐 Web search context preview: {websearch_context_text[:200]}..." if len(
                websearch_context_text) > 200 else f"🌐 Web search context: {websearch_context_text}")

        if has_context:
            # With combined context
            combined_context = "\n\n".join(context_parts)
            if not query:
                query = self._extract_last_user_message(messages)

            logger.info("🎯 === FINAL COMBINED CONTEXT ===")
            logger.info(
                f"🎯 Context parts order: {[part.split(':')[0] for part in context_parts]}")
            logger.info(
                f"🎯 Total context length: {len(combined_context)} characters")
            logger.info(f"🎯 Query used: {query}")
            logger.info("🎯 Combined context preview (first 500 chars):")
            logger.info(f"🎯 {combined_context[:500]}...")
            logger.info("🎯 ================================")

            prompt = f"""You are an AI assistant. Use the following context to answer the user's question.

CONTEXT:
{combined_context}

QUESTION: {query}

INSTRUCTIONS:
- Answer based primarily on the provided context
- Be specific and reference relevant information naturally
- If the context doesn't fully answer the question, say so honestly
- Keep your response helpful and concise

ANSWER:"""
        else:
            # Without context
            query = self._extract_last_user_message(messages)
            prompt = f"{query}"

        try:
            # Log the completion start with essential info
            provider_info = getattr(llm, 'model', 'unknown')
            log_llm_completion_start("azure", provider_info, len(prompt))

            response = await llm.acomplete(prompt)
            content = str(response)

            # Cleanup Azure sessions after completion
            cleanup_azure_clients()

            return {
                "content": content,
                "context_used": has_context,
                "context_sources": {
                    "rag_chunks": len(rag_context.chunks) if rag_context else 0,
                    "attachment_chunks": len(attachment_context.chunks) if attachment_context else 0,
                    "attachment_image_chunks": len(attachment_context.image_chunks) if attachment_context else 0
                },
                "status": "success"
            }

        except Exception as e:
            logger.error(f"LLM completion failed: {e}")
            return {
                "error": f"LLM completion failed: {str(e)}",
                "status": "error"
            }

    async def _generate_direct_response_with_sources(self, rag_context, attachment_context, websearch_context, llm) -> Dict[str, Any]:
        """Generate response with source tracking (pseudo-citations)"""

        context_parts = []
        all_chunks = []
        query = None

        logger.info("🔧 === CONTEXT BUILDING STAGE (WITH SOURCES) ===")

        # Add attachment context and chunks - PRIORITY: File attachments come first
        if attachment_context and (attachment_context.chunks or attachment_context.image_chunks):
            attachment_context_text = file_attachment_manager.chunks_to_context_text(
                attachment_context.chunks, attachment_context.image_chunks)
            # INSERT AT BEGINNING
            context_parts.insert(
                0, f"FILE ATTACHMENTS:\n{attachment_context_text}")
            all_chunks.extend(attachment_context.chunks)
            if attachment_context.image_chunks:
                all_chunks.extend(attachment_context.image_chunks)
            if not query:  # Use attachment query if no RAG query
                query = attachment_context.query_used

            logger.info(
                f"📎 ATTACHMENT CONTEXT ADDED (PRIORITY - SOURCES VERSION):")
            logger.info(
                f"📎 - Text chunks: {len(attachment_context.chunks) if attachment_context.chunks else 0}")
            logger.info(
                f"📎 - Image chunks: {len(attachment_context.image_chunks) if attachment_context.image_chunks else 0}")
            logger.info(f"📎 Attachment context preview: {attachment_context_text[:300]}..." if len(
                attachment_context_text) > 300 else f"📎 Attachment context: {attachment_context_text}")

        # Add RAG context and chunks
        if rag_context and rag_context.chunks:
            rag_context_text = self.rag_processor.chunks_to_context_text(
                rag_context.chunks)
            context_parts.append(f"KNOWLEDGE BASE:\n{rag_context_text}")
            all_chunks.extend(rag_context.chunks)
            query = rag_context.query_used
            logger.info(
                f"📚 RAG CONTEXT ADDED (SOURCES VERSION): {len(rag_context.chunks)} chunks")
            logger.info(f"📚 RAG Context preview: {rag_context_text[:200]}..." if len(
                rag_context_text) > 200 else f"📚 RAG Context: {rag_context_text}")

        logger.info(
            f"🎯 SOURCES VERSION - Context parts order: {[part.split(':')[0] for part in context_parts]}")
        logger.info(f"🎯 SOURCES VERSION - Total chunks: {len(all_chunks)}")

        if not context_parts:
            return {
                "error": "No context available for citation generation",
                "status": "error"
            }

        combined_context = "\n\n".join(context_parts)

        prompt = f"""You are an AI assistant. Use the following context to answer the user's question and reference your sources.

CONTEXT:
{combined_context}

QUESTION: {query}

INSTRUCTIONS:
- Answer based primarily on the provided context
- Reference your sources naturally (e.g., "According to the knowledge base..." or "From the attached files...")
- Be specific and cite relevant information
- Keep your response helpful and well-sourced

ANSWER:"""

        try:
            # Log the completion start with essential info
            provider_info = getattr(llm, 'model', 'unknown')
            log_llm_completion_start("azure", provider_info, len(prompt))

            response = await llm.acomplete(prompt)
            content = str(response)

            # Cleanup Azure sessions after completion
            cleanup_azure_clients()

            # Create pseudo-citations from all chunks
            citations = []
            citation_id = 1

            # Add RAG citations
            if rag_context and rag_context.chunks:
                for chunk in rag_context.chunks[:10]:  # Top 10 RAG sources
                    citation = {
                        "id": citation_id,
                        "type": chunk.type,
                        "source_id": chunk.type_id,
                        "text": chunk.chunk_text[:200] + "..." if len(chunk.chunk_text) > 200 else chunk.chunk_text,
                        "similarity": chunk.similarity,
                        "source_category": "knowledge_base"
                    }
                    citations.append(citation)
                    citation_id += 1

            # Add attachment citations - PRIORITY: Images first, then text
            if attachment_context and (attachment_context.chunks or attachment_context.image_chunks):
                # Add image chunk citations first (always included)
                if attachment_context.image_chunks:
                    # Top 5 image chunks
                    for chunk in attachment_context.image_chunks[:5]:
                        citation = {
                            "id": citation_id,
                            "type": "file_attachment_image",
                            "source_id": chunk.url,
                            "text": chunk.chunk_text[:200] + "..." if len(chunk.chunk_text) > 200 else chunk.chunk_text,
                            "similarity": chunk.similarity,
                            "source_category": "file_attachment",
                            "url": chunk.url,
                            "is_image": True
                        }
                        citations.append(citation)
                        citation_id += 1

                # Add text chunk citations (similarity filtered)
                if attachment_context.chunks:
                    # Top 10 text chunks
                    for chunk in attachment_context.chunks[:10]:
                        citation = {
                            "id": citation_id,
                            "type": "file_attachment",
                            "source_id": chunk.url,
                            "text": chunk.chunk_text[:200] + "..." if len(chunk.chunk_text) > 200 else chunk.chunk_text,
                            "similarity": chunk.similarity,
                            "source_category": "file_attachment",
                            "url": chunk.url,
                            "is_image": False
                        }
                        citations.append(citation)
                        citation_id += 1

            return {
                "content": content,
                "citations": citations,
                "context_used": True,
                "context_sources": {
                    "rag_chunks": len(rag_context.chunks) if rag_context else 0,
                    "attachment_chunks": len(attachment_context.chunks) if attachment_context else 0,
                    "attachment_image_chunks": len(attachment_context.image_chunks) if attachment_context else 0,
                    "total_citations": len(citations)
                },
                "status": "success"
            }

        except Exception as e:
            logger.error(f"LLM completion with sources failed: {e}")
            return {
                "error": f"LLM completion failed: {str(e)}",
                "status": "error"
            }

    def _format_as_openai_response(self, response_data, model, llm, provider_enum,
                                   enable_rag, enable_citations, enable_web_search,
                                   rag_context, attachment_context, websearch_context, attachments_count, router_decision=None, generated_title=None):
        """Format the response in OpenAI chat completion format"""
        import time

        # Get the content from the response_data
        content = response_data.get("content", "")
        citations = response_data.get("citations", [])

        return {
            "id": f"chatcmpl-modular-{os.urandom(4).hex()}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model or (llm.model if hasattr(llm, 'model') else 'unknown'),
            "provider": provider_enum.value,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": content
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": 0,  # Could be calculated if needed
                "completion_tokens": len(content.split()) if content else 0,
                "total_tokens": len(content.split()) if content else 0
            },
            # Extended metadata for our system
            "metadata": {
                "rag_enabled": enable_rag,
                "citations_enabled": enable_citations,
                "web_search_enabled": enable_web_search,
                "router_retriever_used": router_decision is not None,
                "router_search_type": router_decision.search_type if router_decision else "mixed",
                "router_reasoning": router_decision.reasoning if router_decision else "",
                "router_confidence": router_decision.confidence if router_decision else 0.0,
                "used_notes": rag_context.used_note_ids if rag_context else [],
                "used_conversations": rag_context.used_conversation_ids if rag_context else [],
                "total_chunks": rag_context.total_chunks if rag_context else 0,
                "attachments_processed": attachments_count,
                "attachment_chunks": attachment_context.total_chunks if attachment_context else 0,
                "attachment_urls": attachment_context.urls_processed if attachment_context else [],
                "web_search_results": websearch_context.total_results if websearch_context else 0,
                "web_search_cache_hit": websearch_context.cache_hit if websearch_context else False,
                "web_search_query": websearch_context.query_used if websearch_context else "",
                "citations": citations if citations else [],
                "generated_title": generated_title  # NEW: Include generated conversation title
            },
            "status": response_data.get("status", "success")
        }

    async def _generate_conversation_title(self, messages: List[Dict[str, Any]], llm) -> str:
        """Generate a concise title for the conversation using the title generator module"""
        try:
            generated_title = await title_generator.generate_conversation_title(messages, llm)
            return generated_title if generated_title else "New Conversation"
        except Exception as e:
            logger.error(f"Failed to generate conversation title: {e}")
            return "New Conversation"

    def _extract_last_user_message(self, messages: List[Dict[str, Any]]) -> str:
        """Extract the last user message for queries"""
        for msg in reversed(messages):
            if isinstance(msg, dict) and msg.get("role") == "user":
                content = msg.get("content", "")
                if isinstance(content, str) and content.strip():
                    return content.strip()
        return "Hello! How can I help you?"

    async def _ensure_embeddings_exist(self, note_ids: List[int] = None, conversation_ids: List[int] = None) -> None:
        """
        🎯 CRITICAL EMBEDDING CHECK METHOD - RUNS BEFORE EVERY RAG SEARCH

        This method is called BEFORE performing vector similarity search to ensure
        all requested notes/conversations have embeddings. Missing embeddings are
        created asynchronously in the background without blocking the current request.

        FLOW:
        1. Check which note_ids are missing embeddings in embedding_v1 table
        2. Check which conversation_ids are missing embeddings in embedding_v1 table  
        3. If < 10 total missing: Launch async background embedding creation
        4. If > 10 total missing: Log warning, limit to first 10 (cost protection)
        5. Continue with RAG search using existing embeddings immediately
        6. Background tasks will make embeddings available for future requests
        """
        if not note_ids and not conversation_ids:
            logger.info(
                "🔍 No note_ids or conversation_ids provided - skipping embedding check")
            return

        try:
            logger.info(
                f"🔍 EMBEDDING CHECK: Scanning {len(note_ids or [])} notes and {len(conversation_ids or [])} conversations")

            # Use our independent embedding manager to check for missing embeddings
            notes_missing, conversations_missing = await embedding_manager.check_and_ensure_embeddings(
                note_ids=note_ids or [],
                conversation_ids=conversation_ids or [],
                max_missing_to_embed=10  # Limit to prevent API cost explosion
            )

            # Log the results for transparency
            if notes_missing:
                logger.info(
                    f"🔄 ASYNC EMBEDDING: {len(notes_missing)} notes missing embeddings, creating in background: {notes_missing}")
            else:
                logger.info(
                    "✅ NOTES: All requested notes already have embeddings")

            if conversations_missing:
                logger.info(
                    f"🔄 ASYNC EMBEDDING: {len(conversations_missing)} conversations missing embeddings, creating in background: {conversations_missing}")
            else:
                logger.info(
                    "✅ CONVERSATIONS: All requested conversations already have embeddings")

            # The embedding manager has now launched background tasks for missing items
            # Current request continues immediately with existing embeddings
            total_missing = len(notes_missing) + len(conversations_missing)
            if total_missing > 0:
                logger.info(
                    f"⚡ BACKGROUND TASKS: {total_missing} embedding tasks running in background")
                logger.info(
                    "🚀 RAG CONTINUES: Using existing embeddings, background embeddings will be available for future requests")

        except Exception as e:
            logger.error(f"❌ EMBEDDING CHECK FAILED: {e}")
            logger.info(
                "🔄 RAG CONTINUES: Proceeding with existing embeddings despite check failure")
            # Don't fail the request, just log the error and continue with existing embeddings

    def get_status(self) -> Dict[str, Any]:
        """Get modular system status"""
        return {
            "providers": self.provider_selector.get_available_providers(),
            "database": self.rag_processor.health_check(),
            "file_attachments": file_attachment_manager.get_status(),
            "status": "operational",
            "version": "modular-v1"
        }

    def _create_message_context(self, router_decision, rag_context, attachment_context, websearch_context, note_ids=None, folder_ids=None, conversation_ids=None):
        """Create context information for message tracking as per Message interface"""
        return {
            "noteIds": list(note_ids) if note_ids else (rag_context.used_note_ids if rag_context else []),
            "folderIds": list(folder_ids) if folder_ids else [],
            "conversationIds": list(conversation_ids) if conversation_ids else (rag_context.used_conversation_ids if rag_context else []),
            "enableRAG": bool(rag_context),
            "enableWebSearch": bool(websearch_context),
            "enableCitations": True,  # Always enabled in this endpoint
            # Additional router information
            "routerUsed": router_decision is not None,
            "routerReasoning": router_decision.reasoning if router_decision else None,
            "routerConfidence": router_decision.confidence if router_decision else None
        }


# Initialize the modular chat endpoint instance
modular_chat_endpoint = ModularChatEndpoint()
