#!/usr/bin/env python3

"""Debug request to see what's happening"""

import httpx
import json
import asyncio

async def debug_request():
    """Send a simple request and print the raw response"""
    
    request = {
        "model": "gpt-4.1-nano",
        "messages": [
            {
                "role": "user", 
                "content": "What is 2 + 2?"
            }
        ],
        "stream": True,
        "temperature": 0.7
    }
    
    headers = {
        "Authorization": "Bearer test-key",
        "Content-Type": "application/json"
    }
    
    print(f"Request: {json.dumps(request, indent=2)}")
    print("\nResponse:")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream('POST', 'http://localhost:5001/v1/chat/completions', 
                                   json=request, headers=headers) as response:
                print(f"Status: {response.status_code}")
                print(f"Headers: {dict(response.headers)}")
                print("\nBody:")
                
                # Read a few lines
                line_count = 0
                async for line in response.aiter_lines():
                    print(f"Line {line_count}: {line}")
                    line_count += 1
                    if line_count > 10:  # Only show first 10 lines
                        print("... (truncated)")
                        break
                        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_request())