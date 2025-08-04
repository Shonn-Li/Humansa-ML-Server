#!/usr/bin/env python3
"""
Test script for the complete form-based appointment booking flow.
Tests Pattern 2 orchestrator with form tools integration.
"""

import asyncio
import aiohttp
import json
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test server configuration
API_BASE_URL = "http://localhost:6001"
TEST_USER_ID = "test_user_form_10001"

async def test_form_creation():
    """Test creating appointment form from natural language."""
    logger.info("\n=== Testing Form Creation ===")
    
    test_queries = [
        "我想预约李明医生看内科，下周一上午9点",
        "帮我约张医生的号，我最近头疼",
        "预约儿科专家门诊，明天下午3点",
        "找王医生看皮肤科，症状是过敏起红疹"
    ]
    
    async with aiohttp.ClientSession() as session:
        for query in test_queries:
            logger.info(f"\nTesting query: {query}")
            
            payload = {
                "messages": [
                    {"role": "user", "content": query}
                ],
                "user_id": TEST_USER_ID,
                "debug": True,
                "stream": False
            }
            
            async with session.post(
                f"{API_BASE_URL}/v1-humansa/chat/completions",
                json=payload
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"Response: {result.get('choices', [{}])[0].get('message', {}).get('content', '')[:200]}...")
                    
                    # Check if form was created
                    content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
                    if 'form_id' in content or '预约信息' in content:
                        logger.info("✅ Form creation successful")
                    else:
                        logger.warning("⚠️ Form may not have been created")
                else:
                    logger.error(f"❌ Error: {response.status}")
                    error_text = await response.text()
                    logger.error(f"Error details: {error_text}")


