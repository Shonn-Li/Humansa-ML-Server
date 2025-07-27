#!/usr/bin/env python3
"""
Test Azure OpenAI Configuration for Humansa V2
Tests that GPT-4.1 is properly configured with Azure endpoints
"""

import os
import asyncio
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_azure_openai_llm():
    """Test Azure OpenAI LLM configuration"""
    logger.info("=== Testing Azure OpenAI LLM Configuration ===")
    
    try:
        from llama_index.llms.azure_openai import AzureOpenAI
        
        # Get Azure credentials
        azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "https://youwoai-dev-resource.openai.azure.com/")
        azure_api_key = os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("AZURE_INFERENCE_CREDENTIAL")
        
        if not azure_api_key:
            logger.error("❌ No Azure API key found! Set AZURE_OPENAI_API_KEY or AZURE_INFERENCE_CREDENTIAL")
            return False
            
        logger.info(f"📍 Azure Endpoint: {azure_endpoint}")
        logger.info(f"🔑 API Key: {'SET' if azure_api_key else 'NOT SET'}")
        
        # Initialize Azure OpenAI with GPT-4.1
        llm = AzureOpenAI(
            model="gpt-4.1",
            deployment_name="gpt-4.1",
            api_key=azure_api_key,
            azure_endpoint=azure_endpoint,
            api_version="2024-02-15-preview",
            temperature=0.7,
            max_tokens=100
        )
        
        logger.info("✅ Azure OpenAI LLM initialized with GPT-4.1")
        
        # Test the LLM
        response = llm.complete("Say 'Azure OpenAI GPT-4.1 is working!' if you can read this.")
        logger.info(f"🤖 LLM Response: {response.text}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Azure OpenAI LLM test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_azure_embeddings():
    """Test Azure embeddings configuration"""
    logger.info("\n=== Testing Azure Embeddings Configuration ===")
    
    try:
        from src.chat.embedding.azure_embeddings import AzureEmbeddingClient, AZURE_EMBEDDINGS_AVAILABLE
        
        if not AZURE_EMBEDDINGS_AVAILABLE:
            logger.error("❌ Azure embeddings not available - missing dependencies")
            return False
            
        # Initialize Azure embeddings
        embedder = AzureEmbeddingClient(model="text-embedding-3-small")
        
        # Test embedding generation
        test_text = "Testing Azure embeddings for Humansa V2"
        embedding = embedder.get_text_embedding(test_text)
        
        logger.info(f"✅ Azure embeddings working! Generated {len(embedding)}-dimensional embedding")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Azure embeddings test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_mem0_azure_config():
    """Test Mem0 Azure configuration"""
    logger.info("\n=== Testing Mem0 Azure Configuration ===")
    
    try:
        from src.humansa.memory.mem0_manager import Mem0Manager
        
        # Get Mem0 instance
        mem0_manager = Mem0Manager.get_instance()
        config = mem0_manager.config
        
        # Check LLM config
        if "llm" in config:
            llm_config = config["llm"]
            logger.info(f"📦 Mem0 LLM Provider: {llm_config.get('provider', 'unknown')}")
            
            if llm_config.get("provider") == "azure_openai":
                logger.info("✅ Mem0 configured to use Azure OpenAI")
                azure_deployment = llm_config.get("config", {}).get("azure_deployment", "unknown")
                logger.info(f"🤖 Azure Deployment: {azure_deployment}")
            else:
                logger.warning("⚠️ Mem0 not using Azure OpenAI")
                
        # Check embedder config
        if "embedder" in config:
            embedder_config = config["embedder"]
            logger.info(f"📦 Mem0 Embedder Provider: {embedder_config.get('provider', 'unknown')}")
            
            if embedder_config.get("provider") == "azure_openai":
                logger.info("✅ Mem0 configured to use Azure embeddings")
            else:
                logger.warning("⚠️ Mem0 not using Azure embeddings")
                
        return True
        
    except Exception as e:
        logger.error(f"❌ Mem0 configuration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all configuration tests"""
    logger.info("🧪 Testing Azure OpenAI Configuration for Humansa V2\n")
    
    # Check environment variables
    logger.info("=== Environment Variables ===")
    env_vars = {
        "AZURE_OPENAI_API_KEY": os.getenv("AZURE_OPENAI_API_KEY"),
        "AZURE_OPENAI_ENDPOINT": os.getenv("AZURE_OPENAI_ENDPOINT"),
        "AZURE_INFERENCE_CREDENTIAL": os.getenv("AZURE_INFERENCE_CREDENTIAL"),
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY")
    }
    
    for key, value in env_vars.items():
        status = "SET" if value else "NOT SET"
        logger.info(f"{key}: {status}")
    
    # Run tests
    results = {
        "Azure OpenAI LLM": await test_azure_openai_llm(),
        "Azure Embeddings": await test_azure_embeddings(),
        "Mem0 Configuration": await test_mem0_azure_config()
    }
    
    # Summary
    logger.info("\n=== Test Summary ===")
    all_passed = True
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        logger.info(f"{test_name}: {status}")
        if not passed:
            all_passed = False
    
    if all_passed:
        logger.info("\n🎉 All tests passed! Azure OpenAI is properly configured.")
    else:
        logger.error("\n❌ Some tests failed. Please check your configuration.")
        logger.info("\nMake sure you have set:")
        logger.info("1. AZURE_OPENAI_API_KEY or AZURE_INFERENCE_CREDENTIAL")
        logger.info("2. AZURE_OPENAI_ENDPOINT (default: https://youwoai-dev-resource.openai.azure.com/)")
        logger.info("3. Removed or commented out OPENAI_API_KEY to use Azure only")


if __name__ == "__main__":
    asyncio.run(main())