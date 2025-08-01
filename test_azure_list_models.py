#!/usr/bin/env python3
"""
List Available Models in Azure OpenAI and Azure AI Inference

This script queries the Azure endpoints to list all available models.
"""

import os
import requests
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def list_azure_openai_models():
    """List available models via Azure OpenAI API"""
    logger.info("\n=== Listing Azure OpenAI Models ===")
    
    try:
        # Azure OpenAI endpoint for listing models
        endpoint = "https://youwoai-dev-resource.openai.azure.com/"
        api_key = os.getenv("AZURE_INFERENCE_CREDENTIAL")
        
        if not api_key:
            logger.error("AZURE_INFERENCE_CREDENTIAL not set!")
            return []
        
        # List deployments endpoint
        url = f"{endpoint}openai/deployments?api-version=2024-02-15-preview"
        headers = {
            "api-key": api_key,
            "Content-Type": "application/json"
        }
        
        logger.info(f"Fetching deployments from: {url}")
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            deployments = response.json()
            logger.info(f"✅ Found {len(deployments.get('data', []))} deployments")
            
            models = []
            for deployment in deployments.get('data', []):
                model_name = deployment.get('model')
                deployment_name = deployment.get('id')
                status = deployment.get('status')
                logger.info(f"  - Deployment: {deployment_name} | Model: {model_name} | Status: {status}")
                if status == 'succeeded':
                    models.append(model_name)
            
            return models
        else:
            logger.error(f"❌ Failed to list deployments: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return []
            
    except Exception as e:
        logger.error(f"❌ Error listing Azure OpenAI models: {e}")
        return []

def list_azure_inference_models():
    """List available models via Azure AI Inference API"""
    logger.info("\n=== Listing Azure AI Inference Models ===")
    
    try:
        endpoint = os.getenv("AZURE_INFERENCE_ENDPOINT")
        api_key = os.getenv("AZURE_INFERENCE_CREDENTIAL")
        
        if not endpoint or not api_key:
            logger.error("Azure Inference credentials not set!")
            return []
        
        # Models endpoint for Azure AI Inference
        url = f"{endpoint.rstrip('/')}/models"
        headers = {
            "api-key": api_key,
            "Content-Type": "application/json"
        }
        
        logger.info(f"Fetching models from: {url}")
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            models_data = response.json()
            logger.info(f"✅ Response received")
            
            models = []
            # Azure AI Inference returns a different format
            if 'data' in models_data:
                for model in models_data['data']:
                    model_id = model.get('id', model.get('name', 'Unknown'))
                    logger.info(f"  - Model: {model_id}")
                    models.append(model_id)
            else:
                # Sometimes it's a direct list
                logger.info(f"Raw response: {json.dumps(models_data, indent=2)}")
                
            return models
        else:
            logger.error(f"❌ Failed to list models: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return []
            
    except Exception as e:
        logger.error(f"❌ Error listing Azure AI Inference models: {e}")
        return []

def check_specific_model_availability(model_name):
    """Check if a specific model is available via direct API call"""
    logger.info(f"\n=== Checking specific model: {model_name} ===")
    
    endpoint = os.getenv("AZURE_INFERENCE_ENDPOINT")
    api_key = os.getenv("AZURE_INFERENCE_CREDENTIAL")
    
    if not endpoint or not api_key:
        logger.error("Azure Inference credentials not set!")
        return False
    
    try:
        # Try to get model info
        url = f"{endpoint.rstrip('/')}/models/{model_name}"
        headers = {
            "api-key": api_key,
            "Content-Type": "application/json"
        }
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            logger.info(f"✅ Model {model_name} is available!")
            logger.info(f"Model info: {json.dumps(response.json(), indent=2)}")
            return True
        else:
            logger.info(f"❌ Model {model_name} not found: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"Error checking model {model_name}: {e}")
        return False

def main():
    """Main function"""
    logger.info("Starting Azure Model Discovery")
    logger.info("=" * 60)
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # List models from both endpoints
    openai_models = list_azure_openai_models()
    inference_models = list_azure_inference_models()
    
    # Check specific O3 models
    o3_models = ["o3", "o3-mini", "o3-pro"]
    o3_availability = {}
    
    for model in o3_models:
        o3_availability[model] = check_specific_model_availability(model)
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("SUMMARY OF AVAILABLE MODELS")
    logger.info("=" * 60)
    
    logger.info("\n📋 Azure OpenAI Deployments:")
    if openai_models:
        for model in set(openai_models):
            logger.info(f"  ✅ {model}")
    else:
        logger.info("  ❌ No models found or unable to list")
    
    logger.info("\n📋 Azure AI Inference Models:")
    if inference_models:
        for model in set(inference_models):
            logger.info(f"  ✅ {model}")
    else:
        logger.info("  ❌ No models found or unable to list")
    
    logger.info("\n🔍 O3 Model Availability:")
    for model, available in o3_availability.items():
        status = "✅ Available" if available else "❌ Not Available"
        logger.info(f"  {model}: {status}")
    
    # Check if any O3 models are available
    if any(o3_availability.values()):
        logger.info("\n✨ O3 models ARE available in your Azure deployment!")
        logger.info("You can use these models in your ML server.")
    else:
        logger.info("\n⚠️  No O3 models are currently available in your Azure deployment.")
        logger.info("Available models are limited to those listed above.")

if __name__ == "__main__":
    main()