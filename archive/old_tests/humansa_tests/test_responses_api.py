#!/usr/bin/env python3
"""
Test script for the new OpenAI-style Responses API
Tests response creation, continuation, forking, and retrieval
"""

import asyncio
import aiohttp
import json
import time
from typing import Dict, Any, List, Optional

# Test configuration
BASE_URL = "http://localhost:5454"
TEST_USER_ID = "test_user_456"

# Test scenarios
TEST_SCENARIOS = [
    # Simple linear conversation
    {
        "name": "Linear Medical Consultation",
        "messages": [
            "你好，我最近总是失眠",
            "失眠大概有多久了？每天几点睡觉？",
            "已经两个月了，每天12点睡但是要到2-3点才能睡着",
            "白天有什么症状吗？比如疲劳、注意力不集中？",
            "是的，白天很困，工作效率很低"
        ]
    },
    # Conversation with forking
    {
        "name": "Forked Conversation - Different Symptoms",
        "messages": [
            "我想咨询一下头疼的问题",
            "头疼的位置在哪里？持续多久了？",
            # Fork point - two different responses
            [
                "主要是前额痛，已经一周了",  # Branch A
                "是偏头痛，右侧太阳穴附近"    # Branch B
            ]
        ]
    },
    # Long conversation for compression testing
    {
        "name": "Long Conversation with Compression",
        "messages": [
            "我妈妈65岁，有高血压病史",
            "她最近血压控制怎么样？在吃什么药？",
            "在吃氨氯地平，每天5mg，血压基本稳定",
            "除了高血压还有其他慢性病吗？",
            "有轻度糖尿病，餐后血糖偶尔偏高",
            "糖尿病用药情况如何？",
            "口服二甲双胍，每天两次",
            "最近有什么不舒服的症状吗？",
            "最近总是头晕，尤其是站起来的时候",
            "这种头晕可能是体位性低血压，建议测量不同体位的血压",
            "好的，我会带她去检查。她还需要注意什么？",
            "注意规律服药，避免突然改变体位，适当补充水分"
        ]
    }
]


async def create_initial_response(session: aiohttp.ClientSession, input_text: str) -> Dict[str, Any]:
    """Create an initial response"""
    url = f"{BASE_URL}/v2/humansa/responses/create"
    payload = {
        "model": "gpt-4-turbo",
        "input": input_text,
        "user_id": TEST_USER_ID,
        "metadata": {
            "test_scenario": "initial"
        }
    }
    
    print(f"\n🔵 Creating initial response: '{input_text[:50]}...'")
    async with session.post(url, json=payload) as response:
        result = await response.json()
        
        if response.status == 200:
            print(f"✅ Response ID: {result.get('id', 'ERROR')}")
            output_text = extract_text_from_output(result.get('output', []))
            print(f"💬 AI: {output_text[:150]}...")
            return result
        else:
            print(f"❌ Error: {result}")
            return None


async def continue_response(
    session: aiohttp.ClientSession,
    previous_response_id: str,
    input_text: str
) -> Dict[str, Any]:
    """Continue from a previous response"""
    url = f"{BASE_URL}/v2/humansa/responses/create"
    payload = {
        "model": "gpt-4-turbo",
        "input": input_text,
        "previous_response_id": previous_response_id,
        "metadata": {
            "test_scenario": "continuation"
        }
    }
    
    print(f"\n🔄 Continuing from {previous_response_id}: '{input_text[:50]}...'")
    async with session.post(url, json=payload) as response:
        result = await response.json()
        
        if response.status == 200:
            print(f"✅ Response ID: {result.get('id', 'ERROR')}")
            output_text = extract_text_from_output(result.get('output', []))
            print(f"💬 AI: {output_text[:150]}...")
            return result
        else:
            print(f"❌ Error: {result}")
            return None


async def retrieve_response(session: aiohttp.ClientSession, response_id: str) -> Dict[str, Any]:
    """Retrieve a response with full history"""
    url = f"{BASE_URL}/v2/humansa/responses/{response_id}"
    
    print(f"\n📥 Retrieving response: {response_id}")
    async with session.get(url) as response:
        result = await response.json()
        
        if response.status == 200:
            print(f"✅ Retrieved successfully")
            print(f"   Conversation ID: {result.get('conversation_id')}")
            print(f"   Turn count: {result.get('conversation_state', {}).get('turn_count', 0)}")
            if result.get('conversation_state', {}).get('summary'):
                print(f"   Summary: {result['conversation_state']['summary'][:100]}...")
            return result
        else:
            print(f"❌ Error: {result}")
            return None


async def test_streaming(
    session: aiohttp.ClientSession,
    previous_response_id: str,
    input_text: str
):
    """Test streaming continuation"""
    url = f"{BASE_URL}/v2/humansa/responses/{previous_response_id}/stream"
    payload = {
        "input": input_text,
        "model": "gpt-4-turbo",
        "metadata": {
            "test_scenario": "streaming"
        }
    }
    
    print(f"\n🌊 Testing streaming from {previous_response_id}: '{input_text[:50]}...'")
    async with session.post(url, json=payload) as response:
        if response.status != 200:
            print(f"❌ Error: {await response.text()}")
            return
        
        full_response = ""
        response_id = None
        
        async for line in response.content:
            line = line.decode('utf-8').strip()
            if line.startswith('data: '):
                data = line[6:]
                if data == '[DONE]':
                    break
                
                try:
                    chunk = json.loads(data)
                    
                    # Check for response metadata
                    if 'response_id' in chunk:
                        response_id = chunk['response_id']
                        print(f"\n✅ Response ID: {response_id}")
                        continue
                    
                    # Extract content
                    if 'choices' in chunk and chunk['choices']:
                        delta = chunk['choices'][0].get('delta', {})
                        if 'content' in delta:
                            content = delta['content']
                            full_response += content
                            print(content, end='', flush=True)
                except json.JSONDecodeError:
                    pass
        
        print(f"\n   Streaming complete. Total length: {len(full_response)}")
        return response_id


