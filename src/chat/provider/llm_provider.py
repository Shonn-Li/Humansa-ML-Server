"""
LLM Provider Module - Clean provider selection and management

This module handles:
- Provider selection based on model/provider preferences
- LLM instance creation and configuration
- Provider availability checking
- Model-to-provider mapping
"""

from llama_index.llms.openai import OpenAI
from llama_index.core.callbacks import CallbackManager, TokenCountingHandler
from llama_index.core.llms.llm import LLM
import os
import logging
from typing import Dict, Any, Optional, Tuple, List
from enum import Enum
from dataclasses import dataclass

# Configure Azure logging to reduce verbosity
azure_loggers = [
    'azure.core.pipeline.policies.http_logging_policy',
    'azure.ai.inference',
    'azure.core.pipeline',
    'azure.identity',
    'azure.core'
]
for logger_name in azure_loggers:
    azure_logger = logging.getLogger(logger_name)
    azure_logger.setLevel(logging.WARNING)  # Only show warnings/errors

# LlamaIndex LLM imports

# Try importing Azure AI Inference (Primary Provider)
try:
    from llama_index.llms.azure_inference import AzureAICompletionsModel
    AZURE_INFERENCE_AVAILABLE = True
except ImportError:
    AZURE_INFERENCE_AVAILABLE = False

# Try importing Azure OpenAI (For router compatibility)
try:
    from llama_index.llms.azure_openai import AzureOpenAI
    AZURE_OPENAI_AVAILABLE = True
except ImportError:
    AZURE_OPENAI_AVAILABLE = False

# Try importing additional providers
try:
    from llama_index.llms.anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

try:
    from llama_index.llms.deepseek import DeepSeek
    DEEPSEEK_AVAILABLE = True
except ImportError:
    DEEPSEEK_AVAILABLE = False

try:
    from llama_index.llms.openai_like import OpenAILike
    OPENAI_LIKE_AVAILABLE = True
except ImportError:
    OPENAI_LIKE_AVAILABLE = False

try:
    from llama_index.llms.gemini import Gemini
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

# Try importing multimodal support
try:
    from llama_index.multi_modal_llms.openai import OpenAIMultiModal
    MULTIMODAL_AVAILABLE = True
except ImportError:
    MULTIMODAL_AVAILABLE = False

logger = logging.getLogger(__name__)


class LLMProvider(Enum):
    """Supported LLM providers"""
    AZURE_INFERENCE = "azure_inference"  # Primary provider - cost-effective
    AZURE_OPENAI = "azure_openai"  # For router compatibility
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    DEEPSEEK = "deepseek"
    XAI = "xai"


@dataclass
class ProviderConfig:
    """Configuration for a provider"""
    provider: LLMProvider
    llm_instance: LLM
    supported_models: list[str]
    is_available: bool
    multimodal: Optional[Any] = None


