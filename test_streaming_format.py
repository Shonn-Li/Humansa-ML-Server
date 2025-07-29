#!/usr/bin/env python3
"""
Test to show the exact streaming format for search results
"""
import asyncio
import aiohttp
import json
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Set environment variables
os.environ['DB_PASSWORD'] = '12931'
os.environ['DB_PORT'] = '5454'
os.environ['DB_HOST'] = 'localhost'
os.environ['DB_USERNAME'] = 'postgres'
os.environ['DB_ACTIVE_DATABASE'] = 'youwoai_test'

async def test_streaming_format():
    """Show the exact format of streamed search results"""
    
    ml_server_url = "http://localhost:5001/v1/multi-agent/response"
    
    print("\n" + "="*80)
    print("STREAMING FORMAT FOR SEARCH RESULTS")
    print("="*80)
    
    # Test context search
    print("\n1. CONTEXT SEARCH FORMAT:")
    print("-" * 40)
    
    test_request = {
        "messages": [{"role": "user", "content": "What AI information is in my notes?"}],
        "model": "openai/gpt-4o-mini",
        "stream": True,
        "user_id": 10001
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(ml_server_url, json=test_request) as response:
            async for line in response.content:
                if line:
                    line_str = line.decode('utf-8').strip()
                    if line_str.startswith('data: '):
                        if line_str == 'data: [DONE]':
                            break
                        try:
                            data = json.loads(line_str[6:])
                            if data.get('type') == 'response.output_item.done':
                                item = data.get('item', {})
                                if item.get('type') == 'context_search_call':
                                    print("Event type: response.output_item.done")
                                    print("Item structure:")
                                    print(f"  - id: {item.get('id')}")
                                    print(f"  - type: {item.get('type')}")
                                    print(f"  - status: {item.get('status')}")
                                    print(f"  - sources: Array of {len(item.get('sources', []))} items")
                                    if item.get('sources'):
                                        print("\n  First source format:")
                                        first_source = item['sources'][0]
                                        for key in first_source:
                                            print(f"    - {key}: {type(first_source[key]).__name__}")
                                    break
                        except:
                            pass
    
    # Test web search
    print("\n\n2. WEB SEARCH FORMAT:")
    print("-" * 40)
    
    test_request = {
        "messages": [{"role": "user", "content": "Search web for OpenAI news"}],
        "model": "openai/gpt-4o-mini",
        "stream": True,
        "user_id": 10001
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(ml_server_url, json=test_request) as response:
            async for line in response.content:
                if line:
                    line_str = line.decode('utf-8').strip()
                    if line_str.startswith('data: '):
                        if line_str == 'data: [DONE]':
                            break
                        try:
                            data = json.loads(line_str[6:])
                            if data.get('type') == 'response.output_item.done':
                                item = data.get('item', {})
                                if item.get('type') == 'web_search_call':
                                    print("Event type: response.output_item.done")
                                    print("Item structure:")
                                    print(f"  - id: {item.get('id')}")
                                    print(f"  - type: {item.get('type')}")
                                    print(f"  - status: {item.get('status')}")
                                    print(f"  - results: Array of {len(item.get('results', []))} items")
                                    if item.get('results'):
                                        print("\n  First result format:")
                                        first_result = item['results'][0]
                                        for key in first_result:
                                            print(f"    - {key}: {type(first_result[key]).__name__}")
                                    break
                        except:
                            pass
    
    print("\n" + "="*80)
    print("KEY DIFFERENCES:")
    print("- Context Search: Uses 'sources' key, includes note_id")
    print("- Web Search: Uses 'results' key, includes url")
    print("="*80)

if __name__ == "__main__":
    asyncio.run(test_streaming_format())