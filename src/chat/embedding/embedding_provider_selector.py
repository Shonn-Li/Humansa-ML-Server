"""
Embedding Provider Selector - Choose between Azure and OpenAI embeddings

This module provides embedding provider selection with Azure AI Inference as primary
and OpenAI as fallback, similar to the LLM provider structure.
"""

import os
import logging
from typing import Dict, Any, Optional, List
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class EmbeddingProvider(Enum):
    """Available embedding providers"""
    AZURE_INFERENCE = "azure_inference"
    OPENAI = "openai"


@dataclass
class EmbeddingConfig:
    """Configuration for an embedding provider"""
    provider: EmbeddingProvider
    client_instance: Any
    supported_models: List[str]
    is_available: bool


class EmbeddingProviderSelector:
    """Selects and manages embedding providers with Azure as primary"""

    def __init__(self):
        self.providers: Dict[EmbeddingProvider, EmbeddingConfig] = {}
        self._initialize_providers()

    def _initialize_providers(self):
        """Initialize all available embedding providers"""
        logger.info("=== Embedding Provider Initialization ===")

        # Azure AI Inference (Primary Provider for embeddings)
        try:
            from .azure_embeddings import AzureEmbeddingClient, AZURE_EMBEDDINGS_AVAILABLE

            if AZURE_EMBEDDINGS_AVAILABLE and os.getenv("AZURE_INFERENCE_ENDPOINT") and os.getenv("AZURE_INFERENCE_CREDENTIAL"):
                azure_client = AzureEmbeddingClient(
                    model="text-embedding-3-small")

                # Test connection
                if azure_client.test_connection():
                    self.providers[EmbeddingProvider.AZURE_INFERENCE] = EmbeddingConfig(
                        provider=EmbeddingProvider.AZURE_INFERENCE,
                        client_instance=azure_client,
                        supported_models=[
                            "text-embedding-3-small",
                            "text-embedding-3-large",
                            "text-embedding-ada-002"
                        ],
                        is_available=True
                    )
                    logger.info(
                        "✅ Azure AI Inference embedding provider initialized (PRIMARY)")
                else:
                    logger.warning(
                        "⚠️ Azure AI Inference embedding connection test failed")
            else:
                logger.info(
                    "ℹ️ Azure AI Inference embedding not configured (missing credentials)")

        except ImportError:
            logger.info(
                "ℹ️ Azure AI Inference embedding not available (missing dependencies)")
        except Exception as e:
            logger.error(
                f"❌ Azure AI Inference embedding initialization failed: {e}")

        # OpenAI (Fallback Provider)
        try:
            from .openai_embeddings import OpenAIEmbeddingClient

            if os.getenv("OPENAI_API_KEY"):
                openai_client = OpenAIEmbeddingClient(
                    model="text-embedding-3-small")

                self.providers[EmbeddingProvider.OPENAI] = EmbeddingConfig(
                    provider=EmbeddingProvider.OPENAI,
                    client_instance=openai_client,
                    supported_models=[
                        "text-embedding-3-small",
                        "text-embedding-3-large",
                        "text-embedding-ada-002"
                    ],
                    is_available=True
                )
                logger.info(
                    "✅ OpenAI embedding provider initialized (FALLBACK)")
            else:
                logger.info(
                    "ℹ️ OpenAI embedding not configured (missing API key)")

        except Exception as e:
            logger.error(f"❌ OpenAI embedding initialization failed: {e}")

        # Log summary
        available_providers = [p.value for p in self.providers.keys()]
        logger.info(f"📊 Available embedding providers: {available_providers}")

    def get_embedding_client(self, provider_name: Optional[str] = None, model: Optional[str] = None):
        """
        Get embedding client with provider selection

        Args:
            provider_name: Specific provider to use ('azure_inference', 'openai')
            model: Specific model to use

        Returns:
            Embedding client instance
        """

        # Case 1: Specific provider requested
        if provider_name:
            provider_enum = self._get_provider_enum(provider_name)
            if provider_enum and provider_enum in self.providers:
                config = self.providers[provider_enum]
                client = config.client_instance
                logger.info(
                    f"🎯 Using requested embedding provider: {provider_enum.value}")
                return client
            else:
                logger.warning(
                    f"⚠️ Requested embedding provider '{provider_name}' not available")

        # Case 2: Auto-selection with priority
        # Priority: Azure Inference (Primary) > OpenAI (Fallback)
        priority_order = [EmbeddingProvider.AZURE_INFERENCE,
                          EmbeddingProvider.OPENAI]

        for provider_enum in priority_order:
            if provider_enum in self.providers:
                config = self.providers[provider_enum]
                client = config.client_instance
                logger.info(
                    f"✅ Auto-selected embedding provider: {provider_enum.value}")
                return client

        # Fallback error
        raise ValueError(
            "No embedding providers available. Please check your API keys and Azure configuration.")

    def _get_provider_enum(self, provider_name: str) -> Optional[EmbeddingProvider]:
        """Convert provider name string to enum"""
        provider_mapping = {
            "azure_inference": EmbeddingProvider.AZURE_INFERENCE,
            "azure": EmbeddingProvider.AZURE_INFERENCE,
            "openai": EmbeddingProvider.OPENAI,
        }
        return provider_mapping.get(provider_name.lower())

    def get_available_providers(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all available providers"""
        result = {}

        for provider_enum, config in self.providers.items():
            result[provider_enum.value] = {
                "available": config.is_available,
                "models": config.supported_models,
                "type": "embedding"
            }

        return result

    def test_all_providers(self) -> Dict[str, bool]:
        """Test all available embedding providers"""
        results = {}

        for provider_enum, config in self.providers.items():
            try:
                client = config.client_instance
                if hasattr(client, 'test_connection'):
                    test_result = client.test_connection()
                else:
                    # Try a simple embedding test
                    test_embedding = client.get_text_embedding("test")
                    test_result = len(test_embedding) > 0

                results[provider_enum.value] = test_result
                logger.info(
                    f"{'✅' if test_result else '❌'} {provider_enum.value} embedding test: {'PASS' if test_result else 'FAIL'}")

            except Exception as e:
                results[provider_enum.value] = False
                logger.error(
                    f"❌ {provider_enum.value} embedding test failed: {e}")

        return results


# Global embedding provider selector instance
embedding_provider_selector = EmbeddingProviderSelector()
