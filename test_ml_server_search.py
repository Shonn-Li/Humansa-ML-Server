#!/usr/bin/env python3
"""
Test ML server multi-agent endpoint with search functionality
"""
import asyncio
import aiohttp
import json
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Set environment variables before imports
os.environ['DB_PASSWORD'] = '031203'
os.environ['DB_PORT'] = '5454'
os.environ['DB_HOST'] = 'localhost'
os.environ['DB_USERNAME'] = 'postgres'
os.environ['DB_ACTIVE_DATABASE'] = 'youwoai_test'

async def test_ml_server_search():
    """Test the ML server's multi-agent endpoint with search"""
    
    # ML server URL
    ml_server_url = "http://localhost:5001/v1/multi-agent/response"
    
    # Test request that should trigger context search
    test_request = {
        "messages": [{
            "role": "user",
            "content": "What information do you have about AI or machine learning in my notes?"
        }],
        "model": "openai/gpt-4o-mini",
        "stream": True,
        "user_id": 10001  # Test user ID
    }
    
    print("Testing ML Server Multi-Agent Endpoint with Search")
    print("=" * 80)
    print(f"URL: {ml_server_url}")
    print(f"Request: {json.dumps(test_request, indent=2)}")
    print("=" * 80)
    
    found_search_events = []
    found_search_results = []
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(ml_server_url, json=test_request) as response:
                print(f"\nResponse status: {response.status}")
                
                if response.status != 200:
                    text = await response.text()
                    print(f"Error response: {text}")
                    return
                
                print("\nStreaming response:")
                print("-" * 80)
                
                async for line in response.content:
                    if line:
                        line_str = line.decode('utf-8').strip()
                        if line_str.startswith('data: '):
                            if line_str == 'data: [DONE]':
                                break
                                
                            try:
                                data = json.loads(line_str[6:])
                                event_type = data.get('type', '')
                                
                                # Look for search-related events
                                if 'search' in event_type.lower():
                                    print(f"\n🔍 SEARCH EVENT: {event_type}")
                                    print(json.dumps(data, indent=2))
                                    found_search_events.append(data)
                                
                                # Look for output_item.done events
                                if event_type == 'response.output_item.done':
                                    item = data.get('item', {})
                                    item_type = item.get('type', '')
                                    
                                    if 'search' in item_type:
                                        print(f"\n📦 SEARCH DONE EVENT:")
                                        print(json.dumps(item, indent=2))
                                        
                                        # Check for results
                                        has_results = bool(item.get('results') or item.get('sources'))
                                        result_count = len(item.get('results', item.get('sources', [])))
                                        
                                        print(f"✅ Has results: {has_results}")
                                        print(f"📊 Result count: {result_count}")
                                        
                                        if has_results:
                                            found_search_results.append(item)
                                            print(f"🎯 Search results successfully included in output_item.done!")
                                        else:
                                            print(f"❌ No search results in output_item.done event")
                            
                            except json.JSONDecodeError:
                                pass
                            except Exception as e:
                                print(f"Error processing line: {e}")
                
                print("\n" + "=" * 80)
                print(f"\nSummary:")
                print(f"- Found {len(found_search_events)} search-related events")
                print(f"- Found {len(found_search_results)} search results in output_item.done events")
                
                if found_search_results:
                    print(f"\n✅ SUCCESS: Search results are being included in output_item.done events!")
                    for idx, result in enumerate(found_search_results):
                        print(f"\n  Result {idx + 1}:")
                        print(f"  - Type: {result.get('type')}")
                        print(f"  - Results/Sources count: {len(result.get('results', result.get('sources', [])))}")
                else:
                    print(f"\n❌ ISSUE: No search results found in output_item.done events")
                    print(f"   The ML server may not be including search results properly.")
        
    except Exception as e:
        print(f"\nRequest failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("Starting ML server test...")
    print("Make sure the ML server is running on port 5001")
    print("Make sure the test database is running on port 5454")
    print()
    
    asyncio.run(test_ml_server_search())