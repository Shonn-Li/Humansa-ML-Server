

"""
Azure AI Inference Embeddings Client for Modular Embedding System

This module provides Azure AI Inference embedding functionality using the same
endpoint configuration as the LLM provider.
"""

import os
import logging
from typing import List, Dict, Any
from dotenv import load_dotenv

# Import token management system
from chat.token import get_token_counter, TextTruncator

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

        # Initialize token management
        self.token_counter = get_token_counter(model)
        self.truncator = TextTruncator(model)

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

            # Validate and truncate using accurate token counting
            is_valid, token_count = self.truncator.validate_text_tokens(text)
            
            if not is_valid:
                logger.warning(f"⚠️ Text too long ({token_count} tokens), truncating...")
                text, final_tokens, was_truncated = self.truncator.truncate_text(text)
                logger.info(f"📏 Truncated text: {token_count} -> {final_tokens} tokens ({len(text)} chars)")

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

            # Use intelligent batch truncation with conservative limits
            max_tokens_per_text = 6000  # Individual text limit (conservative)
            max_batch_tokens = 15000    # Batch limit (conservative for Azure)
            
            processed_texts, token_counts, total_tokens = self.truncator.truncate_texts_batch(
                valid_texts,
                max_tokens_per_text=max_tokens_per_text,
                max_total_tokens=max_batch_tokens
            )

            if not processed_texts:
                raise ValueError("No valid texts to embed after processing")

            logger.debug(f"🔍 Processing batch: {len(processed_texts)} texts, {total_tokens} tokens")

            # Use Azure AI Inference embeddings API for batch processing
            response = self.client.embed(
                input=processed_texts,
                model=self.model
            )

            embeddings = [item.embedding for item in response.data]
            logger.debug(f"🔗 Azure batch embeddings generated for {len(processed_texts)} texts")

            # If we had to skip some texts due to batch limits, process them recursively
            remaining_texts = valid_texts[len(processed_texts):]
            if remaining_texts:
                logger.info(f"🔄 Processing remaining {len(remaining_texts)} texts in new batch")
                remaining_embeddings = self.get_text_embeddings(remaining_texts)
                embeddings.extend(remaining_embeddings)

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
                    error_msg = str(e)
                    logger.warning(
                        f"⚠️ Batch {i//batch_size + 1} failed on attempt {attempt + 1}: {e}")

                    # Special handling for token limit errors
                    if "maximum context length" in error_msg or "too many tokens" in error_msg.lower():
                        logger.error(
                            f"🚨 Token limit exceeded. Attempting more aggressive truncation...")
                        try:
                            # Use more aggressive truncation
                            aggressive_texts = []
                            for text in batch:
                                truncated_text, token_count, was_truncated = self.truncator.truncate_text(
                                    text, max_tokens=4000  # Very conservative limit
                                )
                                aggressive_texts.append(truncated_text)
                                
                            # Try again with aggressively truncated texts
                            batch_embeddings = self.get_text_embeddings(aggressive_texts)
                            all_embeddings.extend(batch_embeddings)
                            logger.info(f"✅ Recovered with aggressive truncation")
                            break
                            
                        except Exception as retry_e:
                            logger.error(f"❌ Aggressive truncation also failed: {retry_e}")
                            if attempt == max_retries - 1:
                                # Last attempt failed, skip this batch or raise error
                                logger.error(f"❌ Failed to process batch after {max_retries} attempts")
                                raise
                    else:
                        # For other errors, just retry or fail
                        if attempt == max_retries - 1:
                            logger.error(f"❌ Failed to process batch after {max_retries} attempts")
                            raise

        return all_embeddings

    def estimate_tokens(self, text: str) -> int:
        """
        DEPRECATED: Use token_counter for accurate token counting
        This method is kept for backward compatibility
        """
        logger.warning("estimate_tokens is deprecated. Use self.token_counter.count_tokens() instead")
        return self.token_counter.count_tokens(text)

    def validate_text_length(self, text: str, max_tokens: int = 6000) -> bool:
        """
        DEPRECATED: Use truncator.validate_text_tokens() for accurate validation
        This method is kept for backward compatibility
        """
        logger.warning("validate_text_length is deprecated. Use self.truncator.validate_text_tokens() instead")
        is_valid, _ = self.truncator.validate_text_tokens(text, max_tokens)
        return is_valid

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
