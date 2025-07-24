#!/usr/bin/env python3
"""
Detailed test to verify search result streaming format
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
os.environ['DB_PASSWORD'] = '12931'
os.environ['DB_PORT'] = '5454'
os.environ['DB_HOST'] = 'localhost'
os.environ['DB_USERNAME'] = 'postgres'
os.environ['DB_ACTIVE_DATABASE'] = 'youwoai_test'

async def test_context_search_streaming():
    """Test context search streaming with detailed output"""
    
    ml_server_url = "http://localhost:5001/v1/multi-agent/response"
    
    # Test request that should trigger context search
    test_request = {
        "messages": [{
            "role": "user",
            "content": "What information do you have about AI or machine learning in my notes?"
        }],
        "model": "openai/gpt-4o-mini",
        "stream": True,
        "user_id": 10001
    }
    
    print("\n" + "="*80)
    print("TESTING CONTEXT SEARCH STREAMING")
    print("="*80)
    
    context_search_events = []
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(ml_server_url, json=test_request) as response:
                print(f"Response status: {response.status}\n")
                
                async for line in response.content:
                    if line:
                        line_str = line.decode('utf-8').strip()
                        if line_str.startswith('data: '):
                            if line_str == 'data: [DONE]':
                                break
                                
                            try:
                                data = json.loads(line_str[6:])
                                event_type = data.get('type', '')
                                
                                # Look for context search events
                                if event_type == 'response.output_item.added':
                                    item = data.get('item', {})
                                    if item.get('type') == 'context_search_call':
                                        print(f"\n🔍 CONTEXT SEARCH STARTED:")
                                        print(json.dumps(data, indent=2))
                                        context_search_events.append(('started', data))
                                
                                elif event_type == 'response.output_item.done':
                                    item = data.get('item', {})
                                    if item.get('type') == 'context_search_call':
                                        print(f"\n✅ CONTEXT SEARCH COMPLETED:")
                                        print(json.dumps(data, indent=2))
                                        context_search_events.append(('completed', data))
                                        
                                        # Check for results
                                        if 'results' in item or 'sources' in item:
                                            results = item.get('results', item.get('sources', []))
                                            print(f"\n📊 SEARCH RESULTS FOUND: {len(results)} items")
                                            
                                            # Show first few results
                                            for i, result in enumerate(results[:3]):
                                                print(f"\nResult {i+1}:")
                                                if 'note_id' in result:
                                                    print(f"  - Note ID: {result['note_id']}")
                                                if 'title' in result:
                                                    print(f"  - Title: {result['title']}")
                                                if 'type' in result:
                                                    print(f"  - Type: {result['type']}")
                                                if 'content' in result:
                                                    print(f"  - Content: {result['content'][:100]}...")
                                        else:
                                            print("❌ NO RESULTS IN OUTPUT_ITEM.DONE EVENT")
                                
                            except json.JSONDecodeError:
                                pass
    
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    
    return context_search_events

async def test_web_search_streaming():
    """Test web search streaming with detailed output"""
    
    ml_server_url = "http://localhost:5001/v1/multi-agent/response"
    
    # Test request that should trigger web search
    test_request = {
        "messages": [{
            "role": "user",
            "content": "Search the web for the latest news about OpenAI o3 model"
        }],
        "model": "openai/gpt-4o-mini",
        "stream": True,
        "user_id": 10001
    }
    
    print("\n" + "="*80)
    print("TESTING WEB SEARCH STREAMING")
    print("="*80)
    
    web_search_events = []
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(ml_server_url, json=test_request) as response:
                print(f"Response status: {response.status}\n")
                
                async for line in response.content:
                    if line:
                        line_str = line.decode('utf-8').strip()
                        if line_str.startswith('data: '):
                            if line_str == 'data: [DONE]':
                                break
                                
                            try:
                                data = json.loads(line_str[6:])
                                event_type = data.get('type', '')
                                
                                # Look for web search events
                                if event_type == 'response.output_item.added':
                                    item = data.get('item', {})
                                    if item.get('type') == 'web_search_call':
                                        print(f"\n🌐 WEB SEARCH STARTED:")
                                        print(json.dumps(data, indent=2))
                                        web_search_events.append(('started', data))
                                
                                elif event_type == 'response.output_item.done':
                                    item = data.get('item', {})
                                    if item.get('type') == 'web_search_call':
                                        print(f"\n✅ WEB SEARCH COMPLETED:")
                                        print(json.dumps(data, indent=2))
                                        web_search_events.append(('completed', data))
                                        
                                        # Check for results
                                        if 'results' in item:
                                            results = item.get('results', [])
                                            print(f"\n📊 WEB SEARCH RESULTS FOUND: {len(results)} items")
                                            
                                            # Show first few results
                                            for i, result in enumerate(results[:3]):
                                                print(f"\nResult {i+1}:")
                                                if 'title' in result:
                                                    print(f"  - Title: {result['title']}")
                                                if 'url' in result:
                                                    print(f"  - URL: {result['url']}")
                                                if 'snippet' in result:
                                                    print(f"  - Snippet: {result['snippet'][:100]}...")
                                        else:
                                            print("❌ NO RESULTS IN OUTPUT_ITEM.DONE EVENT")
                                
                            except json.JSONDecodeError:
                                pass
    
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    
    return web_search_events

async def main():
    """Run all tests"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Starting search streaming tests...")
    print("Make sure the ML server is running on port 5001")
    print("Make sure the test database is running on port 5454")
    
    # Test context search
    context_events = await test_context_search_streaming()
    
    # Wait a bit between tests
    await asyncio.sleep(2)
    
    # Test web search
    web_events = await test_web_search_streaming()
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    print(f"\nContext Search Events:")
    for event_type, data in context_events:
        item = data.get('item', {})
        if event_type == 'completed':
            has_results = bool(item.get('results') or item.get('sources'))
            result_count = len(item.get('results', item.get('sources', [])))
            print(f"  - {event_type}: has_results={has_results}, count={result_count}")
        else:
            print(f"  - {event_type}")
    
    print(f"\nWeb Search Events:")
    for event_type, data in web_events:
        item = data.get('item', {})
        if event_type == 'completed':
            has_results = bool(item.get('results'))
            result_count = len(item.get('results', []))
            print(f"  - {event_type}: has_results={has_results}, count={result_count}")
        else:
            print(f"  - {event_type}")

if __name__ == "__main__":
    asyncio.run(main())