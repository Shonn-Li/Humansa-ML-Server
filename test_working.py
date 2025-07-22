#!/usr/bin/env python3
"""
Working test that properly connects to test server
"""

import asyncio
import aiohttp
import json
import sys
import os

# Test cases
TEST_CASES = [
    {
        "name": "Context Search",
        "request": {
            "model": "gpt-4.1-nano",
            "messages": [{"role": "user", "content": "Search my notes for PARL"}],
            "stream": True,
            "enable_citations": True,
            "user_id": 10001
        }
    },
    {
        "name": "File Attachment",
        "request": {
            "model": "gpt-4.1-nano", 
            "messages": [{"role": "user", "content": "Summarize this paper"}],
            "attachments": ["https://arxiv.org/pdf/2505.18499.pdf"],
            "stream": True,
            "enable_citations": True,
            "user_id": 10001
        }
    },
    {
        "name": "Multi-Agent",
        "request": {
            "model": "gpt-4.1-nano",
            "messages": [{"role": "user", "content": "Compare this paper with my notes on PARL"}],
            "attachments": ["https://arxiv.org/pdf/2505.18499.pdf"],
            "stream": True,
            "enable_citations": True,
            "user_id": 10001
        }
    }
]


async def test_endpoint():
    """Test the actual endpoints"""
    print("=" * 60)
    print("TESTING MULTI-AGENT ENDPOINTS")
    print("=" * 60)
    
    # Test both possible endpoints
    endpoints = [
        "http://localhost:5002/v1/chat/completions",
        "http://localhost:5002/v1/multi-agent/response"
    ]
    
    timeout = aiohttp.ClientTimeout(total=60)
    
    async with aiohttp.ClientSession(timeout=timeout) as session:
        # First, find which endpoint works
        working_endpoint = None
        
        for endpoint in endpoints:
            print(f"\nTrying endpoint: {endpoint}")
            try:
                # Try a simple request
                test_request = {
                    "model": "gpt-4.1-nano",
                    "messages": [{"role": "user", "content": "Hi"}],
                    "stream": False,
                    "user_id": 10001
                }
                
                async with session.post(endpoint, json=test_request) as resp:
                    if resp.status == 200:
                        print(f"✅ Endpoint works: {endpoint}")
                        working_endpoint = endpoint
                        break
                    else:
                        print(f"❌ Endpoint returned {resp.status}")
            except Exception as e:
                print(f"❌ Failed to connect: {e}")
        
        if not working_endpoint:
            print("\n❌ No working endpoint found!")
            print("Make sure test server is running: python test_server.py")
            return
        
        # Now run actual tests
        print(f"\n{'='*40}")
        print(f"Running tests on: {working_endpoint}")
        print(f"{'='*40}")
        
        for test in TEST_CASES:
            print(f"\nTest: {test['name']}")
            print("-" * 40)
            
            try:
                tools_used = []
                response_text = ""
                citations = []
                
                # Make streaming request
                async with session.post(working_endpoint, json=test["request"]) as resp:
                    if resp.status != 200:
                        print(f"❌ HTTP {resp.status}: {await resp.text()}")
                        continue
                    
                    # Process SSE stream
                    async for line in resp.content:
                        if not line:
                            continue
                        
                        line = line.decode('utf-8').strip()
                        if line.startswith('data: '):
                            data = line[6:]
                            if data == '[DONE]':
                                break
                            
                            try:
                                event = json.loads(data)
                                event_type = event.get("type", "")
                                
                                # For non-streaming response
                                if "choices" in event:
                                    choice = event["choices"][0]
                                    if "message" in choice:
                                        response_text = choice["message"]["content"]
                                    continue
                                
                                # For streaming response
                                if event_type == "response.output_item.added":
                                    item = event.get("item", {})
                                    item_type = item.get("type")
                                    if item_type and item_type.endswith("_call"):
                                        tools_used.append(item_type)
                                
                                elif event_type == "response.output_text.delta":
                                    response_text += event.get("delta", "")
                                
                                elif event_type == "response.output_text.annotation.added":
                                    citations.append(event.get("annotation", {}))
                            
                            except json.JSONDecodeError:
                                continue
                
                print(f"✅ Success!")
                print(f"Tools: {', '.join(tools_used) if tools_used else 'None'}")
                print(f"Citations: {len(citations)}")
                print(f"Response length: {len(response_text)} chars")
                
                # Validation
                if test["name"] == "Context Search" and "context_search_call" not in tools_used:
                    print("⚠️  Warning: Expected context_search_call")
                elif test["name"] == "File Attachment" and "file_search_call" not in tools_used:
                    print("⚠️  Warning: Expected file_search_call")
                elif test["name"] == "Multi-Agent":
                    if "context_search_call" not in tools_used or "file_search_call" not in tools_used:
                        print("⚠️  Warning: Expected both context_search_call and file_search_call")
                
            except Exception as e:
                print(f"❌ Error: {e}")
                import traceback
                traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    # Run with asyncio
    asyncio.run(test_endpoint())