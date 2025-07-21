"""
Response Agent - Generates the final response

This agent takes all the context from other agents and generates
the final response to the user. It supports both streaming and
non-streaming modes.
"""

from typing import Dict, Any, List, AsyncGenerator, Tuple
import logging
import re

from .base import BaseAgent
from ..provider.llm_provider import LLMProviderSelector
from ..config.system_prompts import SystemPromptManager
from ..citation.citation_position_tracker import citation_position_tracker
from llama_index.core.llms import ChatMessage

logger = logging.getLogger(__name__)


class ResponseAgent(BaseAgent):
    """Enhanced agent for generating responses with streaming support"""
    
    def __init__(self, llm_provider_manager: LLMProviderSelector):
        super().__init__()
        self.llm_provider_manager = llm_provider_manager
        self.system_prompt_manager = SystemPromptManager()
        self.supports_streaming = True
        self.citation_pattern = re.compile(r'\[(\d+)\]')
    
    async def run(self, request: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate the final response with optional citations (non-streaming)"""
        
        # Build combined context and sources
        combined_context, sources = self._build_combined_context_with_sources(context)
        
        # Check if citations should be enabled
        enable_citations = self._should_enable_citations(request, sources)
        
        # Prepare messages
        messages = self._prepare_messages(request, combined_context, sources, enable_citations)
        
        # Get LLM provider
        model = request.get("model", "gpt-4o-mini")
        provider_info = self.llm_provider_manager.get_provider(None, model)
        llm = provider_info["llm"]
        
        # Generate response
        response = await llm.achat(messages)
        response_text = response.message.content
        
        # Extract citation annotations if citations are enabled
        annotations = []
        if enable_citations and sources:
            _, annotations = citation_position_tracker.extract_citations_with_positions(response_text, sources)
        
        return {
            "status": "success",
            "response": response_text,
            "annotations": [ann.to_dict() for ann in annotations],
            "sources": sources if enable_citations else [],
            "metadata": {
                "model": request.get("model", "gpt-4o-mini"),
                "context_used": bool(combined_context),
                "citations_enabled": enable_citations
            }
        }
    
    async def stream(self, request: Dict[str, Any], context: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """Generate the response with streaming and citations"""
        
        # Build combined context and sources
        combined_context, sources = self._build_combined_context_with_sources(context)
        
        # Check if citations should be enabled
        enable_citations = self._should_enable_citations(request, sources)
        
        # Prepare messages
        messages = self._prepare_messages(request, combined_context, sources, enable_citations)
        
        # Get LLM provider
        model = request.get("model", "gpt-4o-mini")
        provider_info = self.llm_provider_manager.get_provider(None, model)
        llm = provider_info["llm"]
        
        # Stream response
        try:
            stream = await llm.astream_chat(messages)
            
            # Accumulate response for citation tracking
            accumulated_response = ""
            
            # Stream the response chunks
            async for chunk in stream:
                if chunk.delta:
                    accumulated_response += chunk.delta
                    yield {
                        "type": "response_chunk",
                        "content": chunk.delta,
                        "metadata": {"agent": "response"}
                    }
            
            # Extract and yield citation annotations if enabled
            if enable_citations and sources:
                _, annotations = citation_position_tracker.extract_citations_with_positions(accumulated_response, sources)
                
                # Yield annotation data
                yield {
                    "type": "annotations",
                    "annotations": [ann.to_dict() for ann in annotations],
                    "sources": sources
                }
            
            # Final result
            yield {
                "status": "success",
                "response": accumulated_response,
                "metadata": {
                    "model": request.get("model", "gpt-4o-mini"),
                    "context_used": bool(combined_context),
                    "citations_enabled": enable_citations,
                    "source_count": len(sources)
                }
            }
            
        except Exception as e:
            logger.error(f"Error in response streaming: {e}")
            yield {"type": "error", "error": str(e)}
    
    def _build_combined_context_with_sources(self, context: Dict[str, Any]) -> Tuple[str, List[Dict[str, Any]]]:
        """Build combined context and extract sources from all agents"""
        context_parts = []
        all_sources = []
        source_counter = 1
        
        # Attachment context and sources
        if "attachment_agent" in context:
            attachment_context = context["attachment_agent"].get("context", "")
            if attachment_context:
                context_parts.append(f"[{source_counter}] Attachment Content:\n{attachment_context}")
                # Add attachment as a source
                all_sources.append({
                    "source_id": f"attachment_{source_counter}",
                    "type": "attachment",
                    "title": "User Attachment",
                    "content": attachment_context[:500],  # First 500 chars
                    "url": context["attachment_agent"].get("url", ""),
                    "metadata": {
                        "filename": context["attachment_agent"].get("filename", "attachment")
                    }
                })
                source_counter += 1
        
        # RAG context and sources
        if "rag_agent" in context:
            rag_sources = context["rag_agent"].get("sources", [])
            for source in rag_sources:
                # Format source content
                source_content = source.get("content", "")[:500]
                context_parts.append(f"[{source_counter}] Knowledge Base:\n{source_content}")
                
                # Add RAG source with custom metadata
                all_sources.append({
                    "source_id": f"rag_{source_counter}",
                    "type": "rag_node",
                    "title": source.get("title", f"Note {source_counter}"),
                    "content": source_content,
                    "url": f"youwo://note/{source.get('note_id', '')}",  # Custom URL scheme
                    "metadata": {
                        "note_id": source.get("note_id"),
                        "node_id": source.get("node_id"),
                        "chunk_id": source.get("chunk_id"),
                        "score": source.get("score", 0.0)
                    }
                })
                source_counter += 1
        
        # Web search context and sources
        if "web_search_agent" in context:
            web_results = context["web_search_agent"].get("results", [])
            for result in web_results:
                # Format web result
                snippet = result.get("snippet", "") if isinstance(result, dict) else getattr(result, "snippet", "")
                title = result.get("title", "") if isinstance(result, dict) else getattr(result, "title", "")
                url = result.get("link", result.get("url", "")) if isinstance(result, dict) else getattr(result, "link", "")
                
                context_parts.append(f"[{source_counter}] {title}:\n{snippet}")
                
                # Add web source
                all_sources.append({
                    "source_id": f"web_{source_counter}",
                    "type": "web_search",
                    "title": title,
                    "content": snippet,
                    "url": url,
                    "metadata": {
                        "search_engine": "google"
                    }
                })
                source_counter += 1
        
        combined_context = "\n\n".join(context_parts)
        return combined_context, all_sources
    
    def _prepare_messages(self, request: Dict[str, Any], combined_context: str, sources: List[Dict[str, Any]], enable_citations: bool) -> List[ChatMessage]:
        """Prepare messages for LLM with citation instructions"""
        messages = []
        
        # System message
        system_prompt = self.system_prompt_manager.get_system_prompt(
            request.get("model", "gpt-4o-mini")
        )
        messages.append(ChatMessage(role="system", content=system_prompt))
        
        # Add context with citation instructions if enabled
        if combined_context:
            context_message = f"Context for answering the user's question:\n\n{combined_context}"
            
            # Add citation instructions if enabled and we have sources
            if enable_citations and sources:
                context_message += """\n\nCITATION INSTRUCTIONS:
1. You MUST cite sources using numbered brackets like [1], [2], etc.
2. Place citations immediately after the relevant statement or fact.
3. You can cite multiple sources for one statement like [1, 3].
4. Only cite sources that directly support your statement.
5. Every factual claim from the provided sources must have a citation.
6. Do NOT use markdown links or any other citation format.

Example: According to the documentation [1], the feature works by processing data [2, 3]."""
            
            messages.append(ChatMessage(
                role="system",
                content=context_message
            ))
        
        # Add conversation history
        for msg in request["messages"]:
            messages.append(ChatMessage(role=msg["role"], content=msg["content"]))
        
        return messages
    
    def _should_enable_citations(self, request: Dict[str, Any], sources: List[Dict[str, Any]]) -> bool:
        """Determine if citations should be enabled"""
        # Check explicit setting first
        if "enable_citations" in request:
            return request["enable_citations"]
        
        # Enable by default if we have any sources
        return len(sources) > 0