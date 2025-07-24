#!/usr/bin/env python3
"""
Detailed test of agentic RAG processor
"""
import asyncio
import aiohttp
import json
import os
import sys
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Set environment variables
os.environ['DB_PASSWORD'] = '12931'
os.environ['DB_PORT'] = '5454'
os.environ['DB_HOST'] = 'localhost'
os.environ['DB_USERNAME'] = 'postgres'
os.environ['DB_ACTIVE_DATABASE'] = 'youwoai_test'


async def test_single_query(query: str, user_id: int = 10001):
    """Test a single query and show detailed results"""
    
    ml_server_url = "http://localhost:5002/v1/multi-agent/response"
    
    print(f"\n{'='*80}")
    print(f"Query: {query}")
    print(f"User ID: {user_id}")
    print(f"Time: {datetime.now()}")
    print(f"{'='*80}")
    
    request = {
        "messages": [{"role": "user", "content": query}],
        "model": "gpt-4-mini",
        "user_id": user_id,
        "enable_rag": True,
        "enable_citations": True,
        "enable_web_search": False,
        "stream": True,  # Test streaming to see all events
        "completion_type": "system"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(ml_server_url, json=request) as response:
                print(f"\nHTTP Status: {response.status}")
                
                # Track what we find
                context_search_found = False
                sources_found = []
                response_text = ""
                citations_found = []
                
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
                                
                                # Track different event types
                                if event_type == 'response.output_item.added':
                                    item = event.get('item', {})
                                    if item.get('type') == 'context_search_call':
                                        print(f"\n🔍 Context search initiated")
                                        context_search_found = True
                                
                                elif event_type == 'response.output_item.done':
                                    item = event.get('item', {})
                                    if item.get('type') == 'context_search_call':
                                        sources = item.get('sources', item.get('results', []))
                                        print(f"\n✅ Context search completed: {len(sources)} sources found")
                                        
                                        for i, source in enumerate(sources[:5]):
                                            note_id = source.get('note_id', source.get('type_id'))
                                            title = source.get('title', 'Untitled')
                                            content_preview = source.get('content', '')[:100]
                                            sources_found.append({
                                                'note_id': note_id,
                                                'title': title,
                                                'preview': content_preview
                                            })
                                            print(f"   {i+1}. Note #{note_id}: {title}")
                                            print(f"      Preview: {content_preview}...")
                                
                                elif event_type == 'response.output_text.delta':
                                    delta = event.get('delta', '')
                                    response_text += delta
                                
                                elif event_type == 'response.output_text.annotation.added':
                                    annotation = event.get('annotation', {})
                                    citations_found.append(annotation)
                                
                            except json.JSONDecodeError:
                                pass
                
                # Summary
                print(f"\n📊 Summary:")
                print(f"   - Context search performed: {context_search_found}")
                print(f"   - Sources found: {len(sources_found)}")
                print(f"   - Citations added: {len(citations_found)}")
                print(f"   - Response length: {len(response_text)} chars")
                
                if response_text:
                    print(f"\n📝 Response preview:")
                    print(f"   {response_text[:500]}...")
                
                return {
                    'success': True,
                    'context_search': context_search_found,
                    'sources': sources_found,
                    'citations': citations_found,
                    'response': response_text
                }
                    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e)
        }


async def main():
    """Run comprehensive tests"""
    
    # Test different query types
    test_queries = [
        # Temporal queries
        "Summarize my recent notes and highlight the key points",
        "What did I write about in the last week?",
        "Show me notes from today",
        
        # Topic-based queries
        "What do my notes say about AI and embeddings?",
        "Find information about machine learning",
        "Search for startup ideas in my notes",
        
        # Document type queries
        "List all PDF documents",
        "Show me all my documents",
        
        # Specific content queries
        "What is mentioned about Zepto?",
        "Find notes about Andrew Ng",
        "What did I write about product demos?"
    ]
    
    # Run tests
    results = []
    for query in test_queries:
        result = await test_single_query(query)
        results.append({
            'query': query,
            'result': result
        })
        
        # Wait a bit between queries to not overwhelm the server
        await asyncio.sleep(2)
    
    # Final summary
    print(f"\n{'='*80}")
    print(f"FINAL SUMMARY")
    print(f"{'='*80}")
    
    successful = sum(1 for r in results if r['result']['success'])
    with_context_search = sum(1 for r in results if r['result'].get('context_search', False))
    with_sources = sum(1 for r in results if len(r['result'].get('sources', [])) > 0)
    
    print(f"\nTotal queries tested: {len(results)}")
    print(f"Successful: {successful}")
    print(f"Used context search: {with_context_search}")
    print(f"Found sources: {with_sources}")
    
    print(f"\nDetailed results:")
    for r in results:
        sources_count = len(r['result'].get('sources', []))
        status = "✅" if r['result']['success'] else "❌"
        print(f"{status} {r['query'][:50]}... - {sources_count} sources")


if __name__ == "__main__":
    asyncio.run(main())