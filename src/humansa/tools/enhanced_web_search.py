"""
Enhanced Web Search Tool for Humansa with Streaming Search Results

This module provides ChatGPT-like streaming web search functionality where:
1. Each search query streams individual results as they're found
2. Results include link information that's appended to the frontend
3. Search process is transparent with progress updates
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime
from chat.websearch.web_search_processor import WebSearchProcessor

logger = logging.getLogger(__name__)


class StreamingWebSearchTool:
    """Enhanced web search tool with streaming results"""

    def __init__(self, stream_callback=None):
        self.web_search = WebSearchProcessor()
        self.stream_callback = stream_callback

    async def search_web_streaming(self, query: str, category: Optional[str] = None,
                                   language: str = "zh") -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream web search results as they're found, similar to ChatGPT.

        This function:
        1. Yields progress updates as search happens
        2. Yields individual search results as they're found
        3. Provides final summary with all links
        """

        logger.info(f"🌐 Starting streaming web search for: {query}")

        # Yield initial search start
        yield {
            "type": "search_start",
            "query": query,
            "message": f"Searching the web for: {query}",
            "timestamp": datetime.now().isoformat()
        }

        try:
            # Perform the search
            search_results = await self.web_search.search_web_content(query, num_results=5)

            if not search_results.results:
                yield {
                    "type": "search_complete",
                    "query": query,
                    "results": [],
                    "total_found": 0,
                    "message": "No results found",
                    "timestamp": datetime.now().isoformat()
                }
                return

            # Stream each result individually (ChatGPT-like)
            accumulated_links = []

            for i, result in enumerate(search_results.results):
                # Add small delay to simulate real-time finding
                await asyncio.sleep(0.3)

                link_info = {
                    "url": result.link,
                    "title": result.title,
                    "snippet": result.snippet,
                    "source": result.source,
                    "position": i + 1
                }

                accumulated_links.append(link_info)

                # Yield individual result found
                yield {
                    "type": "search_result_found",
                    "query": query,
                    "result": link_info,
                    "progress": f"Found result {i + 1}/{len(search_results.results)}",
                    "accumulated_links": accumulated_links.copy(),  # Frontend can build list
                    "timestamp": datetime.now().isoformat()
                }

            # Yield final summary
            yield {
                "type": "search_complete",
                "query": query,
                "results": accumulated_links,
                "total_found": len(accumulated_links),
                "search_performed": search_results.search_performed,
                "cache_hit": search_results.cache_hit,
                "message": f"Found {len(accumulated_links)} relevant results",
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"❌ Streaming web search failed: {e}")
            yield {
                "type": "search_error",
                "query": query,
                "error": str(e),
                "message": f"Search failed: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }

    async def search_web_structured_streaming(self, query: str, category: Optional[str] = None,
                                              language: str = "zh") -> Dict[str, Any]:
        """
        Enhanced web search with streaming capability for tool calls.

        This is called by the agent and streams results via callback.
        """

        logger.info(
            f"🌐 search_web_structured_streaming called with: query={query}")

        # Safety check for internal terms
        internal_terms = ["医生", "诊所", "预约", "挂号", "doctor", "clinic", "appointment", "booking",
                          "价格", "pricing", "费用", "医疗服务", "medical service"]

        query_lower = query.lower()
        if any(term in query_lower for term in internal_terms):
            return {
                "success": False,
                "error": "Web search is for external information only. Use internal tools for Humansa services.",
                "query": query,
                "suggestion": "Try using our internal search tools instead"
            }

        try:
            accumulated_results = []
            search_progress = []

            # Stream search results if callback is available
            if self.stream_callback:
                async for search_event in self.search_web_streaming(query, category, language):
                    # Send each search event to the streaming callback
                    self.stream_callback({
                        'type': 'web_search_event',
                        'event': search_event,
                        'timestamp': datetime.now().isoformat()
                    })

                    # Track progress
                    search_progress.append(search_event)

                    # Accumulate results
                    if search_event["type"] == "search_result_found":
                        accumulated_results.append(search_event["result"])
                    elif search_event["type"] == "search_complete":
                        accumulated_results = search_event["results"]
            else:
                # Fallback: non-streaming search
                search_results = await self.web_search.search_web_content(query, num_results=5)
                accumulated_results = [
                    {
                        "url": result.link,
                        "title": result.title,
                        "snippet": result.snippet,
                        "source": result.source,
                        "position": i + 1
                    }
                    for i, result in enumerate(search_results.results)
                ]

            return {
                "success": True,
                "query": query,
                "language": language,
                "results": accumulated_results,
                "total_results": len(accumulated_results),
                "search_type": "streaming_web_search",
                "message": f"Found {len(accumulated_results)} web results with streaming updates",
                "search_progress": search_progress,  # Full event log
                "note": "Results were streamed in real-time during search"
            }

        except Exception as e:
            logger.error(f"❌ search_web_structured_streaming failed: {e}")
            return {"error": str(e), "success": False}
