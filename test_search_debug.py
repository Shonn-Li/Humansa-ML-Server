#!/usr/bin/env python3
"""Debug script to test note search functionality"""

import asyncio
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from chat.postgres.db_manager import PostgresManager
from chat.search.hybrid_search import HybridSearchEngine

async def test_search():
    # Initialize database
    postgres = PostgresManager()
    hybrid_search = HybridSearchEngine(postgres)
    
    # Test user ID
    user_id = 10001
    
    # Test queries
    test_queries = [
        "machine learning",
        "AI",
        "neural network",
        "test",
        "data"
    ]
    
    print("=== Testing Keyword Search ===")
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        
        # Test keyword search
        results = hybrid_search.keyword_search_notes(query, user_id, limit=5)
        print(f"Keyword search found {len(results)} notes")
        for r in results[:3]:
            print(f"  - Note {r['type_id']}: {r['title']} (rank: {r['rank']:.3f})")
            if 'snippet' in r:
                print(f"    Snippet: {r['snippet'][:100]}...")
    
    print("\n=== Checking Database Content ===")
    with postgres.get_connection() as conn:
        with conn.cursor() as cur:
            # Check total notes
            cur.execute("""
                SELECT COUNT(*) 
                FROM note_v1 
                WHERE "ownerId" = %s AND "deletedAt" IS NULL
            """, (user_id,))
            total_notes = cur.fetchone()[0]
            print(f"Total notes for user {user_id}: {total_notes}")
            
            # Sample notes
            cur.execute("""
                SELECT id, "noteTitle", 
                       LEFT(COALESCE(promptcontent->>'currentPromptContent', ''), 100) as content_preview
                FROM note_v1 
                WHERE "ownerId" = %s AND "deletedAt" IS NULL
                LIMIT 5
            """, (user_id,))
            print("\nSample notes:")
            for row in cur.fetchall():
                print(f"  ID: {row[0]}, Title: {row[1]}")
                print(f"    Content: {row[2]}...")
            
            # Check embeddings
            cur.execute("""
                SELECT COUNT(*) 
                FROM embedding_v1 
                WHERE type = 'note' 
                AND type_id IN (
                    SELECT id FROM note_v1 
                    WHERE "ownerId" = %s AND "deletedAt" IS NULL
                )
            """, (user_id,))
            emb_count = cur.fetchone()[0]
            print(f"\nEmbeddings for user notes: {emb_count}")

if __name__ == "__main__":
    asyncio.run(test_search())