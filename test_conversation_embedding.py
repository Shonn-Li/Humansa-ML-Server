#!/usr/bin/env python3
"""
Test conversation embedding creation
"""
import os
import sys
import asyncio

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Set test environment
os.environ['DB_PASSWORD'] = '12931'
os.environ['DB_PORT'] = '5454'
os.environ['DB_HOST'] = 'localhost'
os.environ['DB_USERNAME'] = 'postgres'
os.environ['DB_ACTIVE_DATABASE'] = 'youwoai_test'

async def test_embedding():
    from chat.embedding.conversation_embedder import ConversationEmbedder
    
    print("=" * 60)
    print("TESTING CONVERSATION EMBEDDING")
    print("=" * 60)
    
    embedder = ConversationEmbedder()
    
    # Test with our test conversation
    print("\n1. Testing with conversation 9999:")
    success = await embedder.create_conversation_embedding(9999)
    print(f"   Result: {'Success' if success else 'Failed'}")
    
    # Test with a non-existent conversation
    print("\n2. Testing with non-existent conversation 648:")
    success = await embedder.create_conversation_embedding(648)
    print(f"   Result: {'Success' if success else 'Failed'}")
    
    # Test with an existing conversation
    print("\n3. Testing with existing conversation 10001:")
    success = await embedder.create_conversation_embedding(10001)
    print(f"   Result: {'Success' if success else 'Failed'}")

if __name__ == "__main__":
    asyncio.run(test_embedding())