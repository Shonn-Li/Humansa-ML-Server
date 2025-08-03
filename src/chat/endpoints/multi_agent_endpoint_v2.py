"""
Multi-Agent Response Endpoint v2 - With OpenAI-Compatible Streaming Support

This enhanced version implements proper OpenAI-compatible streaming for the multi-agent workflow.
Each agent can contribute to the streaming response in real-time using the comprehensive format.
Supports reasoning, web search, function calls, and final responses with proper output items.
"""

import asyncio
import json
import logging
import time
import uuid
import traceback
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union, AsyncGenerator
from dataclasses import dataclass, asdict
from enum import Enum
from decimal import Decimal

# Import existing infrastructure
from ..router.intelligent_router import IntelligentRouter, RouterDecision
from ..citation.citation_engine import CitationSource
from ..rag.rag_processor import RAGProcessor
from ..websearch.web_search_processor import WebSearchProcessor
from ..attachment.file_attachment_manager import FileAttachmentManager
from ..provider.llm_provider import LLMProvider, LLMProviderSelector
from llama_index.core.llms import ChatMessage
from ..citation.citation_engine import CitationEngine, CitationResult
# Citation position tracker imported locally where needed
from ..query.query_transformer import QueryTransformer
from ..config.system_prompts import SystemPromptManager

# Import all agents from the new agent modules
from ..agent import (
    BaseAgent,
    RouterAgent,
    ContextSearchAgent,
    WebSearchAgent,
    AttachmentAgent,
    ResponseAgent,
    CodeInterpreterAgent,
    PythonToolAgent
)

logger = logging.getLogger(__name__)


class DecimalEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles Decimal types"""

    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        if hasattr(obj, '__dict__'):
            return obj.__dict__
        return super(DecimalEncoder, self).default(obj)


class StreamingChunk:
    """Helper class to create OpenAI-standard streaming chunks"""

    @staticmethod
    def create(content: str, role: str = "assistant", finish_reason: Optional[str] = None,
               model: str = "gpt-4.1-nano") -> Dict[str, Any]:
        """Create a standard streaming chunk"""
        return {
            "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": model,
            "choices": [{
                "index": 0,
                "delta": {"content": content} if content else {},
                "finish_reason": finish_reason
            }]
        }


class IterativeOrchestrator:
    """Orchestrates iterative agent workflows with evaluation and refinement"""

    def __init__(self, agents: Dict[str, BaseAgent], llm_provider_manager: LLMProviderSelector):
        self.agents = agents
        self.llm_provider_manager = llm_provider_manager
        self.max_iterations = 3
        self.iteration_count = 0

    async def should_iterate(self, context: Dict[str, Any], request: Dict[str, Any]) -> tuple[bool, List[str]]:
        """Evaluate if we need another iteration and which agents to run"""
        response_result = context.get("response_agent", {})
        response_text = response_result.get("response", "")

        # Don't iterate if we've reached max iterations
        if self.iteration_count >= self.max_iterations:
            return False, []

        # Don't iterate if no response was generated
        if not response_text:
            return False, []

        # Use LLM to evaluate response quality
        model = request.get("model", "gpt-4.1-nano")
        provider_info = self.llm_provider_manager.get_provider(None, model)
        llm = provider_info["llm"]

        eval_prompt = f"""Evaluate this response and determine if it needs improvement:

Query: {request['messages'][-1]['content']}
Response: {response_text}

Consider:
1. Is the response complete and accurate?
2. Are there missing details that could be found with more search?
3. Would additional context improve the answer?
4. Are citations needed but missing?

You MUST respond with ONLY valid JSON in this exact format:
{{
    "needs_iteration": false,
    "reason": "Response is complete and accurate",
    "suggested_agents": []
}}

Or if iteration is needed:
{{
    "needs_iteration": true,
    "reason": "Response lacks detail about X",
    "suggested_agents": ["rag", "web_search"]
}}

