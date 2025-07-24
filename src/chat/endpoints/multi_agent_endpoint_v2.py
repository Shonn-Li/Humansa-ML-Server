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
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union, AsyncGenerator
from dataclasses import dataclass, asdict
from enum import Enum

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
            
            # Remove any markdown code blocks if present
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
            
            # Log raw response for debugging
            logger.info(f"Iteration evaluation raw response: {response_text[:200]}...")
            
            eval_result = json.loads(response_text.strip())
            
            if eval_result.get("needs_iteration", False):
                self.iteration_count += 1
                suggested_agents = eval_result.get("suggested_agents", [])
                reason = eval_result.get("reason", "Quality improvement needed")
                logger.info(f"Iteration {self.iteration_count} triggered: {reason}")
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
                logger.info(f"Running {agent_name} agent in iteration {self.iteration_count}")
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
            agent_results["router"] = {"status": "success", "data": router_result}
            
            enabled_agents = router_result.get("enabled_agents", ["response"])
            
            # Phase 2: Context Collection (parallel where possible)
            tasks = []
            
            if "context_search" in enabled_agents:
                tasks.append(("context_search", self.agents["context_search"].run(request, context)))
            
            if "web_search" in enabled_agents:
                tasks.append(("web_search", self.agents["web_search"].run(request, context)))
            
            if "attachment" in enabled_agents:
                tasks.append(("attachment", self.agents["attachment"].run(request, context)))
            
            if "code_interpreter" in enabled_agents:
                tasks.append(("code_interpreter", self.agents["code_interpreter"].run(request, context)))
            
            # Run context collection tasks in parallel
            if tasks:
                results = await asyncio.gather(*[task[1] for task in tasks], return_exceptions=True)
                for i, (agent_name, _) in enumerate(tasks):
                    if isinstance(results[i], Exception):
                        logger.error(f"{agent_name} agent failed: {results[i]}")
                        context[f"{agent_name}_agent"] = {"status": "error", "error": str(results[i])}
                        agent_results[agent_name] = {"status": "error", "error": str(results[i])}
                    else:
                        context[f"{agent_name}_agent"] = results[i]
                        agent_results[agent_name] = {"status": "success", "data": results[i]}
            
            # Phase 3: Response Generation
            response_start = time.time()
            response_result = await self.agents["response"].run(request, context)
            context["response_agent"] = response_result
            agent_times["response"] = time.time() - response_start
            agent_results["response"] = {"status": "success", "data": response_result}
            
            # Phase 4: Citation (if enabled)
            if "citation" in enabled_agents:
                citation_start = time.time()
                citation_result = await self.agents["citation"].run(request, context)
                context["citation_agent"] = citation_result
                agent_times["citation"] = time.time() - citation_start
                agent_results["citation"] = {"status": "success", "data": citation_result}
            
            # Phase 5: Iterative Refinement (if enabled)
            total_iterations = 1  # At least one iteration (initial run)
            if request.get("enable_iterations", True) and "response" in enabled_agents:
                # Create new orchestrator instance per request to avoid state pollution
                orchestrator = IterativeOrchestrator(self.agents, self.llm_provider_manager)
                
                # Check if we need iterations
                needs_iteration, suggested_agents = await orchestrator.should_iterate(context, request)
                
                while needs_iteration:
                    logger.info(f"Running iteration {orchestrator.iteration_count} with agents: {suggested_agents}")
                    
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
            final_response = context.get("response_agent", {}).get("response", "")
            if "citation" in enabled_agents and context.get("citation_agent", {}).get("status") == "success":
                cited_response = context["citation_agent"].get("citations", {}).get("response")
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
            context = {}
            
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
            
            # Stream router reasoning with more detailed text
            reasoning_text = "Analyzing the user's query to determine which tools and agents to use..."
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
            
            # Stream additional reasoning about the decision
            decision_text = f"\n\nBased on the query, I'll use: {', '.join(enabled_agents)}"
            if "context_search" in enabled_agents:
                decision_text += "\n- Context search: To find relevant information from your notes"
            if "web_search" in enabled_agents:
                decision_text += "\n- Web search: To get current information from the internet"
            if "attachment" in enabled_agents:
                decision_text += "\n- File search: To analyze attached files"
            
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
                            yield create_event("response.output_item.done",
                                             sequence_number=sequence,
                                             output_index=current_output_index - 1,
                                             item={
                                                 "id": agent_id,
                                                 "type": "context_search_call",
                                                 "status": "completed"
                                             })
                            sequence += 1
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
                            yield create_event("response.output_item.done",
                                             sequence_number=sequence,
                                             output_index=current_output_index - 1,
                                             item={
                                                 "id": agent_id,
                                                 "type": "file_search_call",
                                                 "status": "completed"
                                             })
                            sequence += 1
                        else:
                            # This should not happen with current agent types
                            logger.warning(f"Unknown agent type for streaming: {agent_name}")
                            
                            # Generate agent ID for unknown agent
                            unknown_agent_id = generate_output_id(agent_name[:2])
                            
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
            if request.get("enable_iterations", True) and "response" in enabled_agents:
                orchestrator = IterativeOrchestrator(self.agents, self.llm_provider_manager)
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
            
            # Generate title from the response
            response_text = context.get("response_agent", {}).get("response", "")
            title = await self._generate_title(request["messages"], response_text)
            
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
            
            # Stream final response events
            yield create_event("response.completed",
                             sequence_number=sequence,
                             response={
                                 "id": response_id,
                                 "status": "completed",
                                 "done": True
                             })
            sequence += 1
            
            yield create_event("response.done",
                             sequence_number=sequence,
                             response={
                                 "id": response_id,
                                 "done": True
                             })
            
        except Exception as e:
            logger.error(f"Error in streaming request: {e}", exc_info=True)
            yield {
                "type": "error",
                "error": {
                    "message": str(e),
                    "type": "internal_error",
                    "code": "streaming_error"
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
        yield create_event("response.output_item.done",
                         output_index=current_output_index,
                         item={
                             "id": search_id,
                             "type": "web_search_call",
                             "status": "completed"
                         })
        
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
            async for chunk in self.agents["response"].stream(request, context):
                chunk_type = chunk.get("type", "")
                
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
                                     reasoning_part_id=generate_output_id("reason_part"),
                                     type="reasoning",
                                     output_index=current_output_index - 1)  # Add to reasoning item
                    
                    yield create_event("response.reasoning_text.delta",
                                     delta=reasoning_content,
                                     output_index=current_output_index - 1)
                
                elif chunk_type == "annotations":
                    # Citation annotations
                    annotations = chunk.get("annotations", [])
                    sources = chunk.get("sources", [])
                
                elif chunk_type == "success":
                    # Final success chunk with metadata
                    final_response = chunk.get("response", accumulated_response)
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

        # Stream annotation events for each citation found
        for annotation in annotations:
            yield create_event("response.output_text.annotation.added",
                             item_id=message_id,
                             output_index=current_output_index,
                             content_index=0,
                             annotation={
                                 "type": annotation["type"],
                                 "start_index": annotation["start_index"],
                                 "end_index": annotation["end_index"],
                                 "text": annotation["text"],
                                 "url": annotation.get("url", ""),
                                 "title": annotation.get("title", ""),
                                 # Custom fields for our RAG nodes
                                 "metadata": {
                                     "source_id": next((s["source_id"] for s in sources if s.get("url") == annotation.get("url")), None),
                                     "source_type": next((s["type"] for s in sources if s.get("url") == annotation.get("url")), "unknown"),
                                     "note_id": next((s["metadata"].get("note_id") for s in sources if s.get("url") == annotation.get("url")), None),
                                     "node_id": next((s["metadata"].get("node_id") for s in sources if s.get("url") == annotation.get("url")), None),
                                 }
                             })

        # Complete output text
        yield create_event("response.output_text.done",
                         item_id=message_id,
                         output_index=current_output_index,
                         content_index=0,
                         text=final_response)
        
        # Complete reasoning with all collected reasoning parts
        if reasoning_parts:
            # Send reasoning completion event if we collected DeepSeek reasoning
            all_reasoning = initial_reasoning + "\n\n" + "".join(reasoning_parts)
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
    
    async def _generate_title(self, messages: List[Dict[str, Any]], response: str) -> str:
        """Generate a title for the conversation"""
        try:
            # Get the first user message
            user_message = ""
            for msg in messages:
                if msg["role"] == "user":
                    user_message = msg["content"]
                    break
            
            if not user_message:
                return "New Conversation"
            
            # Truncate if too long
            if len(user_message) > 100:
                return user_message[:97] + "..."
            
            return user_message
            
        except Exception as e:
            logger.error(f"Error generating title: {e}")
            return "New Conversation"


# Create singleton instance for import
multi_agent_endpoint_v2 = MultiAgentChatEndpointV2()