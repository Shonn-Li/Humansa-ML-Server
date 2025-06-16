"""
Enhanced Chat Bot with GPT-level API endpoints and multi-provider support

This module provides:
- OpenAI-compatible API endpoints
- Multiple LLM provider support (OpenAI, Anthropic, Groq, DeepSeek, etc.)
- Streaming response suppor        # DeepSeek (us        # xAI Grok (using OpenAI-like provider)
        if OPENAI_LIKE_AVAILABLE and os.getenv("XAI_API_KEY"):
            self.providers[LLMProvider.XAI] = {
                "llm": OpenAILike(
                    model="grok-3-beta",
                    api_key=os.getenv("XAI_API_KEY"),
                    api_base="https://api.x.ai/v1",
                    is_chat_model=True,
                    is_function_calling_model=False,
                    context_window=131072,
                    temperature=0.7,
                    callback_manager=CallbackManager([self.token_counter])
                ),
                "models": ["grok-3-beta", "grok-3-mini-beta", "grok-2-vision-1212", "grok-beta"]
            }d provider)
        if DEEPSEEK_AVAILABLE and os.getenv("DEEPSEEK_API_KEY"):
            self.providers[LLMProvider.DEEPSEEK] = {
                "llm": DeepSeek(
                    model="deepseek-chat",
                    api_key=os.getenv("DEEPSEEK_API_KEY"),
                    temperature=0.7,
                    callback_manager=CallbackManager([self.token_counter])
                ),
                "models": ["deepseek-chat", "deepseek-coder", "deepseek-reasoner"]
            }ch integration
- File attachment support (images, PDFs)
- Node ID context preservation
"""

