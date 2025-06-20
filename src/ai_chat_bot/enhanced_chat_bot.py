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

from src.utility.postgres import get_embeddings, get_note_text, save_embeddings
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
    note_ids: Optional[List[int]] = None  # Optional specific note IDs to include
    enable_rag: bool = True  # Option to disable RAG
    enable_citations: bool = False  # NEW: Enable deep search with citations (slower)
    enable_web_search: bool = False
    enable_image_analysis: bool = False
    search_query: Optional[str] = None
    attachments: Optional[List[Dict[str, Any]]] = None


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
    used_notes: Optional[List[int]] = None
    search_results: Optional[List[Dict[str, Any]]] = None
    # Citation source nodes from LlamaIndex
    citations: Optional[List[Dict[str, Any]]] = None


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
                "models": ["gpt-4.1-nano", "gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo", "gpt-4-turbo", "gpt-4.1", "gpt-4.1-mini", "o3", "o4-mini"]
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
        if hasattr(response, 'source_nodes') and response.source_nodes:
            for i, source_node in enumerate(response.source_nodes):
                citation = {
                    "id": i + 1,  # Citations start from 1
                    "content": source_node.node.get_text(),
                    "score": source_node.score if hasattr(source_node, 'score') else None,
                    "metadata": source_node.node.metadata,
                    "node_id": source_node.node.node_id
                }
                citations.append(citation)
        return citations

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
        # If RAG is enabled but citations are NOT requested, use fast search
        if request.enable_rag and not request.enable_citations:
            logger.info("Using FAST RAG search (no re-embedding)")
            return await self._fast_rag_search(request, llm)

        # Otherwise, use the full citation engine (slower but with citations)
        if request.enable_citations:
            logger.info("Using DEEP search with CitationQueryEngine (with re-embedding)")
        
        # For streaming, gather context first then stream
        if request.stream:
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
                    request.note_ids
                )
                context_documents.extend(note_docs)

            # 2. Process web search if enabled
            # 2. Process web search if enabled
            if request.enable_web_search:
                search_query = request.search_query or self._extract_search_query(
                    request.messages)
                if search_query:
                    search_results = await self.web_search.search(search_query)
                    search_docs = self._create_search_documents(search_results)
                    context_documents.extend(search_docs)

            # 3. Process file attachments if provided
            if request.attachments:
                attachment_docs = await self.file_processor.process_attachments(request.attachments)
                context_documents.extend(attachment_docs)

            # Build query engine if we have context (only for citation mode)
            query_engine = None
            if context_documents and request.enable_citations:
                query_engine = await self._build_query_engine(context_documents, llm)

            # Return streaming response
            return self._stream_response(request, query_engine, provider_info, used_notes, search_results)

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
                request.note_ids
            )
            context_documents.extend(note_docs)

        # 2. Process web search if enabled
        if request.enable_web_search:
            search_query = request.search_query or self._extract_search_query(
                request.messages)
            if search_query:
                search_results = await self.web_search.search(search_query)
                search_docs = self._create_search_documents(search_results)
                context_documents.extend(search_docs)

        # 3. Process file attachments if provided
        if request.attachments:
            attachment_docs = await self.file_processor.process_attachments(request.attachments)
            context_documents.extend(attachment_docs)

        # Build query engine if we have context
        query_engine = None
        if context_documents:
            query_engine = await self._build_query_engine(context_documents, llm)

        # Generate response
        return await self._generate_response(request, query_engine, provider_info, used_notes, search_results)

    async def _stream_response(self, request: ChatCompletionRequest, query_engine: Optional[RetrieverQueryEngine],
                               provider_info: Dict, used_notes: List[int],
                               search_results: List[Dict]) -> AsyncGenerator:
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

            context_documents = []
            used_notes = []
            search_results = []

            # 1. Process RAG if enabled
            if request.enable_rag and request.user_id:
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
                        "stage": "rag_search_start",
                        "message": "Starting note search...",
                        "user_id": request.user_id,
                        "folder_ids": request.folder_ids,
                        "note_ids": request.note_ids
                    }
                }

                note_docs, used_notes = await self._get_user_note_context(
                    request.messages,
                    request.user_id,
                    request.folder_ids,
                    request.note_ids
                )
                context_documents.extend(note_docs)

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
                        "stage": "rag_notes_found",
                        "message": f"Found {len(used_notes)} relevant notes with {len(note_docs)} text chunks",
                        "notes_count": len(used_notes),
                        "chunks_count": len(note_docs),
                        "note_ids": used_notes
                    }
                }

            # 2. Process web search if enabled
            if request.enable_web_search:
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
                        "stage": "web_search",
                        "message": "Searching the web..."
                    }
                }

                search_query = request.search_query or self._extract_search_query(
                    request.messages)
                if search_query:
                    search_results = await self.web_search.search(search_query)
                    search_docs = self._create_search_documents(search_results)
                    context_documents.extend(search_docs)

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
                            "stage": "web_results_found",
                            "message": f"Found {len(search_results)} web results",
                            "results_count": len(search_results)
                        }
                    }

            # 3. Process file attachments if provided
            if request.attachments:
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
                        "stage": "processing_attachments",
                        "message": "Processing attachments..."
                    }
                }

                attachment_docs = await self.file_processor.process_attachments(request.attachments)
                context_documents.extend(attachment_docs)

            # Build query engine if we have context
            query_engine = None
            if context_documents:
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
                        "stage": "building_index",
                        "message": f"Building search index from {len(context_documents)} documents...",
                        "document_count": len(context_documents)
                    }
                }

                query_engine = await self._build_query_engine(context_documents, provider_info["llm"])

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
                        "stage": "index_ready",
                        "message": "Search index built successfully, ready to generate response"
                    }
                }

                query_engine = await self._build_query_engine(context_documents, provider_info["llm"])

            # Now yield the actual response
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
            async for chunk in self._stream_llm_response(request, query_engine, provider_info, used_notes, search_results):
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
                                   search_results: List[Dict]) -> AsyncGenerator:
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

                # For streaming, we need to use the context-enhanced query
                # Since LlamaIndex doesn't support streaming RAG well, we'll reconstruct the contextualized prompt

                contextualized_query = await self._build_contextualized_query(query, rag_response)
                logger.info(
                    f"Contextualized query: {contextualized_query[:1000]}...")

                # Now stream the LLM response with the contextualized query
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
            logger.info("Using direct LLM streaming (no RAG)")
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
                "citations": citations if citations else None
            }
        }

    async def _fast_rag_search(self, request: ChatCompletionRequest, llm: LLM) -> Union[ChatCompletionResponse, AsyncGenerator]:
        """Fast RAG search using pre-computed embeddings (no re-embedding)"""
        
        # Get query from messages - only use USER messages for search
        user_messages = [msg.content for msg in request.messages if msg.role == "user"]
        query = " ".join(user_messages) if user_messages else self._messages_to_query(request.messages)
        
        logger.info(f"=== FAST RAG QUERY EXTRACTION ===")
        logger.info(f"Original conversation: {len(request.messages)} messages")
        logger.info(f"User messages: {user_messages}")
        logger.info(f"Search query: {query}")
        logger.info("==================================")
        
        # Get note IDs for RAG
        from src.utility.postgres import get_notes_for_rag
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
                        }]
                    }
                return generate_no_context()
            else:
                # Non-streaming response
                response_text = await llm.acomplete(messages_text)
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
                    citations=None
                )
        
        # Use pre-computed embeddings for CHUNK-level similarity search - much faster and more relevant!
        from src.utility.note_utils import get_most_related_chunks_pgvector
        top_chunks = get_most_related_chunks_pgvector(query, note_ids, max_chunks=15)  # Get top chunks across all notes
        
        logger.info(f"=== FAST RAG CONTEXT DEBUG ===")
        logger.info(f"Query: {query}")
        logger.info(f"Found {len(top_chunks)} relevant chunks from {len(note_ids)} notes")
        
        # Group chunks by note for better context organization
        chunks_by_note = {}
        for note_id, chunk_text, similarity in top_chunks:
            if note_id not in chunks_by_note:
                chunks_by_note[note_id] = []
            chunks_by_note[note_id].append((chunk_text, similarity))
        
        logger.info(f"Chunks distributed across {len(chunks_by_note)} notes")
        
        # Build context from the most relevant chunks
        context_texts = []
        total_context_length = 0
        max_context_length = 8000  # Keep context reasonable for fast response
        
        for note_id, chunk_text, similarity in top_chunks:
            if total_context_length > max_context_length:
                break
                
            # Add context WITHOUT note reference - cleaner for users
            context_piece = chunk_text.strip()
            context_texts.append(context_piece)
            total_context_length += len(context_piece)
            
            logger.info(f"Added chunk from note {note_id} (similarity: {similarity:.3f}, length: {len(chunk_text)})")
        
        context_text = "\n\n".join(context_texts)
        
        logger.info(f"=== FINAL CONTEXT ===")
        logger.info(f"Total context length: {len(context_text)} characters")
        logger.info(f"Context preview: {context_text[:500]}...")
        
        # Build the prompt with the context
        system_prompt = f"""You are an AI assistant helping with information from user notes. 

Use the following context to answer the user's question. The context contains relevant excerpts from the user's notes:

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

        # Extract note IDs from the chunks for response metadata
        used_note_ids = list(set(note_id for note_id, _, _ in top_chunks))

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
                        }],
                        "used_notes": used_note_ids,
                        "search_results": [],
                        "citations": None
                    }
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
                    "used_notes": used_note_ids,
                    "search_results": [],
                    "citations": None
                }
            return generate_with_context()
        else:
            # Non-streaming response
            response = await llm.acomplete(full_prompt)
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
                used_notes=used_note_ids,
                search_results=[],
                citations=None  # No citations in fast mode
            )

    # ...existing code...

    async def _generate_response(self, request: ChatCompletionRequest, query_engine,
                                 provider_info: Dict, used_notes: List[int],
                                 search_results: List[Dict]) -> ChatCompletionResponse:
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
            # Direct LLM call
            logger.info("Using direct LLM call (no citations)")
            llm = provider_info["llm"]
            rag_response = llm.complete(query)
            answer = str(rag_response)
            logger.info(f"Direct response: {answer[:500]}...")

        # Extract citations from the response
        citations = self._extract_citations_from_response(
            rag_response) if rag_response else []

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
            citations=citations if citations else None  # Add citations to response
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

    def list_providers(self) -> Dict[str, List[str]]:
        """List available providers and models"""
        return self.provider_manager.list_available_providers()


# Global instance
enhanced_chat_bot = EnhancedChatBot()
