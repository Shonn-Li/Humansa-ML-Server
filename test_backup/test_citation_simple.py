#!/usr/bin/env python3

"""
Simple test to verify citation functionality
"""

import asyncio
import logging
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import directly
from src.chat.endpoints.multi_agent_endpoint_v2 import MultiAgentChatEndpointV2

async def test_direct_citation():
    """Test citation functionality directly."""
    logger.info("🧪 Testing Citation Functionality Directly")
    logger.info("="*60)
    
    # Create endpoint
    endpoint = MultiAgentChatEndpointV2()
    
    # Create a test request
    request = {
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "user", 
                "content": "What is machine learning?"
            }
        ],
        "stream": True,
        "temperature": 0.7,
        "enable_citations": True
    }
    
    # Create mock context with sources
    context = {
        "rag_agent": {
            "status": "success",
            "sources": [
                {
                    "note_id": "note123",
                    "node_id": "node456",
                    "chunk_id": "chunk789",
                    "title": "Introduction to Machine Learning",
                    "content": "Machine learning is a subset of artificial intelligence that enables systems to learn and improve from experience without being explicitly programmed. It focuses on developing computer programs that can access data and use it to learn for themselves.",
                    "score": 0.95
                },
                {
                    "note_id": "note124",
                    "node_id": "node457",
                    "chunk_id": "chunk790",
                    "title": "Types of Machine Learning",
                    "content": "There are three main types of machine learning: supervised learning where models learn from labeled data, unsupervised learning where models find patterns in unlabeled data, and reinforcement learning where models learn through trial and error.",
                    "score": 0.92
                }
            ]
        }
    }
    
    # Test Response Agent directly
    response_agent = endpoint.agents["response"]
    result = await response_agent.run(request, context)
    
    logger.info(f"\n📝 Response: {result.get('response', '')[:200]}...")
    logger.info(f"📚 Sources found: {len(result.get('sources', []))}")
    logger.info(f"📍 Annotations found: {len(result.get('annotations', []))}")
    logger.info(f"✅ Citations enabled: {result.get('metadata', {}).get('citations_enabled')}")
    
    # Check response for citation markers
    import re
    response_text = result.get('response', '')
    citation_pattern = re.compile(r'\[(\d+)\]')
    citation_markers = citation_pattern.findall(response_text)
    logger.info(f"🔍 Citation markers in response: {citation_markers}")
    
    # Show annotations
    for i, ann in enumerate(result.get('annotations', []), 1):
        logger.info(f"\nAnnotation {i}:")
        logger.info(f"  Text: {ann.get('text')}")
        logger.info(f"  Position: {ann.get('start_index')}-{ann.get('end_index')}")
        logger.info(f"  URL: {ann.get('url')}")
        
        # Verify position
        start = ann.get('start_index', 0)
        end = ann.get('end_index', 0)
        if 0 <= start < len(response_text) and start < end <= len(response_text):
            actual_text = response_text[start:end]
            logger.info(f"  Actual text: '{actual_text}'")
            if actual_text == ann.get('text'):
                logger.info("  ✅ Position correct!")
            else:
                logger.error(f"  ❌ Position mismatch! Expected '{ann.get('text')}'")


async def main():
    """Run tests."""
    await test_direct_citation()


if __name__ == "__main__":
    asyncio.run(main())