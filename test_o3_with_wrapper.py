#!/usr/bin/env python3
"""
Test O3 model with the new wrapper
"""

import os
import sys
import asyncio
import logging
from dotenv import load_dotenv

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from chat.provider.o3_model_wrapper import create_azure_llm_with_o3_support
from llama_index.core.base.llms.types import ChatMessage

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_o3_wrapper():
    """Test O3 model with the wrapper"""
    load_dotenv()
    
    models_to_test = ["o3", "o4-mini", "gpt-4.1-nano"]
    
    for model in models_to_test:
        logger.info(f"\n{'='*60}")
        logger.info(f"Testing {model} with wrapper")
        logger.info(f"{'='*60}")
        
        try:
            # Create LLM instance with wrapper
            llm = create_azure_llm_with_o3_support(
                endpoint=os.getenv("AZURE_INFERENCE_ENDPOINT"),
                credential=os.getenv("AZURE_INFERENCE_CREDENTIAL"),
                model_name=model,
                temperature=0.7,  # Will be ignored for O3/O4
                max_tokens=50     # Will be converted to max_completion_tokens for O3/O4
            )
            
            # Test basic completion
            messages = [
                ChatMessage(role="user", content="What is 2+2? Answer in one number only.")
            ]
            
            logger.info("Testing chat completion...")
            response = await llm.achat(messages)
            logger.info(f"✅ Response: {response.message.content}")
            
            # Test streaming
            logger.info("\nTesting streaming...")
            stream_content = ""
            async for chunk in llm.astream_chat(messages):
                if chunk.delta:
                    stream_content += chunk.delta
            logger.info(f"✅ Streamed response: {stream_content}")
            
            # Test with explicit max_tokens parameter
            logger.info("\nTesting with explicit max_tokens...")
            response2 = await llm.achat(messages, max_tokens=20)
            logger.info(f"✅ Response with max_tokens: {response2.message.content}")
            
        except Exception as e:
            logger.error(f"❌ Failed: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_o3_wrapper())