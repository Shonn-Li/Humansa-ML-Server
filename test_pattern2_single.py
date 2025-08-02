#!/usr/bin/env python3
"""
Test single Pattern 2 request to see tool usage
"""

import asyncio
import json
import aiohttp

API_URL = "http://localhost:6001/v2/humansa/responses/create"

async def test_single():
    """Test single Pattern 2 request"""
    
    request_data = {
        "model": "gpt-4-turbo",
        "input": "我对花生过敏，请记住这个信息",
        "user_id": "test_user_pattern2_001",
        "metadata": {
            "use_pattern2": True
        }
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(API_URL, json=request_data) as response:
            result = await response.json()
            
            print(f"Status: {response.status}")
            print(f"\nFull Response:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            
            # Extract tools used
            tools_used = []
            output = result.get("output", [])
            
            print(f"\nOutput items: {len(output)}")
            for i, item in enumerate(output):
                print(f"  Item {i}: type={item.get('type')}")
                if item.get("type") == "tool_use":
                    tool_name = item.get("tool_use", {}).get("name", "")
                    tools_used.append(tool_name)
                    print(f"    Tool: {tool_name}")
            
            print(f"\nTools used: {tools_used}")

if __name__ == "__main__":
    asyncio.run(test_single())