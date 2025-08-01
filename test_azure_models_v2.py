#!/usr/bin/env python3
"""
Test Azure Model Availability - Direct API Testing

This script tests model availability by trying to use them directly.
"""

import os
import requests
import json
import logging
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_model_with_completion(model_name, endpoint, api_key):
    """Test if a model works by making a simple completion request"""
    try:
        # For Azure AI Inference
        url = f"{endpoint.rstrip('/')}/chat/completions"
        headers = {
            "api-key": api_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model_name,
            "messages": [
                {"role": "user", "content": "Say 'hello' in one word"}
            ],
            "temperature": 0.1,
            "max_tokens": 10
        }
        
        logger.info(f"Testing {model_name} with completion request...")
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            content = result.get('choices', [{}])[0].get('message', {}).get('content', 'No response')
            logger.info(f"✅ {model_name} WORKS! Response: {content}")
            return True
        else:
            error_msg = response.json().get('error', {}).get('message', response.text)
            logger.info(f"❌ {model_name} failed: {error_msg}")
            return False
            
    except Exception as e:
        logger.error(f"❌ {model_name} error: {str(e)}")
        return False

def test_all_potential_models():
    """Test all potentially available models"""
    load_dotenv()
    
    endpoint = os.getenv("AZURE_INFERENCE_ENDPOINT")
    api_key = os.getenv("AZURE_INFERENCE_CREDENTIAL")
    
    if not endpoint or not api_key:
        logger.error("Azure credentials not set!")
        return
    
    # Models to test based on Azure documentation and your config
    models_to_test = [
        # GPT-4 family
        "gpt-4", "gpt-4-turbo", "gpt-4-turbo-preview",
        "gpt-4.1", "gpt-4.1-nano", "gpt-4.1-mini",
        "gpt-4o", "gpt-4o-mini",
        
        # O-series models
        "o3", "o3-mini", "o3-pro",
        "o4", "o4-mini",
        "o1", "o1-mini", "o1-preview",
        
        # GPT-3.5
        "gpt-3.5-turbo", "gpt-35-turbo",
        
        # Other models mentioned in config
        "DeepSeek-R1-0528", "DeepSeek-V3-0324",
        "grok-3", "grok-3-mini", "grok-4",
        
        # Common Azure deployment names
        "gpt-4-32k", "gpt-4-vision-preview",
        "text-embedding-ada-002"
    ]
    
    available_models = []
    
    logger.info("=" * 60)
    logger.info("TESTING ALL POTENTIAL MODELS")
    logger.info("=" * 60)
    
    for model in models_to_test:
        if test_model_with_completion(model, endpoint, api_key):
            available_models.append(model)
        logger.info("-" * 40)
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("SUMMARY OF WORKING MODELS")
    logger.info("=" * 60)
    
    if available_models:
        logger.info(f"\n✅ Found {len(available_models)} working models:")
        for model in available_models:
            logger.info(f"  • {model}")
            
        # Check for O3 models
        o3_models = [m for m in available_models if 'o3' in m.lower()]
        if o3_models:
            logger.info(f"\n🎉 O3 MODELS AVAILABLE: {', '.join(o3_models)}")
        else:
            logger.info("\n⚠️  No O3 models found in working models")
    else:
        logger.info("\n❌ No models were found to be working!")
    
    return available_models

def test_with_different_api_versions():
    """Test O3 with different API versions"""
    load_dotenv()
    
    logger.info("\n" + "=" * 60)
    logger.info("TESTING O3 WITH DIFFERENT API VERSIONS")
    logger.info("=" * 60)
    
    api_versions = [
        "2024-02-15-preview",
        "2024-06-01",
        "2024-08-01-preview",
        "2024-10-01-preview",
        "2024-12-01-preview",
        "2025-01-01-preview"
    ]
    
    endpoint = os.getenv("AZURE_INFERENCE_ENDPOINT")
    api_key = os.getenv("AZURE_INFERENCE_CREDENTIAL")
    
    for version in api_versions:
        try:
            url = f"{endpoint.rstrip('/')}/chat/completions?api-version={version}"
            headers = {
                "api-key": api_key,
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "o3",
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 10
            }
            
            logger.info(f"\nTesting O3 with API version: {version}")
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            
            if response.status_code == 200:
                logger.info(f"✅ O3 works with API version {version}!")
                return version
            else:
                error = response.json().get('error', {}).get('message', 'Unknown error')
                logger.info(f"❌ Failed: {error}")
                
        except Exception as e:
            logger.error(f"❌ Error with version {version}: {str(e)}")
    
    return None

if __name__ == "__main__":
    # Test all models
    available = test_all_potential_models()
    
    # If no O3 found, try different API versions
    if not any('o3' in m.lower() for m in available):
        working_version = test_with_different_api_versions()
        if working_version:
            logger.info(f"\n💡 O3 requires API version: {working_version}")
            logger.info("Update your Azure configuration to use this API version!")