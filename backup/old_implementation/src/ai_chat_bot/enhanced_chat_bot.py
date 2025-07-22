"""
Enhanced Chat Bot with GPT-level API endpoints and multi-provider support

This module provides:
- OpenAI-compatible API endpoints
- Multiple LLM provider support (OpenAI, Anthropic, Groq, DeepSeek, etc.)
- Streaming response support
- Rich integration
- File attachment support (images, PDFs)
- Node ID context preservation
"""

import os
import json
import asyncio
import logging
import time
from typing import List, Dict, Any, Optional, AsyncGenerator, Union
from dataclasses import dataclass
from enum import Enum
import base64
import mimetypes
from pathlib import Path
import math

# LlamaIndex imports
from llama_index.core import Document, Settings, StorageContext
from llama_index.core.indices.vector_store import VectorStoreIndex
from llama_index.core.query_engine import RetrieverQueryEngine, CitationQueryEngine
from llama_index.core.retrievers import RouterRetriever
from llama_index.core.selectors import LLMSingleSelector
from llama_index.core.text_splitter import SentenceSplitter
from llama_index.core.tools import RetrieverTool, FunctionTool
from llama_index.core.llms.llm import LLM
from llama_index.core.embeddings import BaseEmbedding
from llama_index.core.callbacks import CallbackManager, TokenCountingHandler
from llama_index.core.schema import NodeWithScore

# Embeddings
from llama_index.embeddings.openai import OpenAIEmbedding

# LLM Providers
from llama_index.llms.openai import OpenAI

# Try importing additional LLM providers
try:
    from llama_index.llms.anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

# Try importing DeepSeek provider
try:
    from llama_index.llms.deepseek import DeepSeek
    DEEPSEEK_AVAILABLE = True
except ImportError:
    DEEPSEEK_AVAILABLE = False

# Try importing OpenAILike for xAI
try:
    from llama_index.llms.openai_like import OpenAILike
    OPENAI_LIKE_AVAILABLE = True
except ImportError:
    OPENAI_LIKE_AVAILABLE = False

try:
    from llama_index.llms.gemini import Gemini
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

# File readers
try:
    from llama_index.readers.file import PDFReader, ImageReader
    FILE_READERS_AVAILABLE = True
except ImportError:
    FILE_READERS_AVAILABLE = False

try:
    from llama_index.multi_modal_llms.openai import OpenAIMultiModal
    MULTIMODAL_AVAILABLE = True
except ImportError:
    MULTIMODAL_AVAILABLE = False

# Web search (we'll implement this)
try:
    import requests
    from bs4 import BeautifulSoup
    WEB_SEARCH_AVAILABLE = True
except ImportError:
    WEB_SEARCH_AVAILABLE = False

from src.utility.postgres import get_embeddings, get_note_text, save_embeddings, get_notes_for_rag
from src.utility.note_utils import (
    create_and_save_embeddings_separate,
    retrieve_embedding,
    get_most_related_notes
)
from src.ai_chat_bot.link_analyzer import analyze_link

logger = logging.getLogger(__name__)


# Embedding functions from legacy chat_bot.py
class LLMProvider(Enum):
    """Supported LLM providers"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    DEEPSEEK = "deepseek"  # Via DeepSeek native API
    XAI = "xai"  # Via OpenAI-compatible API


class MessageRole(Enum):
    """OpenAI-compatible message roles"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"
    TOOL = "tool"


@dataclass
class ChatMessage:
    """OpenAI-compatible chat message"""
    role: str
    content: Union[str, List[Dict[str, Any]]]
    name: Optional[str] = None
    function_call: Optional[Dict[str, Any]] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None


@dataclass
class ChatCompletionRequest:
    """OpenAI-compatible chat completion request"""
    messages: List[ChatMessage]
    model: Optional[str] = None
    provider: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None
    stop: Optional[Union[str, List[str]]] = None
    stream: bool = False

    # Custom parameters
    user_id: Optional[int] = None  # Mandatory for RAG
    folder_ids: Optional[List[int]] = None  # Optional folder filter
    # Optional specific note IDs to include
    note_ids: Optional[List[int]] = None
    # Optional specific conversation IDs to include (empty = all conversations)
    conversation_ids: Optional[List[int]] = None
    enable_rag: bool = True  # Option to disable RAG
    # NEW: Enable deep search with citations (slower)
    enable_citations: bool = False
    enable_web_search: bool = False
    enable_image_analysis: bool = False
    search_query: Optional[str] = None
    attachments: Optional[List[Dict[str, Any]]] = None
    generate_title: bool = False  # Generate a title for the conversation


@dataclass
class Usage:
    """Token usage information"""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


@dataclass
class ChatCompletionResponse:
    """OpenAI-compatible chat completion response"""
    id: str
    object: str
    created: int
    model: str
    provider: str
    choices: List[Dict[str, Any]]
    usage: Optional[Usage] = None

    # Custom fields with citation support
    used_notes: Optional[List[int]] = None  # Kept for backward compatibility
    used_items: Optional[Dict[str, List[int]]
                         ] = None  # New mixed-type tracking
    search_results: Optional[List[Dict[str, Any]]] = None
    # Citation source nodes from LlamaIndex
    citations: Optional[List[Dict[str, Any]]] = None
    # Generated conversation title
    generated_title: Optional[str] = None


