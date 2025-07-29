#\!/usr/bin/env python3
"""
Test context search with agentic RAG
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


async def test_context_search():
    """Test context search functionality"""
    
    ml_server_url = "http://localhost:5002/v1/multi-agent/response"
    
    test_queries = [
        "Summarize my recent notes and highlight the key points",
        "What did I write about AI?",
        "Find notes about embeddings",
        "Show me all PDF documents",
    ]
    
    for query in test_queries:
        print(f"\n{'='*80}")
        print(f"Query: {query}")
        print(f"{'='*80}")
        
        request = {
            "messages": [{"role": "user", "content": query}],
            "model": "gpt-4-mini",
            "user_id": 10001,
            "enable_rag": True,
            "enable_citations": True,
            "enable_web_search": False,
            "stream": False,
            "completion_type": "system"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(ml_server_url, json=request) as response:
                    result = await response.json()
                    
                    print(f"\nStatus: {response.status}")
                    
                    # Check for output items
                    if result.get("output_items"):
                        print(f"\nOutput Items: {len(result['output_items'])}")
                        for item in result["output_items"]:
                            if item["type"] == "context_search_call":
                                print(f"\n🔍 Context Search:")
                                print(f"   Status: {item.get('status')}")
                                sources = item.get('sources', item.get('results', []))
                                print(f"   Sources found: {len(sources)}")
                                for i, source in enumerate(sources[:3]):
                                    print(f"   {i+1}. Note #{source.get('note_id', 'N/A')}: {source.get('title', 'Untitled')}")
                                    if source.get('content'):
                                        print(f"      Preview: {source['content'][:100]}...")
                            elif item["type"] == "text":
                                print(f"\n📝 Response:")
                                print(f"   {item['content'][:500]}...")
                    
                    # Check for citations
                    if result.get("citations"):
                        print(f"\n📚 Citations: {len(result['citations'])}")
                        for cit in result["citations"][:3]:
                            print(f"   - {cit.get('title', 'Untitled')} (ID: {cit.get('source_id')})")
                    
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_context_search())
EOF < /dev/null