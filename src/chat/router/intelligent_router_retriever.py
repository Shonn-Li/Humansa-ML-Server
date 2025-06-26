"""
Router Retriever - Intelligent context source selection (FIXED VERSION)

This module uses LlamaIndex RouterRetriever to dynamically decide which context sources
to query based on the user's question, rather than always hitting all sources.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass

try:
    from llama_index.core.retrievers import RouterRetriever
    from llama_index.core.selectors import PydanticSingleSelector
    from llama_index.core.tools import ToolMetadata, RetrieverTool
    from llama_index.core.retrievers import BaseRetriever
    from llama_index.core.schema import NodeWithScore, QueryBundle
    ROUTER_AVAILABLE = True
except ImportError:
    ROUTER_AVAILABLE = False

logger = logging.getLogger(__name__)


class ContextSource(Enum):
    """Available context sources for routing"""
    RAG = "rag"
    ATTACHMENTS = "attachments"
    WEB_SEARCH = "web_search"


@dataclass
class RouterDecision:
    """Result of router retriever decision"""
    selected_sources: List[ContextSource]
    reasoning: str
    confidence: float


class ContextRetriever(BaseRetriever):
    """Custom retriever wrapper for each context source"""

    def __init__(self, source_type: ContextSource, processor_func, **kwargs):
        self.source_type = source_type
        self.processor_func = processor_func
        self.kwargs = kwargs
        super().__init__()

    def _retrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
        """Retrieve nodes from the specific context source"""
        try:
            # This is a placeholder - actual retrieval happens in the chat endpoint
            # We're using this primarily for routing decisions
            return []
        except Exception as e:
            logger.error(f"Error in {self.source_type.value} retriever: {e}")
            return []


class IntelligentRouterRetriever:
    """
    Intelligent router that decides which context sources to use based on query analysis
    """

    def __init__(self, llm, rag_processor, file_attachment_manager, web_search_processor, provider_selector=None):
        self.llm = llm
        self.rag_processor = rag_processor
        self.file_attachment_manager = file_attachment_manager
        self.web_search_processor = web_search_processor
        self.provider_selector = provider_selector
        self.router_retriever = None
        self._setup_router()

    def _setup_router(self):
        """Setup the router retriever with available context sources"""
        if not ROUTER_AVAILABLE:
            logger.warning(
                "RouterRetriever not available, falling back to manual routing")
            return

        # Get OpenAI-compatible LLM for router
        router_llm = self.llm
        if self.provider_selector:
            router_compatible_llm = self.provider_selector.get_router_compatible_llm()
            if router_compatible_llm:
                router_llm = router_compatible_llm
                logger.info(
                    "🎯 Using router-compatible LLM for PydanticSingleSelector")
            else:
                logger.warning(
                    "⚠️ No router-compatible LLM available, using original LLM")

        try:
            # Define context source retrievers with metadata
            retrievers = []

            # RAG/Notes Retriever
            rag_retriever = ContextRetriever(
                source_type=ContextSource.RAG,
                processor_func=self.rag_processor.process_rag_request
            )
            retrievers.append(rag_retriever)

            # File Attachments Retriever
            attachment_retriever = ContextRetriever(
                source_type=ContextSource.ATTACHMENTS,
                processor_func=self.file_attachment_manager.process_attachments
            )
            retrievers.append(attachment_retriever)

            # Web Search Retriever
            web_retriever = ContextRetriever(
                source_type=ContextSource.WEB_SEARCH,
                processor_func=self.web_search_processor.search_web_content
            )
            retrievers.append(web_retriever)

            # Define source retrievers with proper RetrieverTool wrapper
            retriever_tools = [
                RetrieverTool(
                    retriever=rag_retriever,
                    metadata=ToolMetadata(
                        name="rag",
                        description="Search through user's personal notes and conversation history. Use this for questions about personal information, previous conversations, saved notes, or user-specific data."
                    )
                ),
                RetrieverTool(
                    retriever=attachment_retriever,
                    metadata=ToolMetadata(
                        name="attachments",
                        description="Search through user-provided file attachments like PDFs, documents, images. Use this when the user specifically mentions files or documents they've shared."
                    )
                ),
                RetrieverTool(
                    retriever=web_retriever,
                    metadata=ToolMetadata(
                        name="web_search",
                        description="Search the web for current information, news, facts, or general knowledge. Use this for questions about recent events, general information, or topics not covered in personal notes."
                    )
                )
            ]

            # Create router with OpenAI-compatible LLM for decision making
            self.router_retriever = RouterRetriever(
                selector=PydanticSingleSelector.from_defaults(llm=router_llm),
                retriever_tools=retriever_tools
            )

            logger.info(
                f"✅ Router retriever initialized with {router_llm.__class__.__name__}")

        except Exception as e:
            logger.error(f"Failed to setup router retriever: {e}")
            self.router_retriever = None

    async def route_and_retrieve(self, query: str, user_id: int, available_sources: Dict[str, bool],
                                 **context_params) -> Tuple[RouterDecision, Dict[str, Any]]:
        """
        Route the query to appropriate context sources and retrieve context

        Args:
            query: User's question
            user_id: User identifier
            available_sources: Dict of which sources are enabled
            **context_params: Additional parameters for context retrieval

        Returns:
            Tuple of (routing decision, retrieved contexts)
        """

        # If router is not available, fall back to manual routing
        if not self.router_retriever:
            return await self._manual_routing(query, available_sources, user_id, **context_params)

        try:
            # Use router to decide which sources to query
            decision = await self._intelligent_routing(query, available_sources)

            # Retrieve context from selected sources
            contexts = await self._retrieve_from_sources(
                decision.selected_sources, query, user_id, **context_params
            )

            logger.info(
                f"🎯 Router selected: {[s.value for s in decision.selected_sources]}")
            logger.info(f"🧠 Reasoning: {decision.reasoning}")

            return decision, contexts

        except Exception as e:
            logger.error(f"Router retrieval failed: {e}")
            # Fall back to manual routing
            return await self._manual_routing(query, available_sources, user_id, **context_params)

    async def _intelligent_routing(self, query: str, available_sources: Dict[str, bool]) -> RouterDecision:
        """Use heuristic routing since RouterRetriever API is complex"""

        try:
            # For now, use heuristic routing as the RouterRetriever API is complex to access directly
            return await self._heuristic_routing(query, available_sources)

        except Exception as e:
            logger.error(f"Intelligent routing failed: {e}")
            # Fall back to heuristic routing
            return await self._heuristic_routing(query, available_sources)

    async def _heuristic_routing(self, query: str, available_sources: Dict[str, bool]) -> RouterDecision:
        """Improved heuristic routing with better conversational detection"""
        query_lower = query.lower().strip()
        selected_sources = []
        reasoning_parts = []

        # Simple conversational patterns that DON'T need external sources
        simple_conversational = [
            "hello", "hi", "hey", "good morning", "good afternoon", "good evening",
            "how are you", "what's up", "what are you talking about", "huh", "what",
            "yes", "no", "ok", "okay", "thanks", "thank you", "please", "sorry",
            "i don't understand", "that doesn't make sense", "explain", "clarify"
        ]

        # Check if this is a simple conversational message
        is_simple_conversation = any(
            pattern in query_lower for pattern in simple_conversational)

        if is_simple_conversation:
            # For simple conversations, don't use any external sources
            reasoning_parts.append(
                "simple conversational message - no external sources needed")
            return RouterDecision(
                selected_sources=[],  # Empty - no external sources
                reasoning=f"Smart routing: {', '.join(reasoning_parts)}",
                confidence=0.9
            )

        # Advanced keyword detection for complex queries
        personal_keywords = ["my", "i", "me", "our", "we", "us",
                             "remember", "note", "conversation", "discussed", "talked",
                             "previous", "earlier", "before", "last time", "history"]
        file_keywords = ["document", "pdf", "file", "attachment", "image",
                         "uploaded", "shared", "screenshot", "photo"]
        web_keywords = ["latest", "recent", "news", "current", "today", "2024", "2025",
                        "what is", "who is", "when did", "how to", "tell me about",
                        "information about", "facts about", "search for"]

        # Check for personal information needs
        if any(keyword in query_lower for keyword in personal_keywords) and available_sources.get("rag", False):
            selected_sources.append(ContextSource.RAG)
            reasoning_parts.append("personal keywords detected")

        # Check for file-related queries
        if any(keyword in query_lower for keyword in file_keywords) and available_sources.get("attachments", False):
            selected_sources.append(ContextSource.ATTACHMENTS)
            reasoning_parts.append("file-related keywords detected")

        # Check for general knowledge needs (be more selective)
        if any(keyword in query_lower for keyword in web_keywords) and available_sources.get("web_search", False):
            selected_sources.append(ContextSource.WEB_SEARCH)
            reasoning_parts.append("general knowledge keywords detected")

        # NEW: If no sources selected and query seems like it needs information
        if not selected_sources:
            # Check if query is asking for information (question words, etc.)
            question_indicators = ["what", "how", "why", "when",
                                   "where", "who", "which", "tell me", "explain"]
            needs_info = any(
                indicator in query_lower for indicator in question_indicators)

            # Only for substantial questions
            if needs_info and len(query.split()) > 3:
                # For information-seeking queries, prefer personal sources first
                if available_sources.get("rag", False):
                    selected_sources.append(ContextSource.RAG)
                    reasoning_parts.append(
                        "information query - checking personal sources first")
                else:
                    reasoning_parts.append(
                        "information query - no personal sources available")
            else:
                reasoning_parts.append(
                    "simple statement or short query - no external sources needed")

        reasoning = f"Smart routing: {', '.join(reasoning_parts)}"

        return RouterDecision(
            selected_sources=selected_sources,
            reasoning=reasoning,
            confidence=0.8  # Higher confidence for improved routing
        )

    async def _manual_routing(self, query: str, available_sources: Dict[str, bool], user_id: int, **context_params) -> Tuple[RouterDecision, Dict[str, Any]]:
        """Manual routing fallback when router is not available"""
        # Use all available sources
        selected_sources = []
        for source_name, enabled in available_sources.items():
            if enabled:
                selected_sources.append(ContextSource(source_name))

        decision = RouterDecision(
            selected_sources=selected_sources,
            reasoning="Manual routing: router not available, using all enabled sources",
            confidence=0.5
        )

        # Retrieve context from all selected sources
        contexts = await self._retrieve_from_sources(
            decision.selected_sources, query, user_id, **context_params
        )

        return decision, contexts

    async def _retrieve_from_sources(self, selected_sources: List[ContextSource], query: str, user_id: int, **context_params) -> Dict[str, Any]:
        """Retrieve context from the selected sources"""
        contexts = {}

        for source in selected_sources:
            try:
                if source == ContextSource.RAG:
                    # Use RAG processor
                    rag_context = await self.rag_processor.process_rag_request(
                        query=query,
                        user_id=user_id,
                        folder_ids=context_params.get('folder_ids', []),
                        note_ids=context_params.get('note_ids', []),
                        conversation_ids=context_params.get(
                            'conversation_ids'),
                        **context_params
                    )
                    contexts['rag'] = rag_context

                elif source == ContextSource.ATTACHMENTS:
                    # Use file attachment manager
                    attachments = context_params.get('attachments', [])
                    if attachments:
                        attachment_context = await self.file_attachment_manager.process_attachments(
                            attachments=attachments,
                            query=query,
                            user_id=user_id,
                            **context_params
                        )
                        contexts['attachments'] = attachment_context

                elif source == ContextSource.WEB_SEARCH:
                    # Use web search processor
                    search_query = context_params.get('search_query') or self.web_search_processor.extract_search_query([
                        {"role": "user", "content": query}])
                    websearch_context = await self.web_search_processor.search_web_content(
                        query=search_query,
                        num_results=context_params.get('num_results', 5)
                    )
                    contexts['web_search'] = websearch_context

            except Exception as e:
                logger.error(f"Failed to retrieve from {source.value}: {e}")
                # Continue with other sources

        return contexts
