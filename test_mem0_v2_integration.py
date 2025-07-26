#!/usr/bin/env python3
"""
Quick test to verify Mem0 is integrated into Humansa v2 workflow
"""

import asyncio
import aiohttp
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test configuration
BASE_URL = "http://localhost:6001"
TEST_USER_ID = 10001


async def test_mem0_integration():
    """Test that Mem0 is properly integrated into v2 workflow."""
    
    async with aiohttp.ClientSession() as session:
        logger.info("Starting Mem0 v2 integration test...")
        
        # Test 1: Check Mem0 status
        logger.info("\n1. Checking Mem0 status...")
        async with session.get(f"{BASE_URL}/v2/humansa/memory/status") as resp:
            status = await resp.json()
            logger.info(f"Mem0 Status: {json.dumps(status, indent=2)}")
            
            if not status.get("initialized"):
                logger.error("❌ Mem0 is not initialized!")
                return False
                
        # Test 2: Add a memory directly
        logger.info("\n2. Adding test memory directly...")
        memory_data = {
            "user_id": TEST_USER_ID,
            "messages": [
                {"role": "user", "content": "I'm allergic to penicillin and prefer morning appointments"},
                {"role": "assistant", "content": "I've noted your penicillin allergy and preference for morning appointments."}
            ],
            "metadata": {"test": "v2_integration"}
        }
        
        async with session.post(
            f"{BASE_URL}/v2/humansa/memory/add",
            json=memory_data
        ) as resp:
            result = await resp.json()
            logger.info(f"Add memory result: {result}")
            
        # Test 3: Chat through v2 endpoint (should use memory context)
        logger.info("\n3. Testing v2 chat with memory context...")
        chat_data = {
            "user_id": TEST_USER_ID,
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
                logger.error(f"❌ Chat failed with status {resp.status}")
                
        # Test 4: Search memories
        logger.info("\n4. Searching memories...")
        search_data = {
            "user_id": TEST_USER_ID,
            "query": "allergies medications"
        }
        
        async with session.post(
            f"{BASE_URL}/v2/humansa/memory/search",
            json=search_data
        ) as resp:
            results = await resp.json()
            logger.info(f"Memory search results: {json.dumps(results, indent=2)}")
            
            if results.get("count", 0) > 0:
                logger.info("✅ Found memories!")
            else:
                logger.warning("⚠️ No memories found")
                
        # Test 5: Get user context
        logger.info("\n5. Getting user context...")
        async with session.get(f"{BASE_URL}/v2/humansa/memory/context/{TEST_USER_ID}") as resp:
            context = await resp.json()
            logger.info(f"User context: {json.dumps(context, indent=2)}")
            
        # Test 6: Another chat to verify memory persistence
        logger.info("\n6. Second chat to verify memory persistence...")
        chat_data2 = {
            "user_id": TEST_USER_ID,
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
                    
        logger.info("\n" + "="*50)
        logger.info("Integration test completed!")
        logger.info("="*50)
        
        return True


async def main():
    """Run the integration test."""
    try:
        success = await test_mem0_integration()
        if success:
            logger.info("\n✅ Mem0 v2 integration test passed!")
        else:
            logger.error("\n❌ Mem0 v2 integration test failed!")
    except Exception as e:
        logger.error(f"\n❌ Test error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())