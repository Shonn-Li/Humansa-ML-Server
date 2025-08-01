#!/usr/bin/env python3
"""
Test O3 and O4-mini with correct parameters
"""

import os
import requests
import json
import logging
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_o3_model():
    """Test O3 with max_completion_tokens parameter"""
    load_dotenv()
    
    endpoint = os.getenv("AZURE_INFERENCE_ENDPOINT")
    api_key = os.getenv("AZURE_INFERENCE_CREDENTIAL")
    
    models = ["o3", "o4-mini"]
    
    for model in models:
        logger.info(f"\n=== Testing {model} with correct parameters ===")
        
        url = f"{endpoint.rstrip('/')}/chat/completions"
        headers = {
            "api-key": api_key,
            "Content-Type": "application/json"
        }
        
        # Use max_completion_tokens instead of max_tokens
        # O3/O4 models have strict parameter requirements
        payload = {
            "model": model,
            "messages": [
                {"role": "user", "content": "What is 2+2? Answer in one number only."}
            ],
            # temperature must be 1 (default) for O3/O4
            "max_completion_tokens": 50  # Changed from max_tokens
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                content = result.get('choices', [{}])[0].get('message', {}).get('content', 'No response')
                usage = result.get('usage', {})
                logger.info(f"✅ {model} WORKS!")
                logger.info(f"Response: {content}")
                logger.info(f"Usage: {json.dumps(usage, indent=2)}")
                
                # Check if it supports streaming
                logger.info(f"\nTesting {model} with streaming...")
                payload['stream'] = True
                stream_response = requests.post(url, headers=headers, json=payload, stream=True, timeout=30)
                if stream_response.status_code == 200:
                    logger.info(f"✅ {model} supports streaming!")
                else:
                    logger.info(f"❌ {model} streaming failed: {stream_response.status_code}")
                
            else:
                error = response.json()
                logger.error(f"❌ {model} failed: {json.dumps(error, indent=2)}")
                
        except Exception as e:
            logger.error(f"❌ {model} error: {str(e)}")

if __name__ == "__main__":
    test_o3_model()