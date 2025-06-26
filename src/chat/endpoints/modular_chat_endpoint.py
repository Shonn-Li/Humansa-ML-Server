"""
New Modular Chat Endpoint - Integration with existing system

This endpoint demonstrates the new modular architecture working alongside
the existing enhanced_chat_bot.py implementation for comparison and gradual migration.
"""

from chat.websearch.web_search_processor import web_search_processor
from chat.attachment.file_attachment_manager import file_attachment_manager
from chat.embedding.embedding_manager import embedding_manager
from chat.rag.rag_processor import RAGProcessor
from chat.provider.llm_provider import LLMProviderSelector
from chat.citation import CitationEngine, StreamingCitationEngine
from chat.router.intelligent_router_correct import IntelligentRouter
from chat.title.title_generator import title_generator
import os
import json
import logging
import time
import asyncio
from typing import Dict, Any, List, Optional

# Import our new modular system - fix paths
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

# Import for chat message handling
try:
    from llama_index.core.base.llms.types import ChatMessage, MessageRole
except ImportError:
    # Fallback if import fails
    class MessageRole:
        SYSTEM = "system"
        USER = "user"
        ASSISTANT = "assistant"

    class ChatMessage:
        def __init__(self, role, content):
            self.role = role
            self.content = content


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
        self.router = None  # Will be initialized when needed for intelligent routing decisions

        # Configure Azure logging to reduce verbosity
        configure_azure_logging()

        logger.info(
            "ModularChatEndpoint initialized with citation engines and router retriever support")

    async def handle_chat_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
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
            "model": "gpt-4o-mini",
            "temperature": 0.7,
            "max_tokens": 1000
        }
        """

        # Extract parameters
        messages = request_data.get("messages", [])
        user_id = request_data.get("user_id")
        enable_rag = request_data.get("enable_rag", True)
        enable_citations = request_data.get("enable_citations", False)
        enable_web_search = request_data.get("enable_web_search", False)
        enable_router_retriever = request_data.get(
            "enable_router_retriever", True)  # Default True
        # NEW: Generate conversation title
        generate_title = request_data.get("generate_title", False)
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
            f"Router Enabled: {enable_router_retriever}, Generate Title: {generate_title}")
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

            # Initialize Intelligent Router (decision-maker only, not a retriever)
            if enable_router_retriever and not self.router:
                self.router = IntelligentRouter(
                    provider_selector=self.provider_selector)
                logger.info(
                    "🎯 Intelligent Router initialized for decision-making")

            # Phase 2: Intelligent Routing Decision (DECISION ONLY, NOT RETRIEVAL)
            rag_context = None
            attachment_context = None
            websearch_context = None
            router_decision = None
            query = self._extract_last_user_message(messages)

            # Step 1: Router Decision - Override enable flags based on query analysis
            if enable_router_retriever and self.router:
                logger.info(
                    "🎯 USING INTELLIGENT ROUTER FOR DECISION-MAKING...")

                try:
                    # Prepare client flags for router
                    client_flags = {
                        'enable_rag': enable_rag,
                        'enable_web_search': enable_web_search,
                        'enable_attachments': bool(attachments),
                        'enable_citations': enable_citations
                    }

                    # Router makes decision on which sources to enable/disable
                    router_decision = self.router.make_routing_decision(
                        query, client_flags)

                    # Apply router decision to override client flags (within constraints)
                    enable_rag = router_decision.final_flags.get(
                        'enable_rag', enable_rag)
                    enable_web_search = router_decision.final_flags.get(
                        'enable_web_search', enable_web_search)
                    enable_citations = router_decision.final_flags.get(
                        'enable_citations', enable_citations)
                    # Attachments cannot be overridden if provided by client
                    enable_attachments = bool(attachments)

                    logger.info(
                        f"🎯 Router Decision: {router_decision.reasoning}")
                    logger.info(
                        f"🔧 Final Flags: RAG={enable_rag}, WebSearch={enable_web_search}, Citations={enable_citations}, Attachments={enable_attachments}")
                    if router_decision.changes_made:
                        logger.info(
                            f"📋 Router Changes: {', '.join(router_decision.changes_made)}")

                except Exception as e:
                    logger.error(f"❌ Router decision failed: {e}")
                    logger.info("🔄 Using original client flags...")
                    # Keep original flags if router fails

            # Step 2: Context Retrieval Based on Final Flags
            logger.info("⚡ STARTING CONTEXT RETRIEVAL BASED ON FINAL FLAGS...")

            # Create tasks for parallel execution based on final enable flags
            tasks = []

            # RAG Processing Task (if enabled after router decision)
            if enable_rag:
                logger.info("🔍 STARTING RAG WITH EMBEDDED CHECKS...")
                rag_task = self.rag_processor.process_rag_request(
                    messages=messages,
                    user_id=user_id,
                    note_ids=note_ids,
                    folder_ids=folder_ids,
                    conversation_ids=conversation_ids,
                    top_k=20
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

            # Web Search Processing Task (if enabled after router decision)
            if enable_web_search:
                logger.info("🌐 STARTING WEB SEARCH...")
                search_query_to_use = search_query or web_search_processor.extract_search_query(
                    messages)
                websearch_task = web_search_processor.search_web_content(
                    query=search_query_to_use,
                    num_results=5
                )
                tasks.append(("websearch", websearch_task))

            # Execute tasks in parallel (if any)
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
                    "⚡ No context retrieval needed based on final flags")

            # Phase 3: Response Generation - Stream vs Non-Stream
            if stream:
                # Streaming response - yield chunks
                logger.info("🌊 STREAMING MODE: Starting streaming response")
                return self._stream_response(
                    request_data, rag_context, attachment_context, websearch_context,
                    llm, provider_enum, model, enable_citations, router_decision, generate_title
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

        # Add RAG context
        if rag_context and rag_context.chunks:
            has_context = True
            rag_context_text = self.rag_processor.chunks_to_context_text(
                rag_context.chunks)
            context_parts.append(f"KNOWLEDGE BASE:\n{rag_context_text}")
            query = rag_context.query_used

        # Add attachment context
        if attachment_context and attachment_context.chunks:
            has_context = True
            attachment_context_text = file_attachment_manager.chunks_to_context_text(
                attachment_context.chunks)
            context_parts.append(
                f"FILE ATTACHMENTS:\n{attachment_context_text}")
            if not query:  # Use attachment query if no RAG query
                query = attachment_context.query_used

        # Add web search context
        if websearch_context and websearch_context.results:
            has_context = True
            websearch_context_text = web_search_processor.results_to_context_text(
                websearch_context.results)
            context_parts.append(
                f"WEB SEARCH RESULTS:\n{websearch_context_text}")
            if not query:  # Use web search query if no other query
                query = websearch_context.query_used

        if has_context:
            # With combined context
            combined_context = "\n\n".join(context_parts)
            if not query:
                query = self._extract_last_user_message(messages)

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

            try:
                # Log the completion start with essential info
                provider_info = getattr(llm, 'model', 'unknown')
                log_llm_completion_start("azure", provider_info, len(prompt))

                response = await llm.acomplete(prompt)
            except Exception as e:
                logger.error(f"LLM completion failed: {e}")
                return {
                    "error": f"LLM completion failed: {str(e)}",
                    "status": "error"
                }
        else:
            # Without context - use original messages to preserve system prompts
            try:
                # Convert messages to proper format for chat completion
                chat_messages = []
                for msg in messages:
                    role = MessageRole.SYSTEM if msg.get("role") == "system" else MessageRole.USER if msg.get(
                        "role") == "user" else MessageRole.ASSISTANT
                    chat_messages.append(ChatMessage(
                        role=role, content=msg.get("content", "")))

                # Log the completion start with essential info
                provider_info = getattr(llm, 'model', 'unknown')
                total_content = sum(len(msg.get("content", ""))
                                    for msg in messages)
                log_llm_completion_start("azure", provider_info, total_content)

                response = await llm.achat(chat_messages)
            except Exception as e:
                logger.error(f"LLM chat completion failed: {e}")
                return {
                    "error": f"LLM chat completion failed: {str(e)}",
                    "status": "error"
                }

        # Extract content from response
        content = str(response)

        # Cleanup Azure sessions after completion
        cleanup_azure_clients()

        return {
            "content": content,
            "context_used": has_context,
            "context_sources": {
                "rag_chunks": len(rag_context.chunks) if rag_context else 0,
                "attachment_chunks": len(attachment_context.chunks) if attachment_context else 0
            },
            "status": "success"
        }

    async def _generate_direct_response_with_sources(self, rag_context, attachment_context, websearch_context, llm) -> Dict[str, Any]:
        """Generate response with source tracking (pseudo-citations)"""

        context_parts = []
        all_chunks = []
        query = None

        # Add RAG context and chunks
        if rag_context and rag_context.chunks:
            rag_context_text = self.rag_processor.chunks_to_context_text(
                rag_context.chunks)
            context_parts.append(f"KNOWLEDGE BASE:\n{rag_context_text}")
            all_chunks.extend(rag_context.chunks)
            query = rag_context.query_used

        # Add attachment context and chunks
        if attachment_context and attachment_context.chunks:
            attachment_context_text = file_attachment_manager.chunks_to_context_text(
                attachment_context.chunks)
            context_parts.append(
                f"FILE ATTACHMENTS:\n{attachment_context_text}")
            all_chunks.extend(attachment_context.chunks)
            if not query:  # Use attachment query if no RAG query
                query = attachment_context.query_used

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

            # Add attachment citations
            if attachment_context and attachment_context.chunks:
                # Top 10 attachment sources
                for chunk in attachment_context.chunks[:10]:
                    citation = {
                        "id": citation_id,
                        "type": "file_attachment",
                        "source_id": chunk.url,
                        "text": chunk.chunk_text[:200] + "..." if len(chunk.chunk_text) > 200 else chunk.chunk_text,
                        "similarity": chunk.similarity,
                        "source_category": "file_attachment",
                        "url": chunk.url
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
                "router_decision_used": router_decision is not None,
                "router_decision_changes": router_decision.changes_made if router_decision else [],
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

    async def _stream_response(self, request_data, rag_context, attachment_context, websearch_context, llm, provider_enum, model, enable_citations, router_decision=None, generate_title=False):
        """Generate streaming response - async generator that yields chunks"""
        import time
        import asyncio

        chat_id = f"chatcmpl-modular-{os.urandom(4).hex()}"
        full_content = ""  # Collect full content for title generation

        try:
            # Yield initialization status
            yield {
                "id": chat_id,
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": model or "auto",
                "provider": provider_enum.value,
                "choices": [{
                    "index": 0,
                    "delta": {},
                    "finish_reason": None
                }],
                "progress": {
                    "stage": "initializing",
                    "message": "Starting response generation..."
                }
            }

            # Yield context processing status
            if rag_context:
                yield {
                    "id": chat_id,
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": model or "auto",
                    "provider": provider_enum.value,
                    "choices": [{
                        "index": 0,
                        "delta": {},
                        "finish_reason": None
                    }],
                    "progress": {
                        "stage": "searching_notes",
                        "message": f"Found {rag_context.total_chunks} relevant chunks from {len(rag_context.used_note_ids)} notes"
                    }
                }

            if attachment_context:
                yield {
                    "id": chat_id,
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": model or "auto",
                    "provider": provider_enum.value,
                    "choices": [{
                        "index": 0,
                        "delta": {},
                        "finish_reason": None
                    }],
                    "progress": {
                        "stage": "searching_files",
                        "message": f"Found {attachment_context.total_chunks} relevant chunks from {len(attachment_context.urls_processed)} files"
                    }
                }

            if websearch_context:
                yield {
                    "id": chat_id,
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": model or "auto",
                    "provider": provider_enum.value,
                    "choices": [{
                        "index": 0,
                        "delta": {},
                        "finish_reason": None
                    }],
                    "progress": {
                        "stage": "searching_web",
                        "message": f"Found {websearch_context.total_results} web search results"
                    }
                }

            # Yield response generation start
            yield {
                "id": chat_id,
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": model or "auto",
                "provider": provider_enum.value,
                "choices": [{
                    "index": 0,
                    "delta": {
                        "role": "assistant",
                        "content": ""
                    },
                    "finish_reason": None
                }],
                "progress": {
                    "stage": "generating_response",
                    "message": "Generating AI response..."
                }
            }

            # Build the prompt for LLM streaming
            context_parts = []
            has_context = False
            query = None

            # Add RAG context
            if rag_context and rag_context.chunks:
                has_context = True
                rag_context_text = self.rag_processor.chunks_to_context_text(
                    rag_context.chunks)
                context_parts.append(f"KNOWLEDGE BASE:\n{rag_context_text}")
                query = rag_context.query_used

            # Add attachment context
            if attachment_context and attachment_context.chunks:
                has_context = True
                attachment_context_text = file_attachment_manager.chunks_to_context_text(
                    attachment_context.chunks)
                context_parts.append(
                    f"FILE ATTACHMENTS:\n{attachment_context_text}")
                if not query:
                    query = attachment_context.query_used

            # Add web search context
            if websearch_context and websearch_context.results:
                has_context = True
                websearch_context_text = web_search_processor.results_to_context_text(
                    websearch_context.results)
                context_parts.append(
                    f"WEB SEARCH RESULTS:\n{websearch_context_text}")
                if not query:
                    query = websearch_context.query_used

            # Build the final prompt or use original messages
            if has_context:
                combined_context = "\n\n".join(context_parts)
                if not query:
                    query = self._extract_last_user_message(
                        request_data.get("messages", []))

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

                # Use completion for context-based responses
                stream_response = llm.stream_complete(prompt)
            else:
                # Without context - use original messages to preserve system prompts
                messages = request_data.get("messages", [])
                chat_messages = []
                for msg in messages:
                    role = MessageRole.SYSTEM if msg.get("role") == "system" else MessageRole.USER if msg.get(
                        "role") == "user" else MessageRole.ASSISTANT
                    chat_messages.append(ChatMessage(
                        role=role, content=msg.get("content", "")))

                # Use chat for preserving message structure
                stream_response = llm.stream_chat(chat_messages)

            # Use actual LLM streaming
            try:
                chunk_count = 0
                for chunk in stream_response:
                    chunk_count += 1

                    # Extract content from the chunk (same logic as old implementation)
                    if hasattr(chunk, 'delta') and chunk.delta:
                        content = str(chunk.delta)
                    else:
                        content = str(chunk)

                    if content:
                        full_content += content  # Collect for title generation

                        yield {
                            "id": chat_id,
                            "object": "chat.completion.chunk",
                            "created": int(time.time()),
                            "model": model or "auto",
                            "provider": provider_enum.value,
                            "choices": [{
                                "index": 0,
                                "delta": {
                                    "content": content
                                },
                                "finish_reason": None
                            }]
                        }

                    # Yield control to event loop (important for async generators)
                    await asyncio.sleep(0)

                logger.info(f"🌊 Streamed {chunk_count} chunks successfully")

            except Exception as stream_error:
                logger.warning(
                    f"⚠️ LLM streaming failed, falling back to non-streaming: {stream_error}")
                # Fallback to non-streaming response
                response_data = await self._generate_direct_response(rag_context, attachment_context, websearch_context, request_data.get("messages", []), llm)
                content = response_data.get("content", "")
                full_content = content  # Store for title generation

                # Yield the complete content in one chunk
                yield {
                    "id": chat_id,
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": model or "auto",
                    "provider": provider_enum.value,
                    "choices": [{
                        "index": 0,
                        "delta": {
                            "content": content
                        },
                        "finish_reason": None
                    }]
                }

            # Generate conversation title if requested
            generated_title = None
            if generate_title:
                try:
                    # Create a temporary message list with the full conversation including new assistant response
                    messages_with_response = request_data.get(
                        "messages", []).copy()
                    messages_with_response.append({
                        "role": "assistant",
                        "content": full_content
                    })
                    generated_title = await self._generate_conversation_title(messages_with_response, llm)
                except Exception as e:
                    logger.error(f"Failed to generate title in streaming: {e}")
                    generated_title = "New Conversation"

            # Final chunk with metadata and title
            final_metadata = {
                "rag_enabled": bool(rag_context),
                "router_decision_used": router_decision is not None,
                "router_decision_changes": router_decision.changes_made if router_decision else [],
                "used_notes": rag_context.used_note_ids if rag_context else [],
                "used_conversations": rag_context.used_conversation_ids if rag_context else [],
                "total_chunks": rag_context.total_chunks if rag_context else 0,
                "attachment_chunks": attachment_context.total_chunks if attachment_context else 0,
                "web_search_results": websearch_context.total_results if websearch_context else 0
            }

            if generated_title:
                final_metadata["generated_title"] = generated_title

            # Final chunk
            yield {
                "id": chat_id,
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": model or "auto",
                "provider": provider_enum.value,
                "choices": [{
                    "index": 0,
                    "delta": {},
                    "finish_reason": "stop"
                }],
                "metadata": final_metadata
            }

        except Exception as e:
            logger.error(f"❌ Streaming error: {e}")
            yield {
                "id": chat_id,
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": model or "auto",
                "provider": provider_enum.value,
                "choices": [{
                    "index": 0,
                    "delta": {},
                    "finish_reason": "error"
                }],
                "error": str(e)
            }


# Initialize the modular chat endpoint instance
modular_chat_endpoint = ModularChatEndpoint()
