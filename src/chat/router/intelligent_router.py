import json
import logging
import asyncio
import os
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


@dataclass
class RouterDecision:
    selected_tool: str
    search_type: str
    confidence: float
    reasoning: str
    query_classification: str


class IntelligentRouter:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        # Clean, correct tools array
        self.tools = [
            "no_context",
            "knowledge_base_notes",
            "knowledge_base_conversations",
            "knowledge_base_full",
            "attachments",
            "web_search"
        ]

        self.tool_descriptions = {
            "no_context": "For general questions that don't require specific user data or context",
            "knowledge_base_notes": "For queries specifically about user's notes, documents, or written content",
            "knowledge_base_conversations": "For queries specifically about user's chat history or conversations",
            "knowledge_base_full": "For queries that need both notes and conversations, or general knowledge base search",
            "attachments": "For queries about images, files, or media attachments",
            "web_search": "For current events, real-time information, or topics not in the knowledge base"
        }

    async def route_query(self, query: str, user_id: str, conversation_history: Optional[List[Dict]] = None) -> RouterDecision:
        """Route a query to the appropriate tool using LLM-based routing."""
        try:
            llm_decision = await self._llm_route(query, conversation_history)
            if llm_decision:
                logger.info(
                    f"LLM routing successful: {llm_decision.selected_tool}")
                return llm_decision
        except Exception as e:
            logger.warning(f"LLM routing failed: {e}")

        # Fallback to heuristic routing
        logger.info("Falling back to heuristic routing")
        return self._heuristic_route(query)

    async def _llm_route(self, query: str, conversation_history: Optional[List[Dict]] = None) -> Optional[RouterDecision]:
        """Use LLM to intelligently route the query."""

        # Build tools description for prompt
        tools_desc = "\n".join([f"{i}: {tool} - {desc}"
                               for i, (tool, desc) in enumerate(self.tool_descriptions.items())])

        system_prompt = f"""You are a query router that selects the best tool for answering user questions.

Available tools:
{tools_desc}

Guidelines:
- Use tool 1 (knowledge_base_notes) for queries about "my notes", "documents I saved", "things I wrote"
- Use tool 2 (knowledge_base_conversations) for queries about "our conversation", "what we discussed", "chat history"
- Use tool 3 (knowledge_base_full) for general knowledge queries that might need both sources
- Use tool 4 (attachments) for queries about images, files, or media
- Use tool 5 (web_search) for current events, real-time info, or recent developments
- Use tool 0 (no_context) for general questions that don't need user-specific data

Return a JSON object with:
- tool_index: number (0-5)
- confidence: float (0.0-1.0)
- reasoning: string explaining your choice
- query_classification: string describing the query type

Example response:
{{"tool_index": 1, "confidence": 0.9, "reasoning": "User is asking about their notes", "query_classification": "notes_query"}}"""

        user_prompt = f"Query: {query}"

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=200
            )

            content = response.choices[0].message.content.strip()
            logger.debug(f"LLM router response: {content}")

            # Parse JSON response
            try:
                result = json.loads(content)
                tool_index = result.get("tool_index")

                if tool_index is not None and 0 <= tool_index < len(self.tools):
                    selected_tool = self.tools[tool_index]
                    decision = self._map_tool_to_decision(
                        selected_tool,
                        result.get("confidence", 0.8),
                        result.get("reasoning", "LLM routing"),
                        result.get("query_classification", "general")
                    )
                    logger.info(
                        f"LLM selected tool {tool_index}: {selected_tool}")
                    return decision
                else:
                    logger.warning(
                        f"Invalid tool index from LLM: {tool_index}")

            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse LLM response as JSON: {e}")

        except Exception as e:
            logger.error(f"Error in LLM routing: {e}")

        return None

    def _heuristic_route(self, query: str) -> RouterDecision:
        """Fallback heuristic routing based on keyword matching."""
        query_lower = query.lower()

        # Notes-specific keywords
        notes_keywords = ["my notes", "documents",
                          "saved", "wrote", "written", "note"]
        if any(keyword in query_lower for keyword in notes_keywords):
            return self._map_tool_to_decision("knowledge_base_notes", 0.7, "Heuristic: notes keywords", "notes_query")

        # Conversation-specific keywords
        conv_keywords = ["our conversation", "we discussed", "discuss", "chat",
                         "talked about", "conversation history", "we talked", "our chat"]
        if any(keyword in query_lower for keyword in conv_keywords):
            return self._map_tool_to_decision("knowledge_base_conversations", 0.7, "Heuristic: conversation keywords", "conversation_query")

        # Attachment keywords
        attachment_keywords = ["image", "picture",
                               "file", "photo", "attachment", "uploaded"]
        if any(keyword in query_lower for keyword in attachment_keywords):
            return self._map_tool_to_decision("attachments", 0.7, "Heuristic: attachment keywords", "attachment_query")

        # Web search keywords
        web_keywords = ["current", "recent", "latest",
                        "news", "today", "happening now"]
        if any(keyword in query_lower for keyword in web_keywords):
            return self._map_tool_to_decision("web_search", 0.7, "Heuristic: web search keywords", "web_query")

        # Default to full knowledge base
        return self._map_tool_to_decision("knowledge_base_full", 0.6, "Heuristic: default fallback", "general_query")

    def _map_tool_to_decision(self, tool_name: str, confidence: float, reasoning: str, classification: str) -> RouterDecision:
        """Map tool name to RouterDecision with correct search_type."""

        # Map tool names to search types
        search_type_mapping = {
            "no_context": "none",
            "knowledge_base_notes": "notes",
            "knowledge_base_conversations": "conversations",
            "knowledge_base_full": "mixed",
            "attachments": "attachments",
            "web_search": "web"
        }

        search_type = search_type_mapping.get(tool_name, "mixed")

        return RouterDecision(
            selected_tool=tool_name,
            search_type=search_type,
            confidence=confidence,
            reasoning=reasoning,
            query_classification=classification
        )

    def get_available_tools(self) -> List[str]:
        """Return list of available tools."""
        return self.tools.copy()

    def get_tool_description(self, tool_name: str) -> Optional[str]:
        """Get description for a specific tool."""
        return self.tool_descriptions.get(tool_name)
