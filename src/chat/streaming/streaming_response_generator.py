"""
Simplified Streaming Response Module - Using astream_chat for everything

This module handles streaming AI responses for both context-aware and 
context-free chat scenarios using a unified astream_chat approach.
Context is added as system messages instead of custom prompts.
"""

import time
import asyncio
import logging
import os
from typing import Dict, Any, List, Optional, AsyncGenerator
from llama_index.core.base.llms.types import ChatMessage, MessageRole

logger = logging.getLogger(__name__)


class StreamingResponseGenerator:
    """
    Simplified streaming response generator using astream_chat for everything
    """

    def __init__(self, rag_processor, file_attachment_manager, web_search_processor):
        self.rag_processor = rag_processor
        self.file_attachment_manager = file_attachment_manager
        self.web_search_processor = web_search_processor
        logger.info(
            "StreamingResponseGenerator initialized with unified astream_chat approach")

    def _convert_to_chat_messages(self, messages: List[Dict[str, Any]]) -> List[ChatMessage]:
        """Convert message dictionaries to ChatMessage objects"""
        chat_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            # Map roles to MessageRole enum
            if role == "system":
                llamaindex_role = MessageRole.SYSTEM
            elif role == "assistant":
                llamaindex_role = MessageRole.ASSISTANT
            else:  # user or any other role
                llamaindex_role = MessageRole.USER

            chat_messages.append(ChatMessage(
                role=llamaindex_role,
                content=content
            ))

        return chat_messages

    async def generate_streaming_response(
        self,
        request_data: Dict[str, Any],
        rag_context,
        attachment_context,
        websearch_context,
        llm,
        provider_enum,
        model: str,
        enable_citations: bool,
        router_decision=None,
        generate_title: bool = False
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Generate streaming response using unified astream_chat approach
        """

        chat_id = f"chatcmpl-modular-{os.urandom(4).hex()}"
        full_content = ""

        logger.info(f"🌊 === UNIFIED STREAMING RESPONSE (astream_chat) ===")
        logger.info(f"🌊 Chat ID: {chat_id}")
        logger.info(f"🌊 Model: {model}, Provider: {provider_enum.value}")

        try:
            # Phase 1: Initialization
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

            # Phase 2: Build context and messages
            messages = request_data.get("messages", [])

            # Build context parts
            context_parts = []
            has_context = False

            logger.info("🔧 === CONTEXT BUILDING STAGE ===")

            # Add attachment context - PRIORITY: File attachments come first
            if attachment_context and (attachment_context.chunks or attachment_context.image_chunks):
                has_context = True
                attachment_context_text = self.file_attachment_manager.chunks_to_context_text(
                    attachment_context.chunks, attachment_context.image_chunks)
                context_parts.insert(
                    0, f"FILE ATTACHMENTS:\n{attachment_context_text}")

                logger.info("📎 ATTACHMENT CONTEXT ADDED:")
                logger.info(
                    f"📎 - Text chunks: {len(attachment_context.chunks) if attachment_context.chunks else 0}")
                logger.info(
                    f"📎 - Image chunks: {len(attachment_context.image_chunks) if attachment_context.image_chunks else 0}")

            # Add RAG context
            if rag_context and rag_context.chunks:
                has_context = True
                rag_context_text = self.rag_processor.chunks_to_context_text(
                    rag_context.chunks)
                context_parts.append(f"KNOWLEDGE BASE:\n{rag_context_text}")
                logger.info(
                    f"📚 RAG CONTEXT ADDED: {len(rag_context.chunks)} chunks")

                # Log detailed RAG context content
                logger.info("📚 === RAG CONTEXT DETAILS ===")
                logger.info(
                    f"RAG context preview (first 300 chars):\n{rag_context_text[:300]}{'...' if len(rag_context_text) > 300 else ''}")
                logger.info(f"📊 Chunk breakdown:")
                note_chunks = [
                    c for c in rag_context.chunks if c.type == 'note']
                conv_chunks = [
                    c for c in rag_context.chunks if c.type == 'conversation']
                logger.info(f"  - Note chunks: {len(note_chunks)}")
                logger.info(f"  - Conversation chunks: {len(conv_chunks)}")
                if note_chunks:
                    logger.info(
                        f"  - Note IDs: {list(set(c.type_id for c in note_chunks))[:5]}{'...' if len(set(c.type_id for c in note_chunks)) > 5 else ''}")
                if conv_chunks:
                    logger.info(
                        f"  - Conversation IDs: {list(set(c.type_id for c in conv_chunks))[:5]}{'...' if len(set(c.type_id for c in conv_chunks)) > 5 else ''}")
                logger.info("=== END RAG CONTEXT DETAILS ===")

            # Add web search context
            if websearch_context and websearch_context.results:
                has_context = True
                websearch_context_text = self.web_search_processor.results_to_context_text(
                    websearch_context.results)
                context_parts.append(
                    f"WEB SEARCH RESULTS:\n{websearch_context_text}")
                logger.info(
                    f"🌐 WEB SEARCH CONTEXT ADDED: {len(websearch_context.results)} results")

            # Phase 3: Prepare messages for streaming
            if has_context:
                # WITH CONTEXT: Insert system message right before the last user message
                combined_context = "\n\n".join(context_parts)

                logger.info(
                    "🌊 STREAMING WITH CONTEXT: Adding system message before last user message")
                logger.info(
                    f"🌊 Context length: {len(combined_context)} characters")

                # Log the actual combined context content
                logger.info("🌊 === FINAL COMBINED CONTEXT ===")
                logger.info(
                    f"Context preview (first 500 chars):\n{combined_context[:500]}{'...' if len(combined_context) > 500 else ''}")
                logger.info(f"📊 Context structure:")
                for i, part in enumerate(context_parts):
                    part_type = "UNKNOWN"
                    if part.startswith("FILE ATTACHMENTS:"):
                        part_type = "FILE ATTACHMENTS"
                    elif part.startswith("KNOWLEDGE BASE:"):
                        part_type = "KNOWLEDGE BASE"
                    elif part.startswith("WEB SEARCH RESULTS:"):
                        part_type = "WEB SEARCH RESULTS"
                    logger.info(
                        f"  Part {i+1}: {part_type} ({len(part)} chars)")
                logger.info("=== END FINAL COMBINED CONTEXT ===")

                system_message = {
                    "role": "system",
                    "content": f"""Below are the relevant context based on the latest user message:

AVAILABLE CONTEXT:
{combined_context}

Please use this context to answer the user's question accurately and naturally."""
                }

                # Insert system message right before the last user message
                messages_with_context = messages.copy()
                if len(messages_with_context) > 0 and messages_with_context[-1].get("role") == "user":
                    # Insert system message before the last user message
                    messages_with_context.insert(-1, system_message)
                else:
                    # Fallback: add system message at the end
                    messages_with_context.append(system_message)

            else:
                # WITHOUT CONTEXT: Use original messages
                logger.info(
                    "🌊 STREAMING WITHOUT CONTEXT: Using original messages")
                messages_with_context = messages

            # Convert to ChatMessage objects
            chat_messages = self._convert_to_chat_messages(
                messages_with_context)

            logger.info(f"🌊 Final chat messages count: {len(chat_messages)}")
            logger.info(
                f"🌊 Message roles: {[msg.role.value for msg in chat_messages]}")

            # Phase 4: Status update
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

            # Phase 5: Stream the response using astream_chat
            logger.info("🌊 CALLING: llm.astream_chat (unified approach)")

            # Get the async iterator - some LLMs return a coroutine that needs to be awaited
            try:
                stream_response = llm.astream_chat(chat_messages)
                # Check if it's a coroutine that needs to be awaited
                if hasattr(stream_response, '__await__'):
                    stream_response = await stream_response
            except Exception as stream_setup_error:
                logger.error(f"❌ Stream setup error: {stream_setup_error}")
                raise stream_setup_error

            chunk_count = 0
            full_content = ""  # Track the complete content for title generation

            async for chunk in stream_response:
                chunk_count += 1

                # DEBUG: Log chunk structure for first few chunks
                if chunk_count <= 3:
                    logger.info(f"🔍 DEBUG Chunk {chunk_count} structure:")
                    logger.info(f"🔍 - Type: {type(chunk)}")
                    logger.info(f"🔍 - Has delta: {hasattr(chunk, 'delta')}")
                    logger.info(
                        f"🔍 - Has message: {hasattr(chunk, 'message')}")
                    if hasattr(chunk, 'delta'):
                        logger.info(
                            f"🔍 - Delta content: '{str(chunk.delta)[:50]}...'")
                    if hasattr(chunk, 'message') and hasattr(chunk.message, 'content'):
                        logger.info(
                            f"🔍 - Message content: '{str(chunk.message.content)[:50]}...'")

                # Extract content from chat stream chunk - handle different formats
                new_content = ""

                # Method 1: Try delta first (incremental content)
                if hasattr(chunk, 'delta') and chunk.delta:
                    delta_content = str(chunk.delta)
                    if delta_content and delta_content != 'None':
                        new_content = delta_content

                # Method 2: Try message.content (usually cumulative)
                elif hasattr(chunk, 'message') and hasattr(chunk.message, 'content'):
                    current_full_content = chunk.message.content

                    # Only extract NEW content if this is cumulative
                    if current_full_content and len(current_full_content) > len(full_content):
                        new_content = current_full_content[len(full_content):]
                    # If current_full_content is equal or smaller, it's likely a duplicate or final chunk
                    # DON'T use it as new_content to avoid duplication

                # Method 3: Fallback to string conversion (be very careful here)
                elif str(chunk) not in ['None', '', 'ChatResponse()']:
                    potential_content = str(chunk)
                    # Only use if it doesn't look like the full content
                    if len(potential_content) < 100 and not full_content.endswith(potential_content):
                        new_content = potential_content

                # Only send if we have new content
                if new_content:
                    full_content += new_content  # Update our running total

                    logger.debug(
                        f"🌊 Chunk {chunk_count}: NEW='{new_content[:30]}...' (total len: {len(full_content)})")

                    yield {
                        "id": chat_id,
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": model or "auto",
                        "provider": provider_enum.value,
                        "choices": [{
                            "index": 0,
                            "delta": {
                                "content": new_content  # Only the NEW content
                            },
                            "finish_reason": None
                        }]
                    }

                # Yield control to event loop
                await asyncio.sleep(0)

            logger.info(
                f"🌊 STREAMING COMPLETED: {chunk_count} chunks, {len(full_content)} characters")
            logger.info(f"🌊 Context used: {has_context}")

            # Phase 6: Final chunk with metadata
            final_metadata = {
                "rag_enabled": bool(rag_context),
                "web_search_enabled": bool(websearch_context),
                "attachments_enabled": bool(attachment_context),
                "context_used": has_context,
                "router_used": router_decision is not None,
                "used_notes": rag_context.used_note_ids if rag_context else [],
                "used_conversations": rag_context.used_conversation_ids if rag_context else [],
                "total_chunks": rag_context.total_chunks if rag_context else 0,
                "attachment_chunks": attachment_context.total_chunks if attachment_context else 0,
                "web_search_results": websearch_context.total_results if websearch_context else 0
            }

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

            logger.info("🌊 === STREAMING RESPONSE COMPLETED ===")

        except Exception as e:
            logger.error(f"❌ Streaming error: {e}")
            logger.error(f"❌ Error type: {type(e)}")
            logger.error(f"❌ Error details: {str(e)}")

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

    async def _yield_context_status(self, chat_id, model, provider_enum,
                                    rag_context, attachment_context, websearch_context):
        """Yield status updates for context processing"""

        if rag_context:
            logger.info(
                f"📚 Yielding RAG status: {rag_context.total_chunks} chunks from {len(rag_context.used_note_ids)} notes")
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
            logger.info(
                f"📎 Yielding attachment status: {attachment_context.total_chunks} chunks from {len(attachment_context.urls_processed)} files")
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
            logger.info(
                f"🌐 Yielding web search status: {websearch_context.total_results} results")
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

    async def _build_streaming_context(self, request_data, rag_context, attachment_context, websearch_context):
        """Build context for streaming and determine strategy"""

        logger.info("🔧 === STREAMING CONTEXT BUILDING STAGE ===")

        context_parts = []
        has_context = False
        query = None

        # Add attachment context - PRIORITY: File attachments come first
        if attachment_context and (attachment_context.chunks or attachment_context.image_chunks):
            has_context = True
            attachment_context_text = self.file_attachment_manager.chunks_to_context_text(
                attachment_context.chunks, attachment_context.image_chunks)
            context_parts.insert(
                0, f"FILE ATTACHMENTS:\n{attachment_context_text}")
            if not query:
                query = attachment_context.query_used

            logger.info(
                f"📎 ATTACHMENT CONTEXT ADDED (PRIORITY - STREAMING VERSION):")
            logger.info(
                f"📎 - Text chunks: {len(attachment_context.chunks) if attachment_context.chunks else 0}")
            logger.info(
                f"📎 - Image chunks: {len(attachment_context.image_chunks) if attachment_context.image_chunks else 0}")
            logger.info(f"📎 Attachment context preview: {attachment_context_text[:300]}..." if len(
                attachment_context_text) > 300 else f"📎 Attachment context: {attachment_context_text}")

        # Add RAG context
        if rag_context and rag_context.chunks:
            has_context = True
            rag_context_text = self.rag_processor.chunks_to_context_text(
                rag_context.chunks)
            context_parts.append(f"KNOWLEDGE BASE:\n{rag_context_text}")
            query = rag_context.query_used
            logger.info(
                f"📚 RAG CONTEXT ADDED (STREAMING VERSION): {len(rag_context.chunks)} chunks")
            logger.info(f"📚 RAG Context preview: {rag_context_text[:200]}..." if len(
                rag_context_text) > 200 else f"📚 RAG Context: {rag_context_text}")

        # Add web search context
        if websearch_context and websearch_context.results:
            has_context = True
            websearch_context_text = self.web_search_processor.results_to_context_text(
                websearch_context.results)
            context_parts.append(
                f"WEB SEARCH RESULTS:\n{websearch_context_text}")
            if not query:
                query = websearch_context.query_used
            logger.info(
                f"🌐 WEB SEARCH CONTEXT ADDED (STREAMING): {len(websearch_context.results)} results")
            logger.info(f"🌐 Web search context preview: {websearch_context_text[:200]}..." if len(
                websearch_context_text) > 200 else f"🌐 Web search context: {websearch_context_text}")

        # Build final prompt if context exists
        prompt = None
        if has_context:
            combined_context = "\n\n".join(context_parts)
            if not query:
                query = self._extract_last_user_message(
                    request_data.get("messages", []))

            logger.info("🎯 === FINAL COMBINED CONTEXT (STREAMING) ===")
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
            logger.info("🎯 === NO CONTEXT AVAILABLE FOR STREAMING ===")
            logger.info("🎯 Will use original message structure for streaming")

        return {
            "has_context": has_context,
            "prompt": prompt,
            "query": query
        }

    async def _stream_with_context(self, chat_id, model, provider_enum, prompt, llm):
        """Stream response with context using stream_complete"""

        logger.info("🌊 === STREAMING WITH CONTEXT PATH ===")
        logger.info("🌊 Using llm.stream_complete(context_prompt)")
        logger.info(f"🌊 Prompt length: {len(prompt)} characters")

        try:
            stream_response = llm.stream_complete(prompt)
            chunk_count = 0

            for chunk in stream_response:
                chunk_count += 1

                # Extract content from the chunk
                content = ""
                if hasattr(chunk, 'delta') and chunk.delta:
                    content = str(chunk.delta)
                else:
                    content = str(chunk)

                if content:
                    logger.debug(
                        f"🌊 WITH CONTEXT - Chunk {chunk_count}: {content[:50]}...")

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

                # Yield control to event loop
                await asyncio.sleep(0)

            logger.info(
                f"🌊 WITH CONTEXT - Streamed {chunk_count} chunks successfully")

        except Exception as stream_error:
            logger.error(f"❌ Context streaming failed: {stream_error}")
            # Fallback for context streaming
            yield {
                "id": chat_id,
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": model or "auto",
                "provider": provider_enum.value,
                "choices": [{
                    "index": 0,
                    "delta": {
                        "content": f"Error in context streaming: {str(stream_error)}"
                    },
                    "finish_reason": None
                }]
            }

    async def _stream_without_context(self, chat_id, model, provider_enum, messages, llm):
        """Stream response without context using astream_chat"""

        logger.info("🌊 === STREAMING WITHOUT CONTEXT PATH ===")
        logger.info("🌊 Using llm.astream_chat(chat_messages)")
        logger.info(f"🌊 Messages count: {len(messages)}")

        # Convert messages to ChatMessage objects to preserve system prompts
        chat_messages = self._convert_to_chat_messages(messages)

        try:
            # Use async chat streaming to preserve system prompts and message structure
            stream_response = llm.astream_chat(chat_messages)
            chunk_count = 0

            async for chunk in stream_response:
                chunk_count += 1

                # Extract content from chat stream chunk
                content = ""
                if hasattr(chunk, 'message') and hasattr(chunk.message, 'content'):
                    content = chunk.message.content
                elif hasattr(chunk, 'delta') and chunk.delta:
                    content = str(chunk.delta)
                else:
                    content = str(chunk)

                if content:
                    logger.debug(
                        f"🌊 WITHOUT CONTEXT - Chunk {chunk_count}: {content[:50]}...")

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

                # Yield control to event loop
                await asyncio.sleep(0)

            logger.info(
                f"🌊 WITHOUT CONTEXT - Streamed {chunk_count} chunks successfully")

        except Exception as stream_error:
            logger.error(f"❌ No-context streaming failed: {stream_error}")
            # Fallback for no-context streaming
            yield {
                "id": chat_id,
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": model or "auto",
                "provider": provider_enum.value,
                "choices": [{
                    "index": 0,
                    "delta": {
                        "content": f"Error in no-context streaming: {str(stream_error)}"
                    },
                    "finish_reason": None
                }]
            }

    def _convert_to_chat_messages(self, messages):
        """Convert message dictionaries to LlamaIndex ChatMessage objects"""
        from llama_index.core.base.llms.types import ChatMessage, MessageRole

        chat_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            # Map roles to LlamaIndex MessageRole enum
            if role == "system":
                llamaindex_role = MessageRole.SYSTEM
            elif role == "assistant":
                llamaindex_role = MessageRole.ASSISTANT
            else:  # user or any other role
                llamaindex_role = MessageRole.USER

            chat_messages.append(ChatMessage(
                role=llamaindex_role,
                content=content
            ))

        logger.info(
            f"🔄 Converted {len(messages)} messages to ChatMessage objects")
        logger.info(f"🔄 Roles: {[msg.role.value for msg in chat_messages]}")

        return chat_messages

    def _extract_last_user_message(self, messages: List[Dict[str, Any]]) -> str:
        """Extract the last user message for queries"""
        for msg in reversed(messages):
            if isinstance(msg, dict) and msg.get("role") == "user":
                content = msg.get("content", "")
                if isinstance(content, str) and content.strip():
                    return content.strip()
        return "Hello! How can I help you?"

    async def _generate_title_async(self, messages, full_content, llm):
        """Generate conversation title asynchronously"""
        try:
            # Import here to avoid circular imports
            from ..title.title_generator import title_generator

            # Create a temporary message list with the full conversation including new assistant response
            messages_with_response = messages.copy()
            messages_with_response.append({
                "role": "assistant",
                "content": full_content
            })

            generated_title = await title_generator.generate_conversation_title(messages_with_response, llm)
            return generated_title if generated_title else "New Conversation"
        except Exception as e:
            logger.error(f"Failed to generate title in streaming: {e}")
            return "New Conversation"

    def _create_final_chunk(self, chat_id, model, provider_enum,
                            rag_context, attachment_context, websearch_context,
                            router_decision, generated_title):
        """Create the final chunk with metadata"""

        final_metadata = {
            "rag_enabled": bool(rag_context),
            "web_search_enabled": bool(websearch_context),
            "attachments_enabled": bool(attachment_context),
            "router_used": router_decision is not None,
            "router_reasoning": router_decision.reasoning if router_decision else None,
            "router_confidence": router_decision.confidence if router_decision else None,
            "used_notes": rag_context.used_note_ids if rag_context else [],
            "used_conversations": rag_context.used_conversation_ids if rag_context else [],
            "total_chunks": rag_context.total_chunks if rag_context else 0,
            "attachment_chunks": attachment_context.total_chunks if attachment_context else 0,
            "web_search_results": websearch_context.total_results if websearch_context else 0
        }

        if generated_title:
            final_metadata["generated_title"] = generated_title

        return {
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
