#!/usr/bin/env python3

"""
Simple test to verify RAG can find test notes
"""

import asyncio
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

# Set up TEST ENVIRONMENT
os.environ['DATABASE_URL'] = 'postgresql://postgres:12931@localhost:5454/youwoai_test'

async def test_rag_simple():
    """Test RAG directly"""
    
    print("🔍 Testing RAG with Test Environment")
    print("="*60)
    
    try:
        # Import RAG processor
        from chat.rag.rag_processor import RAGProcessor
        
        rag = RAGProcessor()
        print("✅ RAG Processor initialized")
        
        # Test queries
        test_queries = [
            ("PARL predictable AI", 10001),
            ("predictability aware reinforcement learning", 10001),
            ("G1 graph reasoning", 10002),
            ("Zepto delivery", 10005),
            ("Andrew Ng data-centric", 10007)
        ]
        
        for query, expected_note in test_queries:
            print(f"\n📝 Query: '{query}' (expecting note {expected_note})")
            print("-" * 40)
            
            # Create messages
            messages = [{"role": "user", "content": query}]
            
            # Run RAG
            result = await rag.process_rag_request(
                messages=messages,
                user_id=10001,  # Test user
                top_k=5
            )
            
            print(f"Result type: {type(result)}")
            print(f"Chunks found: {len(result.chunks) if hasattr(result, 'chunks') else 'N/A'}")
            
            if hasattr(result, 'chunks') and result.chunks:
                for i, chunk in enumerate(result.chunks[:3], 1):
                    print(f"\n  Chunk {i}:")
                    print(f"    Type ID: {chunk.type_id}")
                    print(f"    Section ID: {chunk.section_id}")
                    print(f"    Chunk ID: {getattr(chunk, 'chunk_id', 'N/A')}")
                    print(f"    Text preview: {chunk.chunk_text[:100]}...")
                    print(f"    Distance: {getattr(chunk, 'distance', 'N/A')}")
            else:
                print("  ❌ No chunks found!")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_rag_simple())