"""
Modular Web Search Component - Independent web search functionality.

This module provides web search capabilities using multiple APIs (Serper, SerpAPI, Bing)
with intelligent caching and result processing. Completely independent with no external dependencies.
"""

import os
import json
import hashlib
import logging
import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

import requests
from dotenv import load_dotenv

# Import our postgres module for caching
from ..postgres.db_manager import PostgresManager

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Check if web search is available
WEB_SEARCH_AVAILABLE = bool(
    os.getenv("SERPER_API_KEY") or
    os.getenv("SERPAPI_API_KEY") or
    os.getenv("BING_SEARCH_API_KEY")
)


@dataclass
class WebSearchResult:
    """Container for web search result"""
    title: str
    link: str
    snippet: str
    source: str
    cached: bool = False
    cache_age: Optional[str] = None


@dataclass
class WebSearchContext:
    """Container for web search context results"""
    results: List[WebSearchResult]
    query_used: str
    total_results: int
    search_performed: bool
    cache_hit: bool


class WebSearchProcessor:
    """Independent web search processor with caching"""

    def __init__(self):
        self.postgres = PostgresManager()
        self.search_enabled = WEB_SEARCH_AVAILABLE
        logger.info(
            f"WebSearchProcessor initialized - Search enabled: {self.search_enabled}")

        # Initialize cache table
        self._init_cache_table()

    def _init_cache_table(self):
        """Initialize search cache table if it doesn't exist"""
        try:
            with self.postgres.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS web_search_cache (
                            id SERIAL PRIMARY KEY,
                            query_hash VARCHAR(32) UNIQUE NOT NULL,
                            original_query TEXT NOT NULL,
                            results JSONB NOT NULL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            expires_at TIMESTAMP NOT NULL
                        );
                        
                        CREATE INDEX IF NOT EXISTS idx_web_search_cache_hash 
                        ON web_search_cache(query_hash);
                        
                        CREATE INDEX IF NOT EXISTS idx_web_search_cache_expires 
                        ON web_search_cache(expires_at);
                    """)
                    conn.commit()
            logger.info("Web search cache table initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize search cache table: {e}")

    def _get_query_hash(self, query: str) -> str:
        """Generate hash for query caching"""
        # Normalize query for better cache hits
        normalized_query = query.lower().strip()
        return hashlib.sha256(normalized_query.encode()).hexdigest()[:32]

    def _get_cache_ttl_hours(self, query: str) -> int:
        """Get cache TTL in hours based on query type"""
        query_lower = query.lower()

        # News and current events - shorter TTL
        if any(word in query_lower for word in ['news', 'latest', 'today', 'recent', 'current']):
            return 2  # 2 hours

        # Stock prices, weather - very short TTL
        elif any(word in query_lower for word in ['price', 'stock', 'weather', 'temperature']):
            return 1  # 1 hour

        # Reviews, comparisons - longer TTL
        elif any(word in query_lower for word in ['review', 'comparison', 'vs', 'best']):
            return 168  # 7 days

        # General information - medium TTL
        else:
            return 24  # 24 hours

    async def search_web_content(self, query: str, num_results: int = 5) -> WebSearchContext:
        """
        Perform web search with intelligent caching

        Args:
            query: Search query string
            num_results: Number of results to return

        Returns:
            WebSearchContext with search results and metadata
        """
        if not self.search_enabled:
            logger.warning("Web search is disabled - no API keys available")
            return WebSearchContext(
                results=[],
                query_used=query,
                total_results=0,
                search_performed=False,
                cache_hit=False
            )

        if not query or not query.strip():
            logger.warning("Empty search query provided")
            return WebSearchContext(
                results=[],
                query_used=query,
                total_results=0,
                search_performed=False,
                cache_hit=False
            )

        logger.info(
            f"🔍 Web search request: '{query[:100]}...' ({num_results} results)")

        try:
            # Check cache first
            query_hash = self._get_query_hash(query)
            cached_results = await self._get_cached_results(query_hash)

            if cached_results:
                logger.info(f"✅ Cache hit for query: {query[:50]}...")
                return WebSearchContext(
                    results=cached_results,
                    query_used=query,
                    total_results=len(cached_results),
                    search_performed=False,
                    cache_hit=True
                )

            # Cache miss - perform actual search
            logger.info(
                f"❌ Cache miss for query: {query[:50]}... - performing search")
            search_results = await self._perform_search(query, num_results)

            # Cache the results
            if search_results:
                await self._cache_results(query_hash, query, search_results)

            return WebSearchContext(
                results=search_results,
                query_used=query,
                total_results=len(search_results),
                search_performed=True,
                cache_hit=False
            )

        except Exception as e:
            logger.error(f"❌ Web search failed: {e}")
            return WebSearchContext(
                results=[],
                query_used=query,
                total_results=0,
                search_performed=False,
                cache_hit=False
            )

    async def _get_cached_results(self, query_hash: str) -> Optional[List[WebSearchResult]]:
        """Get cached search results if available and not expired"""
        try:
            loop = asyncio.get_event_loop()

            def _get_cache():
                with self.postgres.get_connection() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute("""
                            SELECT results, created_at 
                            FROM web_search_cache 
                            WHERE query_hash = %s 
                            AND expires_at > CURRENT_TIMESTAMP
                        """, (query_hash,))

                        row = cursor.fetchone()
                        if row:
                            return row[0], row[1]  # results, created_at
                        return None

            cached_data = await loop.run_in_executor(None, _get_cache)

            if cached_data:
                results_json, created_at = cached_data

                # Convert to WebSearchResult objects
                cached_results = []
                for result_data in results_json:
                    cached_results.append(WebSearchResult(
                        title=result_data.get('title', ''),
                        link=result_data.get('link', ''),
                        snippet=result_data.get('snippet', ''),
                        source=result_data.get('source', 'web'),
                        cached=True,
                        cache_age=str(created_at)
                    ))

                return cached_results

            return None

        except Exception as e:
            logger.warning(f"Cache lookup failed: {e}")
            return None

    async def _cache_results(self, query_hash: str, query: str, results: List[WebSearchResult]):
        """Cache search results for future use"""
        try:
            loop = asyncio.get_event_loop()
            ttl_hours = self._get_cache_ttl_hours(query)

            # Convert results to JSON
            results_json = []
            for result in results:
                results_json.append({
                    'title': result.title,
                    'link': result.link,
                    'snippet': result.snippet,
                    'source': result.source
                })

            def _save_cache():
                with self.postgres.get_connection() as conn:
                    with conn.cursor() as cursor:
                        expires_at = datetime.now() + timedelta(hours=ttl_hours)

                        cursor.execute("""
                            INSERT INTO web_search_cache 
                            (query_hash, original_query, results, expires_at)
                            VALUES (%s, %s, %s, %s)
                            ON CONFLICT (query_hash) 
                            DO UPDATE SET 
                                results = EXCLUDED.results,
                                expires_at = EXCLUDED.expires_at,
                                created_at = CURRENT_TIMESTAMP
                        """, (query_hash, query, json.dumps(results_json), expires_at))

                        conn.commit()

            await loop.run_in_executor(None, _save_cache)
            logger.info(f"💾 Cached search results for {ttl_hours} hours")

        except Exception as e:
            logger.warning(f"Failed to cache results: {e}")

    async def _perform_search(self, query: str, num_results: int) -> List[WebSearchResult]:
        """Perform the actual search API call"""
        # Try Serper API first (fastest)
        if os.getenv("SERPER_API_KEY"):
            return await self._search_serper(query, num_results)

        # Try SerpAPI
        elif os.getenv("SERPAPI_API_KEY"):
            return await self._search_serpapi(query, num_results)

        # Try Bing Search API
        elif os.getenv("BING_SEARCH_API_KEY"):
            return await self._search_bing(query, num_results)

        logger.warning("No search API keys available")
        return []

    async def _search_serper(self, query: str, num_results: int) -> List[WebSearchResult]:
        """Search using Serper API (Google Search)"""
        logger.info(f"🔍 Using Serper API for search: {query[:50]}...")

        url = "https://google.serper.dev/search"
        headers = {
            "X-API-KEY": os.getenv("SERPER_API_KEY"),
            "Content-Type": "application/json"
        }
        data = {"q": query, "num": num_results}

        loop = asyncio.get_event_loop()

        def _make_request():
            response = requests.post(
                url, json=data, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()

        response_data = await loop.run_in_executor(None, _make_request)

        results = []
        for item in response_data.get("organic", []):
            results.append(WebSearchResult(
                title=item.get("title", ""),
                link=item.get("link", ""),
                snippet=item.get("snippet", ""),
                source="serper"
            ))

        logger.info(f"✅ Serper API returned {len(results)} results")
        return results

    async def _search_serpapi(self, query: str, num_results: int) -> List[WebSearchResult]:
        """Search using SerpAPI"""
        logger.info(f"🔍 Using SerpAPI for search: {query[:50]}...")

        url = "https://serpapi.com/search"
        params = {
            "q": query,
            "engine": "google",
            "api_key": os.getenv("SERPAPI_API_KEY"),
            "num": num_results
        }

        loop = asyncio.get_event_loop()

        def _make_request():
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()

        response_data = await loop.run_in_executor(None, _make_request)

        results = []
        for item in response_data.get("organic_results", []):
            results.append(WebSearchResult(
                title=item.get("title", ""),
                link=item.get("link", ""),
                snippet=item.get("snippet", ""),
                source="serpapi"
            ))

        logger.info(f"✅ SerpAPI returned {len(results)} results")
        return results

    async def _search_bing(self, query: str, num_results: int) -> List[WebSearchResult]:
        """Search using Bing Search API"""
        logger.info(f"🔍 Using Bing API for search: {query[:50]}...")

        url = "https://api.bing.microsoft.com/v7.0/search"
        headers = {
            "Ocp-Apim-Subscription-Key": os.getenv("BING_SEARCH_API_KEY")
        }
        params = {"q": query, "count": num_results}

        loop = asyncio.get_event_loop()

        def _make_request():
            response = requests.get(
                url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            return response.json()

        response_data = await loop.run_in_executor(None, _make_request)

        results = []
        for item in response_data.get("webPages", {}).get("value", []):
            results.append(WebSearchResult(
                title=item.get("name", ""),
                link=item.get("url", ""),
                snippet=item.get("snippet", ""),
                source="bing"
            ))

        logger.info(f"✅ Bing API returned {len(results)} results")
        return results

    def extract_search_query(self, messages: List[Dict[str, Any]]) -> str:
        """Extract search query from chat messages"""
        if not messages:
            return ""

        # Get all user messages
        user_messages = []
        for msg in messages:
            if isinstance(msg, dict) and msg.get("role") == "user":
                content = msg.get("content", "")
                if isinstance(content, str):
                    user_messages.append(content)

        # Use the last user message as search query
        if user_messages:
            query = user_messages[-1].strip()
            logger.info(f"Extracted search query: {query[:100]}...")
            return query

        # Fallback: use last message content
        last_msg = messages[-1]
        if isinstance(last_msg, dict):
            content = last_msg.get("content", "")
            if isinstance(content, str):
                return content.strip()

        return ""

    def results_to_context_text(self, results: List[WebSearchResult], max_length: int = 4000) -> str:
        """
        Convert search results to context text for direct LLM input
        """
        if not results:
            return ""

        context_parts = []
        total_length = 0

        for i, result in enumerate(results):
            # Format result with source
            result_text = f"[Web Search Result {i+1}]\n"
            result_text += f"Title: {result.title}\n"
            result_text += f"URL: {result.link}\n"
            result_text += f"Content: {result.snippet}\n"
            result_text += f"Source: {result.source}"

            if result.cached:
                result_text += " (cached)"

            # Check length limit
            if total_length + len(result_text) > max_length:
                logger.info(
                    f"Web search context length limit reached: {total_length} chars")
                break

            context_parts.append(result_text)
            total_length += len(result_text)

        context_text = "\n\n".join(context_parts)
        logger.info(
            f"Generated web search context: {len(context_text)} chars from {len(context_parts)} results")
        return context_text

    def health_check(self) -> bool:
        """Check if web search is available"""
        return self.search_enabled


# Create global instance
web_search_processor = WebSearchProcessor()
