#!/usr/bin/env python3
"""Quick test for Humansa V2"""

import asyncio
import aiohttp
import json

BASE_URL = "http://localhost:6001"

async def test_identity():
    """Test basic identity query"""
    async with aiohttp.ClientSession() as session:
        # Test 1: Identity
        print("\n1. Testing identity query...")
        request_data = {
            "user_id": 123,
            "messages": [{"role": "user", "content": "你是谁？"}],
            "stream": False
        }
        
        async with session.post(
            f"{BASE_URL}/v2/humansa/chat",
            json=request_data
        ) as response:
            if response.status == 200:
                result = await response.json()
                print(f"Response: {json.dumps(result, indent=2, ensure_ascii=False)}")
                
                # Extract content
                content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
                print(f"\nContent: {content}")
                
                # Check for Humansa keywords
                keywords = ["诺亚新舟", "小诺", "健康", "医疗"]
                found = [k for k in keywords if k in content]
                print(f"Found keywords: {found}")
            else:
                print(f"Error: {response.status}")
                print(await response.text())

        # Test 2: Emergency
        print("\n2. Testing emergency response...")
        request_data = {
            "user_id": 456,
            "messages": [{"role": "user", "content": "我现在胸痛很厉害，呼吸困难"}],
            "stream": False
        }
        
        async with session.post(
            f"{BASE_URL}/v2/humansa/chat",
            json=request_data
        ) as response:
            if response.status == 200:
                result = await response.json()
                content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
                print(f"\nContent: {content}")
                
                # Check for emergency keywords
                keywords = ["120", "急救", "立即", "医院"]
                found = [k for k in keywords if k in content]
                print(f"Found keywords: {found}")

if __name__ == "__main__":
    asyncio.run(test_identity())