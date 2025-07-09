"""
Token Management Module

This module provides accurate token counting and text truncation functionality
using LlamaIndex's TokenCountingHandler and tiktoken for precise token counting.
"""

from .token_counter import TokenCounter, get_token_counter
from .text_truncator import TextTruncator

__all__ = [
    "TokenCounter",
    "get_token_counter",
    "TextTruncator"
]
