#\!/usr/bin/env python3
"""Test multi-agent endpoint via HTTP"""

import aiohttp
import asyncio
import json


async def test_endpoint():
    """Test the multi-agent endpoint via HTTP"""
    
    url = "http://localhost:5002/v1/multi-agent/response"
    
    request_data = {
        "model": "gpt-4.1-nano",
        "messages": [{"role": "user", "content": "What is 2 + 2?"}],
        "stream": True,
        "user_id": 10001
    }
    
    print(f"Testing endpoint: {url}")
    print(f"Request: {json.dumps(request_data, indent=2)}")
    print("-" * 60)
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json=request_data) as response:
                print(f"Status: {response.status}")
                print(f"Headers: {dict(response.headers)}")
                
                if response.status == 200:
                    if response.headers.get('content-type') == 'text/event-stream':
                        print("\nStreaming response:")
                        async for line in response.content:
                            line = line.decode('utf-8').strip()
                            if line.startswith('data:'):
                                data = line[5:].strip()
                                if data and data != '[DONE]':
                                    try:
                                        event = json.loads(data)
                                        print(f"Event: {event.get('type', 'unknown')}")
                                        if event.get('type') == 'response.output_text.delta':
                                            print(f"  Delta: {event.get('delta', '')}")
                                    except json.JSONDecodeError:
                                        print(f"  Raw: {data}")
                    else:
                        body = await response.text()
                        print(f"Response: {body}")
                else:
                    body = await response.text()
                    print(f"Error response: {body}")
                    
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(test_endpoint())
