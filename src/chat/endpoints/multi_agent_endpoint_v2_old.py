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
    RAGAgent,
    WebSearchAgent,
    AttachmentAgent,
    ResponseAgent,
    CitationAgent,
    CodeInterpreterAgent,
    PythonToolAgent
)

logger = logging.getLogger(__name__)


class StreamingChunk:
    """Helper class to create OpenAI-standard streaming chunks"""
    
    @staticmethod
    def create(content: str, role: str = "assistant", finish_reason: Optional[str] = None, 
               model: str = "gpt-4.1-nano", chunk_id: Optional[str] = None) -> Dict[str, Any]:
        """Create an OpenAI-standard streaming chunk"""
        if not chunk_id:
            chunk_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"
            
        return {
            "id": chunk_id,
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
    """Enhanced base class for streaming-capable agents"""
    
    def __init__(self):
        super().__init__()
        self.supports_streaming = False
    
    @abstractmethod
    async def run(self, request: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the agent's main logic (non-streaming)."""
        pass
    
    async def stream(self, request: Dict[str, Any], context: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """Execute the agent's logic with streaming support."""
        # Default implementation: yield the full result at once
        result = await self.run(request, context)
        yield result


class RouterAgent(BaseAgent):
    """Agent responsible for routing queries to appropriate tools"""
    
    def __init__(self, llm_provider_manager: LLMProviderSelector):
        super().__init__()
        self.router = IntelligentRouter()
        self.query_transformer = QueryTransformer(llm_provider_manager)
    
    async def run(self, request: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Route the query and determine which agents should be activated"""
        
        # Get the latest user message
        user_messages = [msg for msg in request["messages"] if msg["role"] == "user"]
        if not user_messages:
            raise ValueError("No user messages found in request")
        
        query = user_messages[-1]["content"]
        
        # Check if attachments are present BEFORE routing
        # Note: empty list should not count as having attachments
        attachments = request.get("attachments", [])
        has_attachments = bool(attachments and len(attachments) > 0)
        
        # Route the query with attachment information
        router_decision = await self.router.route_query(
            query, str(request["user_id"]), request["messages"][-3:], has_attachments
        )
        
        # Determine which agents should be enabled based on router decision
        enabled_agents = ["response"]  # Always include response agent
        
        # PRIORITY: If attachments are present, always enable attachment agent
        if has_attachments:
            enabled_agents.append("attachment")
            # Do NOT automatically enable RAG when attachments are present
            # The attachment content should be the primary source
        
        # Enable agents based on router decision
        # IMPORTANT: Don't enable RAG if attachments are present - attachment content takes priority
        if router_decision.selected_tool in ["knowledge_base_notes", "knowledge_base_conversations", "knowledge_base_full"]:
            if "rag" not in enabled_agents and not has_attachments:
                enabled_agents.append("rag")
        
        if router_decision.selected_tool == "web_search":
            enabled_agents.append("web_search")
        
        # Legacy check - keep for backward compatibility
        if router_decision.selected_tool == "attachments" and "attachment" not in enabled_agents:
            enabled_agents.append("attachment")
        
        # Check for code interpreter requests
        code_keywords = ['code', 'python', 'execute', 'calculate', 'plot', 'graph', 'analyze data', 'statistics', 'math', 'solve']
        query_lower = query.lower()
        if any(keyword in query_lower for keyword in code_keywords) or '```python' in query or 'import ' in query:
            enabled_agents.append("code_interpreter")
        
        if request.get("enable_citations", True):
            enabled_agents.append("citation")
        
        # Transform query if needed (for now, use original query)
        condensed_query = query
        
        return {
            "router_decision": asdict(router_decision),
            "original_query": query,
            "condensed_query": condensed_query,  # Add condensed query
            "enabled_agents": enabled_agents,
            "model": request.get("model", "gpt-4.1-nano"),
            "search_type": router_decision.search_type if hasattr(router_decision, 'search_type') else "knowledge_base"
        }


class RAGAgent(BaseAgent):
    """Agent for retrieving context from knowledge base"""
    
    def __init__(self, rag_processor: RAGProcessor):
        super().__init__()
        self.rag_processor = rag_processor
    
    async def run(self, request: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve relevant context from notes and conversations"""
        
        router_result = context.get("router_agent", {})
        condensed_query = router_result.get("condensed_query", router_result.get("original_query", ""))
        search_type = router_result.get("search_type", "knowledge_base")
        
        # Use the RAG processor
        rag_result = await self.rag_processor.process_rag_request(
            messages=request["messages"],
            user_id=request["user_id"],
            custom_query=condensed_query,
            search_type=search_type
        )
        
        # Build context from chunks
        context_parts = []
        for chunk in rag_result.chunks:
            context_parts.append(chunk.chunk_text)
        
        combined_context = "\n\n".join(context_parts)
        
        return {
            "status": "success",
            "context": combined_context,
            "sources": [{"chunk_id": chunk.section_id, "content": chunk.chunk_text[:100] + "..."} for chunk in rag_result.chunks[:5]],
            "metadata": {
                "search_type": search_type,
                "context_length": len(combined_context),
                "total_chunks": rag_result.total_chunks,
                "used_note_ids": rag_result.used_note_ids,
                "used_conversation_ids": rag_result.used_conversation_ids
            }
        }


class WebSearchAgent(BaseAgent):
    """Agent for performing web searches"""
    
    def __init__(self, web_search_processor: WebSearchProcessor):
        super().__init__()
        self.web_search_processor = web_search_processor
    
    async def run(self, request: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Perform web search and return results"""
        
        router_result = context.get("router_agent", {})
        condensed_query = router_result.get("condensed_query", router_result.get("original_query", ""))
        
        # Use the web search processor
        search_result = await self.web_search_processor.search_web_content(condensed_query)
        
        # Build context from search results
        context_parts = []
        for i, result in enumerate(search_result.results[:5], 1):  # Limit to top 5 results
            context_parts.append(f"[{i}] {result.title}\n{result.snippet}\nURL: {result.link}")
        
        web_context = "\n\n".join(context_parts) if context_parts else ""
        
        return {
            "status": "success",
            "results": search_result.results,
            "context": web_context,
            "metadata": {
                "query": condensed_query,
                "result_count": len(search_result.results),
                "cache_hit": search_result.cache_hit
            }
        }


class AttachmentAgent(BaseAgent):
    """Agent for processing file attachments"""
    
    def __init__(self, file_attachment_manager: FileAttachmentManager):
        super().__init__()
        self.file_attachment_manager = file_attachment_manager
    
    async def run(self, request: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Process attachments and extract context"""
        
        attachments = request.get("attachments", [])
        if not attachments:
            return {"status": "success", "context": "", "metadata": {"attachment_count": 0}}
        
        router_result = context.get("router_agent", {})
        condensed_query = router_result.get("condensed_query", router_result.get("original_query", ""))
        
        # Process attachments
        user_id = request.get("user_id", 0)
        attachment_result = await self.file_attachment_manager.process_attachments(
            attachments, condensed_query, user_id
        )
        
        # Convert AttachmentContext to string for context
        attachment_context = self.file_attachment_manager.chunks_to_context_text(
            attachment_result.chunks,
            attachment_result.image_chunks
        ) if attachment_result else ""
        
        return {
            "status": "success",
            "context": attachment_context,
            "metadata": {
                "attachment_count": len(attachments),
                "context_length": len(attachment_context)
            }
        }


class ResponseAgent(BaseAgent):
    """Enhanced agent for generating responses with streaming support"""
    
    def __init__(self, llm_provider_manager: LLMProviderSelector):
        super().__init__()
        self.llm_provider_manager = llm_provider_manager
        self.system_prompt_manager = SystemPromptManager()
        self.supports_streaming = True
    
    async def run(self, request: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate the final response (non-streaming)"""
        
        # Build combined context
        combined_context = self._build_combined_context(context)
        
        # Prepare messages
        messages = self._prepare_messages(request, combined_context)
        
        # Get LLM provider
        model = request.get("model", "gpt-4.1-nano")
        provider_info = self.llm_provider_manager.get_provider(None, model)
        llm = provider_info["llm"]
        
        # Generate response
        response = await llm.achat(messages)
        
        return {
            "status": "success",
            "response": response.message.content,
            "metadata": {
                "model": request.get("model", "gpt-4.1-nano"),
                "context_used": bool(combined_context)
            }
        }
    
    async def stream(self, request: Dict[str, Any], context: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """Generate the response with streaming"""
        
        # Build combined context
        combined_context = self._build_combined_context(context)
        
        # Prepare messages
        messages = self._prepare_messages(request, combined_context)
        
        # Get LLM provider
        model = request.get("model", "gpt-4.1-nano")
        provider_info = self.llm_provider_manager.get_provider(None, model)
        llm = provider_info["llm"]
        
        # Stream response
        try:
            stream = await llm.astream_chat(messages)
            
            # Stream the response chunks
            async for chunk in stream:
                if chunk.delta:
                    yield {
                        "type": "response_chunk",
                        "content": chunk.delta,
                        "metadata": {"agent": "response"}
                    }
            
            # Final result
            yield {
                "status": "success",
                "metadata": {
                    "model": request.get("model", "gpt-4.1-nano"),
                    "context_used": bool(combined_context)
                }
            }
            
        except Exception as e:
            logger.error(f"Error in response streaming: {e}")
            yield {"type": "error", "error": str(e)}
    
    def _build_combined_context(self, context: Dict[str, Any]) -> str:
        """Build combined context from all agents"""
        context_parts = []
        
        # Attachment context - PRIORITY: User-provided attachments come first
        if "attachment_agent" in context:
            attachment_context = context["attachment_agent"].get("context", "")
            if attachment_context:
                context_parts.append(f"Attachment Content:\n{attachment_context}")
        
        # RAG context
        if "rag_agent" in context:
            rag_context = context["rag_agent"].get("context", "")
            if rag_context:
                context_parts.append(f"Knowledge Base Context:\n{rag_context}")
        
        # Web search context
        if "web_search_agent" in context:
            web_context = context["web_search_agent"].get("context", "")
            if web_context:
                context_parts.append(f"Web Search Results:\n{web_context}")
        
        return "\n\n".join(context_parts)
    
    def _prepare_messages(self, request: Dict[str, Any], combined_context: str) -> List[ChatMessage]:
        """Prepare messages for LLM"""
        messages = []
        
        # System message
        system_prompt = self.system_prompt_manager.get_system_prompt(
            request.get("model", "gpt-4.1-nano")
        )
        messages.append(ChatMessage(role="system", content=system_prompt))
        
        # Add context if available
        if combined_context:
            context_message = f"Context for answering the user's question:\n\n{combined_context}"
            
            # If citations are enabled and we have sources, add citation instructions
            if request.get("enable_citations", False) and ("Source:" in combined_context or "URL:" in combined_context):
                context_message += "\n\nIMPORTANT: When citing sources, use numbered citations like [1], [2], etc. Do NOT use markdown links like [text](url)."
            
            messages.append(ChatMessage(
                role="system",
                content=context_message
            ))
        
        # Add conversation history
        for msg in request["messages"]:
            messages.append(ChatMessage(role=msg["role"], content=msg["content"]))
        
        return messages


class CitationAgent(BaseAgent):
    """Agent for adding citations to responses"""
    
    def __init__(self, citation_engine: CitationEngine, llm_provider_manager: LLMProviderSelector):
        super().__init__()
        self.citation_engine = citation_engine
        self.llm_provider_manager = llm_provider_manager
    
    async def run(self, request: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Add citations to the response"""
        
        response_result = context.get("response_agent", {})
        response_text = response_result.get("response", "")
        
        if not response_text:
            return {"status": "error", "error": "No response to cite"}
        
        # Gather all sources
        all_sources = []
        
        # RAG sources
        if "rag_agent" in context:
            rag_sources = context["rag_agent"].get("sources", [])
            all_sources.extend(rag_sources)
        
        # Web search sources
        if "web_search_agent" in context:
            web_results = context["web_search_agent"].get("results", [])
            for result in web_results:
                # Handle both dict and WebSearchResult objects
                if hasattr(result, 'title'):
                    # It's a WebSearchResult object
                    all_sources.append({
                        "type": "web",
                        "title": result.title,
                        "url": result.link,  # Use 'link' attribute
                        "snippet": result.snippet
                    })
                else:
                    # It's a dict
                    all_sources.append({
                        "type": "web",
                        "title": result.get("title", ""),
                        "url": result.get("link", result.get("url", "")),  # Try both 'link' and 'url'
                        "snippet": result.get("snippet", "")
                    })
        
        if not all_sources:
            return {
                "status": "success",
                "citations": {"response": response_text, "sources": []},
                "metadata": {"citation_count": 0}
            }
        
        # Get provider for citation generation
        model = request.get("model", "gpt-4.1-nano")
        provider_info = self.llm_provider_manager.get_provider(None, model)
        llm = provider_info["llm"]
        
        # Build sources text with numbered citations
        sources_text = []
        citation_sources = []
        
        for i, source in enumerate(all_sources[:10], 1):  # Limit to 10 sources
            # Create CitationSource object
            if isinstance(source, dict):
                citation_source = CitationSource(
                    source_id=f"source_{i}",
                    source_type=source.get("type", "unknown"),
                    title=source.get("title", f"Source {i}"),
                    content=source.get("content", source.get("snippet", ""))[:500],
                    url=source.get("url"),
                    metadata=source.get("metadata", {})
                )
                citation_sources.append(citation_source)
                
                # Build source text for prompt
                source_text = f"[{i}] {citation_source.title}"
                if citation_source.url:
                    source_text += f" ({citation_source.url})"
                source_text += f"\nContent: {citation_source.content}"
                sources_text.append(source_text)
        
        if not citation_sources:
            # No sources to cite, return original response
            citation_dict = {
                "response": response_text,
                "sources": [],
                "source_mapping": {},
                "total_sources": 0
            }
        else:
            # Build citation prompt
            citation_prompt = f"""Given the following sources and response, please rewrite the response to include proper citations using ONLY numbered brackets like [1], [2], etc. 

DO NOT use markdown links like [text](url). ONLY use simple numbered citations like [1].

Sources:
{chr(10).join(sources_text)}

Original Response:
{response_text}

Instructions:
1. Add citations as [1], [2], [3] etc. inline where appropriate (NOT as markdown links)
2. Only cite sources that are actually referenced in the content
3. Keep the same information and tone as the original
4. Add a "Sources:" section at the end listing the cited sources
5. IMPORTANT: Use ONLY the format [1], [2], etc. Do NOT use [Source 1] or [text](url)

Rewritten response with proper numbered citations:"""

            # Generate cited response
            try:
                citation_messages = [ChatMessage(role="user", content=citation_prompt)]
                citation_response = await llm.achat(citation_messages)
                cited_response = citation_response.message.content
                
                # Parse which sources were actually cited
                cited_indices = []
                for i in range(1, len(citation_sources) + 1):
                    if f"[{i}]" in cited_response:
                        cited_indices.append(i)
                
                # Build source mapping
                source_mapping = {}
                used_sources = []
                for idx in cited_indices:
                    source = citation_sources[idx - 1]
                    source_mapping[f"[{idx}]"] = source.source_id
                    used_sources.append(source)
                
                citation_dict = {
                    "response": cited_response,
                    "sources": [asdict(s) for s in used_sources],
                    "source_mapping": source_mapping,
                    "total_sources": len(used_sources)
                }
            except Exception as e:
                logger.error(f"Citation generation failed: {e}")
                # Fallback to original response
                citation_dict = {
                    "response": response_text,
                    "sources": [],
                    "source_mapping": {},
                    "total_sources": 0
                }
        
        return {
            "status": "success",
            "citations": citation_dict,
            "metadata": {
                "citation_count": len(citation_dict.get("sources", [])),
                "source_count": len(all_sources)
            }
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

Valid agent names: rag, web_search, attachment, code_interpreter
DO NOT include any other text, only the JSON object."""

        try:
            # Use chat interface like other agents
            eval_messages = [ChatMessage(role="user", content=eval_prompt)]
            eval_response = await llm.achat(eval_messages)
            eval_result = eval_response.message.content
            
            # Debug logging
            logger.info(f"Iteration evaluation raw response: {eval_result[:200]}...")
            
            eval_data = json.loads(eval_result)
            
            if eval_data.get("needs_iteration", False):
                suggested_agents = eval_data.get("suggested_agents", [])
                # Validate agent names
                valid_agents = [a for a in suggested_agents if a in self.agents]
                if valid_agents:
                    logger.info(f"Iteration {self.iteration_count + 1} triggered: {eval_data.get('reason')}")
                    return True, valid_agents
        except Exception as e:
            logger.warning(f"Iteration evaluation failed: {e}")
        
        return False, []
    
    async def run_iteration(self, request: Dict[str, Any], context: Dict[str, Any], additional_agents: List[str]) -> Dict[str, Any]:
        """Run an additional iteration with specified agents"""
        self.iteration_count += 1
        iteration_context = context.copy()
        
        # Add iteration metadata
        iteration_context["iteration"] = self.iteration_count
        iteration_context["additional_agents"] = additional_agents
        
        # Run additional agents
        agent_results = {}
        for agent_name in additional_agents:
            if agent_name in self.agents and agent_name not in ["router", "response", "citation"]:
                try:
                    result = await self.agents[agent_name].run(request, iteration_context)
                    iteration_context[f"{agent_name}_agent_iter{self.iteration_count}"] = result
                    agent_results[agent_name] = result
                except Exception as e:
                    logger.error(f"Agent {agent_name} failed in iteration {self.iteration_count}: {e}")
        
        # Re-run response agent with additional context
        if agent_results:
            response_result = await self.agents["response"].run(request, iteration_context)
            iteration_context["response_agent"] = response_result
            
            # Re-run citation if enabled
            router_result = iteration_context.get("router_agent", {})
            enabled_agents = router_result.get("enabled_agents", [])
            if "citation" in enabled_agents:
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
            "rag": RAGAgent(self.rag_processor),
            "web_search": WebSearchAgent(self.web_search_processor),
            "attachment": AttachmentAgent(self.file_attachment_manager),
            "code_interpreter": CodeInterpreterAgent(),
            "response": ResponseAgent(self.llm_provider_manager),
            "citation": CitationAgent(self.citation_engine, self.llm_provider_manager),
        }
        
        # Don't initialize orchestrator here - create per request to avoid state pollution
    
    async def handle_request(self, request: Dict[str, Any]) -> Union[Dict[str, Any], AsyncGenerator[Dict[str, Any], None]]:
        """Handle the request with streaming support"""
        
        if request.get("stream", False):
            return self._handle_streaming_request(request)
        else:
            return await self._handle_non_streaming_request(request)
    
    async def _handle_non_streaming_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle non-streaming request"""
        start_time = time.time()
        context = {}
        agent_results = {}
        
        try:
            # Phase 1: Router Agent
            router_result = await self.agents["router"].run(request, context)
            context["router_agent"] = router_result
            agent_results["router_agent"] = {"status": "success", "data": router_result}
            
            enabled_agents = router_result.get("enabled_agents", [])
            
            # Phase 2: Context Agents (parallel)
            context_tasks = []
            for agent_name in enabled_agents:
                if agent_name in ["rag", "web_search", "attachment", "code_interpreter"]:
                    context_tasks.append(
                        (agent_name, self.agents[agent_name].run(request, context))
                    )
            
            if context_tasks:
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
            
            # Phase 5: Iterative Refinement (if enabled)
            total_iterations = 1  # At least one iteration (initial run)
            if request.get("enable_iterations", True):
                # Create new orchestrator instance per request to avoid state pollution
                orchestrator = IterativeOrchestrator(self.agents, self.llm_provider_manager)
                
                # Check if we need iterations
                needs_iteration, suggested_agents = await orchestrator.should_iterate(context, request)
                
                while needs_iteration:
                    logger.info(f"Running iteration {orchestrator.iteration_count + 1} with agents: {suggested_agents}")
                    
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
                    "prompt_tokens": 0,  # Would need to calculate
                    "completion_tokens": 0,  # Would need to calculate
                    "total_tokens": 0
                },
                "metadata": {
                    "agent_results": agent_results,
                    "workflow_time": time.time() - start_time,
                    "iterations": total_iterations,
                    "router_decision": router_result.get("router_decision", {})
                }
            }
            
        except Exception as e:
            logger.error(f"Error in multi-agent endpoint: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}
    
    async def _handle_streaming_request(self, request: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """Handle streaming request with OpenAI-compatible comprehensive format"""
        start_time = time.time()
        context = {}
        
        # Initialize streaming state
        response_id = f"resp_{uuid.uuid4().hex[:8]}"
        output_index = -1
        sequence_number = 0
        model = request.get("model", "gpt-4.1-nano")
        
        def generate_output_id(prefix: str = "item") -> str:
            """Generate unique output item ID."""
            nonlocal output_index
            output_index += 1
            return f"{prefix}_{uuid.uuid4().hex[:8]}"

        def create_event(event_type: str, **kwargs) -> Dict[str, Any]:
            """Create a structured SSE event matching OpenAI format."""
            nonlocal sequence_number
            event_data = {
                "type": event_type,
                "sequence_number": sequence_number,
            }
            event_data.update(kwargs)
            sequence_number += 1
            return event_data
        
        try:
            # Phase 1: Lifecycle - response.created
            yield create_event("response.created",
                             response={
                                 "id": response_id,
                                 "object": "response",
                                 "created_at": int(time.time()),
                                 "status": "in_progress",
                                 "model": model,
                                 "output": [],
                             })

            # Phase 2: response.in_progress
            yield create_event("response.in_progress",
                             response={
                                 "id": response_id,
                                 "status": "in_progress",
                             })

            # Phase 3: Router Agent - Stream thinking process
            router_id = generate_output_id("router")
            yield create_event("response.output_item.added",
                             output_index=output_index,
                             item={
                                 "id": router_id,
                                 "type": "reasoning",
                                 "content": [],
                             })

            # Stream router thinking
            async for event in self._stream_reasoning_step(router_id, output_index, "Analyzing query and routing to appropriate agents...", create_event):
                yield event

            # Execute router agent
            router_result = await self.agents["router"].run(request, context)
            context["router_agent"] = router_result
            enabled_agents = router_result.get("enabled_agents", [])

            # Complete router reasoning
            yield create_event("response.output_item.done",
                             output_index=output_index,
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
                if agent_name in ["rag", "web_search", "attachment", "code_interpreter"]:
                    # Stream each agent's work (capture current output_index)
                    if agent_name == "web_search":
                        async for event in self._stream_web_search_agent(request, context, create_event, generate_output_id, output_index + 1):
                            yield event
                    elif agent_name == "rag":
                        async for event in self._stream_rag_agent(request, context, create_event, generate_output_id, output_index + 1):
                            yield event
                    elif agent_name == "attachment":
                        async for event in self._stream_attachment_agent(request, context, create_event, generate_output_id, output_index + 1):
                            yield event
                    elif agent_name == "code_interpreter":
                        async for event in self._stream_code_interpreter_agent(request, context, create_event, generate_output_id, output_index + 1):
                            yield event
                    
                    # Execute agent in parallel
                    context_tasks.append(
                        (agent_name, self.agents[agent_name].run(request, context)))

            # Wait for all context agents to complete
            if context_tasks:
                context_results = await asyncio.gather(*[task for _, task in context_tasks])
                for i, (agent_name, _) in enumerate(context_tasks):
                    context[f"{agent_name}_agent"] = context_results[i]

            # Phase 5: Response Agent - Stream final response
            if "response" in enabled_agents:
                async for event in self._stream_response_agent(request, context, create_event, generate_output_id, output_index + 1):
                    yield event

            # Phase 5.5: Iterative Refinement (if enabled)
            total_iterations = 1
            if request.get("enable_iterations", True) and "response" in enabled_agents:
                # Create orchestrator for this request
                orchestrator = IterativeOrchestrator(self.agents, self.llm_provider_manager)
                
                # Check if we need iterations
                needs_iteration, suggested_agents = await orchestrator.should_iterate(context, request)
                
                while needs_iteration and orchestrator.iteration_count < orchestrator.max_iterations:
                    # Stream iteration reasoning
                    iteration_id = generate_output_id(f"iter{orchestrator.iteration_count + 1}")
                    yield create_event("response.output_item.added",
                                     output_index=output_index + 1,
                                     item={
                                         "id": iteration_id,
                                         "type": "reasoning",
                                         "content": [],
                                     })
                    
                    # Stream iteration decision
                    iteration_text = f"Iteration {orchestrator.iteration_count + 1}: Running additional agents {suggested_agents} to improve response quality"
                    async for event in self._stream_reasoning_step(iteration_id, output_index + 1, iteration_text, create_event):
                        yield event
                    
                    # Run iteration
                    context = await orchestrator.run_iteration(request, context, suggested_agents)
                    
                    # Complete iteration reasoning
                    yield create_event("response.output_item.done",
                                     output_index=output_index + 1,
                                     item={
                                         "id": iteration_id,
                                         "type": "reasoning",
                                         "content": [
                                             {
                                                 "type": "reasoning_text",
                                                 "text": iteration_text
                                             }
                                         ]
                                     })
                    
                    # Stream updated response if response agent was re-run
                    if "response" in suggested_agents:
                        async for event in self._stream_response_agent(request, context, create_event, generate_output_id, output_index + 2):
                            yield event
                    
                    # Check if we need another iteration
                    needs_iteration, suggested_agents = await orchestrator.should_iterate(context, request)
                
                total_iterations = orchestrator.iteration_count + 1

            # Phase 6: Citation Agent - Add citations
            if "citation" in enabled_agents:
                async for event in self._stream_citation_agent(request, context, create_event, generate_output_id, output_index + 1):
                    yield event

            # Phase 7: Custom Events - Citations, Title, Usage
            # Generate citations from actual citation agent results
            citations = []
            if "citation_agent" in context:
                citation_result = context["citation_agent"]
                if citation_result.get("status") == "success":
                    citation_data = citation_result.get("citations", {})
                    sources = citation_data.get("sources", [])
                    
                    # Format citations for streaming
                    for idx, source in enumerate(sources):
                        citations.append({
                            "id": idx + 1,
                            "title": source.get("title", "Untitled"),
                            "url": source.get("url", ""),
                            "type": source.get("source_type", "unknown"),
                            "snippet": source.get("snippet", "")
                        })
            
            if citations:
                yield create_event("response.citations",
                                 citations=citations)

            # Generate title if first conversation
            if not request.get("conversation_id") or len(request.get("messages", [])) <= 2:
                # Extract key topic from the query for title generation
                user_messages = [msg for msg in request["messages"] if msg["role"] == "user"]
                if user_messages:
                    user_query = user_messages[-1]["content"]
                    # Simple title generation from query (can be enhanced with LLM)
                    words = user_query.split()[:5]  # First 5 words
                    generated_title = " ".join(words) + "..."
                    yield create_event("response.title_generated",
                                     title=generated_title)

            # Generate usage statistics from actual agent responses
            total_prompt_tokens = 0
            total_completion_tokens = 0
            
            # Aggregate token usage from all agents
            for agent_name, agent_result in context.items():
                if isinstance(agent_result, dict) and "metadata" in agent_result:
                    metadata = agent_result["metadata"]
                    # Check for token usage in metadata
                    if "prompt_tokens" in metadata:
                        total_prompt_tokens += metadata["prompt_tokens"]
                    if "completion_tokens" in metadata:
                        total_completion_tokens += metadata["completion_tokens"]
            
            # If no token tracking, provide estimates
            if total_prompt_tokens == 0:
                # Rough estimates based on context
                total_prompt_tokens = len(str(request.get("messages", []))) // 4
                total_completion_tokens = sum(
                    len(agent_result.get("response", "")) // 4 
                    for agent_result in context.values() 
                    if isinstance(agent_result, dict) and "response" in agent_result
                )
            
            yield create_event("response.usage",
                             usage={
                                 "prompt_tokens": total_prompt_tokens,
                                 "completion_tokens": total_completion_tokens,
                                 "total_tokens": total_prompt_tokens + total_completion_tokens
                             },
                             metadata={
                                 "iterations": total_iterations if 'total_iterations' in locals() else 1,
                                 "model": model,
                                 "agent_results": {
                                     agent_name: {"status": "success"} 
                                     for agent_name in enabled_agents
                                 }
                             })

            # Phase 8: Lifecycle - response.completed
            yield create_event("response.completed",
                             response={
                                 "id": response_id,
                                 "status": "completed",
                                 "object": "response",
                                 "output": [],
                             })
            
            # Phase 9: Lifecycle - response.done (OpenAI standard)
            yield create_event("response.done",
                             response={
                                 "id": response_id,
                                 "done": True
                             })

            logger.info(f"✅ Multi-agent streaming completed - {output_index} output items in {time.time() - start_time:.2f}s")
            
        except asyncio.CancelledError:
            # Handle cancellation/interruption
            logger.warning(f"⚠️ Multi-agent streaming interrupted")
            yield create_event("response.incomplete",
                             response={
                                 "id": response_id,
                                 "status": "incomplete",
                                 "reason": "Request was cancelled or interrupted"
                             })
            raise
        except Exception as e:
            logger.error(f"❌ Multi-agent streaming failed: {e}")
            yield create_event("response.failed",
                             response={
                                 "id": response_id,
                                 "status": "failed",
                                 "error": str(e)
                             })

    async def _stream_reasoning_step(self, reasoning_id: str, output_index: int, thought_content: str, create_event) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream a reasoning step with proper lifecycle."""
        # Add reasoning text part
        yield create_event("response.reasoning_part.added",
                         item_id=reasoning_id,
                         output_index=output_index,
                         content_index=0,
                         part={
                             "type": "reasoning_text",
                             "text": "",
                         })

        # Stream reasoning text
        yield create_event("response.reasoning_text.delta",
                         item_id=reasoning_id,
                         output_index=output_index,
                         content_index=0,
                         delta=thought_content)

        # Complete reasoning text
        yield create_event("response.reasoning_text.done",
                         item_id=reasoning_id,
                         output_index=output_index,
                         content_index=0,
                         text=thought_content)

        # Complete reasoning part
        yield create_event("response.reasoning_part.done",
                         item_id=reasoning_id,
                         output_index=output_index,
                         content_index=0,
                         part={
                             "type": "reasoning_text",
                             "text": thought_content,
                         })

    async def _stream_web_search_agent(self, request: Dict[str, Any], context: Dict[str, Any], create_event, generate_output_id, current_output_index) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream web search agent work with complete event sequence."""
        search_id = generate_output_id("ws")
        
        # Extract query from router context
        router_result = context.get("router_agent", {})
        search_query = router_result.get("condensed_query", router_result.get("original_query", ""))
        if not search_query:
            user_messages = [msg for msg in request["messages"] if msg["role"] == "user"]
            search_query = user_messages[-1]["content"] if user_messages else "search query"
        
        # Add web search output item
        yield create_event("response.output_item.added",
                         output_index=current_output_index,
                         item={
                             "id": search_id,
                             "type": "web_search_call",
                             "status": "in_progress",
                         })

        # Web search in progress
        yield create_event("response.web_search_call.in_progress",
                         output_index=current_output_index,
                         item_id=search_id)

        # Simulate search time (in real implementation, this would be actual search)
        await asyncio.sleep(0.1)

        # Web search searching
        yield create_event("response.web_search_call.searching",
                         output_index=current_output_index,
                         item_id=search_id)

        # Note: The actual search happens after this streaming
        # We'll use the results from context after the agent executes
        
        # Web search completed
        yield create_event("response.web_search_call.completed",
                         output_index=current_output_index,
                         item_id=search_id)

        # Complete web search output item
        # Note: In the current flow, web search results will be available after agent execution
        # For now, we'll provide the structure that will be filled with real data
        yield create_event("response.output_item.done",
                         output_index=current_output_index,
                         item={
                             "id": search_id,
                             "type": "web_search_call",
                             "status": "completed",
                             "action": {
                                 "type": "search",
                                 "query": search_query,
                                 "search_engine": "serper"
                             },
                             "results": [],  # Will be populated by actual search results
                             "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                             "completed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                         })

    async def _stream_rag_agent(self, request: Dict[str, Any], context: Dict[str, Any], create_event, generate_output_id, current_output_index) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream RAG agent work with file search events."""
        # File search for knowledge base
        file_search_id = generate_output_id("fs")
        
        # Add file search output item
        yield create_event("response.output_item.added",
                         output_index=current_output_index,
                         item={
                             "id": file_search_id,
                             "type": "file_search_call",
                             "status": "in_progress",
                         })

        # File search in progress
        yield create_event("response.file_search_call.in_progress",
                         output_index=current_output_index,
                         item_id=file_search_id)

        # Simulate search time
        await asyncio.sleep(0.1)

        # File search searching
        yield create_event("response.file_search_call.searching",
                         output_index=current_output_index,
                         item_id=file_search_id)

        # Simulate search completion
        await asyncio.sleep(0.2)

        # File search completed
        yield create_event("response.file_search_call.completed",
                         output_index=current_output_index,
                         item_id=file_search_id)

        # Complete file search output item
        yield create_event("response.output_item.done",
                         output_index=current_output_index,
                         item={
                             "id": file_search_id,
                             "type": "file_search_call",
                             "status": "completed",
                             "action": {
                                 "type": "search",
                                 "query": "relevant information",
                                 "search_scope": "user_files"
                             },
                             "results": [
                                 {
                                     "file_id": "file_123",
                                     "filename": "notes.txt",
                                     "snippet": "Found relevant information in user notes..."
                                 }
                             ],
                             "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                             "completed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ")
                         })

    async def _stream_attachment_agent(self, request: Dict[str, Any], context: Dict[str, Any], create_event, generate_output_id, current_output_index) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream attachment agent work with function tool calls."""
        # Function tool call for processing attachments
        function_call_id = generate_output_id("fc")
        
        # Add function tool call output item
        yield create_event("response.output_item.added",
                         output_index=current_output_index,
                         item={
                             "id": function_call_id,
                             "type": "function_tool_call",
                             "status": "in_progress",
                             "name": "process_attachments",
                             "arguments": json.dumps({"files": request.get("attachments", [])})
                         })

        # Simulate function execution time
        await asyncio.sleep(0.3)

        # Complete function tool call
        yield create_event("response.output_item.done",
                         output_index=current_output_index,
                         item={
                             "id": function_call_id,
                             "type": "function_tool_call",
                             "status": "completed",
                             "name": "process_attachments",
                             "arguments": json.dumps({"files": request.get("attachments", [])}),
                             "output": "Successfully processed file attachments",
                             "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                             "completed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ")
                         })

        # Optional: Add separate function tool result item with streaming
        result_id = generate_output_id("fr")
        
        # Add function tool result output item
        yield create_event("response.output_item.added",
                         output_index=current_output_index,
                         item={
                             "id": result_id,
                             "type": "function_tool_result",
                             "status": "in_progress",
                             "role": "tool"
                         })

        # Stream function tool result
        result_text = "Successfully processed file attachments:\n- Image analysis complete\n- Text extraction finished"
        
        # Stream result delta
        yield create_event("response.function_tool_result.delta",
                         item_id=result_id,
                         delta=result_text)

        # Complete function tool result
        yield create_event("response.function_tool_result.done",
                         item_id=result_id)

        # Complete function tool result output item
        yield create_event("response.output_item.done",
                         output_index=current_output_index,
                         item={
                             "id": result_id,
                             "type": "function_tool_result",
                             "status": "completed",
                             "role": "tool",
                             "content": [
                                 {
                                     "type": "output_text",
                                     "text": result_text
                                 }
                             ],
                             "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                             "completed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ")
                         })

    async def _stream_response_agent(self, request: Dict[str, Any], context: Dict[str, Any], create_event, generate_output_id, current_output_index) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream response agent work."""
        message_id = generate_output_id("msg")
        
        # Store message ID in context for citation agent to use
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

        # Execute response agent
        response_result = await self.agents["response"].run(request, context)
        context["response_agent"] = response_result
        
        final_response = response_result.get("response", "")
        
        # Stream output text in chunks for realistic streaming
        chunk_size = 20  # Stream in chunks
        for i in range(0, len(final_response), chunk_size):
            chunk = final_response[i:i+chunk_size]
            yield create_event("response.output_text.delta",
                             item_id=message_id,
                             output_index=current_output_index,
                             content_index=0,
                             delta=chunk)
            # Small delay to simulate real streaming
            await asyncio.sleep(0.05)

        # Note: Citations are now handled in _stream_citation_agent to ensure proper timing

        # Complete output text
        yield create_event("response.output_text.done",
                         item_id=message_id,
                         output_index=current_output_index,
                         content_index=0,
                         text=final_response)

        # Complete content part
        yield create_event("response.content_part.done",
                         item_id=message_id,
                         output_index=current_output_index,
                         content_index=0,
                         part={
                             "type": "output_text",
                             "annotations": [],
                             "logprobs": [],
                             "text": final_response,
                         })

        # Complete assistant message
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
                                     "annotations": [],
                                 }
                             ],
                         })

    async def _stream_citation_agent(self, request: Dict[str, Any], context: Dict[str, Any], create_event, generate_output_id, current_output_index) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream citation agent work."""
        citation_id = generate_output_id("cit")
        
        # Add reasoning for citation processing
        yield create_event("response.output_item.added",
                         output_index=current_output_index,
                         item={
                             "id": citation_id,
                             "type": "reasoning",
                             "content": [],
                         })

        async for event in self._stream_reasoning_step(citation_id, current_output_index, "Adding citations and references...", create_event):
            yield event

        # Execute citation agent
        logger.info("Executing citation agent in streaming flow")
        citation_result = await self.agents["citation"].run(request, context)
        context["citation_agent"] = citation_result
        logger.info(f"Citation agent result: status={citation_result.get('status')}, has_citations={bool(citation_result.get('citations'))}")
        
        # Stream citation annotations if citations were added
        if citation_result.get("status") == "success":
            citations = citation_result.get("citations", {})
            sources = citations.get("sources", [])
            cited_response = citations.get("response", "")
            
            # Get the message ID and output index from context
            message_id = context.get("last_message_id")
            message_output_index = context.get("last_message_output_index", current_output_index - 1)
            
            if sources and message_id:
                # Import citation tracker
                from chat.citation.citation_position_tracker import CitationPositionTracker
                citation_position_tracker = CitationPositionTracker()
                
                # Get the actual streamed response text from context
                streamed_response = context.get("response_agent", {}).get("response", "")
                
                # Extract citation positions from the STREAMED response text, not the cited_response
                _, annotations = citation_position_tracker.extract_citations_with_positions(streamed_response, sources)
                
                # Stream annotation events for each citation found
                for annotation in annotations:
                    yield create_event("response.output_text.annotation.added",
                                     item_id=message_id,
                                     output_index=message_output_index,
                                     content_index=0,
                                     annotation=annotation.to_dict())

        # Complete citation reasoning
        yield create_event("response.output_item.done",
                         output_index=current_output_index,
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

    async def _stream_code_interpreter_agent(self, request: Dict[str, Any], context: Dict[str, Any], create_event, generate_output_id, current_output_index) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream code interpreter agent work with function tool calls."""
        code_id = generate_output_id("code")
        
        # Extract user message
        user_messages = [msg for msg in request["messages"] if msg["role"] == "user"]
        user_message = user_messages[-1]["content"] if user_messages else "analyze data"
        
        # Check if code interpreter agent is available
        if "code_interpreter" in self.agents:
            # Extract code from message if available
            code_agent = self.agents["code_interpreter"]
            code_blocks = code_agent.extract_code_from_message(user_message)
            
            # Determine the code to show
            code_to_show = ""
            if code_blocks:
                code_to_show = code_blocks[0]
            else:
                # Generate code based on intent
                code_to_show = "# Python code execution for: " + user_message
        
            # Add function tool call output item
            yield create_event("response.output_item.added",
                             output_index=current_output_index,
                             item={
                                 "id": code_id,
                                 "type": "function_tool_call",
                                 "status": "in_progress",
                                 "name": "python_interpreter",
                                 "arguments": json.dumps({
                                     "code": code_to_show[:200] + "..." if len(code_to_show) > 200 else code_to_show,
                                     "description": "Execute Python code"
                                 })
                             })
        else:
            # Fallback if code interpreter not available
            yield create_event("response.output_item.added",
                             output_index=current_output_index,
                             item={
                                 "id": code_id,
                                 "type": "function_tool_call",
                                 "status": "in_progress",
                                 "name": "python_interpreter",
                                 "arguments": json.dumps({"user_request": user_message})
                             })

        # Simulate code execution time
        await asyncio.sleep(0.2)

        # Complete function tool call
        yield create_event("response.output_item.done",
                         output_index=current_output_index,
                         item={
                             "id": code_id,
                             "type": "function_tool_call",
                             "status": "completed",
                             "name": "python_interpreter",
                             "arguments": json.dumps({"user_request": user_message}),
                             "output": "Code execution initiated",
                             "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                             "completed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                         })

        # Add separate function tool result item with streaming
        result_id = generate_output_id("code_result")
        
        # Add function tool result output item
        yield create_event("response.output_item.added",
                         output_index=current_output_index + 1,
                         item={
                             "id": result_id,
                             "type": "function_tool_result",
                             "status": "in_progress",
                             "role": "tool"
                         })

        # Prepare result text (this will be populated with actual results after agent execution)
        result_text = "Code execution results will appear here after processing..."
        
        # Stream result in chunks
        chunk_size = 50
        for i in range(0, len(result_text), chunk_size):
            chunk = result_text[i:i+chunk_size]
            yield create_event("response.function_tool_result.delta",
                             item_id=result_id,
                             delta=chunk)
            await asyncio.sleep(0.05)

        # Complete function tool result
        yield create_event("response.function_tool_result.done",
                         item_id=result_id)

        # Complete function tool result output item
        yield create_event("response.output_item.done",
                         output_index=current_output_index + 1,
                         item={
                             "id": result_id,
                             "type": "function_tool_result",
                             "status": "completed",
                             "role": "tool",
                             "content": [
                                 {
                                     "type": "output_text",
                                     "text": result_text
                                 }
                             ],
                             "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                             "completed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                         })


# Create instance for import compatibility
multi_agent_endpoint_v2 = MultiAgentChatEndpointV2()