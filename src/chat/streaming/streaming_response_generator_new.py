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
        logger.info("StreamingResponseGenerator initialized with unified astream_chat approach")

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
                context_parts.insert(0, f"FILE ATTACHMENTS:\n{attachment_context_text}")

                logger.info("📎 ATTACHMENT CONTEXT ADDED:")
                logger.info(f"📎 - Text chunks: {len(attachment_context.chunks) if attachment_context.chunks else 0}")
                logger.info(f"📎 - Image chunks: {len(attachment_context.image_chunks) if attachment_context.image_chunks else 0}")

            # Add RAG context
            if rag_context and rag_context.chunks:
                has_context = True
                rag_context_text = self.rag_processor.chunks_to_context_text(rag_context.chunks)
                context_parts.append(f"KNOWLEDGE BASE:\n{rag_context_text}")
                logger.info(f"📚 RAG CONTEXT ADDED: {len(rag_context.chunks)} chunks")

            # Add web search context
            if websearch_context and websearch_context.results:
                has_context = True
                websearch_context_text = self.web_search_processor.results_to_context_text(websearch_context.results)
                context_parts.append(f"WEB SEARCH RESULTS:\n{websearch_context_text}")
                logger.info(f"🌐 WEB SEARCH CONTEXT ADDED: {len(websearch_context.results)} results")

            # Phase 3: Prepare messages for streaming
            if has_context:
                # WITH CONTEXT: Add system message with context
                combined_context = "\n\n".join(context_parts)
                
                logger.info("🌊 STREAMING WITH CONTEXT: Adding system message")
                logger.info(f"🌊 Context length: {len(combined_context)} characters")
                
                system_message = {
                    "role": "system",
                    "content": f"""You are a helpful AI assistant. Use the following context to answer questions when relevant.

AVAILABLE CONTEXT:
{combined_context}

INSTRUCTIONS:
- Answer based on the provided context when relevant
- Be specific and reference information naturally
- If the context doesn't contain relevant information, answer normally
- Keep responses helpful and concise"""
                }
                
                # Build messages with system context
                messages_with_context = [system_message] + messages
                
            else:
                # WITHOUT CONTEXT: Use original messages
                logger.info("🌊 STREAMING WITHOUT CONTEXT: Using original messages")
                messages_with_context = messages

            # Convert to ChatMessage objects
            chat_messages = self._convert_to_chat_messages(messages_with_context)
            
            logger.info(f"🌊 Final chat messages count: {len(chat_messages)}")
            logger.info(f"🌊 Message roles: {[msg.role.value for msg in chat_messages]}")

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
                    full_content += content
                    
                    logger.debug(f"🌊 Chunk {chunk_count}: {content[:50]}...")

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

            logger.info(f"🌊 STREAMING COMPLETED: {chunk_count} chunks, {len(full_content)} characters")
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
