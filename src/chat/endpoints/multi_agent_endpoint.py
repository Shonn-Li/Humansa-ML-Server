"""
Multi-Agent Response Endpoint v1

This endpoint implements a multi-agent workflow where different specialized agents
handle different aspects of the response generation process:

1. RouterAgent - Routes queries to appropriate agents based on intent
2. RAGAgent - Retrieves relevant context from notes and conversations
3. WebSearchAgent - Performs web searches when needed
4. AttachmentAgent - Processes file attachments (images, PDFs, etc.)
5. ResponseAgent - Generates the final response using gathered context
6. CitationAgent - Adds citations and references to responses

Each agent is autonomous and can be invoked independently or as part of a workflow.
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
from ..rag.rag_processor import RAGProcessor
from ..websearch.web_search_processor import WebSearchProcessor
from ..attachment.file_attachment_manager import FileAttachmentManager
from ..provider.llm_provider import LLMProvider, LLMProviderSelector
from llama_index.core.llms import ChatMessage
from ..citation.citation_engine import CitationEngine, CitationResult
from ..query.query_transformer import QueryTransformer
from ..config.system_prompts import SystemPromptManager


logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Base class for all agents"""

    def __init__(self):
        super().__init__()

    @abstractmethod
    async def run(self, request: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the agent's main logic."""
        pass


class RouterAgent(BaseAgent):
    """Agent responsible for routing queries to appropriate tools"""

    def __init__(self, llm_provider_manager: LLMProviderSelector):
        super().__init__()
        self.router = IntelligentRouter()
        self.query_transformer = QueryTransformer(llm_provider_manager)

    async def run(self, request: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Route the query and determine which agents should be activated"""

        # Get the latest user message
        user_messages = [
            msg for msg in request["messages"] if msg["role"] == "user"]
        if not user_messages:
            raise ValueError("No user messages found in request")

        query = user_messages[-1]["content"]

        # Route the query using the original query only
        router_decision = await self.router.route_query(
            query, str(request["user_id"]), request["messages"][-3:]
        )

        # Determine which agents should be enabled based on router decision
        enabled_agents = ["response"]  # Always include response agent

        # Enable agents based on router decision
        if router_decision.selected_tool in ["knowledge_base_notes", "knowledge_base_conversations", "knowledge_base_full"]:
            enabled_agents.append("rag")

        if router_decision.selected_tool == "web_search":
            enabled_agents.append("web_search")

        if router_decision.selected_tool == "attachments" or request.get("attachments"):
            enabled_agents.append("attachment")

        if request.get("enable_citations", True):
            enabled_agents.append("citation")

        return {
            "router_decision": asdict(router_decision),
            "original_query": query,
            "enabled_agents": enabled_agents,
            "model": request.get("model", "gpt-4.1-nano"),
            "search_type": router_decision.search_type if hasattr(router_decision, 'search_type') else "knowledge_base"
        }


class RAGAgent(BaseAgent):
    """Agent responsible for retrieving context from notes and conversations"""

    def __init__(self, rag_processor: RAGProcessor):
        super().__init__()
        self.rag_processor = rag_processor

    async def run(self, request: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve relevant context from user's knowledge base"""

        # Get search parameters from router context
        router_data = context.get("router_agent", {})
        search_type = router_data.get("search_type", "knowledge_base")
        query = router_data.get("original_query", "")
        if not query:
            user_messages = [
                msg for msg in request["messages"] if msg["role"] == "user"]
            query = user_messages[-1]["content"] if user_messages else ""

        # Process RAG request
        rag_context = await self.rag_processor.process_rag_request(
            messages=request["messages"],
            user_id=request["user_id"],
            note_ids=request.get("note_ids"),
            folder_ids=request.get("folder_ids"),
            conversation_ids=request.get("conversation_ids"),
            custom_query=query,
            search_type=search_type
        )

        return {
            "rag_context": asdict(rag_context),
        }


class WebSearchAgent(BaseAgent):
    """Agent responsible for performing web searches"""

    def __init__(self, web_search_processor: WebSearchProcessor):
        super().__init__()
        self.web_search_processor = web_search_processor

    async def run(self, request: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Perform web search for current information"""

        # Get search query from router context
        router_data = context.get("router_agent", {})
        search_query = router_data.get("original_query", "")
        if not search_query:
            user_messages = [
                msg for msg in request["messages"] if msg["role"] == "user"]
            search_query = user_messages[-1]["content"] if user_messages else ""

        # Perform web search
        web_context = await self.web_search_processor.search_web_content(
            query=search_query,
            num_results=5
        )

        return {
            "web_context": asdict(web_context) if web_context else None,
        }


class AttachmentAgent(BaseAgent):
    """Agent responsible for processing file attachments"""

    def __init__(self, file_attachment_manager: FileAttachmentManager):
        super().__init__()
        self.file_attachment_manager = file_attachment_manager

    async def run(self, request: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Process file attachments and extract content"""

        if not request.get("attachments"):
            return {"attachment_context": None}

        # Get search query from router context
        router_data = context.get("router_agent", {})
        search_query = router_data.get("original_query", "")

        if not search_query:
            # Fallback to original query
            user_messages = [
                msg for msg in request["messages"] if msg["role"] == "user"]
            search_query = user_messages[-1]["content"] if user_messages else ""

        # Process attachments
        attachment_context = await self.file_attachment_manager.process_attachments(
            attachments=request["attachments"],
            user_id=request["user_id"],
            query=search_query
        )

        return {
            "attachment_context": asdict(attachment_context) if attachment_context else None,
        }


class ResponseAgent(BaseAgent):
    """Agent responsible for generating the final response"""

    def __init__(self, llm_provider_manager: LLMProviderSelector):
        super().__init__()
        self.llm_manager = llm_provider_manager
        self.system_prompt_manager = SystemPromptManager()

    async def run(self, request: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate the final response using gathered context"""

        # Get query and model from context
        router_data = context.get("router_agent", {})
        query = router_data.get("original_query", "")
        model = router_data.get("model", "gpt-4.1-nano")

        # Get an LLM instance
        provider_info = self.llm_manager.get_provider(model=model)
        llm = provider_info["llm"]

        if not llm:
            error_message = f"Could not get LLM provider for model {model}"
            logger.error(error_message)
            return {"status": "error", "error": error_message}

        # Build context string
        context_str = self._build_context_string(context)

        # Prepare the prompt for the LLM
        messages = self._prepare_prompt(request, query, context_str)

        # Convert messages to ChatMessage objects for LlamaIndex
        chat_messages = []
        for msg in messages:
            role = msg["role"]
            chat_messages.append(ChatMessage(role=role, content=msg["content"]))

        # Generate response using the LLM
        response = await llm.achat(chat_messages)

        return {
            "status": "success",
            "response": response.message.content,
            "model_used": model,
        }

    def _build_context_string(self, context: Dict[str, Any]) -> str:
        """Build a single context string from all available context."""
        context_parts = []
        rag_context = context.get("rag_agent", {}).get("rag_context")
        if rag_context and rag_context.get("chunks"):
            context_parts.append("## Knowledge Base Context:")
            for chunk in rag_context["chunks"]:
                context_parts.append(f"- {chunk.get('chunk_text', '')}")

        web_context = context.get("web_search_agent", {}).get("web_context")
        if web_context and web_context.get("results"):
            context_parts.append("## Web Search Results:")
            for result in web_context["results"]:
                context_parts.append(
                    f"- {result.get('title', '')}: {result.get('snippet', '')}")

        attachment_context = context.get(
            "attachment_agent", {}).get("attachment_context")
        if attachment_context and attachment_context.get("chunks"):
            context_parts.append("## File Attachments:")
            for chunk in attachment_context["chunks"]:
                context_parts.append(f"- {chunk.get('content', '')}")

        return "\n".join(context_parts)

    def _prepare_prompt(self, request: Dict[str, Any], query: str, context_str: str) -> List[Dict[str, str]]:
        """Prepare the prompt for the LLM."""
        messages = request["messages"].copy()
        if not any(msg["role"] == "system" for msg in messages):
            system_prompt = self.system_prompt_manager.get_system_prompt(
                completion_type=request.get("completion_type", "system"),
                custom_prompt=request.get("system_prompt")
            )
            messages.insert(0, {"role": "system", "content": system_prompt})

        if context_str:
            context_message = {
                "role": "system",
                "content": f"Here is some context for the user's query:\n{context_str}"
            }
            # Insert context before the last user message
            last_user_idx = -1
            for i in range(len(messages) - 1, -1, -1):
                if messages[i]["role"] == "user":
                    last_user_idx = i
                    break
            if last_user_idx != -1:
                messages.insert(last_user_idx, context_message)
            else:
                messages.append(context_message)

        return messages


class CitationAgent(BaseAgent):
    """Agent for generating citations based on context"""

    def __init__(self, citation_engine: CitationEngine, llm_provider_manager: LLMProviderSelector):
        super().__init__()
        self.citation_engine = citation_engine
        self.llm_manager = llm_provider_manager

    async def run(self, request: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run the citation agent to generate a response with citations.
        """
        try:
            # Get the original query and model from context
            router_data = context.get("router_agent", {})
            query = router_data.get("original_query", "")
            model = router_data.get("model", "gpt-4.1-nano")

            # Reconstruct proper context objects for citation engine
            rag_context_data = context.get("rag_agent", {}).get("rag_context")
            web_context_data = context.get(
                "web_search_agent", {}).get("web_context")
            attachment_context_data = context.get(
                "attachment_agent", {}).get("attachment_context")

            # Convert RAG context back to proper objects
            rag_context = None
            if rag_context_data and rag_context_data.get("chunks"):
                from ..rag.rag_processor import RAGContext
                from ..postgres.db_manager import ChunkResult

                chunks = [ChunkResult(**chunk) if isinstance(chunk, dict)
                          else chunk for chunk in rag_context_data["chunks"]]
                rag_context = RAGContext(
                    chunks=chunks,
                    used_note_ids=rag_context_data.get("used_note_ids", []),
                    used_conversation_ids=rag_context_data.get(
                        "used_conversation_ids", []),
                    total_chunks=rag_context_data.get("total_chunks", 0),
                    query_used=rag_context_data.get("query_used", "")
                )

            # Convert web search context back to proper objects
            web_context = None
            if web_context_data and web_context_data.get("results"):
                from ..websearch.web_search_processor import WebSearchContext, WebSearchResult

                results = [WebSearchResult(**result) if isinstance(
                    result, dict) else result for result in web_context_data["results"]]
                web_context = WebSearchContext(
                    results=results,
                    query_used=web_context_data.get("query_used", ""),
                    total_results=web_context_data.get("total_results", 0),
                    search_performed=True,
                    cache_hit=False
                )

            # Attachment context
            attachment_context = attachment_context_data

            # Get an LLM instance
            provider_info = self.llm_manager.get_provider(model=model)
            llm = provider_info["llm"]

            if not llm:
                error_message = f"Could not get LLM provider for model {model}"
                logger.error(error_message)
                return {"status": "error", "error": error_message}

            # Generate citation response
            citation_result = self.citation_engine.generate_citation_response(
                query=query,
                rag_context=rag_context,
                attachment_context=attachment_context,
                websearch_context=web_context,
                llm=llm
            )

            return {
                "status": "success",
                "citations": citation_result.to_dict(),
            }
        except Exception as e:
            logger.error(f"CitationAgent error: {str(e)}", exc_info=True)
            return {"status": "error", "error": str(e)}


class MultiAgentChatEndpoint:
    """Main endpoint for handling multi-agent chat requests."""

    def __init__(self):
        self.llm_provider_manager = LLMProviderSelector()
        self.rag_processor = RAGProcessor()
        self.web_search_processor = WebSearchProcessor()
        self.file_attachment_manager = FileAttachmentManager()
        self.citation_engine = CitationEngine()

        self.agents = {
            "router": RouterAgent(self.llm_provider_manager),
            "rag": RAGAgent(self.rag_processor),
            "web_search": WebSearchAgent(self.web_search_processor),
            "attachment": AttachmentAgent(self.file_attachment_manager),
            "response": ResponseAgent(self.llm_provider_manager),
            "citation": CitationAgent(self.citation_engine, self.llm_provider_manager),
        }

        # Initialize streaming state
        self.response_id = f"resp_{uuid.uuid4().hex[:8]}"
        self.output_index = -1
        self.sequence_number = 0

    def generate_output_id(self, prefix: str = "item") -> str:
        """Generate unique output item ID."""
        self.output_index += 1
        return f"{prefix}_{uuid.uuid4().hex[:8]}"

    def create_event(self, event_type: str, **kwargs) -> Dict[str, Any]:
        """Create a structured SSE event matching OpenAI format."""
        event_data = {
            "type": event_type,
            "sequence_number": self.sequence_number,
        }
        event_data.update(kwargs)
        self.sequence_number += 1
        return event_data

    async def _handle_request_internal(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Internal handler for the multi-agent workflow (non-streaming)."""
        start_time = time.time()
        context = {}
        agent_results = {}

        # Phase 1: Router Agent
        router_result = await self.agents["router"].run(request, context)
        context["router_agent"] = router_result
        agent_results["router_agent"] = {"status": "success", "data": router_result}

        enabled_agents = router_result.get("enabled_agents", [])

        # Phase 2: Context Agents (parallel)
        context_tasks = []
        for agent_name in enabled_agents:
            if agent_name in ["rag", "web_search", "attachment"]:
                context_tasks.append(
                    (agent_name, self.agents[agent_name].run(request, context)))

        context_results = await asyncio.gather(*[task for _, task in context_tasks])
        for i, (agent_name, _) in enumerate(context_tasks):
            context[f"{agent_name}_agent"] = context_results[i]
            agent_results[f"{agent_name}_agent"] = {"status": "success", "data": context_results[i]}

        # Phase 3: Response Agent
        if "response" in enabled_agents:
            response_result = await self.agents["response"].run(request, context)
            context["response_agent"] = response_result
            agent_results["response_agent"] = {"status": "success", "data": response_result}

        # Phase 4: Citation Agent
        if "citation" in enabled_agents:
            citation_result = await self.agents["citation"].run(request, context)
            context["citation_agent"] = citation_result
            agent_results["citation_agent"] = {"status": "success", "data": citation_result}

        # Final Response Assembly
        final_response = context.get("response_agent", {}).get("response", "")
        if "citation" in enabled_agents and context.get("citation_agent", {}).get("status") == "success":
            cited_response = context["citation_agent"].get("citations", {}).get("response")
            if cited_response:
                final_response = cited_response

        return {
            "status": "success",
            "response": final_response,
            "metadata": {
                "agent_results": agent_results,
                "workflow_time": time.time() - start_time,
            }
        }

    async def _handle_request_streaming(self, request: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """Streaming handler for the multi-agent workflow with OpenAI-compatible format."""
        start_time = time.time()
        context = {}
        
        try:
            # Phase 1: Lifecycle - response.created
            yield self.create_event("response.created",
                                  response={
                                      "id": self.response_id,
                                      "object": "response",
                                      "created_at": int(time.time()),
                                      "status": "in_progress",
                                      "model": request.get("model", "gpt-4.1-nano"),
                                      "output": [],
                                  })

            # Phase 2: response.in_progress
            yield self.create_event("response.in_progress",
                                  response={
                                      "id": self.response_id,
                                      "status": "in_progress",
                                  })

            # Phase 3: Router Agent - Stream thinking process
            router_id = self.generate_output_id("router")
            yield self.create_event("response.output_item.added",
                                  output_index=self.output_index,
                                  item={
                                      "id": router_id,
                                      "type": "reasoning",
                                      "content": [],
                                  })

            # Stream router thinking
            async for event in self._stream_reasoning_step(router_id, "Understanding your request..."):
                yield event

            # Run router agent
            router_result = await self.agents["router"].run(request, context)
            context["router_agent"] = router_result
            enabled_agents = router_result.get("enabled_agents", [])

            # Complete router reasoning
            yield self.create_event("response.output_item.done",
                                  output_index=self.output_index,
                                  item={
                                      "id": router_id,
                                      "type": "reasoning",
                                      "content": [
                                          {
                                              "type": "reasoning_text",
                                              "text": f"Query routed to agents: {', '.join(enabled_agents)}"
                                          }
                                      ]
                                  })

            # Phase 4: Context Agents - Stream their work
            context_tasks = []
            for agent_name in enabled_agents:
                if agent_name in ["rag", "web_search", "attachment"]:
                    # Stream each agent's work
                    if agent_name == "web_search":
                        async for event in self._stream_web_search_agent(request, context):
                            yield event
                    elif agent_name == "rag":
                        async for event in self._stream_rag_agent(request, context):
                            yield event
                    elif agent_name == "attachment":
                        async for event in self._stream_attachment_agent(request, context):
                            yield event
                    
                    # Execute agent
                    context_tasks.append(
                        (agent_name, self.agents[agent_name].run(request, context)))

            # Wait for all context agents to complete
            if context_tasks:
                context_results = await asyncio.gather(*[task for _, task in context_tasks])
                for i, (agent_name, _) in enumerate(context_tasks):
                    context[f"{agent_name}_agent"] = context_results[i]

            # Phase 5: Response Agent - Stream final response
            if "response" in enabled_agents:
                async for event in self._stream_response_agent(request, context):
                    yield event

            # Phase 6: Citation Agent - Add citations
            if "citation" in enabled_agents:
                async for event in self._stream_citation_agent(request, context):
                    yield event

            # Phase 7: Lifecycle - response.completed
            yield self.create_event("response.completed",
                                  response={
                                      "id": self.response_id,
                                      "status": "completed",
                                      "object": "response",
                                      "output": [],
                                  })

            logger.info(f"✅ Multi-agent streaming completed - {self.output_index} output items in {time.time() - start_time:.2f}s")

        except Exception as e:
            logger.error(f"❌ Multi-agent streaming failed: {e}")
            yield self.create_event("response.failed",
                                  response={
                                      "id": self.response_id,
                                      "status": "failed",
                                      "error": str(e)
                                  })

    async def _stream_reasoning_step(self, reasoning_id: str, thought_content: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream a reasoning step with proper lifecycle."""
        # Add reasoning text part
        yield self.create_event("response.reasoning_part.added",
                              item_id=reasoning_id,
                              output_index=self.output_index,
                              content_index=0,
                              part={
                                  "type": "reasoning_text",
                                  "text": "",
                              })

        # Stream reasoning text
        yield self.create_event("response.reasoning_text.delta",
                              item_id=reasoning_id,
                              output_index=self.output_index,
                              content_index=0,
                              delta=thought_content)

        # Complete reasoning text
        yield self.create_event("response.reasoning_text.done",
                              item_id=reasoning_id,
                              output_index=self.output_index,
                              content_index=0,
                              text=thought_content)

        # Complete reasoning part
        yield self.create_event("response.reasoning_part.done",
                              item_id=reasoning_id,
                              output_index=self.output_index,
                              content_index=0,
                              part={
                                  "type": "reasoning_text",
                                  "text": thought_content,
                              })

    async def _stream_web_search_agent(self, request: Dict[str, Any], context: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream web search agent work."""
        search_id = self.generate_output_id("ws")
        
        # Add web search output item
        yield self.create_event("response.output_item.added",
                              output_index=self.output_index,
                              item={
                                  "id": search_id,
                                  "type": "web_search_call",
                                  "status": "in_progress",
                              })

        # Web search in progress
        yield self.create_event("response.web_search_call.in_progress",
                              output_index=self.output_index,
                              item_id=search_id)

        # Web search searching
        yield self.create_event("response.web_search_call.searching",
                              output_index=self.output_index,
                              item_id=search_id)

        # Web search completed
        yield self.create_event("response.web_search_call.completed",
                              output_index=self.output_index,
                              item_id=search_id)

        # Complete web search output item
        yield self.create_event("response.output_item.done",
                              output_index=self.output_index,
                              item={
                                  "id": search_id,
                                  "type": "web_search_call",
                                  "status": "completed",
                                  "action": {
                                      "type": "search",
                                      "query": "web search query",
                                  },
                              })

    async def _stream_rag_agent(self, request: Dict[str, Any], context: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream RAG agent work."""
        rag_id = self.generate_output_id("rag")
        
        # Add reasoning for RAG search
        yield self.create_event("response.output_item.added",
                              output_index=self.output_index,
                              item={
                                  "id": rag_id,
                                  "type": "reasoning",
                                  "content": [],
                              })

        async for event in self._stream_reasoning_step(rag_id, "Searching through knowledge base for relevant information..."):
            yield event

        # Complete RAG reasoning
        yield self.create_event("response.output_item.done",
                              output_index=self.output_index,
                              item={
                                  "id": rag_id,
                                  "type": "reasoning",
                                  "content": [
                                      {
                                          "type": "reasoning_text",
                                          "text": "Found relevant information in knowledge base"
                                      }
                                  ]
                              })

    async def _stream_attachment_agent(self, request: Dict[str, Any], context: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream attachment agent work."""
        attachment_id = self.generate_output_id("att")
        
        # Add reasoning for attachment processing
        yield self.create_event("response.output_item.added",
                              output_index=self.output_index,
                              item={
                                  "id": attachment_id,
                                  "type": "reasoning",
                                  "content": [],
                              })

        async for event in self._stream_reasoning_step(attachment_id, "Processing file attachments..."):
            yield event

        # Complete attachment reasoning
        yield self.create_event("response.output_item.done",
                              output_index=self.output_index,
                              item={
                                  "id": attachment_id,
                                  "type": "reasoning",
                                  "content": [
                                      {
                                          "type": "reasoning_text",
                                          "text": "File attachments processed successfully"
                                      }
                                  ]
                              })

    async def _stream_response_agent(self, request: Dict[str, Any], context: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream response agent work."""
        message_id = self.generate_output_id("msg")
        
        # Add assistant message output item
        yield self.create_event("response.output_item.added",
                              output_index=self.output_index,
                              item={
                                  "id": message_id,
                                  "type": "message",
                                  "role": "assistant",
                                  "status": "in_progress",
                              })

        # Add content part
        yield self.create_event("response.content_part.added",
                              item_id=message_id,
                              output_index=self.output_index,
                              content_index=0,
                              part={
                                  "type": "output_text",
                                  "annotations": [],
                                  "logprobs": [],
                                  "text": "",
                              })

        # Execute response agent
        response_result = await self.agents["response"].run(request, context)
        context["response_agent"] = response_result
        
        final_response = response_result.get("response", "")
        
        # Stream output text
        yield self.create_event("response.output_text.delta",
                              item_id=message_id,
                              output_index=self.output_index,
                              content_index=0,
                              delta=final_response)

        # Complete output text
        yield self.create_event("response.output_text.done",
                              item_id=message_id,
                              output_index=self.output_index,
                              content_index=0,
                              text=final_response)

        # Complete content part
        yield self.create_event("response.content_part.done",
                              item_id=message_id,
                              output_index=self.output_index,
                              content_index=0,
                              part={
                                  "type": "output_text",
                                  "annotations": [],
                                  "logprobs": [],
                                  "text": final_response,
                              })

        # Complete assistant message
        yield self.create_event("response.output_item.done",
                              output_index=self.output_index,
                              item={
                                  "id": message_id,
                                  "type": "message",
                                  "role": "assistant",
                                  "status": "completed",
                                  "content": [
                                      {
                                          "type": "output_text",
                                          "text": final_response,
                                          "annotations": [],
                                      }
                                  ],
                              })

    async def _stream_citation_agent(self, request: Dict[str, Any], context: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream citation agent work."""
        citation_id = self.generate_output_id("cit")
        
        # Add reasoning for citation processing
        yield self.create_event("response.output_item.added",
                              output_index=self.output_index,
                              item={
                                  "id": citation_id,
                                  "type": "reasoning",
                                  "content": [],
                              })

        async for event in self._stream_reasoning_step(citation_id, "Adding citations and references..."):
            yield event

        # Execute citation agent
        citation_result = await self.agents["citation"].run(request, context)
        context["citation_agent"] = citation_result

        # Complete citation reasoning
        yield self.create_event("response.output_item.done",
                              output_index=self.output_index,
                              item={
                                  "id": citation_id,
                                  "type": "reasoning",
                                  "content": [
                                      {
                                          "type": "reasoning_text",
                                          "text": "Citations added to response"
                                      }
                                  ]
                              })

    async def handle_request(self, request: Dict[str, Any]) -> Union[Dict[str, Any], AsyncGenerator[Dict[str, Any], None]]:
        """Public handler for the endpoint - supports both streaming and non-streaming."""
        try:
            # Check if streaming is requested
            if request.get("stream", False):
                return self._handle_request_streaming(request)
            else:
                return await self._handle_request_internal(request)
        except Exception as e:
            logger.error(f"Error in multi-agent endpoint: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}


# Create instance for import compatibility
multi_agent_endpoint = MultiAgentChatEndpoint()


async def handle_multi_agent_request(request_data: Dict[str, Any]):
    """
    Global function to handle multi-agent requests with streaming support.
    
    This can be imported and used directly in Flask/FastAPI route handlers.
    """
    return await multi_agent_endpoint.handle_request(request_data)


async def handle_multi_agent_request_streaming(request_data: Dict[str, Any]):
    """
    Global function to handle multi-agent requests with streaming.
    
    This can be imported and used directly in Flask/FastAPI route handlers.
    """
    request_data["stream"] = True
    return await multi_agent_endpoint.handle_request(request_data)
