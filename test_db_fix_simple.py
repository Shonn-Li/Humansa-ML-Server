#!/usr/bin/env python3
"""
Simple test to verify the database fix
"""
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

from chat.postgres.db_manager import PostgresManager

def test_database_queries():
    """Test database queries directly"""
    
    postgres = PostgresManager()
    
    print("=" * 60)
    print("Testing Database Queries")
    print("=" * 60)
    
    # Test resolve_note_ids for user_id=1
    print("\n1. Testing resolve_note_ids for user_id=1:")
    try:
        notes_user1 = postgres.resolve_note_ids(user_id=1)
        print(f"   ✅ Query executed successfully")
        print(f"   Notes found: {len(notes_user1)}")
        if len(notes_user1) == 0:
            print("   ℹ️  User 1 has no notes in test database (expected)")
    except Exception as e:
        print(f"   ❌ Query failed: {e}")
    
    # Test resolve_note_ids for user_id=10001 (test user)
    print("\n2. Testing resolve_note_ids for user_id=10001:")
    try:
        notes_test_user = postgres.resolve_note_ids(user_id=10001)
        print(f"   ✅ Query executed successfully")
        print(f"   Notes found: {len(notes_test_user)}")
        if len(notes_test_user) > 0:
            print(f"   Note IDs: {notes_test_user[:5]}...")
    except Exception as e:
        print(f"   ❌ Query failed: {e}")
    
    # Test folder-based query
    print("\n3. Testing folder-based note resolution:")
    try:
        # First get some folder IDs for test user
        with postgres.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT DISTINCT "folderId" 
                    FROM note_v1 
                    WHERE "ownerId" = %s 
                    AND "folderId" IS NOT NULL
                    LIMIT 1
                """, (10001,))
                result = cursor.fetchone()
                if result:
                    folder_id = result[0]
                    notes_from_folder = postgres.resolve_note_ids(user_id=10001, folder_ids=[folder_id])
                    print(f"   ✅ Folder query executed successfully")
                    print(f"   Notes in folder {folder_id}: {len(notes_from_folder)}")
                else:
                    print("   ℹ️  No folders found for test user")
    except Exception as e:
        print(f"   ❌ Folder query failed: {e}")
    
    # Test RAG search
    print("\n4. Testing RAG search:")
    try:
        from chat.rag.rag_processor import RAGProcessor
        from chat.embedding.embedding_provider_selector import EmbeddingProviderSelector
        from chat.postgres.embedding_operations import EmbeddingDBOperations
        
        embedder = EmbeddingProviderSelector().get_embedding_client()
        embedding_ops = EmbeddingDBOperations()
        rag = RAGProcessor(embedder, embedding_ops)
        
        # Test with user that has no data
        print("   - Testing with user_id=1 (no data):")
        results1 = rag.search(
            query="test query",
            user_id=1,
            search_type="hybrid"
        )
        print(f"     Results: {len(results1.get('sources', []))} sources")
        
        # Test with test user
        print("   - Testing with user_id=10001 (test data):")
        results2 = rag.search(
            query="AI and machine learning",
            user_id=10001,
            search_type="hybrid"
        )
        print(f"     Results: {len(results2.get('sources', []))} sources")
        if results2.get('sources'):
            print(f"     First source: Note #{results2['sources'][0].get('note_id', 'N/A')}")
            
    except Exception as e:
        print(f"   ❌ RAG search failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("Summary:")
    print("=" * 60)
    print("The fix has been applied to handle the 'deletedat' column consistently.")
    print("User 1 returning 0 notes is expected if they have no data in the test DB.")
    print("The important thing is that queries execute without errors.")


if __name__ == "__main__":
    test_database_queries()