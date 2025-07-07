"""
Token Counter Module

This module provides accurate token counting using LlamaIndex's TokenCountingHandler
and tiktoken for precise token measurement.
"""

import logging
import tiktoken
from typing import Dict, Optional, List, Any
from llama_index.core.callbacks import CallbackManager, TokenCountingHandler

logger = logging.getLogger(__name__)


class TokenCounter:
    """Accurate token counter using tiktoken and LlamaIndex TokenCountingHandler"""
    
    def __init__(self, model: str = "gpt-3.5-turbo"):
        """
        Initialize token counter for a specific model
        
        Args:
            model: The model name to get the appropriate tokenizer
        """
        self.model = model
        self._tokenizer = None
        self._encoding = None
        self._token_handler = None
        
        # Initialize tokenizer
        self._init_tokenizer()
        
        logger.info(f"TokenCounter initialized for model: {model}")
    
    def _init_tokenizer(self):
        """Initialize the tokenizer for the specified model"""
        try:
            # Get tiktoken encoding for the model
            self._encoding = tiktoken.encoding_for_model(self.model)
            self._tokenizer = self._encoding.encode
            
            # Initialize LlamaIndex token counting handler
            self._token_handler = TokenCountingHandler(tokenizer=self._tokenizer)
            
            logger.debug(f"Tokenizer initialized for model: {self.model}")
            
        except KeyError:
            logger.warning(f"Model {self.model} not found in tiktoken, using cl100k_base encoding")
            # Fallback to cl100k_base encoding (used by GPT-4, GPT-3.5-turbo)
            self._encoding = tiktoken.get_encoding("cl100k_base")
            self._tokenizer = self._encoding.encode
            self._token_handler = TokenCountingHandler(tokenizer=self._tokenizer)
        
        except Exception as e:
            logger.error(f"Failed to initialize tokenizer: {e}")
            # Ultimate fallback - use simple estimation
            self._tokenizer = None
            self._encoding = None
            self._token_handler = None
    
    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text using accurate tiktoken encoding
        
        Args:
            text: The text to count tokens for
            
        Returns:
            int: The number of tokens
        """
        if not text:
            return 0
        
        try:
            if self._tokenizer:
                return len(self._tokenizer(text))
            else:
                # Fallback to estimation
                return self._estimate_tokens_fallback(text)
                
        except Exception as e:
            logger.warning(f"Token counting failed, using fallback: {e}")
            return self._estimate_tokens_fallback(text)
    
    def count_tokens_batch(self, texts: List[str]) -> List[int]:
        """
        Count tokens for multiple texts
        
        Args:
            texts: List of texts to count tokens for
            
        Returns:
            List[int]: List of token counts
        """
        return [self.count_tokens(text) for text in texts]
    
    def get_total_tokens(self, texts: List[str]) -> int:
        """
        Get total token count for a list of texts
        
        Args:
            texts: List of texts
            
        Returns:
            int: Total token count
        """
        return sum(self.count_tokens_batch(texts))
    
    def _estimate_tokens_fallback(self, text: str) -> int:
        """
        Fallback token estimation method
        
        Args:
            text: The text to estimate tokens for
            
        Returns:
            int: Estimated token count
        """
        # More accurate estimation based on OpenAI documentation
        # English text: ~4 characters per token
        # But this can vary significantly, so we use a more conservative approach
        
        # Count words and characters
        word_count = len(text.split())
        char_count = len(text)
        
        # Estimate based on word count (more reliable for English text)
        # Average ~1.3 tokens per word for English
        word_based_estimate = int(word_count * 1.3)
        
        # Estimate based on character count (useful for non-English or special characters)
        # Conservative estimate: 3 characters per token (tighter than the usual 4)
        char_based_estimate = int(char_count / 3)
        
        # Use the higher estimate to be conservative
        estimated_tokens = max(word_based_estimate, char_based_estimate)
        
        logger.debug(f"Fallback token estimation: {estimated_tokens} tokens for {char_count} chars / {word_count} words")
        
        return estimated_tokens
    
    def get_callback_manager(self) -> Optional[CallbackManager]:
        """
        Get LlamaIndex callback manager with token counting
        
        Returns:
            CallbackManager: Callback manager with token counting
        """
        if self._token_handler:
            return CallbackManager([self._token_handler])
        return None
    
    def get_token_handler(self) -> Optional[TokenCountingHandler]:
        """
        Get the token counting handler
        
        Returns:
            TokenCountingHandler: The token counting handler
        """
        return self._token_handler
    
    def reset_counts(self):
        """Reset the token counting handler counts"""
        if self._token_handler:
            self._token_handler.reset_counts()
    
    def get_token_counts_summary(self) -> Dict[str, Any]:
        """
        Get summary of token usage from the handler
        
        Returns:
            Dict: Token usage summary
        """
        if not self._token_handler:
            return {"error": "Token handler not available"}
        
        return {
            "total_embedding_tokens": self._token_handler.total_embedding_token_count,
            "total_llm_prompt_tokens": self._token_handler.prompt_llm_token_count,
            "total_llm_completion_tokens": self._token_handler.completion_llm_token_count,
            "total_llm_tokens": self._token_handler.total_llm_token_count,
            "num_llm_events": len(self._token_handler.llm_token_counts),
            "num_embedding_events": len(self._token_handler.embedding_token_counts)
        }


# Global token counter instances for different models
_token_counters: Dict[str, TokenCounter] = {}


def get_token_counter(model: str = "gpt-3.5-turbo") -> TokenCounter:
    """
    Get or create a token counter for a specific model
    
    Args:
        model: The model name
        
    Returns:
        TokenCounter: Token counter instance
    """
    if model not in _token_counters:
        _token_counters[model] = TokenCounter(model)
    
    return _token_counters[model]


# Pre-initialize common token counters
def initialize_common_counters():
    """Initialize token counters for commonly used models"""
    common_models = [
        "gpt-3.5-turbo",
        "gpt-4",
        "text-embedding-3-small", 
        "text-embedding-3-large",
        "text-embedding-ada-002"
    ]
    
    for model in common_models:
        try:
            get_token_counter(model)
            logger.info(f"Initialized token counter for {model}")
        except Exception as e:
            logger.warning(f"Failed to initialize token counter for {model}: {e}")


# Initialize on module import
try:
    initialize_common_counters()
except Exception as e:
    logger.warning(f"Failed to initialize common token counters: {e}")
