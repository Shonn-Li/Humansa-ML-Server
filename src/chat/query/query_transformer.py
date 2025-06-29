"""
Query Transformation Module using LlamaIndex CondenseQuestionChatEngine

This module transforms user queries by adding conversational context from the last 3 messages,
creating contextually enriched queries that improve RAG retrieval, attachment similarity search,
and web search results. Only activates when there are multiple messages in the conversation.
"""

import logging
from typing import List, Dict, Any, Optional
from llama_index.core import VectorStoreIndex, Document
from llama_index.core.chat_engine import CondenseQuestionChatEngine
from llama_index.core.base.llms.types import ChatMessage
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
        self._condense_chat_engine = None
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

    def _get_condense_chat_engine(self) -> CondenseQuestionChatEngine:
        """Get or create the CondenseQuestionChatEngine with placeholder query engine"""
        if not self._condense_chat_engine:
            llm = self._get_llm()

            # Create a dummy/placeholder index and query engine
            # This is required by CondenseQuestionChatEngine but won't be used for actual retrieval
            dummy_doc = Document(
                text="This is a dummy document for query condensation.")
            dummy_index = VectorStoreIndex.from_documents([dummy_doc])
            placeholder_query_engine = dummy_index.as_query_engine(llm=llm)

            # Create the CondenseQuestionChatEngine with the placeholder
            self._condense_chat_engine = CondenseQuestionChatEngine.from_defaults(
                query_engine=placeholder_query_engine,
                llm=llm,
                verbose=False
            )
            logger.info(
                "✅ CondenseQuestionChatEngine initialized with placeholder query engine")

        return self._condense_chat_engine

    def _extract_conversation_context(self, messages: List[Dict[str, Any]]) -> List[ChatMessage]:
        """
        Extract the last 3 messages from conversation history for context

        Args:
            messages: List of message dictionaries with 'role' and 'content'

        Returns:
            List of ChatMessage objects for LlamaIndex (excluding the current/last user message)
        """
        if not messages or len(messages) <= 1:
            return []

        # Take last 3 messages maximum, excluding the current/last message
        recent_messages = messages[-4:-
                                   1] if len(messages) >= 4 else messages[:-1]

        chat_messages = []
        for msg in recent_messages:
            role = msg.get('role', 'user')
            content = msg.get('content', '').strip()

            if content:
                # Use string constants for roles instead of MessageRole enum
                if role == 'system':
                    message_role = 'system'
                elif role == 'assistant':
                    message_role = 'assistant'
                else:
                    message_role = 'user'

                chat_messages.append(ChatMessage(
                    role=message_role, content=content))

        return chat_messages

    def _extract_last_user_message(self, messages: List[Dict[str, Any]]) -> str:
        """Extract the last user message from the conversation"""
        for message in reversed(messages):
            if message.get('role') == 'user':
                return message.get('content', '')
        return ''

    async def transform_query(self,
                              original_query: str,
                              messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Transform the original query using conversation context

        TEMPORARILY DISABLED: Returns original query without transformation
        for better performance while keeping all code for future use.

        Args:
            original_query: The original user query
            messages: Full conversation history

        Returns:
            Dictionary with:
            - condensed_query: The contextually enriched query (currently same as original)
            - original_query: The original query
            - context_messages_used: Number of messages used for context
            - transformation_success: Whether transformation succeeded
        """

        # TEMPORARY: Skip transformation for better performance
        # TODO: Re-enable when condensed query approach is optimized
        logger.info(
            "⚡ Query transformation temporarily disabled - using original query")
        return {
            "condensed_query": original_query,
            "original_query": original_query,
            "context_messages_used": 0,
            "transformation_success": False,
            "fallback_reason": "temporarily_disabled"
        }

        # ORIGINAL CODE PRESERVED FOR FUTURE USE (COMMENTED OUT):
        # ========================================================
        # try:
        #     # Check if we have enough messages for transformation
        #     if len(messages) <= 1:
        #         logger.info("📝 Single message conversation - skipping query transformation")
        #         return {
        #             "condensed_query": original_query,
        #             "original_query": original_query,
        #             "context_messages_used": 0,
        #             "transformation_success": False,
        #             "fallback_reason": "single_message"
        #         }
        #
        #     # Extract conversation context (last 3 messages, excluding current)
        #     context_messages = self._extract_conversation_context(messages)
        #
        #     if not context_messages:
        #         logger.info("📝 No conversation context available, using original query")
        #         return {
        #             "condensed_query": original_query,
        #             "original_query": original_query,
        #             "context_messages_used": 0,
        #             "transformation_success": False,
        #             "fallback_reason": "no_context"
        #         }
        #
        #     # Get the condense chat engine
        #     condense_engine = self._get_condense_chat_engine()
        #
        #     # Get the current query
        #     current_query = self._extract_last_user_message(messages)
        #     if not current_query:
        #         current_query = original_query
        #
        #     logger.info(f"🔄 Transforming query with {len(context_messages)} context messages")
        #     logger.info(f"Original query: {current_query[:100]}...")
        #
        #     # Reset chat history and add context
        #     condense_engine.reset()
        #     for msg in context_messages:
        #         condense_engine.chat_history.append(msg)
        #
        #     # Generate the condensed query using the chat engine
        #     response = await condense_engine.achat(current_query)
        #     condensed_query = response.response
        #
        #     logger.info(f"✅ Query transformation successful")
        #     logger.info(f"🎯 Condensed query: {condensed_query[:100]}...")
        #
        #     return {
        #         "condensed_query": condensed_query,
        #         "original_query": original_query,
        #         "context_messages_used": len(context_messages),
        #         "transformation_success": True
        #     }
        #
        # except Exception as e:
        #     logger.error(f"❌ Query transformation failed: {e}")
        #     logger.info("Falling back to original query")
        #
        #     return {
        #         "condensed_query": original_query,
        #         "original_query": original_query,
        #         "context_messages_used": 0,
        #         "transformation_success": False,
        #         "fallback_reason": f"error: {str(e)}"
        #     }

    def transform_query_sync(self,
                             original_query: str,
                             messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Synchronous version of transform_query for compatibility

        TEMPORARILY DISABLED: Returns original query without transformation
        for better performance while keeping all code for future use.
        """

        # TEMPORARY: Skip transformation for better performance
        # TODO: Re-enable when condensed query approach is optimized
        logger.info(
            "⚡ Query transformation (sync) temporarily disabled - using original query")
        return {
            "condensed_query": original_query,
            "original_query": original_query,
            "context_messages_used": 0,
            "transformation_success": False,
            "fallback_reason": "temporarily_disabled"
        }

        # ORIGINAL CODE PRESERVED FOR FUTURE USE:
        # ========================================
        # try:
        #     # Check if we have enough messages for transformation
        #     if len(messages) <= 1:
        #         logger.info("📝 Single message conversation - skipping query transformation")
        #         return {
        #             "condensed_query": original_query,
        #             "original_query": original_query,
        #             "context_messages_used": 0,
        #             "transformation_success": False,
        #             "fallback_reason": "single_message"
        #         }
        #
        #     # Extract conversation context (last 3 messages, excluding current)
        #     context_messages = self._extract_conversation_context(messages)
        #
        #     if not context_messages:
        #         logger.info("📝 No conversation context available, using original query")
        #         return {
        #             "condensed_query": original_query,
        #             "original_query": original_query,
        #             "context_messages_used": 0,
        #             "transformation_success": False,
        #             "fallback_reason": "no_context"
        #         }
        #
        #     # Get the condense chat engine
        #     condense_engine = self._get_condense_chat_engine()
        #
        #     # Clear any existing chat history and add the context messages
        #     condense_engine.reset()
        #     for msg in context_messages:
        #         condense_engine.chat_history.append(msg)
        #
        #     # Get the current query
        #     current_query = self._extract_last_user_message(messages)
        #     if not current_query:
        #         current_query = original_query
        #
        #     logger.info(f"🔄 Transforming query with {len(context_messages)} context messages")
        #     logger.info(f"📋 Original query: {current_query[:100]}...")
        #
        #     # Generate the condensed query using the chat engine (synchronous)
        #     response = condense_engine.chat(current_query)
        #
        #     # The condensed query is the standalone question generated by the engine
        #     condensed_query = response.response.strip()
        #
        #     logger.info(f"✅ Query transformation successful")
        #     logger.info(f"🎯 Condensed query: {condensed_query[:100]}...")
        #
        #     return {
        #         "condensed_query": condensed_query,
        #         "original_query": original_query,
        #         "context_messages_used": len(context_messages),
        #         "transformation_success": True
        #     }
        #
        # except Exception as e:
        #     logger.error(f"❌ Query transformation failed: {e}")
        #     logger.info("Falling back to original query")
        #
        #     return {
        #         "condensed_query": original_query,
        #         "original_query": original_query,
        #         "context_messages_used": 0,
        #         "transformation_success": False,
        #         "fallback_reason": f"error: {str(e)}"
        #     }
