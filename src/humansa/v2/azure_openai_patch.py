"""
Patch for Azure OpenAI to fix the 'blocks' attribute error
"""

import logging
from typing import Any, Dict, List, Optional, Sequence
from llama_index.llms.azure_openai import AzureOpenAI as BaseAzureOpenAI
from llama_index.core.base.llms.types import ChatMessage, MessageRole

logger = logging.getLogger(__name__)


class PatchedAzureOpenAI(BaseAzureOpenAI):
    """
    Patched version of AzureOpenAI that handles the 'blocks' attribute error
    """
    
    def _prepare_chat_messages(self, messages: Sequence[ChatMessage]) -> List[Dict[str, Any]]:
        """
        Override to ensure messages are properly formatted
        """
        formatted_messages = []
        
        for msg in messages:
            if isinstance(msg, dict):
                # If it's already a dict, use it as is
                formatted_messages.append(msg)
            elif hasattr(msg, 'dict'):
                # If it has a dict method, use that
                formatted_messages.append(msg.dict())
            else:
                # Otherwise, try to construct a dict
                try:
                    formatted_msg = {
                        "role": msg.role.value if hasattr(msg.role, 'value') else str(msg.role),
                        "content": msg.content
                    }
                    formatted_messages.append(formatted_msg)
                except Exception as e:
                    logger.error(f"Error formatting message: {e}")
                    # Fallback
                    formatted_messages.append({
                        "role": "user",
                        "content": str(msg)
                    })
        
        return formatted_messages
    
    def chat(self, messages: Sequence[ChatMessage], **kwargs: Any) -> Any:
        """
        Override chat to handle message formatting
        """
        try:
            # Try the original method first
            return super().chat(messages, **kwargs)
        except AttributeError as e:
            if "'dict' object has no attribute 'blocks'" in str(e):
                logger.warning("Encountered 'blocks' error, attempting workaround...")
                # Convert messages to proper format
                formatted_messages = self._prepare_chat_messages(messages)
                # Try again with formatted messages
                return super()._chat(formatted_messages, **kwargs)
            else:
                raise
    
    def stream_chat(self, messages: Sequence[ChatMessage], **kwargs: Any) -> Any:
        """
        Override stream_chat to handle message formatting
        """
        try:
            # Try the original method first
            return super().stream_chat(messages, **kwargs)
        except AttributeError as e:
            if "'dict' object has no attribute 'blocks'" in str(e):
                logger.warning("Encountered 'blocks' error in stream_chat, attempting workaround...")
                # Convert messages to proper format
                formatted_messages = self._prepare_chat_messages(messages)
                # Try again with formatted messages
                return super()._stream_chat(formatted_messages, **kwargs)
            else:
                raise