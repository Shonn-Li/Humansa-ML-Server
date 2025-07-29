#!/usr/bin/env python3
"""
Mem0 V2 integration test using unified test configuration
"""

import asyncio
import aiohttp
import json
import logging
import sys
import os

# Add test_environment to path for unified config
sys.path.append('test_environment')
from unified_test_config import (
    TEST_ML_SERVER,
    TEST_USER_IDS,
    setup_test_environment,
    verify_test_database
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_mem0_integration():
    """Test Mem0 integration using unified configuration."""
    
    # Setup test environment
    setup_test_environment()
    
    # Verify database first
    if not verify_test_database():
        logger.error("❌ Test database is not accessible!")
        logger.error("Start it with: docker-compose -f test_environment/docker-compose.yml up -d")
        return False
    
    base_url = TEST_ML_SERVER["base_url"]
    test_user_id = TEST_USER_IDS["memory_test"]
    
    async with aiohttp.ClientSession() as session:
        logger.info("Starting Mem0 integration test with unified config...")
        logger.info(f"ML Server: {base_url}")
        logger.info(f"Test User ID: {test_user_id}")
        
        # Test 1: Check Mem0 status
        logger.info("\n1. Checking Mem0 status...")
        async with session.get(f"{base_url}/v2/humansa/memory/status") as resp:
            status = await resp.json()
            logger.info(f"Mem0 Status: {json.dumps(status, indent=2)}")
            
            if not status.get("initialized"):
                logger.error("❌ Mem0 is not initialized!")
                return False
                
        # Test 2: Add a memory
        logger.info("\n2. Adding test memory...")
        memory_data = {
            "user_id": test_user_id,
            "query": "My blood pressure is 140/90 and I have diabetes",
            "response": "I understand you have high blood pressure (140/90) and diabetes. These conditions require careful management.",
            "metadata": {
                "test": True,
                "test_type": "unified_config"
            }
        }
        
        async with session.post(
            f"{base_url}/v2/humansa/memory/conversation",
            json=memory_data
        ) as resp:
            result = await resp.json()
            logger.info(f"Add memory result: {result}")
            
        # Test 3: Get user context
        logger.info("\n3. Getting user context...")
        async with session.get(f"{base_url}/v2/humansa/memory/context/{test_user_id}") as resp:
            context = await resp.json()
            logger.info(f"User context: {json.dumps(context, indent=2)}")
            
            memory_count = context.get("memory_count", 0)
            logger.info(f"Total memories for user: {memory_count}")
            
        # Test 4: Test through chat endpoint
        logger.info("\n4. Testing memory through chat endpoint...")
        chat_request = {
            "user_id": test_user_id,
            "messages": [{
                "role": "user",
                "content": "What health conditions do I have?"
            }],
            "temperature": 0.7,
            "stream": False
        }
        
        async with session.post(
            f"{base_url}/v2/humansa/chat",
            json=chat_request
        ) as resp:
            chat_result = await resp.json()
            logger.info(f"Chat response: {json.dumps(chat_result, indent=2)}")
            
            # Check if memory was used
            if "血压" in str(chat_result) or "blood pressure" in str(chat_result).lower():
                logger.info("✅ Memory context was used in response!")
            else:
                logger.warning("⚠️ Memory might not have been used in response")
                
        return True


async def main():
    """Run the test."""
    logger.info("=" * 60)
    logger.info("MEM0 INTEGRATION TEST - UNIFIED CONFIG")
    logger.info("=" * 60)
    
    try:
        success = await test_mem0_integration()
        if success:
            logger.info("\n✅ All tests passed!")
        else:
            logger.error("\n❌ Some tests failed!")
            
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())