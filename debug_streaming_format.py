#!/usr/bin/env python3

"""Debug streaming format to see actual response structure"""

import httpx
import json
import asyncio

async def debug_streaming():
    """Send a streaming request and print raw events"""
    
    request = {
        "model": "gpt-4.1-nano",
        "messages": [
            {
                "role": "user", 
                "content": "Hi"
            }
        ],
        "stream": True,
        "temperature": 0.7,
        "user_id": 10001
    }
    
    headers = {
        "Authorization": "Bearer test-key",
        "Content-Type": "application/json"
    }
    
    print(f"Request: {json.dumps(request, indent=2)}")
    print("\nStreaming Response Events:")
    print("="*60)
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream('POST', 'http://localhost:5001/v1/chat/completions', 
                                   json=request, headers=headers) as response:
                print(f"Status: {response.status_code}")
                print(f"Headers: {dict(response.headers)}\n")
                
                event_count = 0
                async for line in response.aiter_lines():
                    if line:
                        print(f"Event {event_count}: {line}")
                        
                        # Try to parse if it's JSON after "data: "
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str != "[DONE]":
                                try:
                                    data = json.loads(data_str)
                                    print(f"  Parsed: {json.dumps(data, indent=2)}")
                                except:
                                    print(f"  Could not parse as JSON")
                        
                        event_count += 1
                        if event_count > 5:  # Show first 5 events
                            print("\n... (showing first 5 events only)")
                            break
                        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_streaming())