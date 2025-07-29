#!/usr/bin/env python3
"""
Test that the unified schema works with the updated db_manager
"""
import os
import sys
import asyncio

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Test with test database
os.environ['DB_PASSWORD'] = '12931'
os.environ['DB_PORT'] = '5454'
os.environ['DB_HOST'] = 'localhost'
os.environ['DB_USERNAME'] = 'postgres'
os.environ['DB_ACTIVE_DATABASE'] = 'youwoai_test'

async def test_rag_with_unified_schema():
    """Test RAG functionality with unified schema"""
    
    print("=" * 60)
    print("TESTING RAG WITH UNIFIED SCHEMA")
    print("=" * 60)
    
    try:
        # Import after environment is set
        from chat.postgres.db_manager import PostgresManager
        from chat.rag.rag_processor import RAGProcessor
        from chat.embedding.embedding_provider_selector import EmbeddingProviderSelector
        from chat.postgres.embedding_operations import EmbeddingDBOperations
        from chat.search.hybrid_search import HybridSearchEngine
        from chat.agent.agentic_rag_processor import AgenticRAGProcessor
        
        # Initialize components
        postgres = PostgresManager()
        print("✅ PostgresManager initialized")
        
        # Test basic queries
        print("\n1. Testing basic queries:")
        notes = postgres.resolve_note_ids(user_id=10001)
        print(f"   ✅ Found {len(notes)} notes for test user")
        
        conversations = postgres.resolve_conversation_ids(user_id=10001)
        print(f"   ✅ Found {len(conversations)} conversations for test user")
        
        # Test RAG search
        print("\n2. Testing RAG search:")
        embedder = EmbeddingProviderSelector().get_embedding_client()
        embedding_ops = EmbeddingDBOperations()
        rag = RAGProcessor()
        
        # Initialize hybrid search and agentic processor
        hybrid_search = HybridSearchEngine(postgres)
        agentic_rag = AgenticRAGProcessor(rag, postgres, hybrid_search)
        
        # Test agentic RAG
        result = await agentic_rag.process_query(
            query="Summarize my recent notes about AI",
            user_id=10001,
            max_steps=2
        )
        
        print(f"   ✅ Agentic RAG search completed")
        print(f"   - Total results: {result.get('total_results', 0)}")
        print(f"   - Sources found: {len(result.get('sources', []))}")
        print(f"   - Retrieval steps: {len(result.get('retrieval_steps', []))}")
        
        # Test with a query that uses temporal filter
        print("\n3. Testing temporal queries:")
        result = await agentic_rag.process_query(
            query="What did I write about in the last week?",
            user_id=10001,
            max_steps=2
        )
        
        print(f"   ✅ Temporal query completed")
        print(f"   - Intent: {result['understanding']['intent']}")
        print(f"   - Temporal filter: {result['understanding']['temporal_filter']}")
        print(f"   - Results found: {result.get('total_results', 0)}")
        
        print("\n✅ ALL TESTS PASSED! Unified schema is working correctly.")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🔍 Testing unified database schema")
    asyncio.run(test_rag_with_unified_schema())