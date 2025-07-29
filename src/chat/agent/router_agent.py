"""
Router Agent - Responsible for routing queries to appropriate tools

This agent analyzes incoming queries and determines which other agents
should be activated to handle the request.
"""

from typing import Dict, Any
from dataclasses import asdict
import logging
import re

from .base import BaseAgent
from ..router.intelligent_router import IntelligentRouter
from ..query.query_transformer import QueryTransformer
from ..provider.llm_provider import LLMProviderSelector

logger = logging.getLogger(__name__)


class RouterAgent(BaseAgent):
    """Agent responsible for routing queries to appropriate tools"""
    
    def __init__(self, llm_provider_manager: LLMProviderSelector):
        super().__init__()
        self.router = IntelligentRouter()
        self.query_transformer = QueryTransformer(llm_provider_manager)
    
    async def run(self, request: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Route the query and determine which agents should be activated"""
        
        # Get the latest user message
        user_messages = [msg for msg in request["messages"] if msg["role"] == "user"]
        if not user_messages:
            raise ValueError("No user messages found in request")
        
        query = user_messages[-1]["content"]
        
        # Check if attachments are present BEFORE routing
        # Note: empty list should not count as having attachments
        attachments = request.get("attachments", [])
        has_attachments = bool(attachments and len(attachments) > 0)
        
        # Check if explicit note_ids or folder_ids are provided
        has_explicit_note_ids = bool(request.get("note_ids"))
        has_explicit_folder_ids = bool(request.get("folder_ids"))
        
        # Route the query with attachment information
        router_decision = await self.router.route_query(
            query, str(request["user_id"]), request["messages"][-3:], has_attachments
        )
        
        # Determine which agents should be enabled based on router decision
        enabled_agents = ["response"]  # Always include response agent
        
        # PRIORITY: If attachments are present, always enable attachment agent
        if has_attachments:
            enabled_agents.append("attachment")
            # Do NOT automatically enable RAG when attachments are present
            # The attachment content should be the primary source
        
        # Enable agents based on router decision AND query content
        # Support mixed agent scenarios by checking multiple conditions
        query_lower = query.lower()
        
        # Context search check (notes and conversations)
        context_keywords = ['my notes', 'my documents', 'search notes', 'find in notes', 'remember', 'recall', 'what did i', 'based on my', 'in my knowledge', 'conversation', 'discussed', 'talked about', 'summarize my', 'summary of my', 'analyze my', 'review my', 'go through my', 'check my', 'look at my', 'read my', 'from my notes', 'in my notes']
        note_id_pattern = r'note\s*(?:id\s*)?(\d+)'
        conversation_id_pattern = r'conversation\s*(?:id\s*)?(\d+)'
        
        # ALWAYS enable context search if explicit note_ids or folder_ids are provided
        if has_explicit_note_ids or has_explicit_folder_ids:
            logger.info(f"🎯 Explicit IDs provided - enabling context search (note_ids: {has_explicit_note_ids}, folder_ids: {has_explicit_folder_ids})")
            if "context_search" not in enabled_agents:
                enabled_agents.append("context_search")
        elif (router_decision.selected_tool in ["knowledge_base_notes", "knowledge_base_conversations", "knowledge_base_full"] or
              any(keyword in query_lower for keyword in context_keywords) or
              re.search(note_id_pattern, query_lower) or
              re.search(conversation_id_pattern, query_lower)):
            if "context_search" not in enabled_agents:
                enabled_agents.append("context_search")
        
        # Web search check
        web_keywords = ['current', 'latest', 'today', 'recent', '2025', '2024', 'news', 'update', 'trend', 'search web', 'online', 'internet']
        if (router_decision.selected_tool == "web_search" or
            any(keyword in query_lower for keyword in web_keywords)):
            enabled_agents.append("web_search")
        
        # File attachment check - only when attachments are present
        if router_decision.selected_tool == "attachments" and "attachment" not in enabled_agents:
            enabled_agents.append("attachment")
        
        # Check for code interpreter requests
        code_keywords = ['code', 'python', 'execute', 'calculate', 'plot', 'graph', 'chart', 'visualiz', 'analyze data', 'statistics', 'math', 'solve', 'fibonacci', 'bar chart']
        if any(keyword in query_lower for keyword in code_keywords) or '```python' in query or 'import ' in query:
            enabled_agents.append("code_interpreter")
        
        # Note: Citation is now part of response agent, not a separate agent
        
        # Transform query if needed (for now, use original query)
        condensed_query = query
        
        return {
            "router_decision": asdict(router_decision),
            "original_query": query,
            "condensed_query": condensed_query,  # Add condensed query
            "enabled_agents": enabled_agents,
            "model": request.get("model", "gpt-4.1-nano"),
            "search_type": router_decision.search_type if hasattr(router_decision, 'search_type') else "knowledge_base",
            "has_explicit_ids": has_explicit_note_ids or has_explicit_folder_ids,
            "explicit_note_ids": request.get("note_ids") if has_explicit_note_ids else None,
            "explicit_folder_ids": request.get("folder_ids") if has_explicit_folder_ids else None
        }