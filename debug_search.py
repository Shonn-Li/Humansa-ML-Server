#!/usr/bin/env python3
"""
Debug search functionality directly
"""
import os
import sys
import asyncio

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Test database setup
os.environ['DB_PASSWORD'] = '12931'
os.environ['DB_PORT'] = '5454'
os.environ['DB_HOST'] = 'localhost'
os.environ['DB_USERNAME'] = 'postgres'
os.environ['DB_ACTIVE_DATABASE'] = 'youwoai_test'

async def debug_search():
    """Debug search functionality"""
    
    from chat.postgres.db_manager import PostgresManager
    from chat.search.hybrid_search import HybridSearchEngine
    from chat.embedding.embedding_provider_selector import EmbeddingProviderSelector
    
    print("=" * 60)
    print("DEBUGGING SEARCH FUNCTIONALITY")
    print("=" * 60)
    
    # Initialize components
    postgres = PostgresManager()
    hybrid_search = HybridSearchEngine(postgres)
    embedder = EmbeddingProviderSelector().get_embedding_client()
    
    # Test user
    user_id = 10001
    
    # Get notes
    notes = postgres.resolve_note_ids(user_id=user_id)
    print(f"\n1. User {user_id} has {len(notes)} notes: {notes[:3]}...")
    
    # Test keyword search
    print("\n2. Testing keyword search for 'AI':")
    results = await hybrid_search.hybrid_search(
        query="AI",
        user_id=user_id,
        query_embedding=None,
        search_type="keyword",
        top_k=5
    )
    print(f"   Found {len(results)} results")
    
    # Test vector search
    print("\n3. Testing vector search for 'artificial intelligence':")
    try:
        embedding = embedder.get_text_embedding("artificial intelligence")
        results = await hybrid_search.hybrid_search(
            query="artificial intelligence",
            user_id=user_id,
            query_embedding=embedding,
            search_type="semantic",
            top_k=5
        )
        print(f"   Found {len(results)} results")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test mixed search
    print("\n4. Testing mixed search for 'Zepto startup':")
    try:
        embedding = embedder.get_text_embedding("Zepto startup")
        results = await hybrid_search.hybrid_search(
            query="Zepto startup",
            user_id=user_id,
            query_embedding=embedding,
            search_type="mixed",
            top_k=5
        )
        print(f"   Found {len(results)} results")
        if results:
            for i, r in enumerate(results[:3]):
                print(f"   {i+1}. Note #{r.type_id}: {r.chunk_text[:100]}...")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Direct database test
    print("\n5. Direct database query test:")
    with postgres.get_connection() as conn:
        with conn.cursor() as cursor:
            # Check embedding table structure
            cursor.execute("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'embedding_v1'
                ORDER BY ordinal_position
            """)
            columns = cursor.fetchall()
            print("   Embedding table columns:")
            for col in columns:
                print(f"     - {col[0]}: {col[1]}")

if __name__ == "__main__":
    asyncio.run(debug_search())