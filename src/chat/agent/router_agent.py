"""
Router Agent - Responsible for routing queries to appropriate tools

This agent analyzes incoming queries and determines which other agents
should be activated to handle the request.
"""

from typing import Dict, Any
from dataclasses import asdict
import logging

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
        
        # Enable agents based on router decision
        # IMPORTANT: Don't enable RAG if attachments are present - attachment content takes priority
        if router_decision.selected_tool in ["knowledge_base_notes", "knowledge_base_conversations", "knowledge_base_full"]:
            if "rag" not in enabled_agents and not has_attachments:
                enabled_agents.append("rag")
        
        if router_decision.selected_tool == "web_search":
            enabled_agents.append("web_search")
        
        # Legacy check - keep for backward compatibility
        if router_decision.selected_tool == "attachments" and "attachment" not in enabled_agents:
            enabled_agents.append("attachment")
        
        # Check for code interpreter requests
        code_keywords = ['code', 'python', 'execute', 'calculate', 'plot', 'graph', 'analyze data', 'statistics', 'math', 'solve']
        query_lower = query.lower()
        if any(keyword in query_lower for keyword in code_keywords) or '```python' in query or 'import ' in query:
            enabled_agents.append("code_interpreter")
        
        if request.get("enable_citations", True):
            enabled_agents.append("citation")
        
        # Transform query if needed (for now, use original query)
        condensed_query = query
        
        return {
            "router_decision": asdict(router_decision),
            "original_query": query,
            "condensed_query": condensed_query,  # Add condensed query
            "enabled_agents": enabled_agents,
            "model": request.get("model", "gpt-4o-mini"),
            "search_type": router_decision.search_type if hasattr(router_decision, 'search_type') else "knowledge_base"
        }