#!/usr/bin/env python3
"""
Detailed test of ML server multi-agent endpoint
"""
import asyncio
import aiohttp
import json
import os
import sys
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Set environment variables before imports
os.environ['DB_PASSWORD'] = '031203'
os.environ['DB_PORT'] = '5454'
os.environ['DB_HOST'] = 'localhost'
os.environ['DB_USERNAME'] = 'postgres'
os.environ['DB_ACTIVE_DATABASE'] = 'youwoai_test'

async def test_ml_server_detailed():
    """Test the ML server's multi-agent endpoint with detailed logging"""
    
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
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Testing ML Server Multi-Agent Endpoint")
    print("=" * 80)
    print(f"URL: {ml_server_url}")
    print(f"Request: {json.dumps(test_request, indent=2)}")
    print("=" * 80)
    
    all_events = []
    event_counts = {}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(ml_server_url, json=test_request) as response:
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Response status: {response.status}")
                
                if response.status != 200:
                    text = await response.text()
                    print(f"Error response: {text}")
                    return
                
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Streaming response:")
                print("-" * 80)
                
                async for line in response.content:
                    if line:
                        line_str = line.decode('utf-8').strip()
                        if line_str.startswith('data: '):
                            if line_str == 'data: [DONE]':
                                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Stream completed")
                                break
                                
                            try:
                                data = json.loads(line_str[6:])
                                event_type = data.get('type', 'unknown')
                                
                                # Count event types
                                event_counts[event_type] = event_counts.get(event_type, 0) + 1
                                
                                # Store all events
                                all_events.append(data)
                                
                                # Print significant events
                                if event_type == 'response.output_item.added':
                                    item = data.get('item', {})
                                    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 📦 OUTPUT ITEM ADDED:")
                                    print(f"  Type: {item.get('type')}")
                                    print(f"  ID: {item.get('id')}")
                                    print(f"  Status: {item.get('status')}")
                                
                                elif event_type == 'response.output_item.done':
                                    item = data.get('item', {})
                                    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] ✅ OUTPUT ITEM DONE:")
                                    print(f"  Type: {item.get('type')}")
                                    print(f"  ID: {item.get('id')}")
                                    print(f"  Status: {item.get('status')}")
                                    
                                    # Check for search results
                                    if 'search' in item.get('type', ''):
                                        has_results = bool(item.get('results') or item.get('sources'))
                                        result_count = len(item.get('results', item.get('sources', [])))
                                        
                                        print(f"  Has results: {has_results}")
                                        print(f"  Result count: {result_count}")
                                        
                                        if has_results:
                                            print(f"  🎯 SEARCH RESULTS FOUND!")
                                            # Print first result
                                            results = item.get('results', item.get('sources', []))
                                            if results:
                                                print(f"  First result: {json.dumps(results[0], indent=4)}")
                                
                                elif event_type == 'response.done':
                                    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🏁 RESPONSE DONE")
                                    response_data = data.get('response', {})
                                    print(f"  Total items: {len(response_data.get('output', []))}")
                                
                                elif 'delta' in event_type:
                                    # Count deltas but don't print each one
                                    pass
                                else:
                                    # Print other event types
                                    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Event: {event_type}")
                            
                            except json.JSONDecodeError:
                                pass
                            except Exception as e:
                                print(f"Error processing line: {e}")
                
                print("\n" + "=" * 80)
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Event Summary:")
                for event_type, count in sorted(event_counts.items()):
                    print(f"  {event_type}: {count}")
                
                # Check for search results
                search_results_found = False
                for event in all_events:
                    if event.get('type') == 'response.output_item.done':
                        item = event.get('item', {})
                        if 'search' in item.get('type', '') and (item.get('results') or item.get('sources')):
                            search_results_found = True
                            break
                
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Final Status:")
                if search_results_found:
                    print("  ✅ SUCCESS: Search results are being included in output_item.done events!")
                else:
                    print("  ❌ ISSUE: No search results found in output_item.done events")
        
    except Exception as e:
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Request failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Starting ML server detailed test...")
    print("Make sure the ML server is running on port 5001")
    print("Make sure the test database is running on port 5454")
    print()
    
    asyncio.run(test_ml_server_detailed())