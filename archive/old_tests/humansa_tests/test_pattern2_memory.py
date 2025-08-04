#!/usr/bin/env python3
"""
Test Pattern 2 orchestrator with memory tools
"""

import asyncio
import json
import aiohttp
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_URL = "http://localhost:6001/v2/humansa/responses/create"
API_HEADERS = {"Content-Type": "application/json"}

# Test cases for memory functionality
test_cases = [
    {
        "name": "Store allergy information",
        "input": "我对青霉素过敏，请记住这个信息",
        "expected_tools": ["store_user_info"],
        "user_id": "test_memory_user_001"
    },
    {
        "name": "Store medication information",
        "input": "我每天吃降压药美托洛尔，早晚各一次",
        "expected_tools": ["store_user_info"],
        "user_id": "test_memory_user_001"
    },
    {
        "name": "Recall allergy before recommending",
        "input": "我感冒了，推荐一些药物",
        "expected_tools": ["recall_user_info", "medication_info"],
        "user_id": "test_memory_user_001"
    },
    {
        "name": "Store and use location for appointment",
        "input": "我在北京朝阳区，帮我找个耳鼻喉科医生",
        "expected_tools": ["store_user_info", "book_appointment"],
        "user_id": "test_memory_user_002"
    },
    {
        "name": "Recall all user information",
        "input": "我的信息有哪些？",
        "expected_tools": ["recall_user_info"],
        "user_id": "test_memory_user_001"
    }
]

async def test_pattern2_memory():
    """Test Pattern 2 with memory tools"""
    
    async with aiohttp.ClientSession() as session:
        for i, test_case in enumerate(test_cases):
            print(f"\n{'='*60}")
            print(f"Test {i+1}: {test_case['name']}")
            print(f"User: {test_case['user_id']}")
            print(f"Input: {test_case['input']}")
            print(f"Expected tools: {test_case['expected_tools']}")
            print(f"{'='*60}")
            
            # Create request
            request_data = {
                "model": "gpt-4-turbo",
                "input": test_case["input"],
                "user_id": test_case["user_id"],
                "metadata": {
                    "test_case": test_case["name"],
                    "use_pattern2": True
                }
            }
            
            try:
                # Send request
                async with session.post(API_URL, headers=API_HEADERS, json=request_data) as response:
                    result = await response.json()
                    
                    if response.status == 200:
                        # Extract tools used
                        tools_used = []
                        output = result.get("output", [])
                        
                        for item in output:
                            if item.get("type") == "tool_use":
                                tool_name = item.get("tool_use", {}).get("name", "")
                                if tool_name:
                                    tools_used.append(tool_name)
                        
                        # Extract text response
                        text_response = ""
                        for item in output:
                            if item.get("type") == "output_text":
                                text_response = item.get("text", "")
                                break
                        
                        print(f"\n✅ Success!")
                        print(f"Tools used: {tools_used}")
                        print(f"Response: {text_response[:200]}...")
                        
                        # Check if expected tools were used
                        for expected_tool in test_case["expected_tools"]:
                            if any(expected_tool in tool for tool in tools_used):
                                print(f"✓ Expected tool '{expected_tool}' was used")
                            else:
                                print(f"✗ Expected tool '{expected_tool}' was NOT used")
                        
                        # Show usage stats
                        usage = result.get("usage", {})
                        print(f"\nAgents used: {usage.get('agents_used', [])}")
                        print(f"Total agents: {usage.get('total_agents', 0)}")
                        
                    else:
                        print(f"\n❌ Error: {response.status}")
                        print(f"Response: {json.dumps(result, indent=2, ensure_ascii=False)}")
                        
            except Exception as e:
                print(f"\n❌ Exception: {e}")
            
            # Wait between tests
            if i < len(test_cases) - 1:
                print("\nWaiting 2 seconds before next test...")
                await asyncio.sleep(2)

if __name__ == "__main__":
    print("Testing Pattern 2 Orchestrator with Memory Tools")
    print("="*60)
    asyncio.run(test_pattern2_memory())