#\!/usr/bin/env python3
"""Simple test to debug streaming response"""

import aiohttp
import asyncio
import json


async def test_simple():
    """Test simple streaming request"""
    
    url = "http://localhost:5002/v1/multi-agent/response"
    
    request_data = {
        "model": "gpt-4.1-nano",
        "messages": [{"role": "user", "content": "What is 2 + 2?"}],
        "stream": True,
        "user_id": 10001
    }
    
    print("Testing simple streaming request...")
    print(f"URL: {url}")
    print(f"Request: {json.dumps(request_data, indent=2)}")
    print("-" * 60)
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json=request_data) as response:
                print(f"Status: {response.status}")
                print(f"Content-Type: {response.headers.get('content-type')}")
                
                if response.status == 200:
                    # Read the entire response
                    text = await response.text()
                    print(f"\nRaw Response (first 1000 chars):")
                    print(text[:1000])
                    
                    # Parse events
                    events = []
                    for line in text.split('\n'):
                        if line.startswith('data:'):
                            data = line[5:].strip()
                            if data and data != '[DONE]':
                                try:
                                    event = json.loads(data)
                                    events.append(event)
                                    print(f"\nEvent: {event.get('type')}")
                                    if event.get('type') == 'response.output_item.added':
                                        print(f"  Item: {event.get('item', {})}")
                                except json.JSONDecodeError as e:
                                    print(f"JSON Error: {e}")
                                    print(f"Data: {data[:100]}")
                    
                    print(f"\nTotal events: {len(events)}")
                else:
                    text = await response.text()
                    print(f"Error: {text}")
                    
        except Exception as e:
            print(f"Exception: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_simple())
