#!/usr/bin/env python
"""Debug appointment agent with more explicit request"""

import asyncio
import aiohttp
import json

async def debug_explicit_appointment_call():
    """Debug with explicit appointment request"""
    
    url = "http://localhost:6001/v2/humansa/chat"
    
    test_queries = [
        "我要预约挂号，需要心内科医生",
        "帮我预约一个心内科医生的号",
        "查询心内科医生的可预约时间",
        "I want to book an appointment with a cardiologist"
    ]
    
    for i, query in enumerate(test_queries):
        print(f"\n{'='*60}")
        print(f"🔍 Test {i+1}: {query}")
        print('='*60)
        
        data = {
            "user_id": f"debug_appointment_{i}",
            "messages": [
                {
                    "role": "user", 
                    "content": query
                }
            ],
            "stream": False,
            "debug": True
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, json=data) as response:
                    print(f"📊 Status: {response.status}")
                    
                    if response.status == 200:
                        result = await response.json()
                        
                        if "choices" in result:
                            content = result["choices"][0]["message"]["content"]
                            
                            if isinstance(content, dict) and "output" in content:
                                actual_content = content["output"][0].get("content", "")
                                print(f"💬 Response: {actual_content}")
                                
                                # Check if it actually searched for slots
                                if "找到" in actual_content or "可预约" in actual_content or "医生" in actual_content:
                                    print("✅ GOOD: Response contains appointment info")
                                elif "请提供" in actual_content or "需要" in actual_content:
                                    print("❌ BAD: Still asking for more info instead of searching")
                                else:
                                    print("❓ UNCLEAR: Response unclear")
                            else:
                                print(f"💬 Response: {content}")
                    else:
                        error_text = await response.text()
                        print(f"❌ Error: {error_text}")
                        
            except Exception as e:
                print(f"❌ Exception: {e}")

if __name__ == "__main__":
    asyncio.run(debug_explicit_appointment_call())