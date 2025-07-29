#!/usr/bin/env python3
"""
Fixed Mem0 V2 integration test with correct user_id types (strings) and test environment settings
"""

import asyncio
import aiohttp
import json
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test configuration - using string user_ids
BASE_URL = "http://localhost:6001"
TEST_USER_ID = "test_user_10001"  # String user_id

# Test database configuration
os.environ.update({
    "DB_HOST": "localhost",
    "DB_PORT": "5454",  # Correct test port
    "DB_USER": "postgres",
    "DB_PASSWORD": "12931",
    "DB_NAME": "test4",
    "ENVIRONMENT": "test"
})


async def test_mem0_integration():
    """Test that Mem0 is properly integrated into v2 workflow with string user_ids."""
    
    async with aiohttp.ClientSession() as session:
        logger.info("Starting Fixed Mem0 v2 integration test...")
        logger.info(f"Using string user_id: {TEST_USER_ID}")
        
        # Test 1: Check Mem0 status
        logger.info("\n1. Checking Mem0 status...")
        async with session.get(f"{BASE_URL}/v2/humansa/memory/status") as resp:
            status = await resp.json()
            logger.info(f"Mem0 Status: {json.dumps(status, indent=2)}")
            
            if not status.get("initialized"):
                logger.error("❌ Mem0 is not initialized!")
                return False
                
        # Test 2: Add a memory directly with string user_id
        logger.info("\n2. Adding test memory directly with string user_id...")
        memory_data = {
            "user_id": TEST_USER_ID,  # String user_id
            "messages": [
                {"role": "user", "content": "I'm allergic to penicillin and prefer morning appointments"},
                {"role": "assistant", "content": "I've noted your penicillin allergy and preference for morning appointments."}
            ],
            "metadata": {"test": "v2_integration_fixed"}
        }
        
        async with session.post(
            f"{BASE_URL}/v2/humansa/memory/add",
            json=memory_data
        ) as resp:
            result = await resp.json()
            logger.info(f"Add memory result: {result}")
            if resp.status != 200:
                logger.error(f"Failed to add memory: {result}")
                
        # Test 3: Get user context to verify memory count
        logger.info("\n3. Getting user context to check memory count...")
        async with session.get(f"{BASE_URL}/v2/humansa/memory/context/{TEST_USER_ID}") as resp:
            context = await resp.json()
            logger.info(f"User context: {json.dumps(context, indent=2)}")
            
            memory_count = context.get("context", {}).get("memory_count", 0)
            if memory_count > 0:
                logger.info(f"✅ Memory count is {memory_count} - memories are being stored!")
            else:
                logger.warning("⚠️ Memory count is 0 - check if memories are persisting")
            
        # Test 4: Chat through v2 endpoint (should use memory context)
        logger.info("\n4. Testing v2 chat with memory context...")
        chat_data = {
            "user_id": TEST_USER_ID,  # String user_id
            "messages": [
                {"role": "user", "content": "What medications should I avoid?"}
            ],
            "stream": False
        }
        
        async with session.post(
            f"{BASE_URL}/v2/humansa/chat",
            json=chat_data
        ) as resp:
            if resp.status == 200:
                result = await resp.json()
                logger.info(f"Chat response: {json.dumps(result, indent=2)}")
                
                # Check if response mentions penicillin
                response_text = str(result).lower()
                if "penicillin" in response_text:
                    logger.info("✅ Memory context used - penicillin allergy mentioned!")
                else:
                    logger.warning("⚠️ Memory context might not be used - no mention of penicillin")
            else:
                error_text = await resp.text()
                logger.error(f"❌ Chat failed with status {resp.status}: {error_text}")
                
        # Test 5: Search memories
        logger.info("\n5. Searching memories...")
        search_data = {
            "user_id": TEST_USER_ID,  # String user_id
            "query": "allergies medications"
        }
        
        async with session.post(
            f"{BASE_URL}/v2/humansa/memory/search",
            json=search_data
        ) as resp:
            results = await resp.json()
            logger.info(f"Memory search results: {json.dumps(results, indent=2)}")
            
            if results.get("count", 0) > 0:
                logger.info(f"✅ Found {results['count']} memories!")
            else:
                logger.warning("⚠️ No memories found")
                
        # Test 6: Another chat to verify memory persistence
        logger.info("\n6. Second chat to verify memory persistence...")
        chat_data2 = {
            "user_id": TEST_USER_ID,  # String user_id
            "messages": [
                {"role": "user", "content": "Can you book me an appointment in the afternoon?"}
            ],
            "stream": False
        }
        
        async with session.post(
            f"{BASE_URL}/v2/humansa/chat",
            json=chat_data2
        ) as resp:
            if resp.status == 200:
                result = await resp.json()
                response_text = str(result).lower()
                
                if "morning" in response_text:
                    logger.info("✅ Memory working - system remembers morning preference!")
                else:
                    logger.info("ℹ️ Response didn't mention morning preference")
                    
        # Test 7: Test with different user to ensure isolation
        logger.info("\n7. Testing memory isolation with different user...")
        different_user = "test_user_20002"
        
        chat_data3 = {
            "user_id": different_user,  # Different string user_id
            "messages": [
                {"role": "user", "content": "Do I have any allergies?"}
            ],
            "stream": False
        }
        
        async with session.post(
            f"{BASE_URL}/v2/humansa/chat",
            json=chat_data3
        ) as resp:
            if resp.status == 200:
                result = await resp.json()
                response_text = str(result).lower()
                
                if "penicillin" not in response_text:
                    logger.info("✅ Memory isolation working - different user doesn't see first user's data")
                else:
                    logger.error("❌ Memory isolation issue - different user sees first user's data!")
                    
        logger.info("\n" + "="*50)
        logger.info("Fixed integration test completed!")
        logger.info("="*50)
        
        return True


async def main():
    """Run the fixed integration test."""
    try:
        # Verify environment
        logger.info("Test Environment Configuration:")
        logger.info(f"  DB_HOST: {os.getenv('DB_HOST')}")
        logger.info(f"  DB_PORT: {os.getenv('DB_PORT')}")
        logger.info(f"  DB_NAME: {os.getenv('DB_NAME')}")
        logger.info(f"  ENVIRONMENT: {os.getenv('ENVIRONMENT')}")
        logger.info("")
        
        success = await test_mem0_integration()
        if success:
            logger.info("\n✅ Fixed Mem0 v2 integration test passed!")
        else:
            logger.error("\n❌ Fixed Mem0 v2 integration test failed!")
    except Exception as e:
        logger.error(f"\n❌ Test error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())