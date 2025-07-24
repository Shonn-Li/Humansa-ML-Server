#!/usr/bin/env python3
"""
Test agentic RAG with proper streaming support
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


async def test_streaming_response(query: str):
    """Test with streaming to see all events"""
    
    ml_server_url = "http://localhost:5002/v1/multi-agent/response"
    
    print(f"\n{'='*60}")
    print(f"Query: {query}")
    print(f"{'='*60}")
    
    request = {
        "messages": [{"role": "user", "content": query}],
        "model": "gpt-4-mini",
        "user_id": 10001,
        "stream": True,  # Enable streaming
        "completion_type": "system"
    }
    
    context_search_found = False
    sources_count = 0
    response_text = ""
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(ml_server_url, json=request, timeout=aiohttp.ClientTimeout(total=30)) as response:
                print(f"Status: {response.status}")
                
                # Read streaming response
                async for line in response.content:
                    if line:
                        line_str = line.decode('utf-8').strip()
                        if line_str.startswith('data: '):
                            data_str = line_str[6:]
                            if data_str == '[DONE]':
                                break
                            
                            try:
                                event = json.loads(data_str)
                                event_type = event.get('type', '')
                                
                                # Track context search
                                if event_type == 'response.output_item.added':
                                    item = event.get('item', {})
                                    if item.get('type') == 'context_search_call':
                                        print("\n🔍 Context search initiated!")
                                        context_search_found = True
                                
                                elif event_type == 'response.output_item.done':
                                    item = event.get('item', {})
                                    if item.get('type') == 'context_search_call':
                                        sources = item.get('sources', item.get('results', []))
                                        sources_count = len(sources)
                                        print(f"\n✅ Context search completed: {sources_count} sources found")
                                        
                                        for i, source in enumerate(sources[:5]):
                                            note_id = source.get('note_id', source.get('type_id'))
                                            title = source.get('title', 'Untitled')
                                            print(f"   {i+1}. Note #{note_id}: {title}")
                                
                                elif event_type == 'response.output_text.delta':
                                    delta = event.get('delta', '')
                                    response_text += delta
                                
                            except json.JSONDecodeError:
                                pass
                
                # Summary
                print(f"\n📊 Results:")
                print(f"   - Context search used: {'Yes' if context_search_found else 'No'}")
                print(f"   - Sources found: {sources_count}")
                print(f"   - Response length: {len(response_text)} chars")
                
                if response_text:
                    print(f"\n📝 Response preview:")
                    print(f"   {response_text[:300]}...")
                    
    except asyncio.TimeoutError:
        print("❌ Request timed out")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Test various queries that should trigger context search"""
    
    # Queries that should trigger context search
    test_queries = [
        "Summarize my recent notes",
        "What did I write about AI and machine learning?",
        "Search my notes for information about Zepto",
        "What are the key topics in my notes?",
        "Find my notes about startups"
    ]
    
    for query in test_queries:
        await test_streaming_response(query)
        await asyncio.sleep(2)  # Brief pause between requests


if __name__ == "__main__":
    print("🚀 Testing Agentic RAG with Streaming")
    print("=" * 60)
    asyncio.run(main())