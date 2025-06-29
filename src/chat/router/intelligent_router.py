"""
Intelligent Router - Pure Decision Layer (Per consultation)

This module uses LlamaIndex's RouterQueryEngine as a pure decision-making layer
that returns JSON decisions about which context sources to enable.
"""

import logging
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

try:
    from llama_index.core.selectors import LLMSingleSelector
    from llama_index.core.tools import ToolMetadata
    ROUTER_AVAILABLE = True
except ImportError:
    ROUTER_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class RouterDecision:
    """Pure router decision output"""
    enable_rag: bool
    enable_web_search: bool
    enable_attachments: bool
    enable_citations: bool  # NEW: Add citations support
    reason: str
    confidence: float


class IntelligentRouter:
    """
    Pure decision-making router using LlamaIndex LLMSingleSelector

    Simple tool selection - just picks which tool to use for the query.
    Returns JSON decisions about which sources to enable.
    Does NOT perform actual retrieval - that's handled by existing processors.
    """

    def __init__(self, provider_selector=None):
        self.provider_selector = provider_selector
        self.selector = None
        self.tools = []
        self._setup_router()

    def _setup_router(self):
        """Setup the LLM selector as pure decision layer - MUCH SIMPLER!"""
        if not ROUTER_AVAILABLE:
            error_msg = "🚨 CRITICAL: LLMSingleSelector imports not available! Check LlamaIndex installation!"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        logger.info("🔧 Setting up LLMSingleSelector - Simple tool selection...")

        try:
            # Get OpenAI-compatible LLM for selector
            router_llm = None
            if self.provider_selector:
                router_llm = self.provider_selector.get_router_compatible_llm()
                if router_llm:
                    logger.info(
                        "🎯 Using router-compatible LLM for tool selection")
                else:
                    error_msg = "🚨 CRITICAL: No router-compatible LLM available! Must have OpenAI/Azure-OpenAI LLM!"
                    logger.error(error_msg)
                    raise RuntimeError(error_msg)
            else:
                error_msg = "🚨 CRITICAL: No provider_selector available! Cannot get LLM for router!"
                logger.error(error_msg)
                raise RuntimeError(error_msg)

            # Create tool metadata for selection (no dummy engines needed!)
            self.tools = [
                ToolMetadata(
                    name="no_context",
                    description="Use this for greetings, chit-chat or questions \
            that can be answered without looking anything up."
                ),
                ToolMetadata(
                    name="knowledge_base",
                    description="Search the user’s own notes/chats **ONLY** when the \
            query explicitly references past discussions or personal content."
                ),
                ToolMetadata(
                    name="attachments",
                    description="Look at files/images the user attached **to THIS message**."
                ),
                ToolMetadata(
                    name="web_search",
                    description="Search the public internet for up-to-date facts or news."
                ),
            ]

            # Create simple LLM selector - just picks which tool to use!
            self.selector = LLMSingleSelector.from_defaults(llm=router_llm)

            logger.info(
                "✅ LLMSingleSelector initialized successfully - Simple and clean!")

        except Exception as e:
            error_msg = f"🚨 CRITICAL: Failed to setup LLMSingleSelector: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

    def decide(self, query: str, available_sources: Dict[str, bool],
               previous_messages: Optional[List[Dict]] = None,
               note_ids: Optional[List[int]] = None,
               folder_ids: Optional[List[int]] = None,
               conversation_ids: Optional[List[int]] = None) -> RouterDecision:
        """
        Make a pure routing decision using RouterQueryEngine ONLY

        ENHANCED RULES:
        1. File attachments ALWAYS have priority when present
        2. If note_ids, folder_ids, or conversation_ids are provided, FORCE ENABLE RAG
        3. File attachments and RAG can BOTH be enabled together when IDs are provided

        Args:
            query: User's question
            available_sources: Dict of which sources are enabled 
            previous_messages: Recent conversation context (for better decisions)
            note_ids: List of note IDs to search (FORCE ENABLES RAG)
            folder_ids: List of folder IDs to search (FORCE ENABLES RAG)
            conversation_ids: List of conversation IDs to search (FORCE ENABLES RAG)

        Returns:
            RouterDecision with enable flags and reasoning
        """

        # CRITICAL RULE: Force enable RAG if any IDs are provided
        force_enable_rag = bool(note_ids or folder_ids or conversation_ids)

        if force_enable_rag:
            logger.info(
                f"🎯 FORCE ENABLING RAG: note_ids={note_ids}, folder_ids={folder_ids}, conversation_ids={conversation_ids}")

        # ENHANCED ATTACHMENT PRIORITY RULE:
        # If attachments are available AND no specific IDs are provided, ONLY use attachments
        # If attachments are available AND specific IDs are provided, use BOTH attachments and RAG
        if available_sources.get("attachments", False):
            if not force_enable_rag:
                # Original behavior: Only attachments when no specific IDs
                logger.info(
                    "🎯 ATTACHMENT PRIORITY: File attachments detected - ONLY using attachments!")
                return RouterDecision(
                    enable_rag=False,        # Disable RAG - focus only on user's files
                    enable_web_search=False,  # Disable web search - focus only on user's files
                    enable_attachments=True,  # ONLY enable attachments when present
                    enable_citations=available_sources.get("citations", False),
                    reason="File attachments have priority - using ONLY user-provided content",
                    confidence=0.95
                )
            else:
                # NEW behavior: Use BOTH attachments and RAG when specific IDs are provided
                logger.info(
                    "🎯 ENHANCED MODE: File attachments + specific IDs detected - using BOTH attachments AND RAG!")
                return RouterDecision(
                    enable_rag=True,         # Enable RAG due to specific IDs
                    enable_web_search=False,  # Still disable web search to focus on user content
                    enable_attachments=True,  # Keep attachments enabled
                    enable_citations=available_sources.get("citations", False),
                    reason=f"Using BOTH attachments and RAG - specific content requested (note_ids={len(note_ids or [])}, folder_ids={len(folder_ids or [])}, conversation_ids={len(conversation_ids or [])})",
                    confidence=0.98
                )

        # FORCE RAG RULE: If specific IDs are provided but no attachments, force enable RAG
        if force_enable_rag:
            logger.info(
                f"🎯 FORCE RAG MODE: Specific IDs provided - force enabling RAG!")
            return RouterDecision(
                enable_rag=True,         # Force enable RAG due to specific IDs
                enable_web_search=False,  # Focus on user's specific content
                enable_attachments=False,  # No attachments available
                enable_citations=available_sources.get("citations", False),
                reason=f"Force enabling RAG due to specific content IDs (note_ids={len(note_ids or [])}, folder_ids={len(folder_ids or [])}, conversation_ids={len(conversation_ids or [])})",
                confidence=0.92
            )

        # FORCE LLMSingleSelector to work - simple and reliable!
        if not self.selector:
            error_msg = "❌ CRITICAL: LLMSingleSelector not available! This must be fixed!"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        logger.info(
            f"🎯 Using LLMSingleSelector for tool selection on query: '{query[:50]}...'")

        try:
            # Enhanced query with recent context (last ~3 turns)
            enhanced_query = query
            if previous_messages:
                recent_context = []
                for msg in previous_messages[-3:]:  # Last 3 messages
                    if msg.get('role') and msg.get('content'):
                        recent_context.append(
                            f"{msg['role']}: {msg['content'][:100]}...")

                if recent_context:
                    enhanced_query = f"Recent context: {' | '.join(recent_context)}\n\nCurrent question: {query}"

            # Get tool selection - SIMPLE!
            logger.info(
                f"📡 Querying LLMSingleSelector with: '{enhanced_query[:100]}...'")

            # selector.select returns a SelectorResult with .ind (index) and .reason
            selection_result = self.selector.select(self.tools, enhanced_query)

            logger.info(f"📨 Selection result: {selection_result}")
            logger.info(f"📊 Selected tool index: {selection_result.ind}")
            logger.info(f"📝 Selection reason: {selection_result.reason}")

            # Get the selected tool
            if 0 <= selection_result.ind < len(self.tools):
                selected_tool_metadata = self.tools[selection_result.ind]
                selected_tool_name = selected_tool_metadata.name
                logger.info(f"✅ Selected tool: {selected_tool_name}")

                # Map tool to decision with selector's reason
                return self._map_tool_to_decision(
                    selected_tool_name,
                    available_sources,
                    selection_result.reason,
                    note_ids,
                    folder_ids,
                    conversation_ids
                )
            else:
                logger.error(f"❌ Invalid tool index: {selection_result.ind}")
                return self._heuristic_routing(query, available_sources, note_ids, folder_ids, conversation_ids)

        except Exception as e:
            logger.error(
                f"🚨 LLMSingleSelector failed: {e} – falling back to heuristics")
            return self._heuristic_routing(query, available_sources, note_ids, folder_ids, conversation_ids)

            # Get router decision
            logger.info(
                f"📡 Querying RouterQueryEngine with: '{enhanced_query[:100]}...'")
            response = self.router_engine.query(enhanced_query)
            logger.info(f"📨 Router response type: {type(response)}")
            logger.info(f"📨 Router response attributes: {dir(response)}")

            # Parse the router's decision - try multiple approaches
            decision_json = getattr(response, 'raw_output', None)
            logger.info(f"📊 Raw output: {decision_json}")

            if decision_json:
                try:
                    parsed = json.loads(decision_json)
                    logger.info(f"✅ Parsed JSON decision: {parsed}")
                    return self._parse_router_response(parsed, available_sources)
                except (json.JSONDecodeError, KeyError) as e:
                    logger.warning(f"❌ Failed to parse JSON: {e}")

            # Fallback: extract tool name from response metadata (LlamaIndex approach)
            tool = (response.metadata.get("chosen_tool") or
                    response.metadata.get("selected_tool") or
                    response.metadata.get("tool_name"))
            logger.info(f"🔧 Selected tool from metadata: {tool}")

            if tool:
                return self._map_tool_to_decision(tool, available_sources)

            # Another fallback: get tool name from first word of response (stock router approach)
            if hasattr(response, 'response') and response.response:
                response_text = str(response.response)
                first_word = response_text.split(
                )[0] if response_text.split() else None
                logger.info(f"� First word from response: {first_word}")
                if first_word and first_word in ["knowledge_base", "attachment", "web_search"]:
                    return self._map_tool_to_decision(first_word, available_sources)

            # Check if response has any tool information
            if hasattr(response, 'source_nodes') and response.source_nodes:
                logger.info(f"� Source nodes: {response.source_nodes}")

            logger.warning(
                "❌ Could not extract decision from RouterQueryEngine - falling back to heuristics")
            logger.error(
                "� Router failed, using fallback to keep chat operational")

            # Graceful fallback instead of crashing
            return self._heuristic_routing(query, available_sources, note_ids, folder_ids, conversation_ids)

        except Exception as e:
            logger.error(f"🚨 Router failed: {e} – falling back to heuristics")
            return self._heuristic_routing(query, available_sources, note_ids, folder_ids, conversation_ids)

    def _parse_router_response(self, parsed_json: Dict[str, Any], available_sources: Dict[str, bool]) -> RouterDecision:
        """Parse the JSON response from RouterQueryEngine"""
        # Expected format from consultation:
        # {
        #   "enable_rag": false,
        #   "enable_web_search": true,
        #   "enable_attachments": true,
        #   "reason": "...",
        #   "confidence": 0.87
        # }

        enable_rag = parsed_json.get(
            "enable_rag", False) and available_sources.get("rag", False)
        enable_web_search = parsed_json.get(
            "enable_web_search", False) and available_sources.get("web_search", False)
        enable_attachments = parsed_json.get(
            "enable_attachments", False) and available_sources.get("attachments", False)
        reason = parsed_json.get("reason", "Router JSON decision")
        confidence = parsed_json.get("confidence", 0.8)

        return RouterDecision(
            enable_rag=enable_rag,
            enable_web_search=enable_web_search,
            enable_attachments=enable_attachments,
            reason=reason,
            confidence=confidence
        )

    def _map_tool_to_decision(self, selected_tool: str, available_sources: Dict[str, bool],
                              reason: str = None,
                              note_ids: Optional[List[int]] = None,
                              folder_ids: Optional[List[int]] = None,
                              conversation_ids: Optional[List[int]] = None) -> RouterDecision:
        """Map selected tool name to enable flags, respecting force RAG rules"""

        # Check if we should force enable RAG due to specific IDs
        force_enable_rag = bool(note_ids or folder_ids or conversation_ids)

        enable_rag = False
        enable_web_search = False
        enable_attachments = False
        enable_citations = available_sources.get("citations", False)

        if not reason:
            reason = f"LLM selected tool: {selected_tool}"

        if selected_tool == "no_context":
            # No context needed - but still force RAG if specific IDs are provided
            if force_enable_rag:
                enable_rag = True
                reason = f"LLM selected no_context but force enabling RAG due to specific IDs (note_ids={len(note_ids or [])}, folder_ids={len(folder_ids or [])}, conversation_ids={len(conversation_ids or [])})"
                logger.info(
                    "🎯 LLM selected no_context but force enabling RAG due to specific IDs")
            else:
                logger.info(
                    "🎯 LLM selected no_context - answering directly without retrieval")
        elif selected_tool == "knowledge_base" and available_sources.get("rag", False):
            enable_rag = True
        elif selected_tool in ["attachments", "attachment"] and available_sources.get("attachments", False):
            enable_attachments = True
            # If specific IDs are provided, also enable RAG alongside attachments
            if force_enable_rag:
                enable_rag = True
                reason = f"LLM selected attachments + force enabling RAG due to specific IDs (note_ids={len(note_ids or [])}, folder_ids={len(folder_ids or [])}, conversation_ids={len(conversation_ids or [])})"
                logger.info(
                    "🎯 LLM selected attachments + force enabling RAG due to specific IDs")
        elif selected_tool == "web_search" and available_sources.get("web_search", False):
            enable_web_search = True
            # If specific IDs are provided, prefer RAG over web search
            if force_enable_rag:
                enable_rag = True
                enable_web_search = False  # Override: focus on user's specific content instead of web
                reason = f"LLM selected web_search but force enabling RAG instead due to specific IDs (note_ids={len(note_ids or [])}, folder_ids={len(folder_ids or [])}, conversation_ids={len(conversation_ids or [])})"
                logger.info(
                    "🎯 LLM selected web_search but force enabling RAG instead due to specific IDs")
        else:
            # LLM selected invalid tool or tool not available - fall back gracefully
            logger.warning(
                f"LLM selected unavailable tool: {selected_tool}. Available: {available_sources}")
            return self._heuristic_routing("", available_sources, note_ids, folder_ids, conversation_ids)

        logger.info(
            f"🎯 Final decision: RAG={enable_rag}, Web={enable_web_search}, Attachments={enable_attachments}, Citations={enable_citations}")

        return RouterDecision(
            enable_rag=enable_rag,
            enable_web_search=enable_web_search,
            enable_attachments=enable_attachments,
            enable_citations=enable_citations,
            reason=reason,
            confidence=0.85
        )

    def _heuristic_routing(self, query: str, available_sources: Dict[str, bool],
                           note_ids: Optional[List[int]] = None,
                           folder_ids: Optional[List[int]] = None,
                           conversation_ids: Optional[List[int]] = None) -> RouterDecision:
        """
        Cheap heuristic fallback when RouterQueryEngine fails

        This ensures the chat keeps running even if the LLM routing fails.
        Now also respects force RAG rules for specific IDs.
        """
        logger.info(
            f"🔄 Using heuristic fallback routing for query: '{query[:50]}...'")

        query_lower = query.lower()

        # FORCE RAG RULE: If specific IDs are provided, force enable RAG
        force_enable_rag = bool(note_ids or folder_ids or conversation_ids)

        # Default values
        enable_rag = available_sources.get("rag", False)
        enable_web_search = False
        enable_attachments = available_sources.get("attachments", False)
        enable_citations = available_sources.get("citations", False)
        reason = "Heuristic fallback routing"

        # Apply force RAG rule
        if force_enable_rag:
            enable_rag = True
            reason = f"Heuristic + Force RAG due to specific IDs (note_ids={len(note_ids or [])}, folder_ids={len(folder_ids or [])}, conversation_ids={len(conversation_ids or [])})"
            logger.info(f"🎯 Heuristic: Force enabling RAG due to specific IDs")

        # Check for current events/real-time queries (enable web search, but not if force RAG is active)
        web_keywords = [
            "latest", "recent", "current", "today", "now", "2024", "2025",
            "breaking", "news", "weather", "stock", "price"
        ]
        if any(keyword in query_lower for keyword in web_keywords) and not force_enable_rag:
            enable_web_search = available_sources.get("web_search", False)
            reason = "Heuristic: Current events/real-time query detected"

        # Check for attachment references
        attachment_keywords = [
            "this file", "this document", "this image", "uploaded", "attached",
            "analyze this", "look at this", "this screenshot"
        ]
        if any(keyword in query_lower for keyword in attachment_keywords):
            enable_attachments = available_sources.get("attachments", False)
            if force_enable_rag:
                reason = f"Heuristic: Attachment reference + Force RAG due to specific IDs"
            else:
                reason = "Heuristic: Attachment reference detected"

        logger.info(
            f"🎯 Heuristic decision: RAG={enable_rag}, Web={enable_web_search}, Attachments={enable_attachments}, Citations={enable_citations}")

        return RouterDecision(
            enable_rag=enable_rag,
            enable_web_search=enable_web_search,
            enable_attachments=enable_attachments,
            enable_citations=enable_citations,
            reason=reason,
            confidence=0.6  # Lower confidence for heuristic routing
        )
