"""
Query Transformation Module using LlamaIndex TransformQueryEngine

This module transforms user queries by adding conversational context from the last 3 messages,
creating contextually enriched queries that improve RAG retrieval, attachment similarity search,
and web search results. Only activates when there are multiple messages in the conversation.
"""

import logging
from typing import List, Dict, Any, Optional
from llama_index.core import VectorStoreIndex, Document
from llama_index.core.query_engine import TransformQueryEngine
from llama_index.core.indices.query.query_transform.base import LLMQueryTransform
from llama_index.core.llms import LLM
from chat.provider.llm_provider import LLMProviderSelector

logger = logging.getLogger(__name__)


class QueryTransformer:
    """
    Transforms user queries using conversational context to create more effective queries
    for downstream processors (RAG, attachments, web search).

    Only transforms queries when there are 2 or more messages in conversation history.
    """

    def __init__(self, provider_selector: LLMProviderSelector):
        self.provider_selector = provider_selector
        self._transform_engine = None
        self._llm = None

    def _get_llm(self) -> LLM:
        """Get LLM for query transformation - prefer fast, cost-effective model"""
        if not self._llm:
            try:
                # Use GPT-4.1-nano for speed and cost efficiency
                provider_enum, llm = self.provider_selector.select_provider_and_model(
                    "azure_inference", "gpt-4.1-nano"
                )
                self._llm = llm
                logger.info(
                    "✅ Query transformer using GPT-4.1-nano for efficiency")
            except Exception as e:
                # Fallback to OpenAI if Azure fails
                logger.warning(
                    f"Azure failed for query transformer, falling back to OpenAI: {e}")
                provider_enum, llm = self.provider_selector.select_provider_and_model(
                    "openai", "gpt-4o-mini"
                )
                self._llm = llm
                logger.info(
                    "✅ Query transformer using OpenAI GPT-4o-mini as fallback")

        return self._llm

    def _get_transform_engine(self) -> TransformQueryEngine:
        """Get or create the TransformQueryEngine"""
        if not self._transform_engine:
            llm = self._get_llm()

            # Create a dummy index - this won't be used for actual querying
            dummy_doc = Document(
                text="This is a dummy document for query transformation.")
            dummy_index = VectorStoreIndex.from_documents([dummy_doc])
            base_query_engine = dummy_index.as_query_engine(llm=llm)

            # Create the condense transform with default "stand-alone question" prompt
            condense_transform = LLMQueryTransform(llm=llm)

            # Wrap with TransformQueryEngine
            self._transform_engine = TransformQueryEngine(
                base_query_engine,
                query_transform=condense_transform
            )
            logger.info("✅ TransformQueryEngine initialized")

        return self._transform_engine

    def _extract_conversation_context(self, messages: List[Dict[str, Any]]) -> List[str]:
        """
        Extract the last 3 messages from conversation history for context

        Args:
            messages: List of message dictionaries with 'role' and 'content'

        Returns:
            List of message content strings
        """
        if not messages:
            return []

        # Take last 3 messages maximum, but exclude the current user message
        # We want the context messages, not including the current query
        context_messages = []
        for msg in messages[-3:]:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            if content:
                # Format as "role: content" for better context
                context_messages.append(f"{role}: {content}")

        return context_messages

    def _extract_current_query(self, messages: List[Dict[str, Any]]) -> str:
        """Extract the last user message as the current query"""
        for message in reversed(messages):
            if message.get('role') == 'user':
                return message.get('content', '')
        return ''

    async def transform_query(self,
                              original_query: str,
                              messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Transform the original query using conversation context

        Args:
            original_query: The original user query
            messages: Full conversation history

        Returns:
            Dictionary with:
            - condensed_query: The contextually enriched query
            - original_query: The original query
            - context_messages_used: Number of messages used for context
            - transformation_success: Whether transformation succeeded
        """
        try:
            # Only transform if there are 2 or more messages (indicating conversation history)
            if len(messages) < 2:
                logger.info(
                    "Single message conversation, skipping query transformation")
                return {
                    "condensed_query": original_query,
                    "original_query": original_query,
                    "context_messages_used": 0,
                    "transformation_success": False,
                    "fallback_reason": "single_message"
                }

            # Extract conversation context (last 3 messages excluding current)
            context_messages = self._extract_conversation_context(
                messages[:-1])  # Exclude last message
            current_query = self._extract_current_query(messages)

            if not context_messages:
                logger.info(
                    "No conversation context available, using original query")
                return {
                    "condensed_query": original_query,
                    "original_query": original_query,
                    "context_messages_used": 0,
                    "transformation_success": False,
                    "fallback_reason": "no_context"
                }

            # Use current query if available, otherwise fall back to original
            query_to_transform = current_query if current_query else original_query

            # Get the transform engine
            transform_engine = self._get_transform_engine()

            logger.info(
                f"🔄 Transforming query with {len(context_messages)} context messages")
            logger.info(f"Original query: {query_to_transform[:100]}...")

            # Transform the query with chat history
            condensed_query = transform_engine.transform_query(
                query_to_transform,
                chat_history=context_messages
            )

            logger.info(f"✅ Query transformation successful")
            logger.info(f"Condensed query: {condensed_query[:100]}...")

            return {
                "condensed_query": condensed_query,
                "original_query": original_query,
                "context_messages_used": len(context_messages),
                "transformation_success": True
            }

        except Exception as e:
            logger.error(f"❌ Query transformation failed: {e}")
            logger.info("Falling back to original query")

            return {
                "condensed_query": original_query,
                "original_query": original_query,
                "context_messages_used": 0,
                "transformation_success": False,
                "fallback_reason": f"error: {str(e)}"
            }

    def transform_query_sync(self,
                             original_query: str,
                             messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Synchronous version of transform_query for compatibility
        """
        try:
            # Only transform if there are 2 or more messages (indicating conversation history)
            if len(messages) < 2:
                logger.info(
                    "Single message conversation, skipping query transformation")
                return {
                    "condensed_query": original_query,
                    "original_query": original_query,
                    "context_messages_used": 0,
                    "transformation_success": False,
                    "fallback_reason": "single_message"
                }

            # Extract conversation context (last 3 messages excluding current)
            context_messages = self._extract_conversation_context(
                messages[:-1])  # Exclude last message
            current_query = self._extract_current_query(messages)

            if not context_messages:
                logger.info(
                    "No conversation context available, using original query")
                return {
                    "condensed_query": original_query,
                    "original_query": original_query,
                    "context_messages_used": 0,
                    "transformation_success": False,
                    "fallback_reason": "no_context"
                }

            # Use current query if available, otherwise fall back to original
            query_to_transform = current_query if current_query else original_query

            # Get the transform engine
            transform_engine = self._get_transform_engine()

            logger.info(
                f"🔄 Transforming query with {len(context_messages)} context messages")
            logger.info(f"Original query: {query_to_transform[:100]}...")

            # Transform the query with chat history (synchronous)
            condensed_query = transform_engine.transform_query(
                query_to_transform,
                chat_history=context_messages
            )

            logger.info(f"✅ Query transformation successful")
            logger.info(f"Condensed query: {condensed_query[:100]}...")

            return {
                "condensed_query": condensed_query,
                "original_query": original_query,
                "context_messages_used": len(context_messages),
                "transformation_success": True
            }

        except Exception as e:
            logger.error(f"❌ Query transformation failed: {e}")
            logger.info("Falling back to original query")

            return {
                "condensed_query": original_query,
                "original_query": original_query,
                "context_messages_used": 0,
                "transformation_success": False,
                "fallback_reason": f"error: {str(e)}"
            }