class LLMProviderManager:
    """Manages multiple LLM providers and automatic selection"""

    def __init__(self):
        self.providers = {}
        self.token_counter = TokenCountingHandler()
        self._initialize_providers()

    def _initialize_providers(self):
        """Initialize available LLM providers"""

        # Debug: Print which providers are being initialized
        logger.info("=== Provider Initialization Debug ===")
        logger.info(
            f"OPENAI_API_KEY: {'SET' if os.getenv('OPENAI_API_KEY') else 'NOT SET'}")
        logger.info(
            f"ANTHROPIC_API_KEY: {'SET' if os.getenv('ANTHROPIC_API_KEY') else 'NOT SET'}")
        logger.info(
            f"GOOGLE_API_KEY: {'SET' if os.getenv('GOOGLE_API_KEY') else 'NOT SET'}")
        logger.info(
            f"DEEPSEEK_API_KEY: {'SET' if os.getenv('DEEPSEEK_API_KEY') else 'NOT SET'}")
        logger.info(
            f"XAI_API_KEY: {'SET' if os.getenv('XAI_API_KEY') else 'NOT SET'}")
        logger.info("=====================================")

        # OpenAI - using most cost-effective model
        if os.getenv("OPENAI_API_KEY"):
            openai_provider = {
                "llm": OpenAI(
                    model="gpt-4.1-nano",  # Most cost-effective: $0.10/$0.40 per 1M tokens
                    temperature=0.7,
                    callback_manager=CallbackManager([self.token_counter])
                ),
                "models": ["gpt-4.1-nano", "gpt-4.1-nano", "gpt-4o", "gpt-3.5-turbo", "gpt-4-turbo", "gpt-4.1", "gpt-4.1-mini", "o3", "o4-mini"]
            }

            # Add multimodal if available
            if MULTIMODAL_AVAILABLE:
                openai_provider["multimodal"] = OpenAIMultiModal(
                    model="gpt-4.1-nano",  # Use cost-effective model for multimodal too
                    callback_manager=CallbackManager([self.token_counter])
                )

            self.providers[LLMProvider.OPENAI] = openai_provider

        # Anthropic - using most cost-effective model
        if ANTHROPIC_AVAILABLE and os.getenv("ANTHROPIC_API_KEY"):
            self.providers[LLMProvider.ANTHROPIC] = {
                "llm": Anthropic(
                    # Most cost-effective: $0.80/$4.00 per 1M tokens
                    model="claude-3-5-haiku-20241022",
                    temperature=0.7,
                    callback_manager=CallbackManager([self.token_counter])
                ),
                "models": ["claude-3-5-haiku-20241022", "claude-3-5-sonnet-20241022", "claude-3-opus-20240229", "claude-3-sonnet-20240229"]
            }

        # Groq removed by user request

        # Gemini - using most cost-effective model
        if GEMINI_AVAILABLE and os.getenv("GOOGLE_API_KEY"):
            self.providers[LLMProvider.GEMINI] = {
                "llm": Gemini(
                    model="models/gemini-2.0-flash",  # Most cost-effective: $0.10/$0.40 per 1M tokens
                    api_key=os.getenv("GOOGLE_API_KEY"),
                    temperature=0.7,
                    callback_manager=CallbackManager([self.token_counter])
                ),
                "models": ["models/gemini-2.0-flash", "models/gemini-1.5-flash", "models/gemini-1.5-pro", "models/gemini-pro"]
            }

        # DeepSeek (using proper DeepSeek provider)
        if DEEPSEEK_AVAILABLE and os.getenv("DEEPSEEK_API_KEY"):
            self.providers[LLMProvider.DEEPSEEK] = {
                "llm": DeepSeek(
                    model="deepseek-chat",
                    api_key=os.getenv("DEEPSEEK_API_KEY"),
                    temperature=0.7,
                    callback_manager=CallbackManager([self.token_counter])
                ),
                "models": ["deepseek-chat", "deepseek-coder", "deepseek-reasoner"]
            }

        # xAI Grok - using most cost-effective model
        if OPENAI_LIKE_AVAILABLE and os.getenv("XAI_API_KEY"):
            self.providers[LLMProvider.XAI] = {
                "llm": OpenAILike(
                    model="grok-3-mini",  # Most cost-effective: $0.60/$4.00 per 1M tokens
                    api_key=os.getenv("XAI_API_KEY"),
                    api_base="https://api.x.ai/v1",
                    is_chat_model=True,
                    is_function_calling_model=False,
                    context_window=131072,
                    temperature=0.7,
                    callback_manager=CallbackManager([self.token_counter])
                ),
                "models": ["grok-3-mini", "grok-3", "grok-2-vision-1212", "grok-2-image-1212"]
            }

    def get_provider(self, provider_name: Optional[str] = None, model: Optional[str] = None) -> Dict[str, Any]:
        """Get LLM provider by name or auto-select best available"""

        logger.info(
            f"get_provider called with provider_name={provider_name}, model={model}")
        logger.info(
            f"Available providers and models: {self.list_available_providers()}")

        if provider_name:
            provider_enum = LLMProvider(provider_name.lower())
            logger.info(f"Looking for provider: {provider_enum}")
            if provider_enum in self.providers:
                provider_info = self.providers[provider_enum]
                logger.info(f"Found provider {provider_enum}, using its LLM")

                # Update model if specified
                if model and model in provider_info["models"]:
                    if hasattr(provider_info["llm"], "model"):
                        provider_info["llm"].model = model
                        logger.info(f"Updated model to: {model}")

                return {
                    "provider": provider_enum,
                    "llm": provider_info["llm"],
                    "multimodal": provider_info.get("multimodal"),
                    "models": provider_info["models"]
                }
            else:
                logger.warning(
                    f"Provider {provider_enum} not found in available providers")

        # If model is specified but no provider, try to find the right provider for the model
        if model and not provider_name:
            logger.info(f"Attempting to find a provider for model: {model}")

            # First, try exact match
            for provider_enum, provider_info in self.providers.items():
                if model in provider_info["models"]:
                    logger.info(
                        f"Found provider {provider_enum.value} supporting model {model}")
                    # Create a copy of the provider info and update the model
                    if hasattr(provider_info["llm"], "model"):
                        provider_info["llm"].model = model
                        logger.info(f"Updated model to: {model}")

                    return {
                        "provider": provider_enum,
                        "llm": provider_info["llm"],
                        "multimodal": provider_info.get("multimodal"),
                        "models": provider_info["models"]
                    }

            # If no exact match, try fuzzy matching for similar models
            logger.info(
                f"No exact match found for model {model}, trying fuzzy matching...")
            model_lower = model.lower()

            for provider_enum, provider_info in self.providers.items():
                for available_model in provider_info["models"]:
                    available_model_lower = available_model.lower()

                    # Check if the requested model name contains key components of available models
                    if any(keyword in model_lower for keyword in ["claude", "sonnet", "opus", "haiku"]) and \
                       any(keyword in available_model_lower for keyword in ["claude", "sonnet", "opus", "haiku"]):

                        # For Claude models, match the family
                        if "claude" in model_lower and "claude" in available_model_lower:
                            if ("sonnet" in model_lower and "sonnet" in available_model_lower) or \
                               ("opus" in model_lower and "opus" in available_model_lower) or \
                               ("haiku" in model_lower and "haiku" in available_model_lower):

                                logger.info(
                                    f"Found similar model: {available_model} for requested {model} in provider {provider_enum.value}")

                                if hasattr(provider_info["llm"], "model"):
                                    provider_info["llm"].model = available_model
                                    logger.info(
                                        f"Updated model to: {available_model}")

                                return {
                                    "provider": provider_enum,
                                    "llm": provider_info["llm"],
                                    "multimodal": provider_info.get("multimodal"),
                                    "models": provider_info["models"]
                                }

                    # For other models, do partial matching
                    elif model_lower in available_model_lower or available_model_lower in model_lower:
                        logger.info(
                            f"Found similar model: {available_model} for requested {model} in provider {provider_enum.value}")

                        if hasattr(provider_info["llm"], "model"):
                            provider_info["llm"].model = available_model
                            logger.info(f"Updated model to: {available_model}")

                        return {
                            "provider": provider_enum,
                            "llm": provider_info["llm"],
                            "multimodal": provider_info.get("multimodal"),
                            "models": provider_info["models"]
                        }

            logger.warning(
                f"No provider found supporting model {model}. Falling back to default provider selection.")

        # Auto-select best available provider (default priority)
        # Priority: OpenAI > Anthropic > Gemini > DeepSeek > xAI
        logger.info(
            "Auto-selecting default provider (highest priority available)...")
        for provider in [LLMProvider.OPENAI, LLMProvider.ANTHROPIC, LLMProvider.GEMINI,
                         LLMProvider.DEEPSEEK, LLMProvider.XAI]:
            if provider in self.providers:
                provider_info = self.providers[provider]
                logger.info(
                    f"Auto-selected provider: {provider.value} with model {provider_info['llm'].model}")
                return {
                    "provider": provider,
                    "llm": provider_info["llm"],
                    "multimodal": provider_info.get("multimodal"),
                    "models": provider_info["models"]
                }

        raise ValueError("No LLM providers available. Please set API keys.")

    def list_available_providers(self) -> Dict[str, List[str]]:
        """List all available providers and their models"""
        return {
            provider.value: info["models"]
            for provider, info in self.providers.items()
        }


class WebSearchTool:
    """Web search integration tool with intelligent caching"""

    def __init__(self):
        self.search_enabled = WEB_SEARCH_AVAILABLE and (
            os.getenv("SERPER_API_KEY") or
            os.getenv("SERPAPI_API_KEY") or
            os.getenv("BING_SEARCH_API_KEY")
        )

        # Initialize cache table
        try:
            from src.utility.postgres import create_search_cache_table
            create_search_cache_table()
        except Exception as e:
            logger.warning(f"Failed to initialize search cache: {e}")

    def _get_query_hash(self, query: str) -> str:
        """Generate hash for query caching"""
        import hashlib
        # Normalize query for better cache hits
        normalized_query = query.lower().strip()
        return hashlib.sha256(normalized_query.encode()).hexdigest()[:32]

    def _get_cache_ttl(self, query: str) -> int:
        """Get cache TTL based on query type"""
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

    async def search(self, query: str, num_results: int = 5) -> List[Dict[str, Any]]:
        """Perform web search with intelligent caching"""
        if not self.search_enabled:
            return []

        try:
            # Check cache first
            query_hash = self._get_query_hash(query)

            try:
                from src.utility.postgres import get_cached_search_results
                cached_result = get_cached_search_results(query_hash)

                if cached_result:
                    logger.info(f"Cache hit for query: {query[:50]}...")
                    results = cached_result['results']
                    # Add cache metadata to results
                    for result in results:
                        result['cached'] = True
                        result['cache_age'] = str(cached_result['created_at'])
                    return results

            except Exception as e:
                logger.warning(f"Cache lookup failed: {e}")

            # Cache miss - perform actual search
            logger.info(f"Cache miss for query: {query[:50]}...")
            results = await self._perform_search(query, num_results)

            # Cache the results
            if results:
                try:
                    from src.utility.postgres import save_search_cache
                    ttl = self._get_cache_ttl(query)
                    save_search_cache(query_hash, query, results, ttl)
                    logger.info(f"Cached search results for {ttl} hours")
                except Exception as e:
                    logger.warning(f"Failed to cache results: {e}")

            # Add cache metadata
            for result in results:
                result['cached'] = False

            return results

        except Exception as e:
            logger.error(f"Web search failed: {e}")
            return []

    async def _perform_search(self, query: str, num_results: int) -> List[Dict[str, Any]]:
        """Perform the actual search API call"""
        # Use Serper API if available
        if os.getenv("SERPER_API_KEY"):
            return await self._search_serper(query, num_results)

        # Use SerpAPI if available
        elif os.getenv("SERPAPI_API_KEY"):
            return await self._search_serpapi(query, num_results)

        # Use Bing Search API if available
        elif os.getenv("BING_SEARCH_API_KEY"):
            return await self._search_bing(query, num_results)

        return []

    async def _search_serper(self, query: str, num_results: int) -> List[Dict[str, Any]]:
        """Search using Serper API"""
        url = "https://google.serper.dev/search"
        headers = {
            "X-API-KEY": os.getenv("SERPER_API_KEY"),
            "Content-Type": "application/json"
        }
        data = {"q": query, "num": num_results}

        response = requests.post(url, json=data, headers=headers, timeout=10)
        response.raise_for_status()

        results = []
        data = response.json()

        for item in data.get("organic", []):
            results.append({
                "title": item.get("title", ""),
                "link": item.get("link", ""),
                "snippet": item.get("snippet", ""),
                "source": "serper"
            })

        return results

    async def _search_serpapi(self, query: str, num_results: int) -> List[Dict[str, Any]]:
        """Search using SerpAPI"""
        url = "https://serpapi.com/search"
        params = {
            "q": query,
            "engine": "google",
            "api_key": os.getenv("SERPAPI_API_KEY"),
            "num": num_results
        }

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()

        results = []
        data = response.json()

        for item in data.get("organic_results", []):
            results.append({
                "title": item.get("title", ""),
                "link": item.get("link", ""),
                "snippet": item.get("snippet", ""),
                "source": "serpapi"
            })

        return results

    async def _search_bing(self, query: str, num_results: int) -> List[Dict[str, Any]]:
        """Search using Bing Search API"""
        url = "https://api.bing.microsoft.com/v7.0/search"
        headers = {
            "Ocp-Apim-Subscription-Key": os.getenv("BING_SEARCH_API_KEY")}
        params = {"q": query, "count": num_results}

        response = requests.get(url, headers=headers,
                                params=params, timeout=10)
        response.raise_for_status()

        results = []
        data = response.json()

        for item in data.get("webPages", {}).get("value", []):
            results.append({
                "title": item.get("name", ""),
                "link": item.get("url", ""),
                "snippet": item.get("snippet", ""),
                "source": "bing"
            })

        return results