async def get_conversation_tree(session: aiohttp.ClientSession, conversation_id: str):
    """Get conversation tree with all branches"""
    url = f"{BASE_URL}/v2/humansa/responses/conversations/{conversation_id}/tree"
    
    print(f"\n🌳 Getting conversation tree for: {conversation_id}")
    async with session.get(url) as response:
        result = await response.json()
        
        if response.status == 200:
            stats = result.get('statistics', {})
            print(f"✅ Conversation statistics:")
            print(f"   Total responses: {stats.get('total_responses', 0)}")
            print(f"   Fork count: {stats.get('fork_count', 0)}")
            print(f"   Total tokens: {stats.get('total_tokens', 0)}")
            print(f"   Tools used: {stats.get('tool_usage', {})}")
            
            # Print tree structure
            tree = result.get('tree', {})
            if tree.get('roots'):
                print("\n   Tree structure:")
                print_tree_node(tree['roots'][0], indent=2)
        else:
            print(f"❌ Error: {result}")


def print_tree_node(node: Dict[str, Any], indent: int = 0):
    """Print a tree node recursively"""
    prefix = "  " * indent + "└─ "
    print(f"{prefix}User: {node['input'][:50]}...")
    print(f"{'  ' * (indent + 1)}AI: {node['output'][:50]}...")
    
    for child in node.get('children', []):
        print_tree_node(child, indent + 1)


def extract_text_from_output(output: List[Dict[str, Any]]) -> str:
    """Extract text from output array"""
    text_parts = []
    for item in output:
        if item.get("type") == "text":
            text_parts.append(item.get("text", ""))
    return " ".join(text_parts)


async def run_linear_conversation(session: aiohttp.ClientSession, messages: List[str]):
    """Run a linear conversation"""
    response_ids = []
    current_response = None
    
    for i, message in enumerate(messages):
        if i == 0:
            # Initial response
            current_response = await create_initial_response(session, message)
        else:
            # Continue from previous
            if current_response:
                current_response = await continue_response(
                    session,
                    current_response['id'],
                    message
                )
        
        if current_response:
            response_ids.append(current_response['id'])
        
        await asyncio.sleep(0.5)  # Small delay between messages
    
    return response_ids


async def run_forked_conversation(session: aiohttp.ClientSession, scenario: Dict[str, Any]):
    """Run a conversation with forking"""
    messages = scenario['messages']
    
    # Create initial response
    response1 = await create_initial_response(session, messages[0])
    if not response1:
        return
    
    # Continue to fork point
    response2 = await continue_response(session, response1['id'], messages[1])
    if not response2:
        return
    
    # Create forks
    fork_responses = []
    for fork_message in messages[2]:
        print(f"\n🔀 Creating fork: '{fork_message}'")
        fork_response = await continue_response(
            session,
            response2['id'],  # Same parent
            fork_message
        )
        if fork_response:
            fork_responses.append(fork_response)
        await asyncio.sleep(0.5)
    
    # Get conversation tree to show forks
    if response1:
        await get_conversation_tree(session, response1['conversation_id'])
    
    return fork_responses


async def run_tests():
    """Run all Responses API tests"""
    print("🧪 Testing HUMANSA V2 Responses API (OpenAI-style)")
    print("=" * 60)
    
    async with aiohttp.ClientSession() as session:
        # Test 1: Linear conversation
        print("\n1️⃣  Test: Linear Medical Consultation")
        scenario1 = TEST_SCENARIOS[0]
        response_ids = await run_linear_conversation(session, scenario1['messages'])
        
        # Retrieve the last response with full history
        if response_ids:
            await retrieve_response(session, response_ids[-1])
        
        # Test 2: Forked conversation
        print("\n\n2️⃣  Test: Forked Conversation")
        scenario2 = TEST_SCENARIOS[1]
        fork_responses = await run_forked_conversation(session, scenario2)
        
        # Test 3: Long conversation with compression
        print("\n\n3️⃣  Test: Long Conversation with Compression")
        scenario3 = TEST_SCENARIOS[2]
        long_response_ids = await run_linear_conversation(session, scenario3['messages'])
        
        if long_response_ids:
            # Check the final response
            final_response = await retrieve_response(session, long_response_ids[-1])
            
            # Test streaming continuation
            if final_response:
                await test_streaming(
                    session,
                    long_response_ids[-1],
                    "她还需要定期复查哪些项目？"
                )
        
        # Test 4: Error handling
        print("\n\n4️⃣  Test: Error Handling")
        
        # Try to continue from non-existent response
        print("\n   Testing non-existent response continuation...")
        await continue_response(session, "resp_fake_123", "Hello")
        
        # Test cleanup
        print("\n\n5️⃣  Test: Cleanup old responses")
        url = f"{BASE_URL}/v2/humansa/responses/cleanup"
        async with session.post(url, json={"max_age_hours": 0.001}) as response:
            result = await response.json()
            print(f"   Cleanup result: {result}")
    
    print("\n\n✅ All tests completed!")


if __name__ == "__main__":
    asyncio.run(run_tests())