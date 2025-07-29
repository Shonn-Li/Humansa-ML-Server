#!/usr/bin/env python3
"""
Test script for the new conversation API
Tests conversation creation, message addition, and context management
"""

import asyncio
import aiohttp
import json
import time
from typing import Dict, Any, List

# Test configuration
BASE_URL = "http://localhost:5454"
TEST_USER_ID = "test_user_123"

# Test conversations
TEST_CONVERSATIONS = [
    # Simple conversation
    {
        "messages": [
            "你好，我最近总是头疼，已经持续一周了",
            "疼痛主要在前额，早上起床时最严重",
            "我对阿司匹林过敏，不能吃",
            "请帮我推荐一下该看哪个科室"
        ]
    },
    # Multi-turn appointment booking
    {
        "messages": [
            "我想预约神经内科的医生",
            "最好是本周末，上午的时间",
            "张医生的号还有吗？",
            "好的，帮我预约周六上午9点的"
        ]
    },
    # Long conversation to test compression
    {
        "messages": [
            "我妈妈今年65岁，最近总是失眠",
            "她有高血压，一直在吃降压药",
            "具体是氨氯地平，每天5mg",
            "失眠已经有两个月了，入睡困难",
            "而且半夜容易醒，醒了就睡不着",
            "白天精神不好，总是打瞌睡",
            "她还有糖尿病，血糖控制还可以",
            "我担心是不是药物副作用",
            "或者需要看看其他科室",
            "她之前看过中医，效果不明显",
            "现在想试试西医的治疗方案",
            "请问应该挂什么科室的号？"
        ]
    }
]


async def create_conversation(session: aiohttp.ClientSession, first_message: str) -> Dict[str, Any]:
    """Create a new conversation"""
    url = f"{BASE_URL}/v2/humansa/conversations"
    payload = {
        "user_id": TEST_USER_ID,
        "message": {
            "role": "user",
            "content": first_message
        }
    }
    
    async with session.post(url, json=payload) as response:
        result = await response.json()
        print(f"\n✅ Created conversation: {result.get('conversation_id', 'ERROR')}")
        print(f"   First response: {result.get('message', {}).get('content', 'ERROR')[:100]}...")
        return result


async def add_message(session: aiohttp.ClientSession, conversation_id: str, message: str) -> Dict[str, Any]:
    """Add a message to existing conversation"""
    url = f"{BASE_URL}/v2/humansa/conversations/{conversation_id}/messages"
    payload = {
        "message": {
            "role": "user",
            "content": message
        }
    }
    
    async with session.post(url, json=payload) as response:
        result = await response.json()
        print(f"   Response: {result.get('message', {}).get('content', 'ERROR')[:100]}...")
        return result


async def get_conversation(session: aiohttp.ClientSession, conversation_id: str) -> Dict[str, Any]:
    """Get conversation details"""
    url = f"{BASE_URL}/v2/humansa/conversations/{conversation_id}"
    
    async with session.get(url) as response:
        result = await response.json()
        print(f"\n📊 Conversation details:")
        print(f"   Turn count: {result.get('turn_count', 0)}")
        print(f"   Messages: {len(result.get('messages', []))}")
        if result.get('summary'):
            print(f"   Summary: {result['summary'][:100]}...")
        return result


async def test_streaming(session: aiohttp.ClientSession, conversation_id: str, message: str):
    """Test streaming endpoint"""
    url = f"{BASE_URL}/v2/humansa/conversations/{conversation_id}/stream"
    payload = {
        "message": {
            "role": "user",
            "content": message
        }
    }
    
    print(f"\n🌊 Testing streaming response...")
    async with session.post(url, json=payload) as response:
        full_response = ""
        async for line in response.content:
            line = line.decode('utf-8').strip()
            if line.startswith('data: '):
                data = line[6:]
                if data == '[DONE]':
                    break
                try:
                    chunk = json.loads(data)
                    if 'choices' in chunk and chunk['choices']:
                        delta = chunk['choices'][0].get('delta', {})
                        if 'content' in delta:
                            full_response += delta['content']
                            print(delta['content'], end='', flush=True)
                except json.JSONDecodeError:
                    pass
        print(f"\n   Streaming complete. Total length: {len(full_response)}")