class FileAttachmentProcessor:
    """Process file attachments (images, PDFs)"""

    def __init__(self):
        self.supported_types = {}

        if FILE_READERS_AVAILABLE:
            self.pdf_reader = PDFReader()
            self.image_reader = ImageReader()
            self.supported_types = {
                'application/pdf': self._process_pdf,
                'image/jpeg': self._process_image,
                'image/png': self._process_image,
                'image/gif': self._process_image,
                'image/webp': self._process_image
            }
        else:
            logger.warning(
                "File readers not available. Install llama-index-readers-file for file attachment support.")

    async def process_attachments(self, attachments: List[Dict[str, Any]]) -> List[Document]:
        """Process file attachments and return documents"""
        if not FILE_READERS_AVAILABLE:
            logger.warning("File attachment processing not available")
            return []

        documents = []

        for attachment in attachments:
            try:
                doc = await self._process_single_attachment(attachment)
                if doc:
                    documents.extend(doc)
            except Exception as e:
                logger.error(f"Failed to process attachment: {e}")
                continue

        return documents

    async def _process_single_attachment(self, attachment: Dict[str, Any]) -> List[Document]:
        """Process a single attachment - supports both base64 content and URLs"""
        file_type = attachment.get('type') or attachment.get('mime_type')
        content = attachment.get('content')  # base64 encoded content
        url = attachment.get('url')  # S3 URL or other accessible URL
        filename = attachment.get('filename', 'attachment')

        if not file_type:
            return []

        # Handle URL-based attachments (recommended for production)
        if url:
            try:
                import requests
                response = requests.get(url, timeout=30)
                response.raise_for_status()
                file_data = response.content
            except Exception as e:
                logger.error(f"Failed to download file from URL {url}: {e}")
                return []

        # Handle base64-encoded content (for direct uploads)
        elif content:
            try:
                file_data = base64.b64decode(content)
            except Exception as e:
                logger.error(f"Failed to decode base64 content: {e}")
                return []
        else:
            logger.error("No content or URL provided for attachment")
            return []

        # Create temporary file
        temp_path = f"/tmp/{filename}"
        with open(temp_path, 'wb') as f:
            f.write(file_data)

        try:
            if file_type in self.supported_types:
                return await self.supported_types[file_type](temp_path, filename)
            else:
                logger.warning(f"Unsupported file type: {file_type}")
                return []
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_path)
            except:
                pass

    async def _process_pdf(self, file_path: str, filename: str) -> List[Document]:
        """Process PDF file"""
        try:
            documents = self.pdf_reader.load_data(file=Path(file_path))
            for doc in documents:
                doc.metadata.update({
                    'filename': filename,
                    'file_type': 'pdf',
                    'source': 'attachment'
                })
            return documents
        except Exception as e:
            logger.error(f"Failed to process PDF {filename}: {e}")
            return []

    async def _process_image(self, file_path: str, filename: str) -> List[Document]:
        """Process image file"""
        try:
            documents = self.image_reader.load_data(file=Path(file_path))
            for doc in documents:
                doc.metadata.update({
                    'filename': filename,
                    'file_type': 'image',
                    'source': 'attachment'
                })
            return documents
        except Exception as e:
            logger.error(f"Failed to process image {filename}: {e}")
            return []


