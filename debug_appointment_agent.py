#!/usr/bin/env python
"""Debug appointment agent to see why it's not calling search function"""

import asyncio
import aiohttp
import json

async def debug_appointment_call():
    """Debug a single appointment call"""
    
    url = "http://localhost:6001/v2/humansa/chat"
    
    data = {
        "user_id": "debug_appointment",
        "messages": [
            {
                "role": "user",
                "content": "我想预约心内科医生"
            }
        ],
        "stream": False,
        "debug": True  # Enable debug mode
    }
    
    print("🔍 Debugging appointment agent call...")
    print(f"📝 Query: {data['messages'][0]['content']}")
    print("="*50)
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json=data) as response:
                print(f"📊 Status: {response.status}")
                
                if response.status == 200:
                    result = await response.json()
                    
                    print("\n🔧 Raw Response Structure:")
                    print(f"Keys: {list(result.keys())}")
                    
                    if "choices" in result:
                        content = result["choices"][0]["message"]["content"]
                        print(f"\nContent type: {type(content)}")
                        
                        if isinstance(content, dict):
                            print(f"Content keys: {list(content.keys())}")
                            
                            if "output" in content:
                                actual_content = content["output"][0].get("content", "")
                                print(f"\n💬 Actual Response:\n{actual_content}")
                            
                            if "metadata" in content:
                                print(f"\n🔍 Metadata: {content['metadata']}")
                        else:
                            print(f"\n💬 Response:\n{content}")
                    
                    print(f"\n📄 Full JSON Response:")
                    print(json.dumps(result, indent=2, ensure_ascii=False))
                    
                else:
                    error_text = await response.text()
                    print(f"❌ Error: {error_text}")
                    
        except Exception as e:
            print(f"❌ Exception: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_appointment_call())