"""
Conversation Title Generation Endpoint

This endpoint is designed to generate titles for existing conversations that don't have titles.
It supports both conversations with messages and conversations without messages.
"""

import logging
import time
import asyncio
from typing import Dict, Any, List, Optional

# Import our modules
from chat.title.title_generator import title_generator
from chat.provider.llm_provider import LLMProviderSelector

logger = logging.getLogger(__name__)


class ConversationTitleEndpoint:
    """
    Endpoint for generating conversation titles for existing conversations

    This is particularly useful for:
    1. Migrating existing conversations that don't have titles
    2. Batch processing conversations to add titles
    3. Re-generating titles for conversations
    """

    def __init__(self):
        self.llm_provider_selector = LLMProviderSelector()

    async def generate_title_for_conversation(self, conversation_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a title for a single conversation

        Args:
            conversation_data: Dictionary containing conversation info:
                - id: conversation ID
                - messages: list of messages (can be empty)
                - user_id: user ID (optional, for context)
                - provider: LLM provider to use (optional, defaults to openai)
                - model: model to use (optional, defaults to gpt-4o-mini)

        Returns:
            Dictionary with generated title and metadata
        """
        try:
            conversation_id = conversation_data.get("id")
            messages = conversation_data.get("messages", [])
            user_id = conversation_data.get("user_id")
            provider = conversation_data.get("provider", "openai")
            model = conversation_data.get("model", "gpt-4o-mini")

            logger.info(
                f"🎯 Generating title for conversation {conversation_id} with {len(messages)} messages")

            # Get LLM instance using the provider selector
            provider_enum, llm = self.llm_provider_selector.select_provider_and_model(
                provider, model
            )

            # Configure LLM parameters for consistent title generation
            llm.temperature = 0.3  # Lower temperature for consistent titles

            generated_title = None

            if messages and len(messages) > 0:
                # Case 1: Conversation has messages - use them to generate title
                logger.info(
                    f"📝 Generating title from {len(messages)} existing messages")
                generated_title = await title_generator.generate_conversation_title(messages, llm)

            else:
                # Case 2: Conversation has no messages - generate a generic but contextual title
                logger.info(
                    "🆕 Generating title for conversation without messages")
                generated_title = await self._generate_title_for_empty_conversation(user_id, llm)

            # Fallback if generation fails
            if not generated_title:
                generated_title = "New Conversation"

            return {
                "success": True,
                "conversation_id": conversation_id,
                "generated_title": generated_title,
                "method": "messages" if messages else "empty",
                "message_count": len(messages)
            }

        except Exception as e:
            logger.error(
                f"❌ Failed to generate title for conversation {conversation_id}: {e}")
            return {
                "success": False,
                "conversation_id": conversation_id,
                "error": str(e),
                "generated_title": "New Conversation"  # Fallback title
            }

    async def generate_titles_batch(self, conversations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate titles for multiple conversations in batch

        Args:
            conversations: List of conversation data dictionaries

        Returns:
            Dictionary with batch results
        """
        try:
            logger.info(
                f"🔄 Starting batch title generation for {len(conversations)} conversations")

            # Process conversations concurrently but with a limit to avoid overwhelming the LLM
            # Max 5 concurrent title generations
            semaphore = asyncio.Semaphore(5)

            async def process_single_conversation(conv_data):
                async with semaphore:
                    return await self.generate_title_for_conversation(conv_data)

            # Execute all title generations
            tasks = [process_single_conversation(
                conv) for conv in conversations]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            successful = []
            failed = []

            for result in results:
                if isinstance(result, Exception):
                    failed.append({"error": str(result)})
                elif result.get("success"):
                    successful.append(result)
                else:
                    failed.append(result)

            logger.info(
                f"✅ Batch complete: {len(successful)} successful, {len(failed)} failed")

            return {
                "success": True,
                "total_processed": len(conversations),
                "successful_count": len(successful),
                "failed_count": len(failed),
                "successful_results": successful,
                "failed_results": failed,
                "processing_time": time.time()
            }

        except Exception as e:
            logger.error(f"❌ Batch title generation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "total_processed": len(conversations),
                "successful_count": 0,
                "failed_count": len(conversations)
            }

    async def _generate_title_for_empty_conversation(self, user_id: Optional[int], llm) -> str:
        """
        Generate a title for a conversation that has no messages yet

        Args:
            user_id: Optional user ID for context
            llm: LLM instance

        Returns:
            Generated title string
        """
        try:
            # Create a simple prompt to generate a contextual but generic title
            messages = [
                {
                    "role": "user",
                    "content": "I'm starting a new conversation. Please give me a short, welcoming title for this chat session."
                }
            ]

            # Use the title generator with this synthetic message
            generated_title = await title_generator.generate_conversation_title(messages, llm)

            # If that fails, try a more direct approach
            if not generated_title:
                prompt = "Generate a short, friendly title (max 4 words) for a new conversation. Examples: 'New Chat', 'Getting Started', 'Fresh Conversation'. Only respond with the title, no quotes."

                # Direct LLM call
                response = await llm.acomplete(prompt)
                generated_title = response.text.strip().strip('"').strip("'")

                # Validate and clean the title
                if len(generated_title) > 30:
                    generated_title = generated_title[:30].strip()

            return generated_title or "New Conversation"

        except Exception as e:
            logger.error(
                f"Failed to generate title for empty conversation: {e}")
            return "New Conversation"


# Initialize the endpoint instance
conversation_title_endpoint = ConversationTitleEndpoint()
