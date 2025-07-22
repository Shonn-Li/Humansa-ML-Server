#!/usr/bin/env python3

"""
Verify test database connection and content
"""

import asyncio
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

# Set up TEST ENVIRONMENT
os.environ['DATABASE_URL'] = 'postgresql://postgres:12931@localhost:5454/youwoai_test'

async def verify_test_db():
    """Verify test database has the expected content"""
    
    print("🔍 Verifying Test Database Connection")
    print("="*60)
    
    try:
        # Import database operations
        from chat.postgres.db_manager import PostgresManager
        
        # Initialize connection
        manager = PostgresManager()
        print("✅ Connected to test database")
        
        # Check notes
        query = """
        SELECT 
            n.id,
            n."noteTitle",
            n."userId",
            n."createdAt",
            f."folderTitle",
            n.notetype,
            LENGTH(n."noteContent") as content_length
        FROM note_v1 n
        LEFT JOIN folder_v1 f ON n."folderId" = f.id
        WHERE n.id IN (10001, 10002, 10003, 10004, 10005, 10006, 10007, 10008, 10009)
        ORDER BY n.id
        """
        
        async with manager.get_connection() as conn:
            rows = await conn.fetch(query)
            
        print(f"\n📚 Found {len(rows)} test notes:")
        for row in rows:
            print(f"  Note {row['id']}: {row['noteTitle'][:50]}...")
            print(f"    User: {row['userId']}, Type: {row['notetype']}, Folder: {row['folderTitle']}")
            print(f"    Content length: {row['content_length']} chars")
        
        # Check embeddings
        embedding_query = """
        SELECT 
            e.type_id as note_id,
            COUNT(*) as embedding_count,
            MIN(LENGTH(e.chunk_text)) as min_chunk_length,
            MAX(LENGTH(e.chunk_text)) as max_chunk_length
        FROM embedding_v1 e
        WHERE e.type_id IN (10001, 10002, 10003, 10004, 10005, 10006, 10007, 10008, 10009)
          AND e.type = 'note'
        GROUP BY e.type_id
        ORDER BY e.type_id
        """
        
        async with manager.get_connection() as conn:
            embedding_rows = await conn.fetch(embedding_query)
        
        print(f"\n🔤 Embeddings for test notes:")
        for row in embedding_rows:
            print(f"  Note {row['note_id']}: {row['embedding_count']} embeddings")
            print(f"    Chunk sizes: {row['min_chunk_length']}-{row['max_chunk_length']} chars")
        
        # Test a specific search
        print(f"\n🔍 Testing search for 'PARL':")
        search_query = """
        SELECT 
            e.type_id,
            e.section_id,
            e.chunk_id,
            SUBSTRING(e.chunk_text, 1, 200) as chunk_preview
        FROM embedding_v1 e
        WHERE e.type = 'note' 
          AND e.type_id = 10001
          AND e.chunk_text ILIKE '%PARL%'
        LIMIT 3
        """
        
        async with manager.get_connection() as conn:
            search_results = await conn.fetch(search_query)
        
        print(f"Found {len(search_results)} chunks containing 'PARL':")
        for i, result in enumerate(search_results, 1):
            print(f"  {i}. Note {result['type_id']} - Chunk {result['chunk_id']}")
            print(f"     {result['chunk_preview']}...")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(verify_test_db())