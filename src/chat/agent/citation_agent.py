"""
Citation Agent - Adds citations to responses

This agent processes the response from the Response Agent and adds
proper citations based on the sources from RAG, web search, and attachments.
"""

from typing import Dict, Any
from dataclasses import asdict
import logging

from .base import BaseAgent
from ..citation.citation_engine import CitationEngine, CitationSource
from ..provider.llm_provider import LLMProviderSelector
from llama_index.core.llms import ChatMessage

logger = logging.getLogger(__name__)


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