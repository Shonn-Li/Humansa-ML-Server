"""
Web Search Agent - Performs web searches for current information

This agent searches the web for up-to-date information to complement
the response when the knowledge base doesn't have sufficient information.
"""

from typing import Dict, Any
import logging

from .base import BaseAgent
from ..websearch.web_search_processor import WebSearchProcessor

logger = logging.getLogger(__name__)


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