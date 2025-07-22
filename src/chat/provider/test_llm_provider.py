"""
Test Script for Updated LLM Provider

This script tests the improved LLM provider implementation to ensure
it matches the enhanced chatbot's functionality.
"""

from chat.provider.llm_provider import LLMProviderSelector
import logging
import sys
import os

# Add path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))


# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_provider_initialization():
    """Test that providers initialize correctly"""
    logger.info("=== Testing Provider Initialization ===")

    try:
        selector = LLMProviderSelector()
        available = selector.get_available_providers()

        logger.info(f"✅ Provider initialization successful")
        logger.info(f"Available providers: {list(available.keys())}")

        for provider_name, info in available.items():
            logger.info(f"  {provider_name}: {len(info['models'])} models")
            logger.info(f"    Models: {info['models']}")

        return True

    except Exception as e:
        logger.error(f"❌ Provider initialization failed: {e}")
        return False


def test_model_selection():
    """Test various model selection scenarios"""
    logger.info("\n=== Testing Model Selection ===")

    selector = LLMProviderSelector()

    test_cases = [
        # (provider, model, description)
        (None, None, "Auto-select default"),
        ("openai", None, "OpenAI with default model"),
        (None, "gpt-4.1-nano", "Find provider for gpt-4.1-nano"),
        (None, "claude-3.5-sonnet", "Find provider for Claude Sonnet (fuzzy)"),
        (None, "grok-3", "Find provider for Grok (fuzzy)"),
        (None, "gemini-flash", "Find provider for Gemini (fuzzy)"),
        (None, "deepseek-chat", "Find provider for DeepSeek"),
        ("anthropic", "claude-3-5-haiku-20241022",
         "Anthropic with specific Claude"),
        ("xai", "grok-3-mini", "xAI with Grok mini"),
    ]

    for provider, model, description in test_cases:
        try:
            logger.info(f"\nTesting: {description}")
            logger.info(f"  Request: provider={provider}, model={model}")

            provider_enum, llm = selector.select_provider_and_model(
                provider, model)

            logger.info(
                f"  ✅ Result: {provider_enum.value} with model {getattr(llm, 'model', 'unknown')}")

        except Exception as e:
            logger.error(f"  ❌ Failed: {e}")


def test_compatibility_methods():
    """Test compatibility with enhanced chatbot API"""
    logger.info("\n=== Testing Compatibility Methods ===")

    selector = LLMProviderSelector()

    try:
        # Test get_provider method (enhanced chatbot compatibility)
        provider_info = selector.get_provider("openai", "gpt-4.1-nano")
        logger.info(f"✅ get_provider method works")
        logger.info(f"  Provider: {provider_info['provider'].value}")
        logger.info(f"  Models: {len(provider_info['models'])} available")
        logger.info(f"  Multimodal: {provider_info['multimodal'] is not None}")

        # Test list_available_providers method
        available = selector.list_available_providers()
        logger.info(f"✅ list_available_providers method works")
        logger.info(f"  Providers: {list(available.keys())}")

        return True

    except Exception as e:
        logger.error(f"❌ Compatibility test failed: {e}")
        return False


def test_fuzzy_matching():
    """Test fuzzy matching capabilities"""
    logger.info("\n=== Testing Fuzzy Matching ===")

    selector = LLMProviderSelector()

    fuzzy_test_cases = [
        ("gpt-4", "Should match gpt-4 family"),
        ("claude-sonnet", "Should match Claude Sonnet family"),
        ("gemini-pro", "Should match Gemini family"),
        ("grok", "Should match Grok family"),
        ("deepseek", "Should match DeepSeek family"),
        ("o1", "Should match o1 family"),
    ]

    for model_request, description in fuzzy_test_cases:
        try:
            logger.info(f"\nTesting fuzzy match: {model_request}")
            logger.info(f"  Expected: {description}")

            provider_enum, llm = selector.select_provider_and_model(
                None, model_request)
            actual_model = getattr(llm, 'model', 'unknown')

            logger.info(
                f"  ✅ Matched: {provider_enum.value} with {actual_model}")

        except Exception as e:
            logger.error(f"  ❌ Fuzzy matching failed for {model_request}: {e}")


def run_all_tests():
    """Run all LLM provider tests"""
    logger.info("🚀 Starting LLM Provider Tests")

    tests = [
        test_provider_initialization,
        test_model_selection,
        test_compatibility_methods,
        test_fuzzy_matching
    ]

    passed = 0
    total = len(tests)

    for test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            logger.error(f"Test {test_func.__name__} crashed: {e}")

    logger.info(f"\n🎉 Test Results: {passed}/{total} tests passed")

    if passed == total:
        logger.info("✅ All tests passed! LLM provider is working correctly.")
    else:
        logger.warning(
            f"⚠️ {total - passed} tests failed. Please check the logs.")


if __name__ == "__main__":
    run_all_tests()
