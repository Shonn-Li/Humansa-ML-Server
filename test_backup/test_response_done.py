#!/usr/bin/env python3
"""Test for response.done event in streaming"""
import asyncio
import httpx
import json

async def test_response_done():
    async with httpx.AsyncClient(timeout=30.0) as client:
        request_data = {
            "messages": [{"role": "user", "content": "Hi"}],
            "user_id": 10001,
            "model": "gpt-4o-mini",
            "stream": True
        }
        
        has_response_done = False
        event_count = 0
        
        async with client.stream('POST', 'http://localhost:5002/v1/multi-agent/response', json=request_data) as response:
            async for line in response.aiter_lines():
                if line.startswith('data: '):
                    data_str = line[6:]
                    if data_str == '[DONE]':
                        break
                    
                    try:
                        event = json.loads(data_str)
                        event_type = event.get('type', '')
                        event_count += 1
                        
                        if event_type == 'response.done':
                            has_response_done = True
                            print(f"✅ Found response.done event at position {event_count}")
                            print(f"   Event data: {json.dumps(event, indent=2)}")
                    except:
                        pass
        
        if has_response_done:
            print("\n✅ SUCCESS: response.done event is present in streaming")
        else:
            print("\n❌ FAILED: response.done event is missing from streaming")
        
        print(f"Total events: {event_count}")

if __name__ == "__main__":
    asyncio.run(test_response_done())