import os
import json
import asyncio
import logging
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
from llama_index.core.query_engine import RetrieverQueryEngine
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
    create_and_save_embeddings,
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
    enable_rag: bool = True  # Option to disable RAG
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

    # Custom fields
    used_notes: Optional[List[int]] = None
    search_results: Optional[List[Dict[str, Any]]] = None


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
        logger.info(f"Available providers: {list(self.providers.keys())}")

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

                return {
                    "provider": provider_enum,
                    "llm": provider_info["llm"],
                    "multimodal": provider_info.get("multimodal"),
                    "models": provider_info["models"]
                }
            else:
                logger.warning(
                    f"Provider {provider_enum} not found in available providers")

        # Auto-select best available provider
        # Priority: OpenAI > Anthropic > Gemini > DeepSeek > xAI
        logger.info("Auto-selecting provider...")
        for provider in [LLMProvider.OPENAI, LLMProvider.ANTHROPIC, LLMProvider.GEMINI,
                         LLMProvider.DEEPSEEK, LLMProvider.XAI]:
            if provider in self.providers:
                provider_info = self.providers[provider]
                logger.info(f"Auto-selected provider: {provider}")
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

    async def chat_completion(self, request: ChatCompletionRequest) -> Union[ChatCompletionResponse, AsyncGenerator]:
        """Main chat completion endpoint"""

        # Validate user ID if RAG is enabled
        if request.enable_rag and not request.user_id:
            raise ValueError("user_id is required when RAG is enabled")

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

        # For streaming, return the async generator directly (not a coroutine)
        if request.stream:
            # Return the generator itself, not a coroutine
            return self._stream_with_progress(request, provider_info)

        # Non-streaming path remains the same
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
                    "delta": {
                        "role": "system",
                        "content": "[Starting search...]"
                    },
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
                        "stage": "searching_notes",
                        "message": "Searching through your notes..."
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
                        "stage": "notes_found",
                        "message": f"Found {len(used_notes)} relevant notes",
                        "notes_found": len(used_notes),
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
                        "stage": "building_context",
                        "message": "Building context from documents..."
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

    async def _stream_llm_response(self, request: ChatCompletionRequest, query_engine: Optional[RetrieverQueryEngine],
                                   provider_info: Dict, used_notes: List[int],
                                   search_results: List[Dict]) -> AsyncGenerator:
        """Stream the actual LLM response"""
        # Convert messages to query
        query = self._messages_to_query(request.messages)

        llm = provider_info["llm"]

        if query_engine:
            # Use RAG with context - note: streaming RAG is complex,
            # for now we'll do direct streaming
            response_gen = llm.stream_complete(query)
        else:
            # Direct LLM streaming
            response_gen = llm.stream_complete(query)

        # Fix: Handle synchronous generator from LlamaIndex
        for chunk in response_gen:
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

        # Final chunk
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
                "search_results": search_results if search_results else None
            }
        }

    async def _get_user_note_context(self, messages: List[ChatMessage], user_id: int,
                                     folder_ids: Optional[List[int]] = None,
                                     note_ids: Optional[List[int]] = None) -> tuple:
        """
        Get context from user's notes based on priority:
        1. If note_ids provided: use only those specific notes
        2. If folder_ids provided: use only notes from those folders
        3. Otherwise: use all notes from the user
        """
        from src.utility.postgres import (
            get_notes_for_rag,
            validate_user_exists,
            validate_folders_belong_to_user
        )

        # Validate user exists
        if not validate_user_exists(user_id):
            logger.warning(f"User {user_id} not found")
            return [], []

        # Validate folders belong to user if provided (and no specific notes)
        if folder_ids and not note_ids:
            if not validate_folders_belong_to_user(user_id, folder_ids):
                logger.warning(f"Some folders do not belong to user {user_id}")
                return [], []

        # Extract the last user message as the query
        user_query = ""
        for msg in reversed(messages):
            if msg.role == MessageRole.USER.value:
                if isinstance(msg.content, str):
                    user_query = msg.content
                else:
                    # Handle multimodal content
                    for item in msg.content:
                        if item.get("type") == "text":
                            user_query = item.get("text", "")
                            break
                break

        if not user_query:
            return [], []

        # Get note IDs based on the priority logic
        available_note_ids = get_notes_for_rag(user_id, folder_ids, note_ids)

        if not available_note_ids:
            logger.info(
                f"No notes found for user {user_id} with given criteria")
            return [], []

        logger.info(f"Found {len(available_note_ids)} notes for RAG search")

        # If user specified 3 or fewer specific note IDs, use them all without similarity filtering
        # This ensures that when a user asks about specific notes, we use exactly those notes
        if note_ids and len(note_ids) <= 3 and len(available_note_ids) <= 3:
            logger.info(
                f"Using all {len(available_note_ids)} specified notes without similarity filtering")
            top_notes = available_note_ids
        else:
            # Get most related notes using embedding similarity
            from src.utility.note_utils import get_most_related_notes
            # Dynamically adjust max_notes based on available notes
            max_notes_to_retrieve = min(
                5, max(3, len(available_note_ids) // 3))
            top_notes = get_most_related_notes(
                user_query, available_note_ids, max_notes=max_notes_to_retrieve)

        # Create documents from notes
        documents = []
        for note_id in top_notes:
            text = get_note_text(note_id)
            if text:
                doc = Document(
                    text=text,
                    metadata={"note_id": note_id,
                              "source": "note", "user_id": user_id}
                )
                documents.append(doc)

        logger.info(f"Retrieved {len(documents)} documents for context")
        return documents, top_notes

    def _extract_search_query(self, messages: List[ChatMessage]) -> str:
        """Extract search query from messages"""
        # Simple implementation - use the last user message
        for msg in reversed(messages):
            if msg.role == MessageRole.USER.value:
                if isinstance(msg.content, str):
                    return msg.content
                else:
                    # Handle multimodal content
                    for item in msg.content:
                        if item.get("type") == "text":
                            return item.get("text", "")
        return ""

    def _create_search_documents(self, search_results: List[Dict[str, Any]]) -> List[Document]:
        """Create documents from search results"""
        documents = []
        for result in search_results:
            doc = Document(
                text=f"Title: {result['title']}\nURL: {result['link']}\nContent: {result['snippet']}",
                metadata={
                    "title": result['title'],
                    "url": result['link'],
                    "source": "web_search",
                    "search_source": result.get('source', 'unknown')
                }
            )
            documents.append(doc)
        return documents

    async def _build_query_engine(self, documents: List[Document], llm: LLM) -> RetrieverQueryEngine:
        """Build query engine from context documents"""
        # Create index
        index = VectorStoreIndex.from_documents(documents)

        # Create retriever
        retriever = index.as_retriever(similarity_top_k=10)

        # Create query engine
        query_engine = RetrieverQueryEngine.from_args(
            retriever=retriever,
            llm=llm
        )

        return query_engine

    async def _generate_response(self, request: ChatCompletionRequest, query_engine,
                                 provider_info: Dict, used_notes: List[int],
                                 search_results: List[Dict]) -> ChatCompletionResponse:
        """Generate non-streaming response"""

        # Convert messages to query
        query = self._messages_to_query(request.messages)

        if query_engine:
            # Use RAG with context
            response = query_engine.query(query)
            answer = str(response)
        else:
            # Direct LLM call
            llm = provider_info["llm"]
            response = llm.complete(query)
            answer = str(response)

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
            search_results=search_results if search_results else None
        )

    async def _stream_response(self, request: ChatCompletionRequest, query_engine: Optional[RetrieverQueryEngine],
                               provider_info: Dict, used_notes: List[int],
                               search_results: List[Dict]) -> AsyncGenerator:
        """Generate streaming response"""

        # Convert messages to query
        query = self._messages_to_query(request.messages)

        llm = provider_info["llm"]

        if query_engine:
            # Use RAG with context - note: streaming RAG is complex,
            # for now we'll do direct streaming
            response_gen = llm.stream_complete(query)
        else:
            # Direct LLM streaming
            response_gen = llm.stream_complete(query)

        # Yield streaming chunks
        async for chunk in response_gen:
            yield {
                "id": f"chatcmpl-{os.urandom(8).hex()}",
                "object": "chat.completion.chunk",
                "created": int(asyncio.get_event_loop().time()),
                "model": request.model or "auto",
                "provider": provider_info["provider"].value,
                "choices": [{
                    "index": 0,
                    "delta": {
                        "content": str(chunk.delta)
                    },
                    "finish_reason": None
                }]
            }

        # Final chunk
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
            "used_notes": used_notes if used_notes else None,
            "search_results": search_results if search_results else None
        }

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

    def list_providers(self) -> Dict[str, List[str]]:
        """List available providers and models"""
        return self.provider_manager.list_available_providers()


# Global instance
enhanced_chat_bot = EnhancedChatBot()
enhanced_chat_bot = EnhancedChatBot()
enhanced_chat_bot = EnhancedChatBot()
enhanced_chat_bot = EnhancedChatBot()