async def test_compression(session: aiohttp.ClientSession, conversation_id: str):
    """Test manual compression endpoint"""
    url = f"{BASE_URL}/v2/humansa/conversations/{conversation_id}/compress"
    
    print(f"\n🗜️  Testing compression...")
    async with session.post(url) as response:
        result = await response.json()
        if 'summary' in result:
            print(f"   Summary: {result['summary'][:150]}...")
            print(f"   Compression ratio: {result.get('compression_ratio', 0):.2%}")
            if result.get('key_information'):
                print(f"   Key info extracted: {list(result['key_information'].keys())}")
        else:
            print(f"   Result: {result.get('message', 'ERROR')}")


async def run_tests():
    """Run all conversation API tests"""
    print("🧪 Testing HUMANSA V2 Conversation API")
    print("=" * 50)
    
    async with aiohttp.ClientSession() as session:
        # Test 1: Simple conversation
        print("\n1️⃣  Test: Simple Conversation")
        conv1 = await create_conversation(session, TEST_CONVERSATIONS[0]["messages"][0])
        conv1_id = conv1.get("conversation_id")
        
        if conv1_id:
            # Add follow-up messages
            for msg in TEST_CONVERSATIONS[0]["messages"][1:]:
                await asyncio.sleep(1)  # Small delay between messages
                await add_message(session, conv1_id, msg)
            
            # Get conversation details
            await get_conversation(session, conv1_id)
        
        # Test 2: Multi-turn appointment
        print("\n2️⃣  Test: Multi-turn Appointment Booking")
        conv2 = await create_conversation(session, TEST_CONVERSATIONS[1]["messages"][0])
        conv2_id = conv2.get("conversation_id")
        
        if conv2_id:
            for msg in TEST_CONVERSATIONS[1]["messages"][1:]:
                await asyncio.sleep(1)
                await add_message(session, conv2_id, msg)
            
            # Test streaming on last message
            await test_streaming(session, conv2_id, "请确认一下预约信息")
        
        # Test 3: Long conversation with compression
        print("\n3️⃣  Test: Long Conversation with Compression")
        conv3 = await create_conversation(session, TEST_CONVERSATIONS[2]["messages"][0])
        conv3_id = conv3.get("conversation_id")
        
        if conv3_id:
            # Add all messages
            for i, msg in enumerate(TEST_CONVERSATIONS[2]["messages"][1:], 1):
                print(f"\n   Adding message {i+1}/12...")
                await add_message(session, conv3_id, msg)
                await asyncio.sleep(0.5)
            
            # Get conversation before compression
            print("\n   Before compression:")
            await get_conversation(session, conv3_id)
            
            # Test compression
            await test_compression(session, conv3_id)
            
            # Get conversation after compression
            print("\n   After compression:")
            await get_conversation(session, conv3_id)
            
            # Add one more message to see compressed context in action
            print("\n   Testing with compressed context:")
            await add_message(session, conv3_id, "她还需要注意什么吗？")
        
        # Test 4: Error handling
        print("\n4️⃣  Test: Error Handling")
        
        # Try to add message to non-existent conversation
        print("\n   Testing non-existent conversation...")
        try:
            await add_message(session, "conv_fake_123", "Hello")
        except Exception as e:
            print(f"   Expected error: {e}")
        
        # Test cleanup
        print("\n5️⃣  Test: Cleanup old conversations")
        url = f"{BASE_URL}/v2/humansa/conversations/cleanup"
        async with session.post(url, json={"max_age_hours": 0.001}) as response:
            result = await response.json()
            print(f"   Cleanup result: {result}")
    
    print("\n✅ All tests completed!")


if __name__ == "__main__":
    asyncio.run(run_tests())