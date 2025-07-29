#!/usr/bin/env python3
"""
Simple test of agentic RAG processor
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


async def test_agentic_rag():
    """Test agentic RAG functionality"""
    
    ml_server_url = "http://localhost:5002/v1/multi-agent/response"
    
    test_queries = [
        "Summarize my recent notes",
        "What did I write about AI?",
        "Find notes about Zepto"
    ]
    
    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"Testing: {query}")
        print(f"{'='*60}")
        
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
                async with session.post(ml_server_url, json=request, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    result = await response.json()
                    
                    print(f"\nStatus: {response.status}")
                    
                    # Check for output items
                    if result.get("output_items"):
                        for item in result["output_items"]:
                            if item["type"] == "context_search_call":
                                sources = item.get('sources', item.get('results', []))
                                print(f"\n✅ Context Search Found: {len(sources)} sources")
                                for i, source in enumerate(sources[:3]):
                                    note_id = source.get('note_id', source.get('type_id'))
                                    title = source.get('title', 'Untitled')
                                    print(f"   {i+1}. Note #{note_id}: {title}")
                    
                    # Check response
                    if result.get("choices"):
                        content = result["choices"][0]["message"]["content"]
                        print(f"\n📝 Response (first 200 chars):")
                        print(f"   {content[:200]}...")
                    
        except asyncio.TimeoutError:
            print("❌ Request timed out after 30 seconds")
        except Exception as e:
            print(f"❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(test_agentic_rag())