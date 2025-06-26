"""
Streaming Citation Engine - Citation system with streaming progress updates

This module provides streaming citation capabilities with priority-based progress updates:
1. RAG processing (searching through notes)
2. File attachment processing (searching through files) 
3. Web search processing (searching through web)
4. LLM response generation with citations
"""

import asyncio
import logging
import os
from typing import AsyncGenerator, Dict, Any, List, Optional
from .citation_engine import CitationEngine, CitationResult, CitationSource

logger = logging.getLogger(__name__)


class StreamingCitationEngine(CitationEngine):
    """Streaming citation engine with progress updates"""

    def __init__(self):
        super().__init__()
        logger.info("StreamingCitationEngine initialized")

    async def stream_citation_response(self,
                                       query: str,
                                       rag_task=None,
                                       attachment_task=None,
                                       websearch_task=None,
                                       llm=None,
                                       request_data: Dict[str, Any] = None) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream citation response with priority-based progress updates

        Priority order: RAG → Attachments → Web Search → LLM Generation

        Args:
            query: User's question
            rag_task: Async RAG processing task
            attachment_task: Async file attachment task
            websearch_task: Async web search task
            llm: LLM provider for generation
            request_data: Original request data for metadata

        Yields:
            Dict: Streaming response chunks with progress and content
        """
        logger.info("🚀 Starting streaming citation response...")

        # Initialize response metadata
        chat_id = f"chatcmpl-{os.urandom(8).hex()}"
        created_time = int(asyncio.get_event_loop().time())
        model_name = request_data.get(
            'model', 'auto') if request_data else 'auto'

        # Yield initial status
        yield self._create_progress_chunk(
            chat_id, created_time, model_name,
            stage="initializing",
            message="Starting search process..."
        )

        # Track completion status
        contexts = {
            'rag': None,
            'attachment': None,
            'websearch': None
        }

        tasks = []
        task_names = []

        # Prepare tasks in priority order
        if rag_task:
            tasks.append(rag_task)
            task_names.append('rag')

        if attachment_task:
            tasks.append(attachment_task)
            task_names.append('attachment')

        if websearch_task:
            tasks.append(websearch_task)
            task_names.append('websearch')

        if not tasks:
            # No context processing needed
            yield self._create_progress_chunk(
                chat_id, created_time, model_name,
                stage="no_context",
                message="No additional context needed, generating direct response..."
            )

            # Generate direct response
            async for chunk in self._stream_direct_response(chat_id, created_time, model_name, query, llm):
                yield chunk
            return

        # Stream progress as tasks complete in priority order
        async for context_update in self._stream_context_gathering(
            chat_id, created_time, model_name, tasks, task_names
        ):
            # Update contexts as they complete
            if 'rag_context' in context_update:
                contexts['rag'] = context_update['rag_context']
            if 'attachment_context' in context_update:
                contexts['attachment'] = context_update['attachment_context']
            if 'websearch_context' in context_update:
                contexts['websearch'] = context_update['websearch_context']

            yield context_update

        # All context gathering complete - generate citation response
        yield self._create_progress_chunk(
            chat_id, created_time, model_name,
            stage="citation_generation_start",
            message="Generating response with citations..."
        )

        # Stream the citation response generation
        async for chunk in self._stream_citation_generation(
            chat_id, created_time, model_name, query,
            contexts['rag'], contexts['attachment'], contexts['websearch'], llm
        ):
            yield chunk

    async def _stream_context_gathering(self,
                                        chat_id: str,
                                        created_time: int,
                                        model_name: str,
                                        tasks: List,
                                        task_names: List[str]) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream context gathering with priority-based progress updates"""

        completed_tasks = set()
        contexts = {}

        # Use asyncio.as_completed to get results as they finish
        for coro in asyncio.as_completed(tasks):
            try:
                result = await coro

                # Determine which task completed by matching the result
                # This is a bit tricky - we'll use task position for now
                task_index = None
                for i, task in enumerate(tasks):
                    if task == coro:
                        task_index = i
                        break

                if task_index is not None and task_index < len(task_names):
                    task_name = task_names[task_index]
                    completed_tasks.add(task_name)
                    contexts[f'{task_name}_context'] = result

                    # Yield priority-based progress update
                    yield self._create_context_progress_chunk(
                        chat_id, created_time, model_name,
                        task_name, result, completed_tasks, len(tasks)
                    )

            except Exception as e:
                logger.error(f"Context gathering task failed: {e}")
                # Continue with other tasks
                continue

    def _create_context_progress_chunk(self,
                                       chat_id: str,
                                       created_time: int,
                                       model_name: str,
                                       completed_task: str,
                                       result: Any,
                                       completed_tasks: set,
                                       total_tasks: int) -> Dict[str, Any]:
        """Create progress chunk for completed context task"""

        # Determine stage and message based on completed task
        if completed_task == 'rag':
            if result and hasattr(result, 'total_chunks') and result.total_chunks > 0:
                stage = "rag_complete"
                message = f"✅ Found {result.total_chunks} relevant notes/conversations"
            else:
                stage = "rag_complete_empty"
                message = "📝 No relevant notes found"

        elif completed_task == 'attachment':
            if result and hasattr(result, 'total_chunks') and result.total_chunks > 0:
                stage = "attachment_complete"
                message = f"✅ Processed {result.total_chunks} file attachments"
            else:
                stage = "attachment_complete_empty"
                message = "📎 No file attachments to process"

        elif completed_task == 'websearch':
            if result and hasattr(result, 'total_results') and result.total_results > 0:
                cache_status = " (cached)" if result.cache_hit else ""
                stage = "websearch_complete"
                message = f"✅ Found {result.total_results} web results{cache_status}"
            else:
                stage = "websearch_complete_empty"
                message = "🌐 No web search results found"
        else:
            stage = f"{completed_task}_complete"
            message = f"✅ {completed_task.title()} processing complete"

        # Determine next task if any
        next_message = None
        if len(completed_tasks) < total_tasks:
            remaining_tasks = ['rag', 'attachment', 'websearch']
            for task in remaining_tasks:
                if task not in completed_tasks:
                    if task == 'rag':
                        next_message = "🔍 Searching through notes..."
                    elif task == 'attachment':
                        next_message = "📎 Searching through files..."
                    elif task == 'websearch':
                        next_message = "🌐 Searching through web..."
                    break

        chunk = self._create_progress_chunk(
            chat_id, created_time, model_name, stage, message
        )

        # Add result context to chunk
        chunk[f'{completed_task}_context'] = result

        # Add next task message if applicable
        if next_message:
            chunk['next_stage_message'] = next_message

        return chunk

    async def _stream_citation_generation(self,
                                          chat_id: str,
                                          created_time: int,
                                          model_name: str,
                                          query: str,
                                          rag_context=None,
                                          attachment_context=None,
                                          websearch_context=None,
                                          llm=None) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream the actual citation response generation"""

        try:
            # Extract sources and build citation prompt
            sources = self._extract_all_sources(
                rag_context, attachment_context, websearch_context)

            if not sources:
                # No sources available - stream direct response
                async for chunk in self._stream_direct_response(chat_id, created_time, model_name, query, llm):
                    yield chunk
                return

            # Build citation prompt
            citation_prompt = self._build_citation_prompt(query, sources)

            # Yield start of generation
            yield self._create_progress_chunk(
                chat_id, created_time, model_name,
                stage="llm_generation_start",
                message=f"Generating response with {len(sources)} sources..."
            )

            # Stream LLM response
            try:
                response_generator = llm.stream_complete(citation_prompt)

                for i, chunk in enumerate(response_generator):
                    chunk_text = chunk.delta if hasattr(
                        chunk, 'delta') else str(chunk)

                    yield {
                        "id": chat_id,
                        "object": "chat.completion.chunk",
                        "created": created_time,
                        "model": model_name,
                        "choices": [{
                            "index": 0,
                            "delta": {
                                "role": "assistant" if i == 0 else None,
                                "content": chunk_text
                            },
                            "finish_reason": None
                        }],
                        "sources": sources if i == 0 else None,  # Include sources in first chunk
                        "total_sources": len(sources) if i == 0 else None
                    }

                # Final chunk with completion
                yield {
                    "id": chat_id,
                    "object": "chat.completion.chunk",
                    "created": created_time,
                    "model": model_name,
                    "choices": [{
                        "index": 0,
                        "delta": {},
                        "finish_reason": "stop"
                    }]
                }

            except Exception as e:
                logger.error(f"LLM streaming failed: {e}")
                yield self._create_error_chunk(chat_id, created_time, model_name, f"Generation failed: {str(e)}")

        except Exception as e:
            logger.error(f"Citation generation failed: {e}")
            yield self._create_error_chunk(chat_id, created_time, model_name, f"Citation processing failed: {str(e)}")

    async def _stream_direct_response(self,
                                      chat_id: str,
                                      created_time: int,
                                      model_name: str,
                                      query: str,
                                      llm=None) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream direct response without citations"""

        try:
            response_generator = llm.stream_complete(query)

            for i, chunk in enumerate(response_generator):
                chunk_text = chunk.delta if hasattr(
                    chunk, 'delta') else str(chunk)

                yield {
                    "id": chat_id,
                    "object": "chat.completion.chunk",
                    "created": created_time,
                    "model": model_name,
                    "choices": [{
                        "index": 0,
                        "delta": {
                            "role": "assistant" if i == 0 else None,
                            "content": chunk_text
                        },
                        "finish_reason": None
                    }]
                }

            # Final chunk
            yield {
                "id": chat_id,
                "object": "chat.completion.chunk",
                "created": created_time,
                "model": model_name,
                "choices": [{
                    "index": 0,
                    "delta": {},
                    "finish_reason": "stop"
                }]
            }

        except Exception as e:
            logger.error(f"Direct response streaming failed: {e}")
            yield self._create_error_chunk(chat_id, created_time, model_name, f"Direct response failed: {str(e)}")

    def _create_progress_chunk(self,
                               chat_id: str,
                               created_time: int,
                               model_name: str,
                               stage: str,
                               message: str) -> Dict[str, Any]:
        """Create progress chunk for streaming"""
        return {
            "id": chat_id,
            "object": "chat.completion.chunk",
            "created": created_time,
            "model": model_name,
            "choices": [{
                "index": 0,
                "delta": {},
                "finish_reason": None
            }],
            "progress": {
                "stage": stage,
                "message": message
            }
        }

    def _create_error_chunk(self,
                            chat_id: str,
                            created_time: int,
                            model_name: str,
                            error_message: str) -> Dict[str, Any]:
        """Create error chunk for streaming"""
        return {
            "id": chat_id,
            "object": "chat.completion.chunk",
            "created": created_time,
            "model": model_name,
            "choices": [{
                "index": 0,
                "delta": {},
                "finish_reason": "error"
            }],
            "error": error_message
        }
