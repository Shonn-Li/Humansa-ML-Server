#!/usr/bin/env python3

"""Simple debug request"""

import httpx
import json
import asyncio

async def simple_request():
    """Send a non-streaming request to debug"""
    
    request = {
        "model": "gpt-4.1-nano",
        "messages": [
            {
                "role": "user", 
                "content": "Hi"
            }
        ],
        "stream": False,
        "temperature": 0.7,
        "user_id": "test-user-001"
    }
    
    headers = {
        "Authorization": "Bearer test-key",
        "Content-Type": "application/json"
    }
    
    print(f"Request: {json.dumps(request, indent=2)}")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post('http://localhost:5001/v1/chat/completions', 
                                       json=request, headers=headers)
            print(f"\nStatus: {response.status_code}")
            print(f"\nResponse: {json.dumps(response.json(), indent=2)}")
                        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(simple_request())