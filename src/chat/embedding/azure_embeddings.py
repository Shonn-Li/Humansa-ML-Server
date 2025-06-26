"""
Azure AI Inference Embeddings Client for Modular Embedding System

This module provides Azure AI Inference embedding functionality using the same
endpoint configuration as the LLM provider.
"""

import os
import logging
from typing import List, Dict, Any
from dotenv import load_dotenv

# Azure AI Inference imports
try:
    from azure.ai.inference import EmbeddingsClient
    from azure.core.credentials import AzureKeyCredential
    AZURE_EMBEDDINGS_AVAILABLE = True
except ImportError:
    AZURE_EMBEDDINGS_AVAILABLE = False

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


class AzureEmbeddingClient:
    """Azure AI Inference embedding client for the modular system"""

    def __init__(self, model: str = "text-embedding-3-small"):
        self.model = model
        self.endpoint = os.getenv("AZURE_INFERENCE_ENDPOINT")
        self.credential = os.getenv("AZURE_INFERENCE_CREDENTIAL")

        if not AZURE_EMBEDDINGS_AVAILABLE:
            raise ImportError(
                "Azure AI Inference not available. Install with: pip install azure-ai-inference")

        if not self.endpoint or not self.credential:
            raise ValueError(
                "AZURE_INFERENCE_ENDPOINT and AZURE_INFERENCE_CREDENTIAL must be set")

        # Create Azure embeddings client
        self.client = EmbeddingsClient(
            endpoint=self.endpoint,
            credential=AzureKeyCredential(self.credential)
        )

        logger.info(
            f"✅ Azure AI Inference embedding client initialized with model: {model}")
        logger.info(
            f"🔗 Endpoint: {self.endpoint.split('/')[-3] if '/' in self.endpoint else 'configured'}")

    def get_text_embedding(self, text: str) -> List[float]:
        """
        Get embedding for a single text string using Azure AI Inference

        Args:
            text: The text to embed

        Returns:
            List[float]: The embedding vector
        """
        try:
            if not text or not text.strip():
                raise ValueError("Text cannot be empty")

            # Use Azure AI Inference embeddings API
            response = self.client.embed(
                input=[text],
                model=self.model
            )

            embedding = response.data[0].embedding
            logger.debug(
                f"🔗 Azure embedding generated for text of length {len(text)}")
            return embedding

        except Exception as e:
            logger.error(f"❌ Azure embedding failed: {e}")
            raise

    def get_text_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Get embeddings for multiple text strings using Azure AI Inference

        Args:
            texts: List of texts to embed

        Returns:
            List[List[float]]: List of embedding vectors
        """
        try:
            if not texts:
                raise ValueError("Texts list cannot be empty")

            # Filter out empty texts
            valid_texts = [text for text in texts if text and text.strip()]
            if not valid_texts:
                raise ValueError("No valid texts to embed")

            # Use Azure AI Inference embeddings API for batch processing
            response = self.client.embed(
                input=valid_texts,
                model=self.model
            )

            embeddings = [item.embedding for item in response.data]
            logger.debug(
                f"🔗 Azure batch embeddings generated for {len(valid_texts)} texts")
            return embeddings

        except Exception as e:
            logger.error(f"❌ Azure batch embedding failed: {e}")
            raise

    def get_embedding_dimension(self) -> int:
        """
        Get the dimension of embeddings for this model

        Returns:
            int: The embedding dimension (1536 for text-embedding-3-small)
        """
        # text-embedding-3-small produces 1536-dimensional embeddings
        if "text-embedding-3-small" in self.model:
            return 1536
        elif "text-embedding-3-large" in self.model:
            return 3072
        else:
            # Default for most OpenAI embedding models
            return 1536

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
                    batch_embeddings = self.get_text_embeddings(batch)
                    all_embeddings.extend(batch_embeddings)
                    logger.info(
                        f"✅ Successfully processed batch {i//batch_size + 1} (attempt {attempt + 1}) with Azure AI Inference")
                    break

                except Exception as e:
                    logger.warning(
                        f"⚠️ Batch {i//batch_size + 1} failed on attempt {attempt + 1}: {e}")
                    if attempt == max_retries - 1:
                        logger.error(
                            f"❌ Failed to process batch after {max_retries} attempts")
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
        return self.estimate_tokens(text) <= max_tokens

    def test_connection(self) -> bool:
        """
        Test the Azure AI Inference connection

        Returns:
            bool: True if connection is successful
        """
        try:
            test_embedding = self.get_text_embedding("test connection")
            return len(test_embedding) > 0
        except Exception as e:
            logger.error(f"❌ Azure embedding connection test failed: {e}")
            return False