class LLMProviderSelector:
    """Clean provider selection and management"""

    def __init__(self):
        self.token_counter = TokenCountingHandler()
        self.providers: Dict[LLMProvider, ProviderConfig] = {}
        self._initialize_providers()

    def _initialize_providers(self):
        """Initialize all available providers"""
        logger.info("=== LLM Provider Initialization Debug ===")
        logger.info(
            f"AZURE_INFERENCE_ENDPOINT: {'SET' if os.getenv('AZURE_INFERENCE_ENDPOINT') else 'NOT SET'}")
        logger.info(
            f"AZURE_INFERENCE_CREDENTIAL: {'SET' if os.getenv('AZURE_INFERENCE_CREDENTIAL') else 'NOT SET'}")
        logger.info(
            f"OPENAI_API_KEY: {'SET' if os.getenv('OPENAI_API_KEY') else 'NOT SET'}")
        logger.info(
            f"ANTHROPIC_API_KEY: {'SET' if os.getenv('ANTHROPIC_API_KEY') else 'NOT SET'}")
        logger.info(
            f"GOOGLE_API_KEY: {'SET' if os.getenv('GOOGLE_API_KEY') else 'NOT SET'}")
        logger.info(
            f"DEEPSEEK_API_KEY: {'SET' if os.getenv('DEEPSEEK_API_KEY') else 'NOT SET'}")
        logger.info(
            f"XAI_API_KEY: {'SET' if os.getenv('XAI_API_KEY') else 'NOT SET'}")
        logger.info("===========================================")

        # Azure AI Inference (Primary Provider) - NOTE: Does NOT support multimodal despite accepting ImageBlocks
        if AZURE_INFERENCE_AVAILABLE and os.getenv("AZURE_INFERENCE_ENDPOINT") and os.getenv("AZURE_INFERENCE_CREDENTIAL"):
            try:
                azure_llm = AzureAICompletionsModel(
                    endpoint=os.getenv("AZURE_INFERENCE_ENDPOINT"),
                    credential=os.getenv("AZURE_INFERENCE_CREDENTIAL"),
                    model_name="gpt-4.1-nano",  # Default to most cost-effective model
                    temperature=0.7,
                    callback_manager=CallbackManager([self.token_counter])
                )

                self.providers[LLMProvider.AZURE_INFERENCE] = ProviderConfig(
                    provider=LLMProvider.AZURE_INFERENCE,
                    llm_instance=azure_llm,
                    supported_models=[
                        # Available Azure models from your deployment
                        "gpt-4.1-nano", "gpt-4.1",  # OpenAI models
                        # GPT-4o models (vision models but not working via AI Inference)
                        "gpt-4o-mini", "gpt-4o",
                        "DeepSeek-R1", "DeepSeek-V3-0324",  # DeepSeek models
                        "grok-3", "grok-3-mini",  # xAI models
                        "o4-mini"  # OpenAI o4 model
                    ],
                    is_available=True,
                    multimodal=None  # IMPORTANT: No multimodal support despite having vision models
                )
                logger.info(
                    "✅ Azure AI Inference provider initialized (PRIMARY - NO MULTIMODAL)")
            except Exception as e:
                logger.error(f"❌ Azure AI Inference provider failed: {e}")

        # Azure OpenAI (For router compatibility) - IMPORTANT: This provider DOES support multimodal properly
        if AZURE_OPENAI_AVAILABLE and os.getenv("AZURE_INFERENCE_CREDENTIAL"):
            try:
                # Use the Azure endpoint URL you provided
                azure_openai_llm = AzureOpenAI(
                    azure_endpoint="https://youwoai-dev-resource.openai.azure.com/",
                    api_key=os.getenv("AZURE_INFERENCE_CREDENTIAL"),
                    api_version="2024-02-15-preview",
                    model="gpt-4o-mini",  # Default model for vision
                    # Required: deployment name (same as model for Azure)
                    engine="gpt-4o-mini",
                    temperature=0.7,
                    callback_manager=CallbackManager([self.token_counter])
                )

                self.providers[LLMProvider.AZURE_OPENAI] = ProviderConfig(
                    provider=LLMProvider.AZURE_OPENAI,
                    llm_instance=azure_openai_llm,
                    supported_models=[
                        "gpt-4.1-nano", "gpt-4.1", "gpt-4o-mini", "gpt-4o",
                        "gpt-4-turbo", "gpt-3.5-turbo"
                    ],
                    is_available=True,
                    multimodal=azure_openai_llm  # This provider DOES support multimodal
                )
                logger.info(
                    "✅ Azure OpenAI provider initialized (ROUTER COMPATIBLE + MULTIMODAL)")
            except Exception as e:
                logger.error(f"❌ Azure OpenAI provider failed: {e}")

        # OpenAI
        if os.getenv("OPENAI_API_KEY"):
            try:
                openai_llm = OpenAI(
                    model="gpt-4.1-nano",  # Most cost-effective model as default
                    temperature=0.7,
                    callback_manager=CallbackManager([self.token_counter])
                )

                config = ProviderConfig(
                    provider=LLMProvider.OPENAI,
                    llm_instance=openai_llm,
                    supported_models=[
                        "gpt-4.1-nano", "gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo",
                        "gpt-4-turbo", "gpt-4.1", "gpt-4.1-mini", "o3", "o4-mini",
                        "gpt-4", "o1-mini", "o1-preview"
                    ],
                    is_available=True
                )

                # Add multimodal support if available
                if MULTIMODAL_AVAILABLE:
                    try:
                        multimodal_llm = OpenAIMultiModal(
                            model="gpt-4.1-nano",  # Use cost-effective model for multimodal too
                            callback_manager=CallbackManager(
                                [self.token_counter])
                        )
                        config.multimodal = multimodal_llm
                        logger.info("✅ OpenAI multimodal support enabled")
                    except Exception as e:
                        logger.warning(
                            f"⚠️ OpenAI multimodal initialization failed: {e}")

                self.providers[LLMProvider.OPENAI] = config
                logger.info("✅ OpenAI provider initialized")
            except Exception as e:
                logger.error(f"❌ OpenAI provider failed: {e}")

        # Anthropic
        if ANTHROPIC_AVAILABLE and os.getenv("ANTHROPIC_API_KEY"):
            try:
                anthropic_llm = Anthropic(
                    model="claude-3-5-haiku-20241022",
                    temperature=0.7,
                    callback_manager=CallbackManager([self.token_counter])
                )

                self.providers[LLMProvider.ANTHROPIC] = ProviderConfig(
                    provider=LLMProvider.ANTHROPIC,
                    llm_instance=anthropic_llm,
                    supported_models=[
                        "claude-3-5-haiku-20241022", "claude-3-5-sonnet-20241022",
                        "claude-3-opus-20240229", "claude-3-sonnet-20240229"
                    ],
                    is_available=True
                )
                logger.info("✅ Anthropic provider initialized")
            except Exception as e:
                logger.error(f"❌ Anthropic provider failed: {e}")

        # Gemini
        if GEMINI_AVAILABLE and os.getenv("GOOGLE_API_KEY"):
            try:
                gemini_llm = Gemini(
                    model="models/gemini-2.0-flash",
                    api_key=os.getenv("GOOGLE_API_KEY"),
                    temperature=0.7,
                    callback_manager=CallbackManager([self.token_counter])
                )

                self.providers[LLMProvider.GEMINI] = ProviderConfig(
                    provider=LLMProvider.GEMINI,
                    llm_instance=gemini_llm,
                    supported_models=[
                        "models/gemini-2.0-flash", "models/gemini-1.5-flash",
                        "models/gemini-1.5-pro", "models/gemini-pro"
                    ],
                    is_available=True
                )
                logger.info("✅ Gemini provider initialized")
            except Exception as e:
                logger.error(f"❌ Gemini provider failed: {e}")

        # DeepSeek
        if DEEPSEEK_AVAILABLE and os.getenv("DEEPSEEK_API_KEY"):
            try:
                deepseek_llm = DeepSeek(
                    model="deepseek-chat",
                    api_key=os.getenv("DEEPSEEK_API_KEY"),
                    temperature=0.7,
                    callback_manager=CallbackManager([self.token_counter])
                )

                self.providers[LLMProvider.DEEPSEEK] = ProviderConfig(
                    provider=LLMProvider.DEEPSEEK,
                    llm_instance=deepseek_llm,
                    supported_models=[
                        "deepseek-chat", "deepseek-coder", "deepseek-reasoner"
                    ],
                    is_available=True
                )
                logger.info("✅ DeepSeek provider initialized")
            except Exception as e:
                logger.error(f"❌ DeepSeek provider failed: {e}")

        # xAI
        if OPENAI_LIKE_AVAILABLE and os.getenv("XAI_API_KEY"):
            try:
                xai_llm = OpenAILike(
                    model="grok-3-mini",  # Most cost-effective xAI model
                    api_key=os.getenv("XAI_API_KEY"),
                    api_base="https://api.x.ai/v1",
                    is_chat_model=True,
                    is_function_calling_model=False,
                    context_window=131072,
                    temperature=0.7,
                    callback_manager=CallbackManager([self.token_counter])
                )

                self.providers[LLMProvider.XAI] = ProviderConfig(
                    provider=LLMProvider.XAI,
                    llm_instance=xai_llm,
                    supported_models=[
                        "grok-3-mini", "grok-3", "grok-2-vision-1212", "grok-2-image-1212",
                        "grok-beta"  # Legacy support
                    ],
                    is_available=True
                )
                logger.info("✅ xAI provider initialized")
            except Exception as e:
                logger.error(f"❌ xAI provider failed: {e}")

        logger.info(f"=== Provider Initialization Complete ===")
        logger.info(f"Available providers: {len(self.providers)}")
        for provider_enum, config in self.providers.items():
            logger.info(
                f"  {provider_enum.value}: {len(config.supported_models)} models")
        logger.info("=========================================")

    def select_provider_and_model(self, requested_provider: Optional[str] = None,
                                  requested_model: Optional[str] = None) -> Tuple[LLMProvider, LLM]:
        """
        Select the best provider and model based on request

        Args:
            requested_provider: Optional provider name
            requested_model: Optional model name

        Returns:
            Tuple of (provider_enum, llm_instance)
        """
        logger.info(
            f"Provider selection - requested_provider: {requested_provider}, requested_model: {requested_model}")

        # Case 1: Both provider and model specified
        if requested_provider and requested_model:
            provider_enum = self._get_provider_enum(requested_provider)

            # Always check if Azure supports the model first (for cost savings)
            if LLMProvider.AZURE_INFERENCE in self.providers:
                azure_config = self.providers[LLMProvider.AZURE_INFERENCE]
                if requested_model in azure_config.supported_models:
                    llm = self._create_llm_instance(
                        LLMProvider.AZURE_INFERENCE, requested_model)
                    logger.info(
                        f"🎯 Override to Azure for cost savings: {LLMProvider.AZURE_INFERENCE.value} with {requested_model} (requested: {requested_provider})")
                    return LLMProvider.AZURE_INFERENCE, llm

            # Fallback to requested provider if Azure doesn't support the model
            if provider_enum and provider_enum in self.providers:
                config = self.providers[provider_enum]
                if requested_model in config.supported_models:
                    # Create new instance with requested model
                    llm = self._create_llm_instance(
                        provider_enum, requested_model)
                    logger.info(
                        f"✅ Selected: {provider_enum.value} with {requested_model}")
                    return provider_enum, llm
                else:
                    logger.warning(
                        f"Model {requested_model} not supported by {provider_enum.value}")

        # Case 2: Only model specified - find provider that supports it
        if requested_model:
            logger.info(
                f"Searching for provider supporting model: {requested_model}")

            # First try exact match, prioritizing Azure for cost savings
            azure_match = None
            other_matches = []

            for provider_enum, config in self.providers.items():
                if requested_model in config.supported_models:
                    if provider_enum == LLMProvider.AZURE_INFERENCE:
                        azure_match = (provider_enum, requested_model)
                        logger.info(
                            f"🎯 Found Azure match for {requested_model}")
                    else:
                        other_matches.append((provider_enum, requested_model))

            # Prioritize Azure if available
            if azure_match:
                provider_enum, model = azure_match
                llm = self._create_llm_instance(provider_enum, model)
                logger.info(
                    f"✅ Selected Azure (prioritized): {provider_enum.value} with {model}")
                return provider_enum, llm

            # Fallback to other providers
            elif other_matches:
                provider_enum, model = other_matches[0]
                llm = self._create_llm_instance(provider_enum, model)
                logger.info(
                    f"✅ Selected fallback: {provider_enum.value} with {model}")
                return provider_enum, llm

            # Try fuzzy matching for similar models
            logger.info(
                f"No exact match found for {requested_model}, trying fuzzy matching...")
            model_lower = requested_model.lower()

            for provider_enum, config in self.providers.items():
                for available_model in config.supported_models:
                    available_model_lower = available_model.lower()

                    # Check for Azure models first (priority)
                    if provider_enum == LLMProvider.AZURE_INFERENCE:
                        # GPT models on Azure
                        if any(keyword in model_lower for keyword in ["gpt", "o1", "o3", "o4"]) and \
                           any(keyword in available_model_lower for keyword in ["gpt", "o1", "o3", "o4"]):
                            logger.info(
                                f"✅ Found Azure GPT match: {available_model} for {requested_model}")
                            llm = self._create_llm_instance(
                                provider_enum, available_model)
                            return provider_enum, llm

                        # DeepSeek models on Azure
                        elif "deepseek" in model_lower and "deepseek" in available_model_lower:
                            logger.info(
                                f"✅ Found Azure DeepSeek match: {available_model} for {requested_model}")
                            llm = self._create_llm_instance(
                                provider_enum, available_model)
                            return provider_enum, llm

                        # Grok models on Azure
                        elif "grok" in model_lower and "grok" in available_model_lower:
                            logger.info(
                                f"✅ Found Azure Grok match: {available_model} for {requested_model}")
                            llm = self._create_llm_instance(
                                provider_enum, available_model)
                            return provider_enum, llm

                    # Check for Claude model family matching
                    if any(keyword in model_lower for keyword in ["claude", "sonnet", "opus", "haiku"]) and \
                       any(keyword in available_model_lower for keyword in ["claude", "sonnet", "opus", "haiku"]):

                        # For Claude models, match the family
                        if "claude" in model_lower and "claude" in available_model_lower:
                            if ("sonnet" in model_lower and "sonnet" in available_model_lower) or \
                               ("opus" in model_lower and "opus" in available_model_lower) or \
                               ("haiku" in model_lower and "haiku" in available_model_lower):

                                logger.info(
                                    f"✅ Found Claude family match: {available_model} for {requested_model}")
                                llm = self._create_llm_instance(
                                    provider_enum, available_model)
                                return provider_enum, llm

                    # Check for GPT model family matching
                    elif any(keyword in model_lower for keyword in ["gpt", "o1", "o3", "o4"]) and \
                            any(keyword in available_model_lower for keyword in ["gpt", "o1", "o3", "o4"]):

                        if ("gpt-4" in model_lower and "gpt-4" in available_model_lower) or \
                           ("gpt-3" in model_lower and "gpt-3" in available_model_lower) or \
                           ("o1" in model_lower and "o1" in available_model_lower) or \
                           ("o3" in model_lower and "o3" in available_model_lower) or \
                           ("o4" in model_lower and "o4" in available_model_lower):

                            logger.info(
                                f"✅ Found GPT family match: {available_model} for {requested_model}")
                            llm = self._create_llm_instance(
                                provider_enum, available_model)
                            return provider_enum, llm

                    # Check for Gemini model family matching
                    elif "gemini" in model_lower and "gemini" in available_model_lower:
                        logger.info(
                            f"✅ Found Gemini family match: {available_model} for {requested_model}")
                        llm = self._create_llm_instance(
                            provider_enum, available_model)
                        return provider_enum, llm

                    # Check for Grok model family matching
                    elif "grok" in model_lower and "grok" in available_model_lower:
                        logger.info(
                            f"✅ Found Grok family match: {available_model} for {requested_model}")
                        llm = self._create_llm_instance(
                            provider_enum, available_model)
                        return provider_enum, llm

                    # Check for DeepSeek model family matching
                    elif "deepseek" in model_lower and "deepseek" in available_model_lower:
                        logger.info(
                            f"✅ Found DeepSeek family match: {available_model} for {requested_model}")
                        llm = self._create_llm_instance(
                            provider_enum, available_model)
                        return provider_enum, llm

                    # Generic partial matching for other cases
                    elif model_lower in available_model_lower or available_model_lower in model_lower:
                        logger.info(
                            f"✅ Found partial match: {available_model} for {requested_model}")
                        llm = self._create_llm_instance(
                            provider_enum, available_model)
                        return provider_enum, llm

            logger.warning(
                f"No provider found for model {requested_model}, falling back to default")

        # Case 3: Only provider specified - use default model
        if requested_provider:
            provider_enum = self._get_provider_enum(requested_provider)
            if provider_enum and provider_enum in self.providers:
                config = self.providers[provider_enum]
                # First model is default
                default_model = config.supported_models[0]
                llm = self._create_llm_instance(provider_enum, default_model)
                logger.info(
                    f"✅ Selected provider {provider_enum.value} with default model {default_model}")
                return provider_enum, llm

        # Case 4: Nothing specified - use best available
        if self.providers:
            # Priority: Azure Inference (Primary) > OpenAI > Anthropic > Gemini > DeepSeek > xAI
            priority_order = [LLMProvider.AZURE_INFERENCE, LLMProvider.OPENAI, LLMProvider.ANTHROPIC,
                              LLMProvider.GEMINI, LLMProvider.DEEPSEEK, LLMProvider.XAI]

            for provider_enum in priority_order:
                if provider_enum in self.providers:
                    config = self.providers[provider_enum]
                    default_model = config.supported_models[0]
                    llm = self._create_llm_instance(
                        provider_enum, default_model)
                    logger.info(
                        f"✅ Auto-selected {provider_enum.value} with {default_model}")
                    return provider_enum, llm

        # Fallback error
        raise ValueError(
            "No LLM providers available. Please check your API keys.")

    def _get_provider_enum(self, provider_name: str) -> Optional[LLMProvider]:
        """Convert provider name string to enum"""
        provider_mapping = {
            "azure_inference": LLMProvider.AZURE_INFERENCE,
            "azure": LLMProvider.AZURE_INFERENCE,  # Alternative name
            "openai": LLMProvider.OPENAI,
            "anthropic": LLMProvider.ANTHROPIC,
            "gemini": LLMProvider.GEMINI,
            "deepseek": LLMProvider.DEEPSEEK,
            "xai": LLMProvider.XAI
        }
        return provider_mapping.get(provider_name.lower())

    def _create_llm_instance(self, provider: LLMProvider, model: str) -> LLM:
        """Create a new LLM instance with specific model"""
        if provider == LLMProvider.AZURE_INFERENCE and AZURE_INFERENCE_AVAILABLE:
            # Configure Azure client with proper session management and connection pooling
            client_kwargs = {
                "connection_timeout": 30.0,
                "read_timeout": 120.0,
                # Use connection pooling to reduce session creation
                "connector": {
                    "limit": 10,  # Max connections
                    "limit_per_host": 5,  # Max per host
                    "keepalive_timeout": 30,
                    "enable_cleanup_closed": True,
                    "force_close": True,  # Force close connections
                    "auto_decompress": True
                }
            }

            llm = AzureAICompletionsModel(
                endpoint=os.getenv("AZURE_INFERENCE_ENDPOINT"),
                credential=os.getenv("AZURE_INFERENCE_CREDENTIAL"),
                model_name=model,
                temperature=0.7,
                callback_manager=CallbackManager([self.token_counter]),
                client_kwargs=client_kwargs
            )

            # Log request info cleanly (without Azure's verbose logging)
            endpoint_short = os.getenv('AZURE_INFERENCE_ENDPOINT', 'N/A').split(
                '/')[-3] if os.getenv('AZURE_INFERENCE_ENDPOINT') else 'N/A'
            logger.info(
                f"🔗 Azure AI Inference configured: {model} -> {endpoint_short}")
            return llm

        elif provider == LLMProvider.AZURE_OPENAI and AZURE_OPENAI_AVAILABLE:
            return AzureOpenAI(
                azure_endpoint="https://youwoai-dev-resource.openai.azure.com/",
                api_key=os.getenv("AZURE_INFERENCE_CREDENTIAL"),
                api_version="2024-02-15-preview",
                model=model,
                # Required: deployment name (same as model for Azure)
                engine=model,
                temperature=0.7,
                callback_manager=CallbackManager([self.token_counter])
            )
        elif provider == LLMProvider.OPENAI:
            return OpenAI(
                model=model,
                temperature=0.7,
                callback_manager=CallbackManager([self.token_counter])
            )
        elif provider == LLMProvider.ANTHROPIC and ANTHROPIC_AVAILABLE:
            return Anthropic(
                model=model,
                temperature=0.7,
                callback_manager=CallbackManager([self.token_counter])
            )
        elif provider == LLMProvider.GEMINI and GEMINI_AVAILABLE:
            return Gemini(
                model=model,
                api_key=os.getenv("GOOGLE_API_KEY"),
                temperature=0.7,
                callback_manager=CallbackManager([self.token_counter])
            )
        elif provider == LLMProvider.DEEPSEEK and DEEPSEEK_AVAILABLE:
            return DeepSeek(
                model=model,
                api_key=os.getenv("DEEPSEEK_API_KEY"),
                temperature=0.7,
                callback_manager=CallbackManager([self.token_counter])
            )
        elif provider == LLMProvider.XAI and OPENAI_LIKE_AVAILABLE:
            return OpenAILike(
                model=model,
                api_key=os.getenv("XAI_API_KEY"),
                api_base="https://api.x.ai/v1",
                is_chat_model=True,
                is_function_calling_model=False,
                context_window=131072,
                temperature=0.7,
                callback_manager=CallbackManager([self.token_counter])
            )
        else:
            raise ValueError(
                f"Provider {provider.value} not available or not supported")

    def get_available_providers(self) -> Dict[str, Dict[str, Any]]:
        """Get list of available providers and their models"""
        result = {}
        for provider_enum, config in self.providers.items():
            result[provider_enum.value] = {
                "models": config.supported_models,
                "available": config.is_available
            }
        return result

    def configure_llm(self, llm: LLM, temperature: Optional[float] = None,
                      max_tokens: Optional[int] = None) -> LLM:
        """Configure LLM with runtime parameters"""
        if temperature is not None:
            llm.temperature = temperature
        if max_tokens is not None:
            llm.max_tokens = max_tokens
        return llm

    def get_provider(self, provider_name: Optional[str] = None, model: Optional[str] = None) -> Dict[str, Any]:
        """
        Get LLM provider info (compatible with enhanced chatbot API)

        Args:
            provider_name: Optional provider name
            model: Optional model name

        Returns:
            Dict with provider, llm, multimodal, and models info
        """
        provider_enum, llm = self.select_provider_and_model(
            provider_name, model)
        config = self.providers[provider_enum]

        return {
            "provider": provider_enum,
            "llm": llm,
            "multimodal": config.multimodal,
            "models": config.supported_models
        }

    def list_available_providers(self) -> Dict[str, List[str]]:
        """List all available providers and their models (compatible with enhanced chatbot)"""
        return {
            provider.value: config.supported_models
            for provider, config in self.providers.items()
        }

    def get_router_compatible_llm(self) -> Optional[LLM]:
        """
        Get an OpenAI-compatible LLM for router functionality
        Router requires OpenAI-compatible LLMs for PydanticSingleSelector

        Returns:
            LLM compatible with router functionality, or None if not available
        """
        # Try Azure OpenAI first (uses same credentials as Azure AI Inference)
        if LLMProvider.AZURE_OPENAI in self.providers:
            azure_openai_config = self.providers[LLMProvider.AZURE_OPENAI]
            logger.info("🎯 Using Azure OpenAI LLM for router compatibility")
            return azure_openai_config.llm_instance

        # Fall back to regular OpenAI if available
        elif LLMProvider.OPENAI in self.providers:
            openai_config = self.providers[LLMProvider.OPENAI]
            logger.info("🎯 Using OpenAI LLM for router compatibility")
            return openai_config.llm_instance

        else:
            logger.warning(
                "⚠️ No OpenAI-compatible LLM available for router - router will be disabled")
            return None