ONLY return the JSON object, no other text."""

        try:
            eval_messages = [ChatMessage(role="user", content=eval_prompt)]
            eval_response = await llm.achat(eval_messages)

            # Clean the response to ensure it's valid JSON
            response_text = eval_response.message.content.strip()

            # Handle DeepSeek <think> tags
            if "<think>" in response_text and "</think>" in response_text:
                # Extract content after </think> tag
                think_end = response_text.find("</think>")
                if think_end != -1:
                    response_text = response_text[think_end + 8:].strip()

            # Remove any markdown code blocks if present
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]

            # Log raw response for debugging
            logger.info(
                f"Iteration evaluation raw response: {response_text[:200]}...")

            eval_result = json.loads(response_text.strip())

            if eval_result.get("needs_iteration", False):
                self.iteration_count += 1
                suggested_agents = eval_result.get("suggested_agents", [])
                reason = eval_result.get(
                    "reason", "Quality improvement needed")
                logger.info(
                    f"Iteration {self.iteration_count} triggered: {reason}")
                return True, suggested_agents

            return False, []

        except Exception as e:
            logger.error(f"Error evaluating iteration need: {e}")
            return False, []

    async def run_iteration(self, request: Dict[str, Any], context: Dict[str, Any],
                            agents_to_run: List[str]) -> Dict[str, Any]:
        """Run a single iteration with specified agents"""
        iteration_context = context.copy()

        # Run specified agents
        for agent_name in agents_to_run:
            if agent_name in self.agents:
                logger.info(
                    f"Running {agent_name} agent in iteration {self.iteration_count}")
                result = await self.agents[agent_name].run(request, iteration_context)
                iteration_context[f"{agent_name}_agent"] = result

        # Always run response agent again to incorporate new context
        if "response" in self.agents:
            logger.info(f"Re-running response agent with updated context")
            response_result = await self.agents["response"].run(request, iteration_context)
            iteration_context["response_agent"] = response_result

        # If citations are enabled, update them
        if request.get("enable_citations", True) and "citation" in self.agents:
            logger.info(f"Updating citations with new context")
            citation_result = await self.agents["citation"].run(request, iteration_context)
            iteration_context["citation_agent"] = citation_result

        return iteration_context


class MultiAgentChatEndpointV2:
    """Enhanced multi-agent chat endpoint with streaming support and iterative workflows"""

    def __init__(self):
        self.llm_provider_manager = LLMProviderSelector()
        self.rag_processor = RAGProcessor()
        self.web_search_processor = WebSearchProcessor()
        self.file_attachment_manager = FileAttachmentManager()
        self.citation_engine = CitationEngine()

        # Initialize agents
        self.agents = {
            "router": RouterAgent(self.llm_provider_manager),
            "context_search": ContextSearchAgent(self.rag_processor),
            "web_search": WebSearchAgent(self.web_search_processor),
            "attachment": AttachmentAgent(self.file_attachment_manager),
            "code_interpreter": CodeInterpreterAgent(),
            "response": ResponseAgent(self.llm_provider_manager),
        }

        # Don't initialize orchestrator here - create per request to avoid state pollution

    async def handle_request(self, request: Dict[str, Any]) -> Union[Dict[str, Any], AsyncGenerator[Dict[str, Any], None]]:
        """Handle the request with streaming support"""

        if request.get("stream", False):
            return self._handle_streaming_request(request)
        else:
            return await self._handle_non_streaming_request(request)

    async def _handle_non_streaming_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle non-streaming request with improved agent tracking"""
        try:
            # Track agent usage and timing
            agent_times = {}
            agent_results = {}
            start_time = time.time()

            # Phase 1: Routing
            context = {}

            router_start = time.time()
            router_result = await self.agents["router"].run(request, context)
            context["router_agent"] = router_result
            agent_times["router"] = time.time() - router_start
            agent_results["router"] = {
                "status": "success", "data": router_result}

            enabled_agents = router_result.get("enabled_agents", ["response"])

            # Phase 2: Context Collection (parallel where possible)
            tasks = []

            if "context_search" in enabled_agents:
                tasks.append(
                    ("context_search", self.agents["context_search"].run(request, context)))

            if "web_search" in enabled_agents:
                tasks.append(
                    ("web_search", self.agents["web_search"].run(request, context)))

            if "attachment" in enabled_agents:
                tasks.append(
                    ("attachment", self.agents["attachment"].run(request, context)))

            if "code_interpreter" in enabled_agents:
                tasks.append(
                    ("code_interpreter", self.agents["code_interpreter"].run(request, context)))

            # Run context collection tasks in parallel
            if tasks:
                results = await asyncio.gather(*[task[1] for task in tasks], return_exceptions=True)
                for i, (agent_name, _) in enumerate(tasks):
                    if isinstance(results[i], Exception):
                        logger.error(
                            f"{agent_name} agent failed: {results[i]}")
                        context[f"{agent_name}_agent"] = {
                            "status": "error", "error": str(results[i])}
                        agent_results[agent_name] = {
                            "status": "error", "error": str(results[i])}
                    else:
                        context[f"{agent_name}_agent"] = results[i]
                        agent_results[agent_name] = {
                            "status": "success", "data": results[i]}

            # Phase 3: Response Generation
            response_start = time.time()
            response_result = await self.agents["response"].run(request, context)
            context["response_agent"] = response_result
            agent_times["response"] = time.time() - response_start
            agent_results["response"] = {
                "status": "success", "data": response_result}

            # Phase 4: Citation (if enabled)
            if "citation" in enabled_agents:
                citation_start = time.time()
                citation_result = await self.agents["citation"].run(request, context)
                context["citation_agent"] = citation_result
                agent_times["citation"] = time.time() - citation_start
                agent_results["citation"] = {
                    "status": "success", "data": citation_result}

            # Phase 5: Iterative Refinement (if enabled)
            total_iterations = 1  # At least one iteration (initial run)
            # TEMPORARILY DISABLED - causing pauses with reasoning models
            if request.get("enable_iterations", False) and "response" in enabled_agents:
                # Create new orchestrator instance per request to avoid state pollution
                orchestrator = IterativeOrchestrator(
                    self.agents, self.llm_provider_manager)

                # Check if we need iterations
                needs_iteration, suggested_agents = await orchestrator.should_iterate(context, request)

                while needs_iteration:
                    logger.info(
                        f"Running iteration {orchestrator.iteration_count} with agents: {suggested_agents}")

                    # Run iteration
                    context = await orchestrator.run_iteration(request, context, suggested_agents)

                    # Record iteration in agent results
                    agent_results[f"iteration_{orchestrator.iteration_count}"] = {
                        "agents": suggested_agents,
                        "status": "success"
                    }

                    # Check if we need another iteration
                    needs_iteration, suggested_agents = await orchestrator.should_iterate(context, request)

                total_iterations = orchestrator.iteration_count + 1

            # Final Response Assembly
            final_response = context.get(
                "response_agent", {}).get("response", "")
            if "citation" in enabled_agents and context.get("citation_agent", {}).get("status") == "success":
                cited_response = context["citation_agent"].get(
                    "citations", {}).get("response")
                if cited_response:
                    final_response = cited_response

            # Format as OpenAI-standard response
            return {
                "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": request.get("model", "gpt-4.1-nano"),
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": final_response
                    },
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": 0,  # Would need token counting
                    "completion_tokens": 0,
                    "total_tokens": 0
                },
                "metadata": {
                    "agents_used": enabled_agents,
                    "agent_times": agent_times,
                    "agent_results": agent_results,
                    "total_time": time.time() - start_time,
                    "iterations_performed": total_iterations - 1  # Don't count initial run
                }
            }

        except Exception as e:
            logger.error(f"Error in non-streaming request: {e}", exc_info=True)
            return {
                "error": {
                    "message": str(e),
                    "type": "internal_error",
                    "code": "multi_agent_error"
                }
            }

    async def _handle_streaming_request(self, request: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """Handle streaming request with OpenAI Response API format"""
        try:
            # Generate response ID
            response_id = f"resp_{uuid.uuid4().hex[:8]}"

            # Helper to create SSE events
            def create_event(event_type: str, **kwargs) -> Dict[str, Any]:
                event = {
                    "type": event_type,
                    "sequence_number": kwargs.get("sequence_number", 0)
                }
                # Add all other kwargs to the event
                event.update(kwargs)
                # Remove sequence_number from kwargs if it was there
                if "sequence_number" in kwargs:
                    del event["sequence_number"]
                return event

            # Helper to generate output IDs
            def generate_output_id(prefix: str = "item") -> str:
                return f"{prefix}_{uuid.uuid4().hex[:8]}"

            sequence = 0
            current_output_index = 0

            # Stream response.created event
            yield create_event("response.created",
                               sequence_number=sequence,
                               response={
                                   "id": response_id,
                                   "object": "response",
                                   "created_at": int(time.time()),
                                   "status": "in_progress",
                                   "model": request.get("model", "gpt-4.1-nano"),
                                   "output": []
                               })
            sequence += 1

            # Stream response.in_progress
            yield create_event("response.in_progress",
                               sequence_number=sequence,
                               response={
                                   "id": response_id,
                                   "status": "in_progress"
                               })
            sequence += 1

            # Initialize context
            context = {"start_time": time.time()}

            # Phase 1: Router Agent (with reasoning)
            router_id = generate_output_id("router")
            yield create_event("response.output_item.added",
                               sequence_number=sequence,
                               output_index=current_output_index,
                               item={
                                   "id": router_id,
                                   "type": "reasoning",
                                   "content": []
                               })
            sequence += 1
            current_output_index += 1

            # Stream router reasoning with user-friendly text
            reasoning_text = "Processing your request..."
            async for event in self._stream_reasoning_step(router_id, current_output_index - 1,
                                                           reasoning_text,
                                                           create_event):
                event["sequence_number"] = sequence
                yield event
                sequence += 1

            # Run router
            router_result = await self.agents["router"].run(request, context)
            context["router_agent"] = router_result
            enabled_agents = router_result.get("enabled_agents", ["response"])

            # Stream a simple progress update without exposing internal details
            decision_text = "\n\nGathering relevant information..."

            async for event in self._stream_reasoning_step(router_id, current_output_index - 1,
                                                           decision_text,
                                                           create_event):
                event["sequence_number"] = sequence
                yield event
                sequence += 1

            # Complete router reasoning
            yield create_event("response.output_item.done",
                               sequence_number=sequence,
                               output_index=current_output_index - 1,
                               item={
                                   "id": router_id,
                                   "type": "reasoning",
                                   "content": [{
                                       "type": "reasoning_text",
                                       "text": reasoning_text + decision_text
                                   }]
                               })
            sequence += 1

            # Start title generation early (in parallel with other agents)
            title_task = None
            if request.get("enable_title_generation", True):
                logger.info(f"🏷️ Starting early title generation at {time.time() - context.get('start_time', time.time()):.2f}s")
                title_task = asyncio.create_task(self._generate_title(request["messages"], None))
                context["title_task"] = title_task
                context["title_start_time"] = time.time()

            # Phase 2: Context Collection Agents
            # Stream each enabled agent's work
            for agent_name in ["context_search", "web_search", "attachment", "code_interpreter"]:
                if agent_name in enabled_agents:
                    # Delegate to agent-specific streaming methods
                    if agent_name == "web_search":
                        async for event in self._stream_web_search_agent(request, context, create_event,
                                                                         generate_output_id, current_output_index):
                            event["sequence_number"] = sequence
                            yield event
                            sequence += 1
                        current_output_index += 1  # Web search adds 1 item
                    elif agent_name == "code_interpreter":
                        async for event in self._stream_code_interpreter_agent(request, context, create_event,
                                                                               generate_output_id, current_output_index):
                            event["sequence_number"] = sequence
                            yield event
                            sequence += 1
                        current_output_index += 1  # Code interpreter adds 1 item
                    else:
                        # Context search uses context_search_call, attachment uses file_search_call
                        if agent_name == "context_search":
                            # First add the context_search_call tool call
                            agent_id = generate_output_id("cs")
                            yield create_event("response.output_item.added",
                                               sequence_number=sequence,
                                               output_index=current_output_index,
                                               item={
                                                   "id": agent_id,
                                                   "type": "context_search_call",
                                                   "status": "in_progress"
                                               })
                            sequence += 1
                            current_output_index += 1

                            # Add a small delay to ensure the tool call event is processed
                            await asyncio.sleep(0.1)

                            # Run context search agent
                            result = await self.agents["context_search"].run(request, context)
                            context["context_search_agent"] = result

                            # Complete context search call
                            item_data = {
                                "id": agent_id,
                                "type": "context_search_call",
                                "status": "completed"
                            }

                            # Include search results if available
                            if result and isinstance(result, dict):
                                # Add both sources and a summary of what was found
                                if "sources" in result:
                                    # Limit sources to prevent overly large payloads
                                    sources = result["sources"]
                                    logger.info(
                                        f"📊 Context search found {len(sources)} sources")

                                    # Log source structure for debugging
                                    if sources:
                                        logger.info(
                                            f"🔍 First source structure: type={sources[0].get('type')}, has_chunks={bool(sources[0].get('chunks'))}, chunk_count={len(sources[0].get('chunks', []))}")
                                        # Calculate total size of sources
                                        import sys
                                        total_size = sys.getsizeof(json.dumps(
                                            sources[:10], cls=DecimalEncoder))
                                        logger.info(
                                            f"📏 Total size of sources (first 10): {total_size} bytes")

                                    # If too many sources, include a subset and indicate more are available
                                    # if len(sources) > 10:
                                    #     item_data["sources"] = sources[:10]
                                    #     item_data["total_sources"] = len(sources)
                                    #     item_data["sources_truncated"] = True
                                    #     item_data["results_summary"] = f"Found {len(sources)} relevant sources (showing first 10)"
                                    #     logger.info(f"📄 Truncated sources from {len(sources)} to 10 for streaming")
                                    # else:
                                        item_data["sources"] = sources
                                        item_data["results_summary"] = f"Found {len(sources)} relevant sources from your notes"
                                        logger.info(
                                            f"📄 Including all {len(sources)} sources in streaming")
                                elif "results" in result:
                                    item_data["results"] = result["results"]

                                # Include metadata if available
                                if "metadata" in result:
                                    item_data["metadata"] = result["metadata"]

                            try:
                                logger.info(
                                    f"📤 Yielding response.output_item.done with sources: {bool(item_data.get('sources'))}, source count: {len(item_data.get('sources', []))}")
                                yield create_event("response.output_item.done",
                                                   sequence_number=sequence,
                                                   output_index=current_output_index - 1,
                                                   item=item_data)
                                sequence += 1
                                logger.info(
                                    f"✅ Successfully yielded response.output_item.done")
                            except Exception as e:
                                logger.error(
                                    f"❌ Failed to serialize context search result: {e}")
                                logger.error(
                                    f"Item data keys: {list(item_data.keys())}")
                                # Yield a simplified version without sources
                                simplified_item = {
                                    "id": agent_id,
                                    "type": "context_search_call",
                                    "status": "completed",
                                    "error": "Failed to serialize sources"
                                }
                                yield create_event("response.output_item.done",
                                                   sequence_number=sequence,
                                                   output_index=current_output_index - 1,
                                                   item=simplified_item)
                                sequence += 1

                            # Also stream the sources as a separate event for client compatibility
                            if result and isinstance(result, dict) and "sources" in result and result["sources"]:
                                # Use the same truncated sources if applicable
                                sources_to_stream = item_data.get(
                                    "sources", result["sources"])
                                logger.info(
                                    f"📤 Streaming sources event with {len(sources_to_stream)} sources")
                                try:
                                    yield create_event("response.context_search.sources",
                                                       sequence_number=sequence,
                                                       sources=sources_to_stream,
                                                       metadata=result.get(
                                                           "metadata", {}),
                                                       total_sources=item_data.get(
                                                           "total_sources"),
                                                       sources_truncated=item_data.get("sources_truncated", False))
                                    sequence += 1
                                    logger.info(
                                        f"✅ Successfully streamed sources event")
                                except Exception as e:
                                    logger.error(
                                        f"❌ Failed to stream sources event: {e}")
                            else:
                                logger.warning(
                                    f"⚠️ Not streaming sources - result type: {type(result)}, has sources: {'sources' in result if isinstance(result, dict) else False}, sources count: {len(result.get('sources', [])) if isinstance(result, dict) else 0}")
                            # Note: We only incremented current_output_index once above (tool call only)
                        elif agent_name == "attachment":
                            # Use file_search_call for attachments
                            agent_id = generate_output_id("fs")
                            yield create_event("response.output_item.added",
                                               sequence_number=sequence,
                                               output_index=current_output_index,
                                               item={
                                                   "id": agent_id,
                                                   "type": "file_search_call",
                                                   "status": "in_progress"
                                               })
                            sequence += 1
                            current_output_index += 1

                            # Add a small delay to ensure the tool call event is processed
                            await asyncio.sleep(0.1)

                            # Run attachment agent
                            result = await self.agents["attachment"].run(request, context)
                            context["attachment_agent"] = result

                            # Complete file search call
                            item_data = {
                                "id": agent_id,
                                "type": "file_search_call",
                                "status": "completed"
                            }

                            # Include search results if available
                            if result and isinstance(result, dict):
                                if "results" in result:
                                    item_data["results"] = result["results"]
                                elif "sources" in result:
                                    item_data["sources"] = result["sources"]
                                    # Add a results summary for the client
                                    item_data["results_summary"] = f"Processed {len(result['sources'])} attachments"

                            yield create_event("response.output_item.done",
                                               sequence_number=sequence,
                                               output_index=current_output_index - 1,
                                               item=item_data)
                            sequence += 1
                        else:
                            # This should not happen with current agent types
                            logger.warning(
                                f"Unknown agent type for streaming: {agent_name}")

                            # Generate agent ID for unknown agent
                            unknown_agent_id = generate_output_id(
                                agent_name[:2])

                            async for event in self._stream_reasoning_step(unknown_agent_id, current_output_index - 1,
                                                                           f"Running {agent_name}...",
                                                                           create_event):
                                event["sequence_number"] = sequence
                                yield event
                                sequence += 1

                            # Run agent
                            result = await self.agents[agent_name].run(request, context)
                            context[f"{agent_name}_agent"] = result

                            # Complete agent reasoning
                            yield create_event("response.output_item.done",
                                               sequence_number=sequence,
                                               output_index=current_output_index - 1,
                                               item={
                                                   "id": unknown_agent_id,
                                                   "type": "reasoning",
                                                   "content": [{
                                                       "type": "reasoning_text",
                                                       "text": f"{agent_name.replace('_', ' ').title()} completed"
                                                   }]
                                               })
                            sequence += 1

            # Phase 3: Response Generation (streaming)
            async for event in self._stream_response_agent(request, context, create_event,
                                                           generate_output_id, current_output_index):
                event["sequence_number"] = sequence
                yield event
                sequence += 1
            current_output_index += 2  # Response adds 1 reasoning + 1 message item

            # Phase 4: Citations are now handled within response agent streaming

            # Phase 5: Iterative Refinement (if enabled)
            # TEMPORARILY DISABLED - causing pauses with reasoning models
            if request.get("enable_iterations", False) and "response" in enabled_agents:
                orchestrator = IterativeOrchestrator(
                    self.agents, self.llm_provider_manager)
                needs_iteration, suggested_agents = await orchestrator.should_iterate(context, request)

                if needs_iteration:
                    # Add iteration reasoning
                    iteration_id = generate_output_id("iter")
                    yield create_event("response.output_item.added",
                                       sequence_number=sequence,
                                       output_index=current_output_index,
                                       item={
                                           "id": iteration_id,
                                           "type": "reasoning",
                                           "content": []
                                       })
                    sequence += 1
                    current_output_index += 1

                    async for event in self._stream_reasoning_step(iteration_id, current_output_index - 1,
                                                                   f"Running iteration with: {', '.join(suggested_agents)}",
                                                                   create_event):
                        event["sequence_number"] = sequence
                        yield event
                        sequence += 1

                    # Run iteration (simplified for now)
                    context = await orchestrator.run_iteration(request, context, suggested_agents)

                    yield create_event("response.output_item.done",
                                       sequence_number=sequence,
                                       output_index=current_output_index - 1,
                                       item={
                                           "id": iteration_id,
                                           "type": "reasoning",
                                           "content": [{
                                               "type": "reasoning_text",
                                               "text": "Iteration completed"
                                           }]
                                       })
                    sequence += 1

            # Check if title is ready (non-blocking)
            title_ready = False
            title = None
            if "title_task" in context:
                elapsed = time.time() - context.get("title_start_time", time.time())
                logger.info(f"🏷️ Checking title task after {elapsed:.2f}s...")
                title_ready = context["title_task"].done()
                logger.info(f"🏷️ Title task done: {title_ready}")
                
                if title_ready:
                    try:
                        title = await context["title_task"]
                        title_duration = time.time() - context.get("title_start_time", time.time())
                        logger.info(f"🏷️ Title ready in {title_duration:.2f}s: '{title}'")
                    except Exception as e:
                        logger.error(f"Title generation failed: {e}")
                        title = None
                else:
                    logger.info(f"🏷️ Title still generating after {elapsed:.2f}s, skipping for now...")
            
            # Send title event if we have it
            if title:
                yield create_event("response.title_generated",
                                   sequence_number=sequence,
                                   title=title)
                sequence += 1
            
            # Stream usage stats
            yield create_event("response.usage",
                               sequence_number=sequence,
                               usage={
                                   "prompt_tokens": 0,  # Would need actual counting
                                   "completion_tokens": 0,
                                   "total_tokens": 0
                               })
            sequence += 1

            # Stream final response events with citations
            response_completed_data = {
                "id": response_id,
                "status": "completed",
                "done": True
            }
            
            # Include citations/annotations if available from response agent
            response_agent_result = context.get("response_agent", {})
            # Check for annotations in the context (set during streaming)
            citations = context.get("annotations", [])
            if not citations:
                # Fallback to response agent result
                citations = response_agent_result.get("annotations", [])
            
            if citations:
                response_completed_data["citations"] = citations
                logger.info(f"📚 Including {len(citations)} citations in response.completed event")
                
            # Debug log the complete event
            logger.info(f"🎯 Sending response.completed with data: {json.dumps(response_completed_data, cls=DecimalEncoder)[:500]}")
            
            # Log timing
            elapsed_time = time.time() - context.get("start_time", time.time())
            logger.info(f"⏱️ Sending response.completed at {elapsed_time:.2f}s from start")
            
            yield create_event("response.completed",
                               sequence_number=sequence,
                               response=response_completed_data)
            sequence += 1

            logger.info(f"⏱️ Sending response.done at {time.time() - context.get('start_time', time.time()):.2f}s from start")
            yield create_event("response.done",
                               sequence_number=sequence,
                               response={
                                   "id": response_id,
                                   "done": True
                               })

        except Exception as e:
            logger.error(f"Error in streaming request: {e}", exc_info=True)
            # Provide more detailed error information
            error_message = str(e) if str(e) else "An unknown error occurred during streaming"
            yield {
                "type": "error",
                "error": {
                    "message": error_message,
                    "type": type(e).__name__,
                    "code": "streaming_error",
                    "details": {
                        "error_class": type(e).__name__,
                        "error_str": str(e),
                        "traceback": traceback.format_exc() if logger.level <= logging.DEBUG else None
                    }
                }
            }

    async def _stream_reasoning_step(self, item_id: str, output_index: int, text: str,
                                     create_event) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream a reasoning step with proper formatting"""
        # Add reasoning text
        yield create_event("response.reasoning_part.added",
                           item_id=item_id,
                           output_index=output_index,
                           content_index=0,
                           part={
                               "type": "reasoning_text",
                               "text": ""
                           })

        # Stream the text in chunks
        chunk_size = 20
        for i in range(0, len(text), chunk_size):
            chunk = text[i:i+chunk_size]
            yield create_event("response.reasoning_text.delta",
                               item_id=item_id,
                               output_index=output_index,
                               content_index=0,
                               delta=chunk)
            await asyncio.sleep(0.05)  # Small delay for realistic streaming

        # Complete the reasoning text
        yield create_event("response.reasoning_text.done",
                           item_id=item_id,
                           output_index=output_index,
                           content_index=0,
                           text=text)

        # Complete the reasoning part
        yield create_event("response.reasoning_part.done",
                           item_id=item_id,
                           output_index=output_index,
                           content_index=0,
                           part={
                               "type": "reasoning_text",
                               "text": text
                           })

    async def _stream_web_search_agent(self, request: Dict[str, Any], context: Dict[str, Any],
                                       create_event, generate_output_id, current_output_index) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream web search agent work using OpenAI Response API format"""
        # Add web search call output item
        search_id = generate_output_id("ws")
        yield create_event("response.output_item.added",
                           output_index=current_output_index,
                           item={
                               "id": search_id,
                               "type": "web_search_call",
                               "status": "in_progress"
                           })

        # Add a small delay to ensure the tool call event is processed
        await asyncio.sleep(0.1)

        # Execute web search
        search_result = await self.agents["web_search"].run(request, context)
        context["web_search_agent"] = search_result

        # Complete web search call
        item_data = {
            "id": search_id,
            "type": "web_search_call",
            "status": "completed"
        }

        # Include search results if available
        if search_result and isinstance(search_result, dict):
            if "results" in search_result:
                # Convert WebSearchResult objects to dicts
                results = []
                for result in search_result["results"]:
                    if hasattr(result, '__dict__'):
                        # It's a dataclass or object, convert to dict
                        results.append({
                            "title": getattr(result, 'title', ''),
                            "url": getattr(result, 'link', ''),
                            "snippet": getattr(result, 'snippet', ''),
                            "source": getattr(result, 'source', ''),
                            "cached": getattr(result, 'cached', False)
                        })
                    else:
                        # Already a dict
                        results.append(result)
                item_data["results"] = results
            elif "sources" in search_result:
                item_data["sources"] = search_result["sources"]

        yield create_event("response.output_item.done",
                           output_index=current_output_index,
                           item=item_data)

        # Note: The actual search results and citations will be included
        # in the response message by the response agent

    async def _stream_response_agent(self, request: Dict[str, Any], context: Dict[str, Any], create_event, generate_output_id, current_output_index) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream response agent work with integrated citations."""

        # First, add reasoning for response generation
        reasoning_id = generate_output_id("resp_reasoning")
        yield create_event("response.output_item.added",
                           output_index=current_output_index,
                           item={
                               "id": reasoning_id,
                               "type": "reasoning",
                               "content": []
                           })
        current_output_index += 1

        # Stream initial reasoning about generating response
        initial_reasoning = "Generating response based on the collected information..."
        async for event in self._stream_reasoning_step(reasoning_id, current_output_index - 1,
                                                       initial_reasoning,
                                                       create_event):
            yield event

        message_id = generate_output_id("msg")

        # Store message ID in context
        context["last_message_id"] = message_id
        context["last_message_output_index"] = current_output_index

        # Add assistant message output item
        yield create_event("response.output_item.added",
                           output_index=current_output_index,
                           item={
                               "id": message_id,
                               "type": "message",
                               "role": "assistant",
                               "status": "in_progress",
                           })

        # Add content part
        yield create_event("response.content_part.added",
                           item_id=message_id,
                           output_index=current_output_index,
                           content_index=0,
                           part={
                               "type": "output_text",
                               "annotations": [],
                               "logprobs": [],
                               "text": "",
                           })

        # Stream response from agent with real-time reasoning support
        accumulated_response = ""
        annotations = []
        sources = []
        reasoning_parts = []

        # Check if we have streaming support
        if hasattr(self.agents["response"], "stream"):
            # Use actual streaming for real-time reasoning
            logger.info("🌊 Using streaming response agent")
            async for chunk in self.agents["response"].stream(request, context):
                chunk_type = chunk.get("type", "")
                logger.debug(f"📦 Response agent chunk type: {chunk_type}")

                if chunk_type == "response_chunk":
                    # Regular content chunk
                    content = chunk.get("content", "")
                    accumulated_response += content
                    yield create_event("response.output_text.delta",
                                       item_id=message_id,
                                       output_index=current_output_index,
                                       content_index=0,
                                       delta=content)

                elif chunk_type == "reasoning_chunk":
                    # DeepSeek reasoning chunk
                    reasoning_content = chunk.get("content", "")
                    reasoning_parts.append(reasoning_content)

                    # Stream reasoning as separate events
                    yield create_event("response.reasoning_part.added",
                                       reasoning_part_id=generate_output_id(
                                           "reason_part"),
                                       type="reasoning",
                                       output_index=current_output_index - 1)  # Add to reasoning item

                    yield create_event("response.reasoning_text.delta",
                                       delta=reasoning_content,
                                       output_index=current_output_index - 1)

                elif chunk_type == "annotations":
                    # Citation annotations
                    annotations = chunk.get("annotations", [])
                    sources = chunk.get("sources", [])
                    
                    logger.info(f"📚 Received annotations from response agent: {len(annotations)} annotations")
                    
                    # Store annotations in context for later use
                    context["annotations"] = annotations

                    # Stream sources data as a separate event
                    if sources:
                        yield create_event("response.sources",
                                           sources=sources,
                                           output_index=current_output_index)
                    
                    # Stream annotations as a separate event for frontend
                    if annotations:
                        yield create_event("response.annotations",
                                           annotations=annotations,
                                           output_index=current_output_index)

                elif chunk_type == "success" or chunk.get("status") == "success":
                    # Final success chunk with metadata
                    logger.info("✅ Received success chunk from response agent")
                    final_response = chunk.get(
                        "response", accumulated_response)
                    context["response_agent"] = chunk

            # Set final response if not already set
            if 'final_response' not in locals():
                final_response = accumulated_response
        else:
            # Fallback to non-streaming version
            response_result = await self.agents["response"].run(request, context)
            context["response_agent"] = response_result

            final_response = response_result.get("response", "")
            annotations = response_result.get("annotations", [])
            sources = response_result.get("sources", [])
            
            logger.info(f"📚 Non-streaming response - annotations: {len(annotations)}, sources: {len(sources)}")

            # Store annotations in context
            if annotations:
                context["annotations"] = annotations
            
            # Stream sources if available
            if sources:
                yield create_event("response.sources",
                                   sources=sources,
                                   output_index=current_output_index)
            
            # Stream annotations if available
            if annotations:
                # Log annotations to verify type_id is included
                logger.info(f"📚 Streaming {len(annotations)} annotations with type_id check:")
                for i, ann in enumerate(annotations[:3]):  # Log first 3 annotations
                    logger.info(f"  Annotation {i}: type={ann.get('type')}, type_id={ann.get('type_id')}, title={ann.get('title')}")
                
                yield create_event("response.annotations",
                                   annotations=annotations,
                                   output_index=current_output_index)

            # Simulate streaming
            chunk_size = 20
            for i in range(0, len(final_response), chunk_size):
                chunk = final_response[i:i+chunk_size]
                yield create_event("response.output_text.delta",
                                   item_id=message_id,
                                   output_index=current_output_index,
                                   content_index=0,
                                   delta=chunk)
                await asyncio.sleep(0.05)

        # Stream annotation events for each citation position found
        # New structure: annotations contain all sources with citation_positions array
        for annotation in annotations:
            # Skip sources that weren't actually cited
            citation_positions = annotation.get("citation_positions", [])
            if not citation_positions:
                continue
                
            # Stream an event for each citation position of this source
            for position in citation_positions:
                annotation_data = {
                    "type": annotation.get("type", "url_citation"),
                    "start_index": position.get("start_index", 0),
                    "end_index": position.get("end_index", 0),
                    "text": position.get("text", ""),
                    "url": annotation.get("url", ""),
                    "title": annotation.get("title", ""),
                    "source_type": annotation.get("type", "web"),
                    "type_id": annotation.get("type_id"),
                }

                # Include note_id and conversation_id if present
                if annotation.get("note_id"):
                    annotation_data["note_id"] = annotation["note_id"]
                if annotation.get("conversation_id"):
                    annotation_data["conversation_id"] = annotation["conversation_id"]

                # Add metadata for additional information
                annotation_data["metadata"] = {
                    "source_type": annotation.get("type", "web"),
                    "type_id": annotation.get("type_id"),
                }

                yield create_event("response.output_text.annotation.added",
                                   item_id=message_id,
                                   output_index=current_output_index,
                                   content_index=0,
                                   annotation=annotation_data)

        # Complete output text
        yield create_event("response.output_text.done",
                           item_id=message_id,
                           output_index=current_output_index,
                           content_index=0,
                           text=final_response)

        # Complete reasoning with all collected reasoning parts
        if reasoning_parts:
            # Send reasoning completion event if we collected DeepSeek reasoning
            all_reasoning = initial_reasoning + \
                "\n\n" + "".join(reasoning_parts)
            yield create_event("response.reasoning_text.done",
                               output_index=current_output_index - 1,
                               text=all_reasoning)

            yield create_event("response.reasoning_part.done",
                               output_index=current_output_index - 1,
                               part={
                                   "type": "reasoning_text",
                                   "text": all_reasoning
                               })

        # Complete the reasoning output item
        yield create_event("response.output_item.done",
                           output_index=current_output_index - 1,
                           item={
                               "id": reasoning_id,
                               "type": "reasoning",
                               "content": [{
                                   "type": "reasoning_text",
                                   "text": initial_reasoning + ("\n\n" + "".join(reasoning_parts) if reasoning_parts else "")
                               }]
                           })

        # Complete content part with annotations
        yield create_event("response.content_part.done",
                           item_id=message_id,
                           output_index=current_output_index,
                           content_index=0,
                           part={
                               "type": "output_text",
                               "annotations": annotations,
                               "logprobs": [],
                               "text": final_response,
                           })

        # Complete assistant message with annotations
        yield create_event("response.output_item.done",
                           output_index=current_output_index,
                           item={
                               "id": message_id,
                               "type": "message",
                               "role": "assistant",
                               "status": "completed",
                               "content": [
                                   {
                                       "type": "output_text",
                                       "text": final_response,
                                       "annotations": annotations,
                                   }
                               ],
                           })

    # Citation agent method removed - citations are now handled within response agent
    # async def _stream_citation_agent(...) - DEPRECATED

    async def _stream_code_interpreter_agent(self, request: Dict[str, Any], context: Dict[str, Any], create_event, generate_output_id, current_output_index) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream code interpreter agent work using OpenAI Response API format"""
        code_id = generate_output_id("ci")

        # Add code interpreter call output item
        yield create_event("response.output_item.added",
                           output_index=current_output_index,
                           item={
                               "id": code_id,
                               "type": "code_interpreter_call",
                               "status": "in_progress"
                           })

        # Add a small delay to ensure the tool call event is processed
        await asyncio.sleep(0.1)

        # Execute code interpreter
        if "code_interpreter" in self.agents:
            code_result = await self.agents["code_interpreter"].run(request, context)
            context["code_interpreter_agent"] = code_result

        # Complete code interpreter call
        yield create_event("response.output_item.done",
                           output_index=current_output_index,
                           item={
                               "id": code_id,
                               "type": "code_interpreter_call",
                               "status": "completed"
                           })

        # Note: The actual code output will be included in the response message

    async def _generate_title(self, messages: List[Dict[str, Any]], response: str = None) -> str:
        """Generate a title for the conversation using the title generator service
        
        Note: The response parameter is ignored as title generator only uses user messages
        """
        start_time = time.time()
        logger.info(f"🏷️ _generate_title started")
        
        # Remove artificial delay - was just for testing
        # await asyncio.sleep(15.0)
        
        try:
            # Import the title generator
            from ..title.title_generator import title_generator
            
            # Get an LLM instance for title generation
            logger.info(f"🏷️ Getting LLM provider for title generation...")
            provider_info = self.llm_provider_manager.get_provider(None, "gpt-4.1-nano")
            llm = provider_info["llm"]
            logger.info(f"🏷️ LLM provider obtained in {time.time() - start_time:.2f}s")
            
            # Generate the title using the proper service
            # Note: title_generator only uses user messages, so we don't need to add response
            logger.info(f"🏷️ Calling title generator...")
            generated_title = await title_generator.generate_conversation_title(
                messages, 
                llm
            )
            logger.info(f"🏷️ Title generated in total {time.time() - start_time:.2f}s")
            
            if generated_title:
                logger.info(f"🏷️ Generated unique title: '{generated_title}'")
                return generated_title
            else:
                # Fallback to user message if generation fails
                user_message = ""
                for msg in messages:
                    if msg["role"] == "user":
                        user_message = msg["content"]
                        break
                
                if user_message and len(user_message) > 100:
                    return user_message[:97] + "..."
                elif user_message:
                    return user_message
                else:
                    return "New Conversation"

        except Exception as e:
            logger.error(f"Error generating title: {e}")
            return "New Conversation"


# Create singleton instance for import
multi_agent_endpoint_v2 = MultiAgentChatEndpointV2()