class EnhancedChatBot:
    """Enhanced chat bot with GPT-level API and multi-provider support"""

    def __init__(self):
        self.provider_manager = LLMProviderManager()
        self.web_search = WebSearchTool()
        self.file_processor = FileAttachmentProcessor()
        self.embedder = OpenAIEmbedding(model="text-embedding-3-small")

        # Configure global settings
        Settings.embed_model = self.embedder

    def _extract_citations_from_response(self, response) -> List[Dict[str, Any]]:
        """Extract citation information from LlamaIndex CitationQueryEngine response"""
        citations = []

        logger.info(f"=== CITATION EXTRACTION DEBUG ===")
        logger.info(f"Response type: {type(response)}")
        logger.info(f"Has source_nodes: {hasattr(response, 'source_nodes')}")

        if hasattr(response, 'source_nodes') and response.source_nodes:
            logger.info(
                f"Extracting citations from {len(response.source_nodes)} source nodes")

            node_types = {}
            for source_node in response.source_nodes:
                metadata = source_node.node.metadata
                node_type = metadata.get('type', 'unknown')
                node_types[node_type] = node_types.get(node_type, 0) + 1

            logger.info(f"Source node types: {node_types}")

            for i, source_node in enumerate(response.source_nodes):
                metadata = source_node.node.metadata
                logger.info(f"Processing source node {i+1}:")
                logger.info(f"  - Type: {metadata.get('type', 'unknown')}")
                logger.info(f"  - Source: {metadata.get('source', 'unknown')}")
                logger.info(
                    f"  - Web search result: {metadata.get('web_search_result', False)}")
                logger.info(
                    f"  - Title: {metadata.get('title', 'No title')[:50]}")

                # Determine citation type and format based on metadata
                if metadata.get('type') == 'web_search' or metadata.get('web_search_result'):
                    # Web search citation
                    citation = {
                        "id": i + 1,
                        "title": metadata.get('title', 'Web Search Result'),
                        "url": metadata.get('url', ''),
                        "type": "web",
                        "snippet": source_node.node.get_text()[:200],
                        "content": source_node.node.get_text(),
                        "score": source_node.score if hasattr(source_node, 'score') else None,
                        "metadata": metadata
                    }
                    logger.info(
                        f"✅ Created web citation: {citation['title'][:50]}")
                elif metadata.get('source') == 'user_note' or metadata.get('note_id'):
                    # Note chunk citation
                    citation = {
                        "id": i + 1,
                        "title": f"Note {metadata.get('note_id', 'Unknown')} (Chunk {metadata.get('chunk_index', 0)})",
                        "nodeId": metadata.get('note_id'),
                        "type": "note",
                        "snippet": source_node.node.get_text()[:200],
                        "content": source_node.node.get_text(),
                        "score": source_node.score if hasattr(source_node, 'score') else None,
                        "metadata": metadata
                    }
                    logger.info(
                        f"✅ Created note citation: {citation['title']}")
                else:
                    # Generic citation (fallback)
                    citation = {
                        "id": i + 1,
                        "title": metadata.get('title', f'Source {i + 1}'),
                        "type": metadata.get('type', 'unknown'),
                        "content": source_node.node.get_text(),
                        "score": source_node.score if hasattr(source_node, 'score') else None,
                        "metadata": metadata,
                        "node_id": source_node.node.node_id
                    }
                    logger.info(
                        f"✅ Created generic citation: {citation['title'][:50]}")
                citations.append(citation)
        else:
            logger.warning(
                "No source nodes found in response - no citations to extract")

        logger.info(f"Final citation summary:")
        citation_types = {}
        for citation in citations:
            ctype = citation.get('type', 'unknown')
            citation_types[ctype] = citation_types.get(ctype, 0) + 1
        logger.info(f"  - Citation types: {citation_types}")
        logger.info(f"  - Total citations: {len(citations)}")
        logger.info(f"=== END CITATION EXTRACTION DEBUG ===")

        return citations

    async def _generate_conversation_title(self, messages: List[ChatMessage], llm) -> Optional[str]:
        """Generate a concise title for the conversation (max 5 words, ~20 chars)"""
        try:
            # Extract key context from conversation - use only first few and last message
            context_messages = []

            # Get first user message for initial context
            first_user_msg = None
            for msg in messages:
                if msg.role == "user":
                    first_user_msg = msg
                    break

            # Get last user message for current context
            last_user_msg = None
            for msg in reversed(messages):
                if msg.role == "user":
                    last_user_msg = msg
                    break

            # Build lightweight context (avoid full conversation)
            if first_user_msg and last_user_msg and first_user_msg != last_user_msg:
                # Multi-turn conversation
                first_content = self._extract_message_text(first_user_msg)[
                    :100]
                last_content = self._extract_message_text(last_user_msg)[:100]
                context = f"Initial: {first_content}\nRecent: {last_content}"
            elif last_user_msg:
                # Single turn or same message
                context = self._extract_message_text(last_user_msg)[:150]
            else:
                return None

            # Create title generation prompt - very specific for brevity
            title_prompt = f"""Generate a very concise conversation title based on this context:

{context}

Requirements:
- Maximum 5 words
- Maximum 20 characters
- No punctuation
- Capture the main topic/intent
- Be specific, not generic

Examples:
- "AI Trends 2024"
- "Python Error Fix"
- "Recipe Ideas"
- "Travel Planning"

Title:"""

            # Use low temperature for consistent, focused titles
            original_temp = getattr(llm, 'temperature', 0.7)
            llm.temperature = 0.1  # Very focused generation

            try:
                response = await llm.acomplete(title_prompt)
                title = str(response).strip()

                # Clean up the title
                title = title.replace('"', '').replace("'", "").strip()

                # Ensure it meets requirements
                words = title.split()
                if len(words) > 5:
                    title = " ".join(words[:5])

                if len(title) > 20:
                    title = title[:20].strip()

                # Restore original temperature
                llm.temperature = original_temp

                logger.info(f"Generated conversation title: '{title}'")
                return title if title else None

            except Exception as e:
                # Restore temperature on error
                llm.temperature = original_temp
                raise e

        except Exception as e:
            logger.error(f"Failed to generate conversation title: {e}")
            return None

    def _extract_message_text(self, message: ChatMessage) -> str:
        """Extract text content from a message (handles both string and multimodal)"""
        if isinstance(message.content, str):
            return message.content
        elif isinstance(message.content, list):
            # Handle multimodal content, extract text parts
            text_parts = []
            for item in message.content:
                if item.get("type") == "text":
                    text_parts.append(item.get("text", ""))
            return " ".join(text_parts)
        return ""

    async def chat_completion(self, request: ChatCompletionRequest) -> Union[ChatCompletionResponse, AsyncGenerator]:
        """Main chat completion endpoint with two-tier search system"""

        # Validate user ID - always required for verification purposes
        if not request.user_id:
            raise ValueError(
                "user_id is always required for verification purposes")

        # Get provider and LLM
        provider_info = self.provider_manager.get_provider(
            request.provider,
            request.model
        )
        llm = provider_info["llm"]

        # Configure LLM settings
        if request.temperature is not None:
            llm.temperature = request.temperature
        if request.max_tokens is not None:
            llm.max_tokens = request.max_tokens

        Settings.llm = llm

        # TWO-TIER SYSTEM DECISION
        # Citations are ONLY enabled when explicitly requested by the user
        # We DO NOT auto-enable citations for web search to avoid unnecessary re-embedding
        logger.info(
            f"Citations explicitly requested: {request.enable_citations}")
        logger.info(f"Web search enabled: {request.enable_web_search}")
        logger.info(f"RAG enabled: {request.enable_rag}")

        # If RAG is enabled but citations are NOT requested, use fast search
        if request.enable_rag and not request.enable_citations:
            logger.info("Using FAST RAG search (no re-embedding)")
            return await self._fast_rag_search(request, llm)

        # Otherwise, use the full citation engine (slower but with citations)
        if request.enable_citations:
            logger.info(
                "Using DEEP search with CitationQueryEngine (with re-embedding)")
        else:
            logger.info(
                "Using SIMPLE context without CitationQueryEngine")

        # For streaming, gather context first then stream
        if request.stream:
            # Gather context from various sources (same as non-streaming)
            context_documents = []
            used_notes = []
            search_results = []

            # 1. Process RAG if enabled
            if request.enable_rag and request.user_id:
                note_docs, used_notes = await self._get_user_note_context(
                    request.messages,
                    request.user_id,
                    request.folder_ids,
                    request.note_ids,
                    request.conversation_ids
                )
                context_documents.extend(note_docs)

            # 2. Process web search if enabled
            if request.enable_web_search:
                search_results = await self._perform_web_search(request.messages[-1]["content"])

            # 3. Process file attachments if provided
            if request.attachments:
                attachment_docs = await self.file_processor.process_attachments(request.attachments)
                context_documents.extend(attachment_docs)

            # Build query engine only if we have context AND citations are enabled
            query_engine = None
            if context_documents and request.enable_citations:
                logger.info(
                    f"Building CitationQueryEngine with {len(context_documents)} documents (WILL CAUSE RE-EMBEDDING)")
                query_engine = await self._build_query_engine(context_documents, llm)
            elif context_documents and not request.enable_citations:
                logger.info(
                    f"Skipping CitationQueryEngine creation - using simple context injection ({len(context_documents)} documents)")
                query_engine = None

            # Stream the response
            return self._stream_response(request, query_engine, provider_info, used_notes, search_results, context_documents)

        # Non-streaming path for citation mode
        # Gather context from various sources
        context_documents = []
        used_notes = []
        search_results = []

        # 1. Process RAG if enabled
        if request.enable_rag and request.user_id:
            note_docs, used_notes = await self._get_user_note_context(
                request.messages,
                request.user_id,
                request.folder_ids,
                request.note_ids,
                request.conversation_ids
            )
            context_documents.extend(note_docs)

        # 2. Process web search if enabled
        if request.enable_web_search:
            logger.info(f"=== WEB SEARCH DEBUG ===")
            logger.info(f"Web search enabled: {request.enable_web_search}")
            logger.info(
                f"Web search tool enabled: {self.web_search.search_enabled}")

            search_query = request.search_query or self._extract_search_query(
                request.messages)
            logger.info(f"Extracted search query: {search_query}")

            if search_query:
                logger.info(f"Performing web search for: {search_query}")
                search_results = await self.web_search.search(search_query)
                logger.info(f"Web search results count: {len(search_results)}")

                if search_results:
                    logger.info("Sample search results:")
                    for i, result in enumerate(search_results[:2]):
                        logger.info(
                            f"  Result {i+1}: {result.get('title', 'No title')[:100]}")

                search_docs = self._create_search_documents(search_results)
                logger.info(f"Created {len(search_docs)} search documents")
                context_documents.extend(search_docs)
            else:
                logger.warning("No search query extracted from messages")
            logger.info(f"=== END WEB SEARCH DEBUG ===")
        else:
            logger.info("Web search disabled or not requested")

        # 3. Process file attachments if provided
        if request.attachments:
            attachment_docs = await self.file_processor.process_attachments(request.attachments)
            context_documents.extend(attachment_docs)

        # Build query engine only if we have context AND citations are enabled
        query_engine = None
        if context_documents and request.enable_citations:
            logger.info(
                f"Building CitationQueryEngine with {len(context_documents)} documents (WILL CAUSE RE-EMBEDDING)")
            query_engine = await self._build_query_engine(context_documents, llm)
        elif context_documents and not request.enable_citations:
            logger.info(
                f"Skipping CitationQueryEngine creation - using simple context injection ({len(context_documents)} documents)")
            query_engine = None

        # Generate response
        return await self._generate_response(request, query_engine, provider_info, used_notes, search_results, context_documents)

    async def _stream_response(self, request: ChatCompletionRequest, query_engine: Optional[RetrieverQueryEngine],
                               provider_info: Dict, used_notes: List[int],
                               search_results: List[Dict], context_documents: List = None) -> AsyncGenerator:
        """Generate streaming response"""
        try:
            # Yield initial status
            yield {
                "id": f"chatcmpl-{os.urandom(8).hex()}",
                "object": "chat.completion.chunk",
                "created": int(asyncio.get_event_loop().time()),
                "model": request.model or "auto",
                "provider": provider_info["provider"].value,
                "choices": [{
                    "index": 0,
                    "delta": {},
                    "finish_reason": None
                }],
                "progress": {
                    "stage": "initializing",
                    "message": "Starting search process"
                }
            }

            context_documents = context_documents or []
            used_notes = used_notes or []
            search_results = search_results or []

            # Now yield the actual response generation status
            yield {
                "id": f"chatcmpl-{os.urandom(8).hex()}",
                "object": "chat.completion.chunk",
                "created": int(asyncio.get_event_loop().time()),
                "model": request.model or "auto",
                "provider": provider_info["provider"].value,
                "choices": [{
                    "index": 0,
                    "delta": {
                        "role": "assistant",
                        "content": ""
                    },
                    "finish_reason": None
                }],
                "progress": {
                    "stage": "generating_response",
                    "message": "Generating response..."
                }
            }

            # Stream the actual response
            async for chunk in self._stream_llm_response(request, query_engine, provider_info, used_notes, search_results, context_documents):
                yield chunk

        except Exception as e:
            logger.error(f"Error in streaming: {e}")
            yield {
                "id": f"chatcmpl-{os.urandom(8).hex()}",
                "object": "chat.completion.chunk",
                "created": int(asyncio.get_event_loop().time()),
                "model": request.model or "auto",
                "provider": provider_info["provider"].value,
                "choices": [{
                    "index": 0,
                    "delta": {},
                    "finish_reason": "error"
                }],
                "error": str(e)
            }

    async def _stream_llm_response(self, request: ChatCompletionRequest, query_engine: Optional[CitationQueryEngine],
                                   provider_info: Dict, used_notes: List[int],
                                   search_results: List[Dict], context_documents: Optional[List[Document]] = None) -> AsyncGenerator:
        """Stream the actual LLM response with proper RAG integration"""

        # Convert messages to query
        query = self._messages_to_query(request.messages)

        logger.info(f"=== STREAMING RAG DEBUG ===")
        logger.info(f"Original query: {query}")

        llm = provider_info["llm"]
        rag_response = None  # Initialize at method scope

        if query_engine:
            logger.info(f"Using streaming RAG with {len(used_notes)} notes")

            # Yield progress: Starting RAG processing
            yield {
                "id": f"chatcmpl-{os.urandom(8).hex()}",
                "object": "chat.completion.chunk",
                "created": int(asyncio.get_event_loop().time()),
                "model": request.model or "auto",
                "provider": provider_info["provider"].value,
                "choices": [{
                    "index": 0,
                    "delta": {},
                    "finish_reason": None
                }],
                "progress": {
                    "stage": "rag_processing",
                    "message": f"Processing RAG query with {len(used_notes)} notes",
                    "note_count": len(used_notes),
                    "used_notes": used_notes
                }
            }

            # First, get the RAG response (this includes context injection)
            try:
                rag_response = query_engine.query(query)
                rag_answer = str(rag_response)

                # Log the RAG processing details
                if hasattr(rag_response, 'source_nodes'):
                    source_count = len(rag_response.source_nodes)
                    logger.info(f"RAG retrieved {source_count} source chunks")

                    # Yield progress: RAG context retrieved
                    yield {
                        "id": f"chatcmpl-{os.urandom(8).hex()}",
                        "object": "chat.completion.chunk",
                        "created": int(asyncio.get_event_loop().time()),
                        "model": request.model or "auto",
                        "provider": provider_info["provider"].value,
                        "choices": [{
                            "index": 0,
                            "delta": {},
                            "finish_reason": None
                        }],
                        "progress": {
                            "stage": "rag_context_retrieved",
                            "message": f"Retrieved {source_count} relevant text chunks",
                            "source_chunks": source_count,
                            "used_notes": used_notes
                        }
                    }

                logger.info(f"RAG complete response: {rag_answer[:500]}...")

                # Yield progress: Starting LLM generation
                yield {
                    "id": f"chatcmpl-{os.urandom(8).hex()}",
                    "object": "chat.completion.chunk",
                    "created": int(asyncio.get_event_loop().time()),
                    "model": request.model or "auto",
                    "provider": provider_info["provider"].value,
                    "choices": [{
                        "index": 0,
                        "delta": {},
                        "finish_reason": None
                    }],
                    "progress": {
                        "stage": "llm_generation_start",
                        "message": "Starting AI response generation with context"
                    }
                }

                # For streaming, we need to be careful not to duplicate context
                # CitationQueryEngine already includes context in its response

                # Check if this is a citation query engine (already has context) or if we need to manually add context
                if hasattr(query_engine, '_retriever') and hasattr(query_engine, '_response_synthesizer'):
                    # This is a CitationQueryEngine - the response already contains proper context
                    # We should stream the response as-is without adding more context
                    logger.info(
                        "Using CitationQueryEngine response directly (no manual context needed)")
                    logger.info(
                        "⚠️  NOT building contextualized query - would cause duplicate context")
                    response_gen = llm.stream_complete(rag_answer)
                else:
                    # Manual context building needed (for non-citation query engines)
                    logger.info(
                        "Building contextualized query for non-citation query engine")
                    contextualized_query = await self._build_contextualized_query(query, rag_response)
                    logger.info(
                        f"Contextualized query: {contextualized_query[:1000]}...")
                    response_gen = llm.stream_complete(contextualized_query)

            except Exception as e:
                logger.error(f"RAG processing failed: {e}")
                # Fall back to direct LLM streaming
                yield {
                    "id": f"chatcmpl-{os.urandom(8).hex()}",
                    "object": "chat.completion.chunk",
                    "created": int(asyncio.get_event_loop().time()),
                    "model": request.model or "auto",
                    "provider": provider_info["provider"].value,
                    "choices": [{
                        "index": 0,
                        "delta": {},
                        "finish_reason": None
                    }],
                    "progress": {
                        "stage": "rag_failed",
                        "message": f"RAG failed, falling back to direct LLM: {str(e)}"
                    }
                }
                response_gen = llm.stream_complete(query)

        else:
            # No query engine - either no RAG or simple context injection mode
            if context_documents:
                logger.info(
                    f"Using simple context injection with {len(context_documents)} documents (no re-embedding)")
                # Yield progress: Context processing
                yield {
                    "id": f"chatcmpl-{os.urandom(8).hex()}",
                    "object": "chat.completion.chunk",
                    "created": int(asyncio.get_event_loop().time()),
                    "model": request.model or "auto",
                    "provider": provider_info["provider"].value,
                    "choices": [{
                        "index": 0,
                        "delta": {},
                        "finish_reason": None
                    }],
                    "progress": {
                        "stage": "context_injection",
                        "message": f"Injecting context from {len(context_documents)} documents",
                        "document_count": len(context_documents)
                    }
                }

                # Build contextualized query without re-embedding
                contextualized_query = await self._build_contextualized_query_from_documents(query, context_documents)
                logger.info(
                    f"Context injection complete: {len(contextualized_query)} characters")

                # Yield progress: Starting LLM generation with context
                yield {
                    "id": f"chatcmpl-{os.urandom(8).hex()}",
                    "object": "chat.completion.chunk",
                    "created": int(asyncio.get_event_loop().time()),
                    "model": request.model or "auto",
                    "provider": provider_info["provider"].value,
                    "choices": [{
                        "index": 0,
                        "delta": {},
                        "finish_reason": None
                    }],
                    "progress": {
                        "stage": "llm_generation_with_context",
                        "message": "Starting AI response generation with injected context"
                    }
                }

                response_gen = llm.stream_complete(contextualized_query)
            else:
                logger.info("Using direct LLM streaming (no RAG, no context)")
                # Yield progress: Direct LLM call
                yield {
                    "id": f"chatcmpl-{os.urandom(8).hex()}",
                    "object": "chat.completion.chunk",
                    "created": int(asyncio.get_event_loop().time()),
                    "model": request.model or "auto",
                    "provider": provider_info["provider"].value,
                    "choices": [{
                        "index": 0,
                        "delta": {},
                        "finish_reason": None
                    }],
                    "progress": {
                        "stage": "direct_llm",
                        "message": "No RAG context available, using direct LLM"
                    }
                }
                response_gen = llm.stream_complete(query)

        # Stream the actual LLM response
        chunk_count = 0
        for chunk in response_gen:
            chunk_count += 1
            yield {
                "id": f"chatcmpl-{os.urandom(8).hex()}",
                "object": "chat.completion.chunk",
                "created": int(asyncio.get_event_loop().time()),
                "model": request.model or "auto",
                "provider": provider_info["provider"].value,
                "choices": [{
                    "index": 0,
                    "delta": {
                        "content": str(chunk.delta) if hasattr(chunk, 'delta') else str(chunk)
                    },
                    "finish_reason": None
                }]
            }
            # Yield control to event loop
            await asyncio.sleep(0)

        logger.info(f"Streamed {chunk_count} chunks")

        # Extract citations for final chunk metadata
        citations = []
        if rag_response and hasattr(rag_response, 'source_nodes') and rag_response.source_nodes:
            citations = self._extract_citations_from_response(rag_response)

        # Generate conversation title if requested
        generated_title = None
        if request.generate_title:
            try:
                # Use the LLM from provider_info
                llm = provider_info["llm"]
                generated_title = await self._generate_conversation_title(request.messages, llm)
            except Exception as e:
                logger.error(f"Failed to generate title in streaming: {e}")

        # Final chunk with citations metadata
        yield {
            "id": f"chatcmpl-{os.urandom(8).hex()}",
            "object": "chat.completion.chunk",
            "created": int(asyncio.get_event_loop().time()),
            "model": request.model or "auto",
            "provider": provider_info["provider"].value,
            "choices": [{
                "index": 0,
                "delta": {},
                "finish_reason": "stop"
            }],
            "metadata": {
                "used_notes": used_notes if used_notes else None,
                "search_results": search_results if search_results else None,
                "citations": citations if citations else None,
                "generated_title": generated_title
            }
        }

    async def _fast_rag_search(self, request: ChatCompletionRequest, llm: LLM) -> Union[ChatCompletionResponse, AsyncGenerator]:
        """Fast RAG search using pre-computed embeddings (no re-embedding)"""

        # Get query from messages - only use USER messages for search
        user_messages = [
            msg.content for msg in request.messages if msg.role == "user"]
        query = " ".join(user_messages) if user_messages else self._messages_to_query(
            request.messages)

        logger.info(f"=== FAST RAG QUERY EXTRACTION ===")
        logger.info(f"Original conversation: {len(request.messages)} messages")
        logger.info(f"User messages: {user_messages}")
        logger.info(f"Search query: {query}")
        logger.info("==================================")

        # Get note IDs for RAG
        note_ids = get_notes_for_rag(
            request.user_id,
            request.folder_ids,
            request.note_ids
        )

        if not note_ids:
            # No notes available, just use LLM directly
            messages_text = self._messages_to_query(request.messages)

            if request.stream:
                # Return streaming generator for no-context case
                async def generate_no_context():
                    response_stream = await llm.astream_complete(messages_text)
                    async for chunk in response_stream:
                        yield {
                            "id": f"chatcmpl-{os.urandom(8).hex()}",
                            "object": "chat.completion.chunk",
                            "created": int(time.time()),
                            "model": request.model or "unknown",
                            "provider": llm.__class__.__name__.lower(),
                            "choices": [{
                                "index": 0,
                                "delta": {"content": str(chunk.delta)},
                                "finish_reason": None
                            }]
                        }
                    # Generate title if requested
                    generated_title = None
                    if request.generate_title:
                        try:
                            generated_title = await self._generate_conversation_title(request.messages, llm)
                        except Exception as e:
                            logger.error(
                                f"Failed to generate title in no-context streaming: {e}")

                    # Final chunk
                    yield {
                        "id": f"chatcmpl-{os.urandom(8).hex()}",
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": request.model or "unknown",
                        "provider": llm.__class__.__name__.lower(),
                        "choices": [{
                            "index": 0,
                            "delta": {},
                            "finish_reason": "stop"
                        }],
                        "generated_title": generated_title
                    }
                return generate_no_context()
            else:
                # Non-streaming response
                response_text = await llm.acomplete(messages_text)

                # Generate conversation title if requested
                generated_title = None
                if request.generate_title:
                    generated_title = await self._generate_conversation_title(request.messages, llm)

                return ChatCompletionResponse(
                    id=f"chatcmpl-{os.urandom(8).hex()}",
                    object="chat.completion",
                    created=int(time.time()),
                    model=request.model or "unknown",
                    provider=llm.__class__.__name__.lower(),
                    choices=[{
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": str(response_text)
                        },
                        "finish_reason": "stop"
                    }],
                    used_notes=[],
                    search_results=[],
                    citations=None,
                    generated_title=generated_title
                )

        # Use mixed-type RAG search for comprehensive context from notes, conversations, and file attachments
        mixed_documents, context_info = await self._get_mixed_context(
            request.messages, request.user_id, request.folder_ids, request.note_ids, request.conversation_ids)

        logger.info(f"=== FAST RAG CONTEXT DEBUG ===")
        logger.info(f"Query: {query}")
        logger.info(
            f"Found {len(mixed_documents)} relevant chunks from mixed sources:")
        logger.info(f"  - {len(context_info.get('used_notes', []))} notes")
        logger.info(
            f"  - {len(context_info.get('used_conversations', []))} conversations")
        logger.info(
            f"  - {len(context_info.get('used_attachments', []))} file attachments")

        # Build context from the most relevant chunks
        context_texts = []
        total_context_length = 0
        max_context_length = 8000  # Keep context reasonable for fast response

        for doc in mixed_documents:
            if total_context_length > max_context_length:
                break

            # Add context WITHOUT reference - cleaner for users
            context_piece = doc.text.strip()
            context_texts.append(context_piece)
            total_context_length += len(context_piece)

            # Log chunk info
            metadata = doc.metadata
            logger.info(f"Added {metadata.get('type', 'unknown')} chunk from {metadata.get('type_id', 'unknown')} "
                        f"(similarity: {metadata.get('similarity_score', 0):.3f}, length: {len(doc.text)})")

        # Prepare used_items tracking for all types
        used_items = {
            'notes': context_info.get('used_notes', []),
            'conversations': context_info.get('used_conversations', []),
            'attachments': context_info.get('used_attachments', [])
        }

        # Add web search results if enabled
        web_search_results = []
        web_search_documents = []

        if request.enable_web_search:
            logger.info(f"=== FAST RAG WEB SEARCH DEBUG ===")
            logger.info(f"Web search enabled: {request.enable_web_search}")
            logger.info(
                f"Web search tool enabled: {self.web_search.search_enabled}")

            search_query = request.search_query or query
            logger.info(f"Extracted search query: {search_query}")

            if search_query:
                logger.info(f"Performing web search for: {search_query}")
                web_search_results = await self.web_search.search(search_query)
                logger.info(
                    f"Web search results count: {len(web_search_results)}")

                if web_search_results:
                    logger.info("Sample web search results:")
                    for i, result in enumerate(web_search_results[:2]):
                        logger.info(
                            f"  Result {i+1}: {result.get('title', 'No title')[:100]}")

                    # Create documents from web search results
                    web_search_documents = self._create_search_documents(
                        web_search_results)
                    logger.info(
                        f"Created {len(web_search_documents)} web search documents")

                    # Use embedding-based relevance filtering for web search results
                    if web_search_documents:
                        relevant_web_docs = await self._filter_relevant_web_documents(
                            web_search_documents, search_query, max_docs=3
                        )
                        logger.info(
                            f"Filtered to {len(relevant_web_docs)} relevant web documents")

                        # Convert relevant web documents to context text
                        for doc in relevant_web_docs:
                            web_piece = f"Web Source - {doc.metadata.get('title', 'Unknown')}:\n{doc.text}"
                            context_texts.append(web_piece)
                            total_context_length += len(web_piece)
                            if total_context_length > max_context_length:
                                break

                        logger.info(
                            f"Added {len(relevant_web_docs)} relevant web search results to context")
                else:
                    logger.info("No web search results found")
            else:
                logger.warning("No search query extracted from messages")
            logger.info(f"=== END FAST RAG WEB SEARCH DEBUG ===")
        else:
            logger.info("Fast RAG web search disabled or not requested")

        context_text = "\n\n".join(context_texts)

        logger.info(f"=== FINAL CONTEXT ===")
        logger.info(f"Total context length: {len(context_text)} characters")
        logger.info(f"Context preview: {context_text[:500]}...")

        # Build the prompt with the context (both mixed sources and web search)
        context_sources = []
        if context_info.get('used_notes') or context_info.get('used_conversations') or context_info.get('used_attachments'):
            context_sources.append("user data")
        if web_search_results:
            context_sources.append("web search results")

        sources_text = " and ".join(
            context_sources) if context_sources else "available information"

        system_prompt = f"""You are an AI assistant helping with information from {sources_text}. 

Use the following context to answer the user's question. The context contains relevant excerpts from {sources_text}:

CONTEXT:
{context_text}

Instructions:
- Answer based primarily on the provided context
- Be specific and reference relevant information naturally
- If the context doesn't fully answer the question, say so honestly
- Keep your response concise but helpful
- Do not reference note IDs or technical identifiers"""

        logger.info(f"=== FINAL PROMPT ===")
        logger.info(f"System prompt length: {len(system_prompt)} characters")

        # Build a simple prompt since the LLM message format is complex
        full_prompt = f"{system_prompt}\n\nUser: {query}\nAssistant:"

        logger.info(f"=== FINAL PROMPT DEBUG ===")
        logger.info(f"System prompt length: {len(system_prompt)} characters")
        logger.info(f"User query: {query}")
        logger.info("============================")

        # Create citations from mixed documents and web search results
        citations = []

        # Add citations from mixed documents (notes, conversations, file attachments)
        for i, doc in enumerate(mixed_documents):
            metadata = doc.metadata
            doc_type = metadata.get('type', 'unknown')
            type_id = metadata.get('type_id', 'unknown')
            similarity = metadata.get('similarity_score', 0)

            # Create appropriate title based on type
            if doc_type == 'note':
                title = f"Note {type_id} (Chunk {i + 1})"
            elif doc_type == 'conversation':
                title = f"Conversation {type_id} (Chunk {i + 1})"
            elif doc_type == 'user':
                title = f"File Attachment {type_id} (Chunk {i + 1})"
            else:
                title = f"{doc_type.title()} {type_id} (Chunk {i + 1})"

            citation = {
                "id": len(citations) + 1,
                "title": title,
                "nodeId": type_id,
                "type": doc_type,
                "snippet": doc.text[:200],
                "content": doc.text,
                "score": similarity,
                "metadata": metadata
            }
            citations.append(citation)

        # Add web search citations
        for i, result in enumerate(web_search_results):
            citation = {
                "id": len(citations) + 1,
                "title": result.get("title", "Web Search Result"),
                "url": result.get("link", ""),
                "type": "web",
                "snippet": result.get("snippet", "")[:200],
                "content": f"Title: {result.get('title', '')}\n\n{result.get('snippet', '')}",
                "metadata": {
                    "source": result.get("source", "web"),
                    "url": result.get("link", ""),
                    "title": result.get("title", ""),
                    "type": "web_search",
                    "search_result_index": i
                }
            }
            citations.append(citation)

        if request.stream:
            # Return streaming generator
            async def generate_with_context():
                response_stream = await llm.astream_complete(full_prompt)
                async for chunk in response_stream:
                    yield {
                        "id": f"chatcmpl-{os.urandom(8).hex()}",
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": request.model or "unknown",
                        "provider": llm.__class__.__name__.lower(),
                        "choices": [{
                            "index": 0,
                            "delta": {"content": str(chunk.delta)},
                            "finish_reason": None
                        }]
                    }
                # Generate title if requested
                generated_title = None
                if request.generate_title:
                    try:
                        generated_title = await self._generate_conversation_title(request.messages, llm)
                    except Exception as e:
                        logger.error(
                            f"Failed to generate title in context streaming: {e}")

                # Final chunk with all metadata
                yield {
                    "id": f"chatcmpl-{os.urandom(8).hex()}",
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": request.model or "unknown",
                    "provider": llm.__class__.__name__.lower(),
                    "choices": [{
                        "index": 0,
                        "delta": {},
                        "finish_reason": "stop"
                    }],
                    "metadata": {
                        "used_items": used_items,
                        "search_results": web_search_results,
                        "citations": citations,
                        "generated_title": generated_title
                    }
                }
            return generate_with_context()
        else:
            # Non-streaming response
            response = await llm.acomplete(full_prompt)

            # Generate conversation title if requested
            generated_title = None
            if request.generate_title:
                generated_title = await self._generate_conversation_title(request.messages, llm)

            return ChatCompletionResponse(
                id=f"chatcmpl-{os.urandom(8).hex()}",
                object="chat.completion",
                created=int(time.time()),
                model=request.model or "unknown",
                provider=llm.__class__.__name__.lower(),
                choices=[{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": str(response)
                    },
                    "finish_reason": "stop"
                }],
                # Backward compatibility
                used_notes=used_items.get('notes', []),
                used_items=used_items,
                search_results=web_search_results,
                citations=citations,
                generated_title=generated_title
            )

    async def _filter_relevant_web_documents(self, web_documents: List[Document], query: str, max_docs: int = 3) -> List[Document]:
        """Filter web search documents by embedding-based relevance to the query"""
        try:
            from llama_index.core import VectorStoreIndex

            logger.info(
                f"Filtering {len(web_documents)} web documents for relevance to: {query}")

            # Create a temporary index from web search documents only
            web_index = VectorStoreIndex.from_documents(
                web_documents, embed_model=self.embedder)

            # Use retriever to get most relevant documents
            retriever = web_index.as_retriever(similarity_top_k=max_docs)
            relevant_nodes = retriever.retrieve(query)

            # Convert back to Document objects with relevance scores
            relevant_docs = []
            for node in relevant_nodes:
                # Add relevance score to metadata
                doc = Document(
                    text=node.node.text,
                    metadata={
                        **node.node.metadata,
                        "relevance_score": node.score if hasattr(node, 'score') else 0.0
                    }
                )
                relevant_docs.append(doc)
                logger.info(
                    f"Selected web doc: {doc.metadata.get('title', 'Unknown')[:50]}... (score: {node.score if hasattr(node, 'score') else 'N/A'})")

            return relevant_docs

        except ImportError as e:
            logger.warning(
                f"LlamaIndex not available for web document filtering: {e}")
            # Fallback: return first max_docs documents
            return web_documents[:max_docs]
        except Exception as e:
            logger.error(f"Error filtering web documents: {e}")
            # Fallback: return first max_docs documents
            return web_documents[:max_docs]

    async def _generate_response(self, request: ChatCompletionRequest, query_engine,
                                 provider_info: Dict, used_notes: List[int],
                                 search_results: List[Dict], context_documents: Optional[List[Document]] = None) -> ChatCompletionResponse:
        """Generate non-streaming response with proper citations"""

        # Convert messages to query
        query = self._messages_to_query(request.messages)

        logger.info(f"=== RAG QUERY DEBUG ===")
        logger.info(f"Original query: {query}")

        rag_response = None
        if query_engine:
            # Use CitationQueryEngine with automatic citations
            logger.info(
                f"Using CitationQueryEngine with {len(used_notes)} notes")
            rag_response = query_engine.query(query)
            answer = str(rag_response)

            # Log the citation information
            if hasattr(rag_response, 'source_nodes'):
                logger.info(
                    f"CitationQueryEngine used {len(rag_response.source_nodes)} source chunks")
                # Log first 3 chunks
                for i, node in enumerate(rag_response.source_nodes[:3]):
                    logger.info(f"Source chunk {i+1}: {node.text[:200]}...")

            logger.info(f"Citation response: {answer[:500]}...")
        else:
            # No CitationQueryEngine - either direct LLM or context injection
            llm = provider_info["llm"]

            if context_documents:
                # Use context injection without re-embedding
                logger.info(
                    f"Using context injection with {len(context_documents)} documents (no re-embedding)")
                contextualized_query = await self._build_contextualized_query_from_documents(query, context_documents)
                rag_response = llm.complete(contextualized_query)
                answer = str(rag_response)
                logger.info(f"Context injection response: {answer[:500]}...")
            else:
                # Direct LLM call without any context
                logger.info("Using direct LLM call (no citations, no context)")
                rag_response = llm.complete(query)
                answer = str(rag_response)
                logger.info(f"Direct response: {answer[:500]}")

        # Extract citations from the response
        citations = self._extract_citations_from_response(
            rag_response) if rag_response else []

        # Generate conversation title if requested
        generated_title = None
        if request.generate_title:
            generated_title = await self._generate_conversation_title(request.messages, llm)

        # Get token usage
        token_counter = self.provider_manager.token_counter
        usage = Usage(
            prompt_tokens=token_counter.prompt_llm_token_count,
            completion_tokens=token_counter.completion_llm_token_count,
            total_tokens=token_counter.total_llm_token_count
        )

        # Reset token counter
        token_counter.reset_counts()

        return ChatCompletionResponse(
            id=f"chatcmpl-{os.urandom(16).hex()}",
            object="chat.completion",
            created=int(asyncio.get_event_loop().time()),
            model=request.model or "auto",
            provider=provider_info["provider"].value,
            choices=[{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": answer
                },
                "finish_reason": "stop"
            }],
            usage=usage,
            used_notes=used_notes if used_notes else None,
            search_results=search_results if search_results else None,
            citations=citations if citations else None,  # Add citations to response
            generated_title=generated_title
        )

    def _messages_to_query(self, messages: List[ChatMessage]) -> str:
        """Convert OpenAI messages format to query string"""
        query_parts = []

        for msg in messages:
            role = msg.role
            content = msg.content

            if isinstance(content, str):
                query_parts.append(f"{role}: {content}")
            elif isinstance(content, list):
                # Handle multimodal content
                text_parts = []
                for item in content:
                    if item.get("type") == "text":
                        text_parts.append(item.get("text", ""))
                if text_parts:
                    query_parts.append(f"{role}: {' '.join(text_parts)}")

        return "\n".join(query_parts)

    async def _build_contextualized_query(self, original_query: str, rag_response) -> str:
        """Build a contextualized query by extracting context from RAG response"""
        try:
            context_parts = []

            # Extract context from source nodes if available
            if hasattr(rag_response, 'source_nodes') and rag_response.source_nodes:
                context_parts.append(
                    "Based on the following information from sources:")
                context_parts.append("")

                # Use top 5 most relevant and number them for citation
                for i, node in enumerate(rag_response.source_nodes[:5]):
                    source_num = i + 1
                    note_id = node.metadata.get('note_id', 'unknown')

                    context_parts.append(
                        f"=== Source [{source_num}] (Note ID: {note_id}) ===")
                    context_parts.append(node.text.strip())
                    context_parts.append("")

                context_parts.append("===")
                context_parts.append("")
                context_parts.append(
                    "Based on the above sources, please answer the following question:")
                context_parts.append(original_query)
            else:
                # No source nodes, use the original query
                return original_query

            contextualized = "\n".join(context_parts)

            # Log the contextualized query for debugging
            logger.info(f"=== CONTEXTUALIZED QUERY ===")
            logger.info(
                contextualized[:2000] + "..." if len(contextualized) > 2000 else contextualized)
            logger.info("=== END CONTEXTUALIZED QUERY ===")

            return contextualized

        except Exception as e:
            logger.error(f"Failed to build contextualized query: {e}")
            return original_query

    async def _build_contextualized_query_from_documents(self, original_query: str, context_documents: List[Document]) -> str:
        """Build a contextualized query from context documents without CitationQueryEngine

        This method creates a context-rich query by directly using the document contents,
        avoiding the need for re-embedding through CitationQueryEngine.
        """
        try:
            if not context_documents:
                return original_query

            context_parts = []
            context_parts.append("Based on the following information:")
            context_parts.append("")

            # Group documents by type for better organization
            note_docs = [
                doc for doc in context_documents if doc.metadata.get('note_id')]
            web_docs = [doc for doc in context_documents if doc.metadata.get(
                'web_search_result')]
            attachment_docs = [
                doc for doc in context_documents if doc.metadata.get('type') == 'attachment']

            source_count = 0

            # Add note documents
            if note_docs:
                context_parts.append("=== Your Notes ===")
                for doc in note_docs[:3]:  # Limit to top 3 notes
                    source_count += 1
                    note_id = doc.metadata.get('note_id', 'unknown')
                    title = doc.metadata.get('title', f'Note {note_id}')
                    context_parts.append(f"[{source_count}] {title}")
                    context_parts.append(
                        doc.text.strip()[:1000] + ("..." if len(doc.text) > 1000 else ""))
                    context_parts.append("")

            # Add web search documents
            if web_docs:
                context_parts.append("=== Web Search Results ===")
                for doc in web_docs[:3]:  # Limit to top 3 web results
                    source_count += 1
                    title = doc.metadata.get('title', 'Web Result')
                    url = doc.metadata.get('url', '')
                    context_parts.append(f"[{source_count}] {title}")
                    if url:
                        context_parts.append(f"Source: {url}")
                    context_parts.append(
                        doc.text.strip()[:1000] + ("..." if len(doc.text) > 1000 else ""))
                    context_parts.append("")

            # Add attachment documents
            if attachment_docs:
                context_parts.append("=== File Attachments ===")
                for doc in attachment_docs:
                    source_count += 1
                    filename = doc.metadata.get('filename', 'Unknown File')
                    file_type = doc.metadata.get('file_type', 'unknown')
                    context_parts.append(
                        f"[{source_count}] {filename} ({file_type})")
                    context_parts.append(
                        doc.text.strip()[:1000] + ("..." if len(doc.text) > 1000 else ""))
                    context_parts.append("")

            context_parts.append("===")
            context_parts.append("")
            context_parts.append(
                "Based on the above information, please answer the following question:")
            context_parts.append(original_query)

            contextualized = "\n".join(context_parts)

            logger.info(
                f"Built contextualized query with {source_count} sources (no re-embedding)")
            logger.info(f"Context length: {len(contextualized)} characters")

            return contextualized

        except Exception as e:
            logger.error(
                f"Failed to build contextualized query from documents: {e}")
            return original_query

    def list_providers(self) -> Dict[str, List[str]]:
        """List available providers and models"""
        return self.provider_manager.list_available_providers()

    def _extract_search_query(self, messages: List[ChatMessage]) -> str:
        """Extract a search query from the conversation messages"""
        # Get the last user message as the search query
        user_messages = [msg for msg in messages if msg.role == "user"]
        if not user_messages:
            return ""

        last_message = user_messages[-1]
        if isinstance(last_message.content, str):
            return last_message.content.strip()
        elif isinstance(last_message.content, list):
            # Handle multimodal content, extract text parts
            text_parts = []
            for item in last_message.content:
                if item.get("type") == "text":
                    text_parts.append(item.get("text", ""))
            return " ".join(text_parts).strip()

        return ""

    def _create_search_documents(self, search_results: List[Dict[str, Any]]) -> List[Document]:
        """Convert search results to LlamaIndex Document objects

        IMPORTANT: These documents should NOT be re-embedded by CitationQueryEngine.
        They are already contextual and should be used directly for citation.
        """
        documents = []

        for i, result in enumerate(search_results):
            # Create document content combining title and snippet
            title = result.get("title", "")
            snippet = result.get("snippet", "")
            link = result.get("link", "")
            source = result.get("source", "web")

            content = f"Title: {title}\n\n{snippet}"

            # Create metadata with flags to prevent re-embedding
            metadata = {
                "source": source,
                "url": link,
                "title": title,
                "search_result_index": i,
                "type": "web_search",
                "pre_embedded": True,  # Flag to indicate this shouldn't be re-embedded
                "direct_citation": True,  # Flag to use directly for citation
                "web_search_result": True  # Clear marker for web search content
            }

            # Create Document object
            doc = Document(
                text=content,
                metadata=metadata
            )

            logger.info(
                f"Created web search document {i+1}: '{title[:50]}...' (should NOT be re-embedded)")
            documents.append(doc)

        logger.info(
            f"Created {len(documents)} web search documents marked as pre-embedded")
        return documents

    async def _build_query_engine(self, documents: List[Document], llm):
        """Build a query engine from documents for citation/RAG purposes"""
        try:
            from llama_index.core import VectorStoreIndex
            from llama_index.core.query_engine import CitationQueryEngine

            # Log document types to understand what we're processing
            logger.info(f"=== QUERY ENGINE CREATION DEBUG ===")
            logger.info(
                f"Building query engine with {len(documents)} documents")

            doc_types = {}
            web_search_docs = 0
            note_docs = 0

            for doc in documents:
                doc_type = doc.metadata.get('type', 'unknown')
                doc_types[doc_type] = doc_types.get(doc_type, 0) + 1

                if doc.metadata.get('web_search_result'):
                    web_search_docs += 1
                elif doc.metadata.get('note_id'):
                    note_docs += 1

            logger.info(f"Document types: {doc_types}")
            logger.info(
                f"Note documents: {note_docs}, Web search documents: {web_search_docs}")

            if web_search_docs > 0:
                logger.info(
                    f"⚠️  {web_search_docs} web search documents will be re-embedded by CitationQueryEngine (known inefficiency)")

            # Create index from documents
            logger.info(
                "Creating VectorStoreIndex (this will embed documents)")
            index = VectorStoreIndex.from_documents(documents)

            # Create query engine
            logger.info("Creating CitationQueryEngine")
            query_engine = CitationQueryEngine.from_args(
                index,
                similarity_top_k=10,
                citation_chunk_size=1024,
            )

            logger.info(f"=== END QUERY ENGINE CREATION DEBUG ===")
            return query_engine

        except ImportError as e:
            logger.warning(
                f"LlamaIndex components not available for query engine: {e}")
            return None
        except Exception as e:
            logger.error(f"Error building query engine: {e}")
            return None

    async def _get_user_note_context(self, messages, user_id, folder_ids=None, note_ids=None, conversation_ids=None):
        """Get user note context for RAG using chunk-based retrieval from embedding_v1

        Args:
            messages: List of chat messages
            user_id: User ID
            folder_ids: Optional list of folder IDs to limit search to
            note_ids: Optional list of specific note IDs to use
            conversation_ids: Optional list of conversation IDs (currently not used in this method)

        Returns:
            Tuple of (documents, used_notes) where:
            - documents: List of Document objects created from chunks
            - used_notes: List of unique note IDs that were used
        """
        try:
            # Add stack trace logging to see who's calling this and prevent duplicates
            import traceback
            stack = traceback.format_stack()
            caller_info = stack[-3].strip() if len(stack) >= 3 else "Unknown caller"

            # Create a cache key to prevent duplicate processing
            cache_key = f"user_context_{user_id}_{hash(str(messages))}"

            # Check if we've already processed this exact request
            if hasattr(self, '_context_cache') and cache_key in self._context_cache:
                logger.info(f"=== DUPLICATE CONTEXT CALL DETECTED ===")
                logger.info(f"Caller: {caller_info}")
                logger.info(f"Cache key: {cache_key}")
                logger.info(
                    f"Returning cached result to prevent duplicate processing")
                return self._context_cache[cache_key]

            # Initialize cache if needed
            if not hasattr(self, '_context_cache'):
                self._context_cache = {}

            logger.info(f"=== NOTE CONTEXT PROCESSING ===")
            logger.info(f"_get_user_note_context called by: {caller_info}")
            logger.info(f"Getting user note context for user {user_id}")

            # Get note IDs for RAG
            note_ids_for_rag = get_notes_for_rag(user_id, folder_ids, note_ids)

            if not note_ids_for_rag:
                logger.info("No notes found for RAG")
                result = ([], [])
                self._context_cache[cache_key] = result
                return result

            logger.info(f"Found {len(note_ids_for_rag)} notes for RAG")

            # Get query from messages
            user_messages = [
                msg.content for msg in messages if msg.role == "user"]
            query = " ".join(user_messages) if user_messages else ""

            if not query:
                logger.warning("No user query found for chunk retrieval")
                result = ([], [])
                self._context_cache[cache_key] = result
                return result

            # Get most relevant chunks using the new chunk-based system
            from src.utility.note_utils import get_most_related_chunks_pgvector
            max_chunks = 20  # Get top 20 most relevant chunks across all notes

            # This returns List[Tuple[note_id, chunk_text, similarity_score]]
            relevant_chunks = get_most_related_chunks_pgvector(
                query, note_ids_for_rag, max_chunks)

            if not relevant_chunks:
                logger.info("No relevant chunks found")
                result = ([], [])
                self._context_cache[cache_key] = result
                return result

            # Convert chunks to Documents and track used notes
            documents = []
            used_note_ids = set()

            for i, (note_id, chunk_text, similarity_score) in enumerate(relevant_chunks):
                try:
                    if chunk_text and chunk_text.strip():
                        # Create document from chunk with metadata
                        doc = Document(
                            text=chunk_text,
                            metadata={
                                "source": "user_note",
                                "note_id": note_id,
                                "type": "note",
                                "chunk_index": i,
                                "similarity_score": similarity_score
                            }
                        )
                        documents.append(doc)
                        used_note_ids.add(note_id)
                        logger.debug(
                            f"Added chunk from note {note_id} (similarity: {similarity_score:.3f})")
                    else:
                        logger.warning(f"Empty chunk text for note {note_id}")
                except Exception as e:
                    logger.error(
                        f"Error processing chunk from note {note_id}: {e}")
                    continue

            used_notes = list(used_note_ids)
            logger.info(
                f"Created {len(documents)} chunk documents from {len(used_notes)} unique notes")

            # Cache the result
            result = (documents, used_notes)
            self._context_cache[cache_key] = result
            logger.info(f"=== END NOTE CONTEXT PROCESSING ===")
            return result

        except Exception as e:
            logger.error(f"Error in _get_user_note_context: {e}")
            return [], []

    async def _get_mixed_context(self, messages, user_id, folder_ids=None, note_ids=None, conversation_ids=None):
        """Get mixed context for RAG using chunk-based retrieval from all types (notes, conversations, file attachments)

        Args:
            messages: List of chat messages
            user_id: User ID
            folder_ids: Optional list of folder IDs to limit note search to
            note_ids: Optional list of specific note IDs to use
            conversation_ids: Optional list of specific conversation IDs to use (empty = search user's conversations)

        Returns:
            Tuple of (documents, context_info) where:
            - documents: List of Document objects created from chunks
            - context_info: Dict with details about used sources
        """
        try:
            logger.info(f"=== MIXED CONTEXT PROCESSING ===")
            logger.info(f"Getting mixed context for user {user_id}")
            logger.info(
                f"Note filters - folders: {folder_ids}, notes: {note_ids}")
            logger.info(f"Conversation filters: {conversation_ids}")

            # Get query from messages
            user_messages = [
                msg.content for msg in messages if msg.role == "user"]
            query = " ".join(user_messages) if user_messages else ""

            if not query:
                logger.warning("No user query found for chunk retrieval")
                return [], {}

            # Prepare type filters for mixed search
            type_filters = {}
            context_info = {
                'used_notes': [],
                'used_conversations': [],
                'used_attachments': [],
                'total_chunks': 0
            }

            # 1. Get note IDs for RAG
            if note_ids is not None or folder_ids is not None:
                note_ids_for_rag = get_notes_for_rag(
                    user_id, folder_ids, note_ids)
                if note_ids_for_rag:
                    type_filters['note'] = note_ids_for_rag
                    logger.info(
                        f"Added {len(note_ids_for_rag)} notes to search")

            # 2. Get conversation IDs for RAG
            if conversation_ids is not None:
                # Specific conversations requested
                if conversation_ids:
                    type_filters['conversation'] = conversation_ids
                    logger.info(
                        f"Added {len(conversation_ids)} specific conversations to search")
                # Empty list means no conversation search
            else:
                # No conversation_ids parameter = search all user's conversations with embeddings
                from src.utility.postgres import get_user_conversations_with_embeddings
                user_conversation_ids = get_user_conversations_with_embeddings(
                    user_id)
                if user_conversation_ids:
                    type_filters['conversation'] = user_conversation_ids
                    logger.info(
                        f"Added {len(user_conversation_ids)} user conversations to search")

            # 3. Get user's file attachment embeddings (type='user')
            from src.utility.postgres import get_user_file_attachment_ids
            user_attachment_ids = get_user_file_attachment_ids(user_id)
            if user_attachment_ids:
                type_filters['user'] = user_attachment_ids
                logger.info(
                    f"Added {len(user_attachment_ids)} file attachments to search")

            if not type_filters:
                logger.info("No sources found for mixed search")
                return [], context_info

            # Perform mixed-type vector search
            from src.utility.postgres import mixed_type_vector_search

            # Generate query embedding using existing embedder
            embedder = OpenAIEmbedding(model="text-embedding-3-small")
            query_embedding = embedder._get_text_embeddings([query])[0]

            # Get most relevant chunks across all types
            max_chunks = 20
            relevant_chunks = mixed_type_vector_search(
                query_embedding, type_filters, max_chunks)

            if not relevant_chunks:
                logger.info("No relevant chunks found in mixed search")
                return [], context_info

            # Convert chunks to Documents and track used sources
            documents = []
            used_note_ids = set()
            used_conversation_ids = set()
            used_attachment_ids = set()

            for i, (type_id, embedding_type, similarity, chunk_text, source) in enumerate(relevant_chunks):
                try:
                    if chunk_text and chunk_text.strip():
                        # Create document from chunk with metadata
                        doc = Document(
                            text=chunk_text,
                            metadata={
                                "source": f"{embedding_type}_{source}",
                                "type_id": type_id,
                                "type": embedding_type,
                                "chunk_index": i,
                                "similarity_score": similarity,
                                # e.g., "summary", "user", etc.
                                "source_detail": source
                            }
                        )
                        documents.append(doc)

                        # Track used sources
                        if embedding_type == 'note':
                            used_note_ids.add(type_id)
                        elif embedding_type == 'conversation':
                            used_conversation_ids.add(type_id)
                        elif embedding_type == 'user':
                            used_attachment_ids.add(type_id)

                        logger.debug(f"Added {embedding_type} chunk from {type_id} "
                                     f"(similarity: {similarity:.3f}, source: {source})")
                    else:
                        logger.warning(
                            f"Empty chunk text for {embedding_type} {type_id}")
                except Exception as e:
                    logger.error(
                        f"Error processing chunk from {embedding_type} {type_id}: {e}")
                    continue

            # Update context info
            context_info.update({
                'used_notes': list(used_note_ids),
                'used_conversations': list(used_conversation_ids),
                'used_attachments': list(used_attachment_ids),
                'total_chunks': len(documents)
            })

            logger.info(
                f"Created {len(documents)} chunk documents from mixed sources:")
            logger.info(f"  - {len(used_note_ids)} notes")
            logger.info(f"  - {len(used_conversation_ids)} conversations")
            logger.info(f"  - {len(used_attachment_ids)} file attachments")
            logger.info(f"=== END MIXED CONTEXT PROCESSING ===")

            return documents, context_info

        except Exception as e:
            logger.error(f"Error in _get_mixed_context: {e}")
            return [], {}
