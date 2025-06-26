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

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


class OpenAIEmbeddingClient:
    """Independent OpenAI embedding client for the modular system"""

    def __init__(self, model: str = "text-embedding-3-small"):
        self.model = model
        self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
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

            response = self.client.embeddings.create(
                model=self.model,
                input=text,
                encoding_format="float"
            )

            embedding = response.data[0].embedding
            logger.debug(f"Generated embedding for text of length {len(text)}")
            return embedding

        except Exception as e:
            logger.error(f"Failed to generate embedding for text: {e}")
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

            response = self.client.embeddings.create(
                model=self.model,
                input=valid_texts,
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
        Rough token estimation for text
        Uses approximate 1 token per 4 characters rule

        Args:
            text: Text to estimate tokens for

        Returns:
            int: Estimated token count
        """
        return len(text) // 4

    def validate_text_length(self, text: str, max_tokens: int = 8000) -> bool:
        """
        Validate that text is within token limits

        Args:
            text: Text to validate
            max_tokens: Maximum allowed tokens

        Returns:
            bool: True if text is within limits
        """
        estimated_tokens = self.estimate_tokens(text)
        if estimated_tokens > max_tokens:
            logger.warning(
                f"Text too long: {estimated_tokens} tokens (max: {max_tokens})")
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
