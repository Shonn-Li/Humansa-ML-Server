#!/usr/bin/env python3
"""
Test the exact production request that was failing
This runs against the production database on port 5001
"""
import asyncio
import aiohttp
import json
import os
import sys
import time

# Use production database settings
# NOTE: We're using port 5001 which should connect to production DB


async def test_exact_production_request():
    """Test the exact request that was failing in production"""
    
    # Wait a bit for server to start
    print("Waiting 5 seconds for server to start...")
    await asyncio.sleep(5)
    
    ml_server_url = "http://localhost:5001/v1/multi-agent/response"
    
    # Exact request from the logs
    request = {
        "messages": [
            {
                "role": "user",
                "content": "Summarize my recent notes and highlight the key points"
            }
        ],
        "model": "deepseek-reasoner",
        "user_id": 1,
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
    print("Testing exact production request")
    print(f"{'='*60}")
    print(f"URL: {ml_server_url}")
    print(f"User ID: {request['user_id']}")
    print(f"Model: {request['model']}")
    print(f"Query: {request['messages'][0]['content']}")
    print(f"{'='*60}")
    
    context_search_found = False
    sources_count = 0
    notes_found_in_search = []
    response_text = ""
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(ml_server_url, json=request, timeout=aiohttp.ClientTimeout(total=60)) as response:
                print(f"\nHTTP Status: {response.status}")
                
                if response.status != 200:
                    error_text = await response.text()
                    print(f"❌ Error response: {error_text}")
                    return
                
                # Read streaming response
                event_count = 0
                async for line in response.content:
                    if line:
                        line_str = line.decode('utf-8').strip()
                        if line_str.startswith('data: '):
                            data_str = line_str[6:]
                            if data_str == '[DONE]':
                                print("\n✅ Stream completed")
                                break
                            
                            event_count += 1
                            
                            try:
                                event = json.loads(data_str)
                                event_type = event.get('type', '')
                                
                                # Log important events
                                if event_type == 'response.output_item.added':
                                    item = event.get('item', {})
                                    if item.get('type') == 'context_search_call':
                                        print(f"\n🔍 Context search initiated (event #{event_count})")
                                        context_search_found = True
                                
                                elif event_type == 'response.output_item.done':
                                    item = event.get('item', {})
                                    if item.get('type') == 'context_search_call':
                                        sources = item.get('sources', item.get('results', []))
                                        sources_count = len(sources)
                                        print(f"\n✅ Context search completed:")
                                        print(f"   - Total sources found: {sources_count}")
                                        
                                        if sources_count == 0:
                                            print("   ⚠️  WARNING: No sources found!")
                                            print("   This is the issue - context search ran but found 0 notes")
                                        else:
                                            print("   - Sources:")
                                            for i, source in enumerate(sources[:5]):
                                                note_id = source.get('note_id', source.get('type_id'))
                                                title = source.get('title', 'Untitled')
                                                notes_found_in_search.append(note_id)
                                                print(f"     {i+1}. Note #{note_id}: {title}")
                                
                                elif event_type == 'response.output_text.delta':
                                    delta = event.get('delta', '')
                                    response_text += delta
                                    if event_count % 50 == 0:
                                        print(f"   ... received {len(response_text)} chars")
                                
                            except json.JSONDecodeError:
                                pass
                
                print(f"\n📊 Final Results:")
                print(f"   - Total events: {event_count}")
                print(f"   - Context search performed: {'Yes' if context_search_found else 'No'}")
                print(f"   - Sources found: {sources_count}")
                print(f"   - Response length: {len(response_text)} chars")
                
                if context_search_found and sources_count == 0:
                    print(f"\n❌ ISSUE CONFIRMED:")
                    print(f"   Context search was triggered but found 0 notes")
                    print(f"   This matches the production issue reported")
                    
                    # Let's check the database directly
                    print(f"\n🔍 Checking database directly...")
                    await check_database_for_user(request['user_id'])
                    
                elif sources_count > 0:
                    print(f"\n✅ SUCCESS: Context search found {sources_count} notes")
                    print(f"   Note IDs: {notes_found_in_search}")
                    
    except asyncio.TimeoutError:
        print("❌ Request timed out after 60 seconds")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


async def check_database_for_user(user_id: int):
    """Check database directly for user's notes"""
    try:
        # Import after server starts to use production settings
        from chat.postgres.db_manager import PostgresManager
        
        postgres = PostgresManager()
        
        with postgres.get_connection() as conn:
            with conn.cursor() as cursor:
                # Check total notes
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM note_v1 
                    WHERE "ownerId" = %s
                """, (user_id,))
                total_notes = cursor.fetchone()[0]
                print(f"   Total notes for user {user_id}: {total_notes}")
                
                # Check active notes
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM note_v1 
                    WHERE "ownerId" = %s AND deletedat IS NULL
                """, (user_id,))
                active_notes = cursor.fetchone()[0]
                print(f"   Active notes (not deleted): {active_notes}")
                
                # Get sample note IDs
                cursor.execute("""
                    SELECT id, "noteTitle", createdate
                    FROM note_v1 
                    WHERE "ownerId" = %s AND deletedat IS NULL
                    ORDER BY createdate DESC
                    LIMIT 5
                """, (user_id,))
                sample_notes = cursor.fetchall()
                
                if sample_notes:
                    print(f"   Sample notes:")
                    for note in sample_notes:
                        print(f"     - Note #{note[0]}: {note[1] or 'Untitled'} (created: {note[2]})")
                
                # Check embeddings
                if active_notes > 0:
                    cursor.execute("""
                        SELECT COUNT(DISTINCT e.type_id)
                        FROM embedding_v1 e
                        INNER JOIN note_v1 n ON e.type_id = n.id AND e.type = 'note'
                        WHERE n."ownerId" = %s AND n.deletedat IS NULL
                    """, (user_id,))
                    embedded_notes = cursor.fetchone()[0]
                    print(f"   Notes with embeddings: {embedded_notes}")
                    
                    if embedded_notes == 0:
                        print(f"   ⚠️  WARNING: User has notes but no embeddings!")
                
    except Exception as e:
        print(f"   ❌ Database check failed: {e}")


if __name__ == "__main__":
    print("🔍 Testing Production Issue with User ID 1")
    print("=" * 60)
    print("This test runs against the production database (port 5001)")
    print("=" * 60)
    asyncio.run(test_exact_production_request())