#!/usr/bin/env python3
"""
Test Azure O3 Model Availability

This script tests if O3 models are available in your Azure OpenAI deployment.
"""

import os
import asyncio
import logging
from llama_index.llms.azure_inference import AzureAICompletionsModel
from llama_index.llms.azure_openai import AzureOpenAI

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_azure_inference_o3():
    """Test O3 models via Azure AI Inference"""
    logger.info("=== Testing Azure AI Inference O3 Models ===")
    
    models_to_test = ["o3-mini", "o3", "o3-pro"]
    results = {}
    
    for model in models_to_test:
        try:
            logger.info(f"\nTesting {model}...")
            
            azure_llm = AzureAICompletionsModel(
                endpoint=os.getenv("AZURE_INFERENCE_ENDPOINT"),
                credential=os.getenv("AZURE_INFERENCE_CREDENTIAL"),
                model_name=model,
                temperature=0.7
            )
            
            # Try a simple completion
            response = await azure_llm.acomplete("Say 'Hello from Azure O3!'")
            
            logger.info(f"✅ {model} is AVAILABLE!")
            logger.info(f"Response: {response.text[:100]}...")
            results[model] = "Available"
            
        except Exception as e:
            logger.error(f"❌ {model} is NOT available: {str(e)}")
            results[model] = f"Not available: {str(e)[:50]}..."
    
    return results

async def test_azure_openai_o3():
    """Test O3 models via Azure OpenAI"""
    logger.info("\n=== Testing Azure OpenAI O3 Models ===")
    
    models_to_test = ["o3-mini", "o3", "o3-pro"]
    results = {}
    
    for model in models_to_test:
        try:
            logger.info(f"\nTesting {model}...")
            
            azure_openai_llm = AzureOpenAI(
                azure_endpoint="https://youwoai-dev-resource.openai.azure.com/",
                api_key=os.getenv("AZURE_INFERENCE_CREDENTIAL"),
                api_version="2024-02-15-preview",
                model=model,
                engine=model,  # Azure requires deployment name
                temperature=0.7
            )
            
            # Try a simple completion
            response = await azure_openai_llm.acomplete("Say 'Hello from Azure O3!'")
            
            logger.info(f"✅ {model} is AVAILABLE!")
            logger.info(f"Response: {response.text[:100]}...")
            results[model] = "Available"
            
        except Exception as e:
            logger.error(f"❌ {model} is NOT available: {str(e)}")
            results[model] = f"Not available: {str(e)[:50]}..."
    
    return results

async def main():
    """Main test function"""
    logger.info("Starting Azure O3 Model Availability Test")
    logger.info("=" * 50)
    
    # Check environment variables
    if not os.getenv("AZURE_INFERENCE_CREDENTIAL"):
        logger.error("AZURE_INFERENCE_CREDENTIAL not set!")
        return
    
    if not os.getenv("AZURE_INFERENCE_ENDPOINT"):
        logger.error("AZURE_INFERENCE_ENDPOINT not set!")
        return
    
    # Test both providers
    inference_results = await test_azure_inference_o3()
    openai_results = await test_azure_openai_o3()
    
    # Summary
    logger.info("\n" + "=" * 50)
    logger.info("SUMMARY OF O3 MODEL AVAILABILITY")
    logger.info("=" * 50)
    
    logger.info("\nAzure AI Inference Results:")
    for model, status in inference_results.items():
        logger.info(f"  {model}: {status}")
    
    logger.info("\nAzure OpenAI Results:")
    for model, status in openai_results.items():
        logger.info(f"  {model}: {status}")
    
    # Recommendations
    logger.info("\nRECOMMENDATIONS:")
    all_results = {**inference_results, **openai_results}
    available_models = [m for m, s in all_results.items() if "Available" in s]
    
    if available_models:
        logger.info(f"✅ Available O3 models: {', '.join(set(available_models))}")
        logger.info("You can use these models in your ML server configuration.")
    else:
        logger.info("❌ No O3 models are currently available in your Azure deployment.")
        logger.info("You may need to request access or wait for deployment in your region.")

if __name__ == "__main__":
    asyncio.run(main())