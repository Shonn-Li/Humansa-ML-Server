"""
Independent OpenAI Embeddings Client for Modular Embedding System

This module provides OpenAI embedding functionality without external dependencies.
NO PLACEHOLDERS - complete implementation copied and adapted from existing code.
"""

import os
import openai
import logging
from typing import List, Dict, Any
from dotenv import load_dotenv

# Import token management system
from chat.token import get_token_counter, TextTruncator

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


class OpenAIEmbeddingClient:
    """Independent OpenAI embedding client for the modular system"""

    def __init__(self, model: str = "text-embedding-3-small"):
        self.model = model
        self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Initialize token management
        self.token_counter = get_token_counter(model)
        self.truncator = TextTruncator(model)
        
        logger.info(f"Initialized OpenAI embedding client with model: {model}")

    def get_text_embedding(self, text: str) -> List[float]:
        """
        Get embedding for a single text string

        Args:
            text: The text to embed

        Returns:
            List[float]: The embedding vector
        """
        try:
            if not text or not text.strip():
                raise ValueError("Text cannot be empty")

            # Validate and truncate using accurate token counting
            is_valid, token_count = self.truncator.validate_text_tokens(text)
            
            if not is_valid:
                logger.warning(f"⚠️ Text too long ({token_count} tokens), truncating...")
                text, final_tokens, was_truncated = self.truncator.truncate_text(text)
                logger.info(f"📏 Truncated text: {token_count} -> {final_tokens} tokens ({len(text)} chars)")

            response = self.client.embeddings.create(
                model=self.model,
                input=text,
                encoding_format="float"
            )

            embedding = response.data[0].embedding
            logger.debug(f"Generated embedding for text of length {len(text)}")
            return embedding

        except Exception as e:
            logger.error(f"❌ OpenAI embedding failed: {e}")
            raise

    def get_text_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Get embeddings for multiple texts in a batch

        Args:
            texts: List of texts to embed

        Returns:
            List[List[float]]: List of embedding vectors
        """
        try:
            if not texts:
                return []

            # Filter out empty texts
            valid_texts = [text for text in texts if text and text.strip()]
            if not valid_texts:
                logger.warning("No valid texts provided for embedding")
                return []

            # Use intelligent batch truncation with conservative limits
            max_tokens_per_text = 6000  # Individual text limit (conservative)
            max_batch_tokens = 15000    # Batch limit (conservative for OpenAI)
            
            processed_texts, token_counts, total_tokens = self.truncator.truncate_texts_batch(
                valid_texts,
                max_tokens_per_text=max_tokens_per_text,
                max_total_tokens=max_batch_tokens
            )

            if not processed_texts:
                logger.warning("No valid texts to embed after processing")
                return []

            logger.debug(f"🔍 Processing batch: {len(processed_texts)} texts, {total_tokens} tokens")

            response = self.client.embeddings.create(
                model=self.model,
                input=processed_texts,
                encoding_format="float"
            )

            embeddings = [data.embedding for data in response.data]
            logger.info(f"Generated {len(embeddings)} embeddings in batch")
            return embeddings

        except Exception as e:
            logger.error(f"Failed to generate batch embeddings: {e}")
            raise

    def get_embeddings_with_retry(self, texts: List[str], max_retries: int = 3, batch_size: int = 50) -> List[List[float]]:
        """
        Get embeddings with retry logic and batch processing

        Args:
            texts: List of texts to embed
            max_retries: Maximum number of retry attempts
            batch_size: Size of each batch for processing

        Returns:
            List[List[float]]: List of embedding vectors
        """
        all_embeddings = []

        # Process in batches
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]

            for attempt in range(max_retries):
                try:
                    batch_embeddings = self.get_text_embeddings_batch(batch)
                    all_embeddings.extend(batch_embeddings)
                    logger.info(
                        f"Successfully processed batch {i//batch_size + 1} (attempt {attempt + 1})")
                    break

                except Exception as e:
                    logger.warning(
                        f"Batch {i//batch_size + 1} failed on attempt {attempt + 1}: {e}")
                    if attempt == max_retries - 1:
                        logger.error(
                            f"Failed to process batch after {max_retries} attempts")
                        raise

                    # Exponential backoff
                    import time
                    time.sleep(2 ** attempt)

        return all_embeddings

    def estimate_tokens(self, text: str) -> int:
        """
        More accurate token estimation for text
        Uses a more conservative estimate based on OpenAI's tokenization patterns

        Args:
            text: Text to estimate tokens for

        Returns:
            int: Estimated token count
        """
        if not text:
            return 0

        # More accurate estimation based on real tokenization patterns:
        # - Average English text: ~3-3.5 chars per token
        # - Technical text: ~2.5-3 chars per token
        # - Text with punctuation/special chars: ~2-2.5 chars per token

        # Use 2.5 chars per token for conservative estimation
        base_estimate = len(text) / 2.5

        # Add buffer for special tokens, punctuation, etc.
        # Count special characters that tend to be separate tokens
        special_chars = text.count('.') + text.count(',') + text.count('!') + text.count('?') + \
            text.count(';') + text.count(':') + text.count('(') + text.count(')') + \
            text.count('[') + text.count(']') + \
            text.count('{') + text.count('}')

        # Each special char might be a separate token
        special_token_estimate = special_chars * 0.5

        # Count newlines and spaces which can affect tokenization
        whitespace_estimate = (text.count('\n') + text.count('\t')) * 0.3

        total_estimate = base_estimate + special_token_estimate + whitespace_estimate

        return int(total_estimate)

    def validate_text_length(self, text: str, max_tokens: int = 6000) -> bool:
        """
        Validate that text is within token limits using improved estimation

        Args:
            text: Text to validate
            max_tokens: Maximum allowed tokens (default 6000 for safety)

        Returns:
            bool: True if text is within limits
        """
        estimated_tokens = self.estimate_tokens(text)
        if estimated_tokens > max_tokens:
            logger.warning(
                f"Text too long: {estimated_tokens} estimated tokens (max: {max_tokens})")
            return False
        return True

    def get_embedding_dimension(self) -> int:
        """
        Get the dimension of embeddings for the current model

        Returns:
            int: Embedding dimension
        """
        model_dimensions = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536
        }
        return model_dimensions.get(self.model, 1536)

    def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check on the embedding service

        Returns:
            Dict[str, Any]: Health check results
        """
        try:
            # Test with a simple embedding
            test_embedding = self.get_text_embedding("Hello, world!")

            return {
                "status": "healthy",
                "model": self.model,
                "embedding_dimension": len(test_embedding),
                "expected_dimension": self.get_embedding_dimension(),
                "api_accessible": True
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "model": self.model,
                "error": str(e),
                "api_accessible": False
            }


# Global embedding client instance
openai_embedder = OpenAIEmbeddingClient()
