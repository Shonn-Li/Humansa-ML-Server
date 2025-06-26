"""
Web Search Module - Modular web search functionality

Provides web search capabilities with caching and multiple API support.
"""

from .web_search_processor import web_search_processor, WebSearchProcessor, WebSearchContext, WebSearchResult

__all__ = [
    'web_search_processor',
    'WebSearchProcessor',
    'WebSearchContext',
    'WebSearchResult'
]
