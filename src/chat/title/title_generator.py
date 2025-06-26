"""
Title Generator - Conversation Title Generation

This module handles the generation of concise conversation titles based on chat messages.
Follows the same logic as the original enhanced_chat_bot.py implementation.
"""

import logging
from typing import Dict, Any, List, Optional, Union
from llama_index.core.llms.llm import LLM

logger = logging.getLogger(__name__)


class TitleGenerator:
    """
    Generate concise conversation titles for chat sessions

    Features:
    - Maximum 5 words, 20 characters
    - Extract key context from first and last user messages
    - Use low temperature for consistent, focused titles
    - Clean title formatting (no quotes, proper length limits)
    """

    def __init__(self):
        """Initialize the title generator"""
        logger.info("TitleGenerator initialized")

    async def generate_conversation_title(self, messages: List[Dict[str, Any]], llm: LLM) -> Optional[str]:
        """
        Generate a concise title for the conversation (max 5 words, ~20 chars)

        Args:
            messages: List of chat messages in OpenAI format
            llm: LLM instance to use for title generation

        Returns:
            Generated title string or None if generation fails
        """
        try:
            # Extract key context from conversation - use only first few and last message
            context_messages = []

            # Get first user message for initial context
            first_user_msg = None
            for msg in messages:
                if isinstance(msg, dict) and msg.get("role") == "user":
                    first_user_msg = msg
                    break

            # Get last user message for current context
            last_user_msg = None
            for msg in reversed(messages):
                if isinstance(msg, dict) and msg.get("role") == "user":
                    last_user_msg = msg
                    break

            # Build lightweight context (avoid full conversation)
            if first_user_msg and last_user_msg and first_user_msg != last_user_msg:
                # Multi-turn conversation
                first_content = self._extract_message_text(first_user_msg)[
                    :100]
                last_content = self._extract_message_text(last_user_msg)[:100]
                context = f"Initial: {first_content}\\nRecent: {last_content}"
            elif last_user_msg:
                # Single turn or same message
                context = self._extract_message_text(last_user_msg)[:150]
            else:
                logger.warning("No user messages found for title generation")
                return None

            # Create title generation prompt - very specific for brevity
            title_prompt = f"""Generate a very concise conversation title based on this context:

{context}

Requirements:
- Maximum 5 words
- Maximum 20 characters
- No punctuation
- Capture the main topic/intent
- Be specific, not generic

Examples:
- "AI Trends 2024"
- "Python Error Fix"
- "Recipe Ideas"
- "Travel Planning"

Title:"""

            # Use low temperature for consistent, focused titles
            original_temp = getattr(llm, 'temperature', 0.7)
            llm.temperature = 0.1  # Very focused generation

            try:
                logger.info("🏷️ Generating conversation title...")
                response = await llm.acomplete(title_prompt)
                title = str(response).strip()

                # Clean up the title
                title = title.replace('"', '').replace("'", "").strip()

                # Ensure it meets requirements
                words = title.split()
                if len(words) > 5:
                    title = " ".join(words[:5])

                if len(title) > 20:
                    title = title[:20].strip()

                # Restore original temperature
                llm.temperature = original_temp

                logger.info(f"✅ Generated conversation title: '{title}'")
                return title if title else None

            except Exception as e:
                # Restore temperature on error
                llm.temperature = original_temp
                raise e

        except Exception as e:
            logger.error(f"❌ Failed to generate conversation title: {e}")
            return None

    def _extract_message_text(self, message: Dict[str, Any]) -> str:
        """
        Extract text content from a message (handles both string and multimodal)

        Args:
            message: Message dict in OpenAI format

        Returns:
            Extracted text content
        """
        content = message.get("content", "")

        if isinstance(content, str):
            return content
        elif isinstance(content, list):
            # Handle multimodal content, extract text parts
            text_parts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_parts.append(item.get("text", ""))
            return " ".join(text_parts)
        return ""

    def get_status(self) -> Dict[str, Any]:
        """Get title generator status"""
        return {
            "module": "title_generator",
            "status": "operational",
            "version": "v1.0.0"
        }


# Create a global instance for easy import
title_generator = TitleGenerator()
