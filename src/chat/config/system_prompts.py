"""
System Prompt Configuration for YouWoAI ML Server

This module handles system prompt management and configuration.
"""

import logging
from datetime import date

logger = logging.getLogger(__name__)


def get_youwoai_system_prompt() -> str:
    """Return the default YouWoAI system prompt (bare‑bones + context note)."""
    current_date = date.today().strftime("%Y-%m-%d")
    return (
        f"You are **YouWoAI**, an AI study assistant.\n\n"
        f"**Current Date**: {current_date}\n\n"
        "Your role: help the user learn faster and answer questions.\n"
        "• Any prior conversation notes, file‑search snippets, file attachments, or web‑search results "
        "will appear as **additional system messages** in this chat. Use them when relevant.\n"
    )


def get_legacy_content_generator_prompt() -> str:
    """Generate the legacy content generator prompt with current date"""
    current_date = date.today().strftime("%Y-%m-%d")
    return f"You are a YouWoAI's content generator aimed to directly output content based on the user's prompt below. Current date: {current_date}."


class SystemPromptManager:
    """Manages system prompts for different completion types"""

    def __init__(self):
        logger.info("SystemPromptManager initialized")

    def get_system_prompt(self, completion_type: str = "system", custom_prompt: str = None) -> str:
        """
        Get system prompt based on completion type

        Args:
            completion_type: "system" (default YouWoAI prompt) or "completion" (legacy content generator)
            custom_prompt: Optional custom system prompt to override defaults

        Returns:
            str: The appropriate system prompt
        """
        if custom_prompt:
            logger.info(
                f"Using custom system prompt (length: {len(custom_prompt)})")
            return custom_prompt

        if completion_type == "system":
            logger.info(
                "Using default YouWoAI system prompt with current date")
            return get_youwoai_system_prompt()
        elif completion_type == "completion":
            logger.info(
                "Using legacy content generator prompt with current date")
            return get_legacy_content_generator_prompt()
        else:
            logger.warning(
                f"Unknown completion_type '{completion_type}', defaulting to YouWoAI system prompt")
            return get_youwoai_system_prompt()

    def should_include_system_prompt(self, messages: list) -> bool:
        """
        Check if we should include a system prompt (i.e., no system message already exists)

        Args:
            messages: List of message objects

        Returns:
            bool: True if system prompt should be added
        """
        # Check if there's already a system message
        for message in messages:
            if message.get("role") == "system":
                logger.info(
                    "System message already exists in messages, skipping system prompt injection")
                return False

        logger.info("No system message found, will inject system prompt")
        return True


# Global instance
system_prompt_manager = SystemPromptManager()
