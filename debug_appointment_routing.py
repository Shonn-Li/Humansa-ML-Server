#!/usr/bin/env python
"""Debug appointment routing to see which agent is actually called"""

import asyncio
import aiohttp
import json

async def debug_appointment_routing():
    """Debug to see which agent handles appointment requests"""
    
    url = "http://localhost:6001/v2/humansa/chat"
    
    # Test with streaming to see thinking process
    data = {
        "user_id": "debug_routing",
        "messages": [
            {
                "role": "user",
                "content": "我想预约心内科医生"
            }
        ],
        "stream": True,  # Enable streaming to see reasoning
        "debug": True
    }
    
    print("🔍 Debugging appointment routing with streaming...")
    print(f"📝 Query: {data['messages'][0]['content']}")
    print("="*60)
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json=data) as response:
                print(f"📊 Status: {response.status}")
                
                if response.status == 200:
                    print("\n🌊 Streaming Response:")
                    print("-" * 40)
                    
                    # Process streaming response
                    async for line in response.content:
                        line_str = line.decode('utf-8').strip()
                        if line_str.startswith('data: '):
                            data_str = line_str[6:]  # Remove 'data: ' prefix
                            if data_str == '[DONE]':
                                break
                            try:
                                chunk_data = json.loads(data_str)
                                if 'choices' in chunk_data and len(chunk_data['choices']) > 0:
                                    delta = chunk_data['choices'][0].get('delta', {})
                                    content = delta.get('content', '')
                                    if content:
                                        print(content, end='', flush=True)
                            except json.JSONDecodeError:
                                continue
                    
                    print("\n" + "-" * 40)
                    print("✅ Streaming complete")
                    
                else:
                    error_text = await response.text()
                    print(f"❌ Error: {error_text}")
                    
        except Exception as e:
            print(f"❌ Exception: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_appointment_routing())