async def test_form_modification():
    """Test modifying appointment form."""
    logger.info("\n=== Testing Form Modification ===")
    
    # First create a form
    async with aiohttp.ClientSession() as session:
        # Create initial form
        create_payload = {
            "messages": [
                {"role": "user", "content": "我想预约李明医生看内科，下周一上午9点"}
            ],
            "user_id": TEST_USER_ID,
            "debug": True,
            "stream": False
        }
        
        async with session.post(
            f"{API_BASE_URL}/v1-humansa/chat/completions",
            json=create_payload
        ) as response:
            if response.status != 200:
                logger.error("Failed to create initial form")
                return
            
            result = await response.json()
            initial_response = result.get('choices', [{}])[0].get('message', {}).get('content', '')
            logger.info(f"Initial form created: {initial_response[:200]}...")
        
        # Test modifications
        modifications = [
            "改成下周二下午3点",
            "换成张医生",
            "我的症状是头痛和发烧"
        ]
        
        for mod in modifications:
            logger.info(f"\nTesting modification: {mod}")
            
            mod_payload = {
                "messages": [
                    {"role": "user", "content": "我想预约李明医生看内科，下周一上午9点"},
                    {"role": "assistant", "content": initial_response},
                    {"role": "user", "content": mod}
                ],
                "user_id": TEST_USER_ID,
                "debug": True,
                "stream": False
            }
            
            async with session.post(
                f"{API_BASE_URL}/v1-humansa/chat/completions",
                json=mod_payload
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    mod_response = result.get('choices', [{}])[0].get('message', {}).get('content', '')
                    logger.info(f"Modification response: {mod_response[:200]}...")
                    
                    if '已更新' in mod_response or '修改' in mod_response:
                        logger.info("✅ Modification successful")
                    else:
                        logger.warning("⚠️ Modification may not have worked")
                else:
                    logger.error(f"❌ Modification error: {response.status}")


async def test_form_confirmation():
    """Test form confirmation flow."""
    logger.info("\n=== Testing Form Confirmation ===")
    
    async with aiohttp.ClientSession() as session:
        # Create and confirm a form
        conversation = [
            ("我想预约王医生看皮肤科，明天上午10点", None),
            ("确认", "确认预约"),
            ("取消", "取消预约")
        ]
        
        messages = []
        
        for user_input, expected_action in conversation:
            logger.info(f"\nUser: {user_input}")
            
            messages.append({"role": "user", "content": user_input})
            
            payload = {
                "messages": messages,
                "user_id": TEST_USER_ID,
                "debug": True,
                "stream": False
            }
            
            async with session.post(
                f"{API_BASE_URL}/v1-humansa/chat/completions",
                json=payload
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    assistant_response = result.get('choices', [{}])[0].get('message', {}).get('content', '')
                    messages.append({"role": "assistant", "content": assistant_response})
                    
                    logger.info(f"Assistant: {assistant_response[:200]}...")
                    
                    if expected_action:
                        if expected_action in assistant_response:
                            logger.info(f"✅ {expected_action} successful")
                        else:
                            logger.warning(f"⚠️ Expected '{expected_action}' not found")
                else:
                    logger.error(f"❌ Error: {response.status}")
                    break


async def test_streaming_form_flow():
    """Test form flow with streaming enabled."""
    logger.info("\n=== Testing Streaming Form Flow ===")
    
    async with aiohttp.ClientSession() as session:
        payload = {
            "messages": [
                {"role": "user", "content": "我想预约李医生看内科，有发烧的症状"}
            ],
            "user_id": TEST_USER_ID,
            "debug": True,
            "stream": True
        }
        
        async with session.post(
            f"{API_BASE_URL}/v1-humansa/chat/completions",
            json=payload
        ) as response:
            if response.status == 200:
                logger.info("Streaming response:")
                full_content = ""
                
                async for line in response.content:
                    line = line.decode('utf-8').strip()
                    if line.startswith('data: '):
                        data = line[6:]
                        if data == '[DONE]':
                            break
                        
                        try:
                            chunk = json.loads(data)
                            if 'choices' in chunk:
                                delta = chunk['choices'][0].get('delta', {})
                                content = delta.get('content', '')
                                if content:
                                    print(content, end='', flush=True)
                                    full_content += content
                        except json.JSONDecodeError:
                            continue
                
                print()  # New line after streaming
                
                if 'form_id' in full_content or '预约信息' in full_content:
                    logger.info("\n✅ Streaming form creation successful")
                else:
                    logger.warning("\n⚠️ Form may not have been created in streaming mode")
            else:
                logger.error(f"❌ Streaming error: {response.status}")


async def test_complex_conversation():
    """Test a complete appointment booking conversation."""
    logger.info("\n=== Testing Complete Appointment Conversation ===")
    
    conversation_flow = [
        "你好，我想看医生",
        "我最近总是头疼，还有点发烧",
        "有内科的专家吗？",
        "那就李明医生吧，什么时候有号？",
        "明天上午可以吗？",
        "好的，9点钟吧",
        "我叫张三",
        "确认预约"
    ]
    
    async with aiohttp.ClientSession() as session:
        messages = []
        
        for user_input in conversation_flow:
            logger.info(f"\n👤 User: {user_input}")
            messages.append({"role": "user", "content": user_input})
            
            payload = {
                "messages": messages,
                "user_id": TEST_USER_ID,
                "debug": False,  # Disable debug for cleaner output
                "stream": False
            }
            
            async with session.post(
                f"{API_BASE_URL}/v1-humansa/chat/completions",
                json=payload
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    assistant_response = result.get('choices', [{}])[0].get('message', {}).get('content', '')
                    messages.append({"role": "assistant", "content": assistant_response})
                    
                    logger.info(f"🤖 Assistant: {assistant_response}")
                else:
                    logger.error(f"❌ Error: {response.status}")
                    break
            
            # Small delay between messages
            await asyncio.sleep(0.5)


async def main():
    """Run all tests."""
    logger.info("Starting Form-Based Appointment Flow Tests")
    logger.info("=" * 50)
    
    # Make sure test server is running
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_BASE_URL}/health") as response:
                if response.status != 200:
                    logger.error(f"Test server not responding at {API_BASE_URL}")
                    return
    except Exception as e:
        logger.error(f"Cannot connect to test server at {API_BASE_URL}: {e}")
        logger.error("Please run: ./run_humansa_test_environment_v2.sh")
        return
    
    # Run tests
    await test_form_creation()
    await test_form_modification()
    await test_form_confirmation()
    await test_streaming_form_flow()
    await test_complex_conversation()
    
    logger.info("\n" + "=" * 50)
    logger.info("All tests completed!")


if __name__ == "__main__":
    asyncio.run(main())