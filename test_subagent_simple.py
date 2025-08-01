#!/usr/bin/env python
"""Simple test for sub-agent architecture"""

import asyncio
import aiohttp
import json

async def test_subagent():
    """Test sub-agent architecture with simple query"""
    
    url = "http://localhost:6001/v2/humansa/chat"
    
    # Test product recommendation
    data = {
        "user_id": "test_user_subagent",
        "messages": [
            {
                "role": "user",
                "content": "我想买一些补充维生素D的产品，有什么推荐吗？"
            }
        ],
        "stream": False
    }
    
    print(f"🧪 Testing sub-agent architecture...")
    print(f"📝 Query: {data['messages'][0]['content']}")
    print(f"🔗 URL: {url}")
    print("=" * 50)
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json=data) as response:
                print(f"📊 Status: {response.status}")
                
                if response.status == 200:
                    result = await response.json()
                    print("✅ SUCCESS!")
                    print(f"📄 Response structure: {list(result.keys())}")
                    
                    if "choices" in result:
                        content = result["choices"][0]["message"]["content"]
                        preview = content[:500] if len(content) > 500 else content
                        suffix = "..." if len(content) > 500 else ""
                        print(f"\n💬 Response:\n{preview}{suffix}")
                    else:
                        print(f"⚠️ Unexpected response format: {json.dumps(result, indent=2)}")
                else:
                    error_text = await response.text()
                    print(f"❌ Error: {error_text}")
                    
        except Exception as e:
            print(f"❌ Exception: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_subagent())