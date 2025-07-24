#!/usr/bin/env python3
"""
Test script to verify that search results are included in output_item.done events
"""
import asyncio
import aiohttp
import json
from datetime import datetime

async def test_search_results():
    """Test the multi-agent endpoint to verify search results are included"""
    
    # Start test server first
    print("Please ensure the test server is running on port 5002")
    print("Run: python test/core/test_server.py")
    print()
    
    url = "http://localhost:5002/v1/multi-agent/chat/stream"
    
    # Test request that triggers web search
    test_request = {
        "messages": [
            {
                "role": "user",
                "content": "What is the latest news about AI?"
            }
        ],
        "user_id": 10001,
        "conversation_id": 2001,
        "model": "openai/gpt-4o-mini",
        "enable_rag": True
    }
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Sending test request...")
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=test_request) as response:
            if response.status != 200:
                print(f"Error: Response status {response.status}")
                return
            
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Receiving streaming response...")
            print("-" * 80)
            
            found_web_search_done = False
            found_context_search_done = False
            web_search_has_results = False
            context_search_has_sources = False
            
            async for line in response.content:
                if line:
                    line_str = line.decode('utf-8').strip()
                    if line_str.startswith('data: '):
                        try:
                            data = json.loads(line_str[6:])
                            
                            # Check for output_item.done events
                            if data.get('type') == 'response.output_item.done':
                                item = data.get('item', {})
                                item_type = item.get('type', '')
                                
                                if item_type == 'web_search_call':
                                    found_web_search_done = True
                                    if 'results' in item or 'sources' in item:
                                        web_search_has_results = True
                                        print(f"✅ WEB SEARCH DONE - Has results: {len(item.get('results', item.get('sources', [])))}")
                                        if 'results' in item and item['results']:
                                            print(f"   First result: {item['results'][0].get('title', 'No title')}")
                                    else:
                                        print("❌ WEB SEARCH DONE - No results field!")
                                
                                elif item_type == 'context_search_call':
                                    found_context_search_done = True
                                    if 'sources' in item or 'results' in item:
                                        context_search_has_sources = True
                                        print(f"✅ CONTEXT SEARCH DONE - Has sources: {len(item.get('sources', item.get('results', [])))}")
                                        if 'sources' in item and item['sources']:
                                            print(f"   First source: {item['sources'][0].get('title', 'No title')}")
                                    else:
                                        print("❌ CONTEXT SEARCH DONE - No sources field!")
                                
                                # Print the full event for debugging
                                print(f"\nFull event: {json.dumps(data, indent=2)}\n")
                            
                        except json.JSONDecodeError:
                            pass
    
    print("-" * 80)
    print("\nTest Results:")
    print(f"Web search done event found: {'✅' if found_web_search_done else '❌'}")
    print(f"Web search has results: {'✅' if web_search_has_results else '❌'}")
    print(f"Context search done event found: {'✅' if found_context_search_done else '❌'}")
    print(f"Context search has sources: {'✅' if context_search_has_sources else '❌'}")
    
    if web_search_has_results or context_search_has_sources:
        print("\n🎉 SUCCESS: Search results are now being included in output_item.done events!")
    else:
        print("\n❌ FAILURE: Search results are still missing from output_item.done events.")

if __name__ == "__main__":
    asyncio.run(test_search_results())