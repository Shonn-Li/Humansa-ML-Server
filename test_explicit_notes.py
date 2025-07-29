"""Test explicit note ID handling in agentic RAG processor"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.chat.agent.agentic_rag_processor import AgenticRAGProcessor
from src.chat.rag.rag_processor import RAGProcessor
from src.chat.search.hybrid_search import HybridSearchEngine
from src.chat.postgres.db_manager import PostgresManager
from src.chat.provider.llm_provider import LLMProviderSelector
from src.chat.embedding.embedding_provider_selector import EmbeddingProviderSelector

async def test_explicit_notes():
    # Initialize components
    postgres = PostgresManager()
    llm_provider = LLMProviderSelector()
    embedding_selector = EmbeddingProviderSelector()
    hybrid_search = HybridSearchEngine(postgres)
    rag_processor = RAGProcessor(postgres, llm_provider, embedding_selector)
    
    agentic_processor = AgenticRAGProcessor(
        rag_processor=rag_processor,
        postgres=postgres,
        hybrid_search=hybrid_search
    )
    
    # Test with explicit note IDs
    print("Testing with explicit note IDs...")
    
    # Test query similar to the debug log
    result = await agentic_processor.process_query(
        query="what did this talk about?",
        user_id=3,
        note_ids=[7487],  # Explicit note ID from debug log
        conversation_ids=None,
        max_steps=3
    )
    
    print(f"\nUnderstanding: {result.get('understanding')}")
    print(f"\nRetrieval steps:")
    for step in result.get('retrieval_steps', []):
        print(f"  - Strategy: {step['strategy']}, Results: {step['results_count']}")
    
    print(f"\nTotal results: {result.get('total_results', 0)}")
    print(f"Sources found: {len(result.get('sources', []))}")
    
    # Print first source if available
    if result.get('sources'):
        first_source = result['sources'][0]
        print(f"\nFirst source:")
        print(f"  Type: {first_source.get('type')}")
        print(f"  ID: {first_source.get('type_id')}")
        print(f"  Title: {first_source.get('title')}")
        print(f"  Chunks: {len(first_source.get('chunks', []))}")

if __name__ == "__main__":
    asyncio.run(test_explicit_notes())