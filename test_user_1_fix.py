#!/usr/bin/env python3
"""
Test the fix for user_id=1 returning 0 notes
This tests the exact request that was failing in production
"""
import asyncio
import aiohttp
import json
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Set environment variables for test database
os.environ['DB_PASSWORD'] = '12931'
os.environ['DB_PORT'] = '5454'
os.environ['DB_HOST'] = 'localhost'
os.environ['DB_USERNAME'] = 'postgres'
os.environ['DB_ACTIVE_DATABASE'] = 'youwoai_test'


async def test_exact_failing_request():
    """Test the exact request that was failing"""
    
    # First, let's check if user_id=1 has any notes in the test database
    from chat.postgres.db_manager import PostgresManager
    
    postgres = PostgresManager()
    
    # Check notes for user_id=1
    print("=" * 60)
    print("Checking database for user_id=1...")
    print("=" * 60)
    
    with postgres.get_connection() as conn:
        with conn.cursor() as cursor:
            # Check if user_id=1 has any notes
            cursor.execute("""
                SELECT COUNT(*) 
                FROM note_v1 
                WHERE "ownerId" = %s
            """, (1,))
            total_count = cursor.fetchone()[0]
            print(f"Total notes for user_id=1: {total_count}")
            
            # Check with deletedat filter
            cursor.execute("""
                SELECT COUNT(*) 
                FROM note_v1 
                WHERE "ownerId" = %s AND deletedat IS NULL
            """, (1,))
            active_count = cursor.fetchone()[0]
            print(f"Active notes for user_id=1 (deletedat IS NULL): {active_count}")
            
            # Let's also check user_id=10001 (test user)
            cursor.execute("""
                SELECT COUNT(*) 
                FROM note_v1 
                WHERE "ownerId" = %s AND deletedat IS NULL
            """, (10001,))
            test_user_count = cursor.fetchone()[0]
            print(f"Active notes for user_id=10001 (test user): {test_user_count}")
    
    # Now test the exact request
    ml_server_url = "http://localhost:5002/v1/multi-agent/response"
    
    request = {
        "messages": [
            {
                "role": "user",
                "content": "Summarize my recent notes and highlight the key points"
            }
        ],
        "model": "deepseek-reasoner",
        "user_id": 1,  # Testing with user_id=1 as in the failing request
        "conversation_id": 645,
        "enable_rag": True,
        "enable_citations": True,
        "enable_web_search": True,
        "enable_title_generation": True,
        "stream": True,
        "completion_type": "system",
        "attachments": []
    }
    
    print(f"\n{'='*60}")
    print("Testing exact failing request...")
    print(f"{'='*60}")
    print(f"Request: {json.dumps(request, indent=2)}")
    
    context_search_found = False
    sources_count = 0
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(ml_server_url, json=request, timeout=aiohttp.ClientTimeout(total=30)) as response:
                print(f"\nStatus: {response.status}")
                
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
                                        
                                        if sources_count == 0:
                                            print("⚠️  WARNING: No sources found!")
                                        else:
                                            for i, source in enumerate(sources[:3]):
                                                note_id = source.get('note_id', source.get('type_id'))
                                                title = source.get('title', 'Untitled')
                                                print(f"   {i+1}. Note #{note_id}: {title}")
                                
                            except json.JSONDecodeError:
                                pass
                
                print(f"\n📊 Results:")
                print(f"   - Context search performed: {'Yes' if context_search_found else 'No'}")
                print(f"   - Sources found: {sources_count}")
                
                if sources_count == 0 and context_search_found:
                    print("\n❌ ISSUE CONFIRMED: Context search ran but found 0 sources")
                    print("   This matches the production issue you reported")
                elif sources_count > 0:
                    print("\n✅ ISSUE FIXED: Context search now finds sources!")
                    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Test with the test user (10001) to verify the fix works
    print(f"\n{'='*60}")
    print("Testing with test user (user_id=10001)...")
    print(f"{'='*60}")
    
    request['user_id'] = 10001
    sources_count = 0
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(ml_server_url, json=request, timeout=aiohttp.ClientTimeout(total=30)) as response:
                print(f"Status: {response.status}")
                
                async for line in response.content:
                    if line:
                        line_str = line.decode('utf-8').strip()
                        if line_str.startswith('data: '):
                            data_str = line_str[6:]
                            if data_str == '[DONE]':
                                break
                            
                            try:
                                event = json.loads(data_str)
                                if event.get('type') == 'response.output_item.done':
                                    item = event.get('item', {})
                                    if item.get('type') == 'context_search_call':
                                        sources = item.get('sources', item.get('results', []))
                                        sources_count = len(sources)
                                        print(f"\n✅ Context search found: {sources_count} sources")
                                        for i, source in enumerate(sources[:3]):
                                            note_id = source.get('note_id', source.get('type_id'))
                                            title = source.get('title', 'Untitled')
                                            print(f"   {i+1}. Note #{note_id}: {title}")
                            except:
                                pass
                
                if sources_count > 0:
                    print(f"\n✅ Test user search works correctly: {sources_count} notes found")
                else:
                    print(f"\n❌ Test user search failed: 0 notes found")
                    
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    print("🔍 Testing the fix for user_id=1 returning 0 notes")
    print("=" * 60)
    asyncio.run(test_exact_failing_request())