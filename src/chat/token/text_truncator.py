"""
Text Truncator Module

This module provides intelligent text truncation based on accurate token counting
to ensure texts fit within model token limits.
"""

import logging
from typing import List, Optional, Tuple
from .token_counter import get_token_counter

logger = logging.getLogger(__name__)


class TextTruncator:
    """Intelligent text truncator that uses accurate token counting"""
    
    def __init__(self, model: str = "text-embedding-3-small"):
        """
        Initialize text truncator for a specific model
        
        Args:
            model: The model name to get appropriate token limits
        """
        self.model = model
        self.token_counter = get_token_counter(model)
        
        # Model-specific token limits
        self.token_limits = {
            "text-embedding-3-small": 8192,
            "text-embedding-3-large": 8192,
            "text-embedding-ada-002": 8192,
            "gpt-3.5-turbo": 16385,  # 16k context
            "gpt-4": 8192,          # 8k context
            "gpt-4-turbo": 128000,   # 128k context
            "gpt-4-32k": 32768      # 32k context
        }
        
        # Get token limit for this model (with safety buffer)
        base_limit = self.token_limits.get(model, 8192)
        self.max_tokens = int(base_limit * 0.85)  # 15% safety buffer
        
        logger.info(f"TextTruncator initialized for {model} (limit: {self.max_tokens} tokens)")
    
    def truncate_text(self, text: str, max_tokens: Optional[int] = None, 
                     preserve_sentences: bool = True) -> Tuple[str, int, bool]:
        """
        Truncate text to fit within token limit
        
        Args:
            text: The text to truncate
            max_tokens: Maximum tokens (uses default if None)
            preserve_sentences: Whether to preserve complete sentences
            
        Returns:
            Tuple[str, int, bool]: (truncated_text, final_token_count, was_truncated)
        """
        if not text:
            return "", 0, False
        
        limit = max_tokens if max_tokens is not None else self.max_tokens
        original_token_count = self.token_counter.count_tokens(text)
        
        # If text is already within limit, return as-is
        if original_token_count <= limit:
            return text, original_token_count, False
        
        logger.info(f"Truncating text: {original_token_count} tokens -> {limit} tokens")
        
        # Binary search for optimal truncation point
        left, right = 0, len(text)
        best_text = ""
        best_tokens = 0
        
        while left < right:
            mid = (left + right + 1) // 2
            candidate_text = text[:mid]
            
            # If preserving sentences, try to end at sentence boundary
            if preserve_sentences and mid < len(text):
                candidate_text = self._truncate_to_sentence_boundary(candidate_text)
            
            token_count = self.token_counter.count_tokens(candidate_text)
            
            if token_count <= limit:
                best_text = candidate_text
                best_tokens = token_count
                left = mid
            else:
                right = mid - 1
        
        # If we couldn't find a good truncation point, use character-based fallback
        if not best_text:
            logger.warning("Binary search failed, using character-based fallback")
            best_text, best_tokens = self._character_based_truncation(text, limit)
        
        logger.info(f"Text truncated: {original_token_count} -> {best_tokens} tokens ({len(text)} -> {len(best_text)} chars)")
        
        return best_text, best_tokens, True
    
    def _truncate_to_sentence_boundary(self, text: str) -> str:
        """
        Truncate text to the last complete sentence
        
        Args:
            text: The text to truncate
            
        Returns:
            str: Text truncated to sentence boundary
        """
        # Look for sentence endings
        sentence_endings = ['. ', '! ', '? ', '.\n', '!\n', '?\n']
        
        best_pos = -1
        for ending in sentence_endings:
            pos = text.rfind(ending)
            if pos > best_pos:
                best_pos = pos
        
        if best_pos > len(text) * 0.7:  # Only truncate if we don't lose too much
            return text[:best_pos + 1].strip()
        
        return text
    
    def _character_based_truncation(self, text: str, max_tokens: int) -> Tuple[str, int]:
        """
        Fallback character-based truncation
        
        Args:
            text: The text to truncate
            max_tokens: Maximum token limit
            
        Returns:
            Tuple[str, int]: (truncated_text, token_count)
        """
        # Conservative estimate: 2.5 characters per token for embedding models
        estimated_chars = int(max_tokens * 2.5)
        
        if estimated_chars >= len(text):
            return text, self.token_counter.count_tokens(text)
        
        # Truncate and verify
        truncated = text[:estimated_chars]
        
        # Try to break at word boundary
        if estimated_chars < len(text):
            last_space = truncated.rfind(' ')
            if last_space > estimated_chars * 0.8:
                truncated = truncated[:last_space]
        
        final_tokens = self.token_counter.count_tokens(truncated)
        
        # If still too long, truncate more aggressively
        while final_tokens > max_tokens and len(truncated) > 0:
            truncated = truncated[:int(len(truncated) * 0.9)]
            final_tokens = self.token_counter.count_tokens(truncated)
        
        return truncated, final_tokens
    
    def truncate_texts_batch(self, texts: List[str], max_tokens_per_text: Optional[int] = None,
                           max_total_tokens: Optional[int] = None) -> Tuple[List[str], List[int], int]:
        """
        Truncate multiple texts with individual and batch limits
        
        Args:
            texts: List of texts to truncate
            max_tokens_per_text: Maximum tokens per individual text
            max_total_tokens: Maximum total tokens for all texts
            
        Returns:
            Tuple[List[str], List[int], int]: (truncated_texts, token_counts, total_tokens)
        """
        if not texts:
            return [], [], 0
        
        per_text_limit = max_tokens_per_text if max_tokens_per_text is not None else self.max_tokens
        total_limit = max_total_tokens if max_total_tokens is not None else per_text_limit * len(texts)
        
        truncated_texts = []
        token_counts = []
        total_tokens = 0
        
        # First pass: truncate individual texts
        for text in texts:
            truncated_text, token_count, _ = self.truncate_text(text, per_text_limit)
            
            # Check if adding this text would exceed total limit
            if total_tokens + token_count > total_limit:
                logger.warning(f"Batch total token limit would be exceeded, stopping at {len(truncated_texts)} texts")
                break
            
            truncated_texts.append(truncated_text)
            token_counts.append(token_count)
            total_tokens += token_count
        
        logger.info(f"Batch truncation: {len(texts)} -> {len(truncated_texts)} texts, {total_tokens} total tokens")
        
        return truncated_texts, token_counts, total_tokens
    
    def get_safe_batch_size(self, texts: List[str], max_batch_tokens: int) -> int:
        """
        Calculate safe batch size for a list of texts
        
        Args:
            texts: List of texts
            max_batch_tokens: Maximum tokens per batch
            
        Returns:
            int: Safe batch size
        """
        if not texts:
            return 0
        
        total_tokens = 0
        batch_size = 0
        
        for text in texts:
            token_count = self.token_counter.count_tokens(text)
            
            if total_tokens + token_count > max_batch_tokens:
                break
            
            total_tokens += token_count
            batch_size += 1
        
        return max(1, batch_size)  # At least 1 text per batch
    
    def validate_text_tokens(self, text: str, max_tokens: Optional[int] = None) -> Tuple[bool, int]:
        """
        Validate if text is within token limit
        
        Args:
            text: The text to validate
            max_tokens: Maximum tokens (uses default if None)
            
        Returns:
            Tuple[bool, int]: (is_valid, token_count)
        """
        if not text:
            return True, 0
        
        limit = max_tokens if max_tokens is not None else self.max_tokens
        token_count = self.token_counter.count_tokens(text)
        
        return token_count <= limit, token_count
