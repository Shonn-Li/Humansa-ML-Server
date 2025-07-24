#!/usr/bin/env python3
"""
Test the agentic RAG processor
"""
import asyncio
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

from chat.agent.agentic_rag_processor import AgenticRAGProcessor
from chat.rag.rag_processor import RAGProcessor
from chat.search.hybrid_search import HybridSearchEngine
from chat.postgres.db_manager import PostgresManager
from chat.embedding.embedding_provider_selector import EmbeddingProviderSelector
from chat.postgres.embedding_operations import EmbeddingDBOperations


async def test_agentic_rag():
    """Test the agentic RAG processor with various queries"""
    
    # Initialize components
    postgres = PostgresManager()
    hybrid_search = HybridSearchEngine(postgres)
    
    # Initialize RAG processor
    rag_processor = RAGProcessor()
    
    # Create agentic processor
    agentic_processor = AgenticRAGProcessor(
        rag_processor=rag_processor,
        postgres=postgres,
        hybrid_search=hybrid_search
    )
    
    # Test queries
    test_queries = [
        ("Summarize my recent notes and highlight the key points", 10001),
        ("What did I write about AI last week?", 10001),
        ("Find all my meeting notes", 10001),
        ("Show me notes about embeddings", 10001),
    ]
    
    for query, user_id in test_queries:
        print(f"\n{'='*80}")
        print(f"Query: {query}")
        print(f"User ID: {user_id}")
        print(f"{'='*80}")
        
        try:
            result = await agentic_processor.process_query(
                query=query,
                user_id=user_id,
                note_ids=None,
                conversation_ids=None,
                max_steps=3
            )
            
            print(f"\nStatus: {result.get('status')}")
            print(f"\nUnderstanding:")
            understanding = result.get('understanding', {})
            print(f"  Intent: {understanding.get('intent')}")
            print(f"  Temporal Filter: {understanding.get('temporal_filter')}")
            print(f"  Key Concepts: {understanding.get('key_concepts')}")
            
            print(f"\nRetrieval Steps:")
            for step in result.get('retrieval_steps', []):
                print(f"  - {step['strategy']}: {step['results_count']} results")
            
            print(f"\nTotal Results: {result.get('total_results')}")
            print(f"Search Summary: {result.get('search_summary')}")
            
            # Show sample results
            if result.get('sources'):
                print(f"\nSample Sources:")
                for source in result['sources'][:3]:
                    print(f"  - {source['type']} #{source['type_id']}: {source.get('title', 'Untitled')}")
                    if source['chunks']:
                        print(f"    First chunk: {source['chunks'][0]['content'][:100]}...")
            
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_agentic_rag())