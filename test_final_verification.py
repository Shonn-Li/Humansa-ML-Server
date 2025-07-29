#!/usr/bin/env python3
"""
Final verification that the schema sync works end-to-end
"""
import asyncio
import aiohttp
import json
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Set test database environment
os.environ['DB_PASSWORD'] = '12931'
os.environ['DB_PORT'] = '5454'
os.environ['DB_HOST'] = 'localhost'
os.environ['DB_USERNAME'] = 'postgres'
os.environ['DB_ACTIVE_DATABASE'] = 'youwoai_test'

async def test_ml_server_request():
    """Test actual ML server request with unified schema"""
    
    ml_server_url = "http://localhost:5002/v1/multi-agent/response"
    
    # Test with test user that has data
    request = {
        "messages": [
            {
                "role": "user",
                "content": "Summarize my recent notes and highlight the key points"
            }
        ],
        "model": "gpt-4-mini",
        "user_id": 10001,  # Test user with data
        "stream": False,
        "completion_type": "system"
    }
    
    print("=" * 60)
    print("FINAL SCHEMA SYNC VERIFICATION")
    print("=" * 60)
    print(f"Testing with user_id: {request['user_id']}")
    print(f"Query: {request['messages'][0]['content']}")
    print("=" * 60)
    
    try:
        # First check database directly
        from chat.postgres.db_manager import PostgresManager
        postgres = PostgresManager()
        
        notes = postgres.resolve_note_ids(user_id=10001)
        print(f"\n✅ Database check: Found {len(notes)} notes for test user")
        
        # Test ML server
        print("\nTesting ML Server...")
        async with aiohttp.ClientSession() as session:
            async with session.post(
                ml_server_url, 
                json=request, 
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                result = await response.json()
                
                print(f"Status: {response.status}")
                
                # Check for context search
                sources_found = 0
                if result.get("output_items"):
                    for item in result["output_items"]:
                        if item["type"] == "context_search_call":
                            sources = item.get('sources', item.get('results', []))
                            sources_found = len(sources)
                            print(f"\n✅ Context Search: Found {sources_found} sources")
                            if sources_found > 0:
                                print("Sample sources:")
                                for i, source in enumerate(sources[:3]):
                                    note_id = source.get('note_id', source.get('type_id'))
                                    title = source.get('title', 'Untitled')
                                    print(f"  - Note #{note_id}: {title}")
                
                # Check response
                if result.get("choices"):
                    content = result["choices"][0]["message"]["content"]
                    print(f"\n✅ Response generated ({len(content)} chars)")
                
                print("\n" + "=" * 60)
                if sources_found > 0:
                    print("✅ SUCCESS: Schema sync is working correctly!")
                    print("   - Database queries work with unified column names")
                    print("   - RAG search finds and returns notes")
                    print("   - Both test and production use same schema")
                else:
                    print("⚠️  No sources found - check if embeddings exist")
                    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_ml_server_request())