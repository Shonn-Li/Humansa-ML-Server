#!/usr/bin/env python3

"""
Test Citation Functionality in Multi-Agent Streaming
"""

import asyncio
import json
import logging
from typing import Dict, Any, List
import httpx
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Test configuration
API_URL = "http://localhost:5002/v1/chat/completions"
API_KEY = "test-key"

async def test_citation_with_mock_sources():
    """Test citation functionality with mock sources in context."""
    logger.info("🧪 Testing Citation Functionality with Mock Sources")
    logger.info("="*60)
    
    # Create a test request that should trigger citations
    request = {
        "model": "gpt-4.1-nano",
        "messages": [
            {
                "role": "user", 
                "content": "Tell me about machine learning algorithms based on the provided sources."
            }
        ],
        "stream": True,
        "temperature": 0.7,
        "enable_citations": True,  # Explicitly enable citations
        # Add mock context to simulate having sources
        "mock_context": {
            "rag_agent": {
                "status": "success",
                "sources": [
                    {
                        "note_id": "note123",
                        "node_id": "node456",
                        "chunk_id": "chunk789",
                        "title": "Introduction to Machine Learning",
                        "content": "Machine learning is a subset of artificial intelligence that enables systems to learn from data. There are three main types: supervised learning, unsupervised learning, and reinforcement learning.",
                        "score": 0.95
                    },
                    {
                        "note_id": "note124",
                        "node_id": "node457",
                        "chunk_id": "chunk790",
                        "title": "Deep Learning Fundamentals",
                        "content": "Deep learning uses neural networks with multiple layers. Convolutional Neural Networks (CNNs) are particularly effective for image recognition tasks.",
                        "score": 0.92
                    }
                ]
            },
            "web_search_agent": {
                "status": "success",
                "results": [
                    {
                        "title": "Recent Advances in ML - 2024",
                        "link": "https://example.com/ml-advances",
                        "snippet": "Transformer models have revolutionized natural language processing. GPT and BERT architectures have shown remarkable performance."
                    }
                ]
            }
        }
    }
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    events = []
    annotations = []
    response_text = ""
    
    try:
        async with httpx.AsyncClient() as client:
            async with client.stream('POST', API_URL, json=request, headers=headers, timeout=30.0) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        
                        try:
                            event = json.loads(data_str)
                            events.append(event)
                            
                            # Collect response text
                            if event["type"] == "response.output_text.delta":
                                response_text += event.get("delta", "")
                            
                            # Collect annotations
                            if event["type"] == "response.output_text.annotation.added":
                                annotation = event.get("annotation", {})
                                annotations.append(annotation)
                                logger.info(f"📍 Citation found: {annotation.get('text')} at position {annotation.get('start_index')}-{annotation.get('end_index')}")
                                logger.info(f"   Source: {annotation.get('title')} ({annotation.get('type')})")
                                if annotation.get("metadata"):
                                    logger.info(f"   Metadata: {annotation['metadata']}")
                            
                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to parse event: {data_str[:100]}... - {e}")
    
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        return False
    
    # Analyze results
    logger.info("\n" + "="*60)
    logger.info("📊 Test Results:")
    logger.info(f"Total events: {len(events)}")
    logger.info(f"Response length: {len(response_text)} characters")
    logger.info(f"Citations found: {len(annotations)}")
    
    if annotations:
        logger.info("\n📚 Citation Details:")
        for i, ann in enumerate(annotations, 1):
            logger.info(f"\nCitation {i}:")
            logger.info(f"  Text: {ann.get('text')}")
            logger.info(f"  Position: {ann.get('start_index')}-{ann.get('end_index')}")
            logger.info(f"  URL: {ann.get('url')}")
            logger.info(f"  Title: {ann.get('title')}")
            logger.info(f"  Type: {ann.get('type')}")
            
            # Extract citation from response
            start = ann.get('start_index', 0)
            end = ann.get('end_index', 0)
            if 0 <= start < len(response_text) and start < end <= len(response_text):
                actual_text = response_text[start:end]
                logger.info(f"  Actual text at position: '{actual_text}'")
                if actual_text != ann.get('text'):
                    logger.warning(f"  ⚠️  Position mismatch! Expected '{ann.get('text')}' but found '{actual_text}'")
    
    # Check if response contains citation markers
    import re
    citation_pattern = re.compile(r'\[(\d+)\]')
    citation_markers = citation_pattern.findall(response_text)
    logger.info(f"\n🔍 Citation markers in response: {citation_markers}")
    
    # Success criteria
    success = len(annotations) > 0 and len(citation_markers) > 0
    
    if success:
        logger.info("\n✅ Citation test PASSED!")
    else:
        logger.error("\n❌ Citation test FAILED!")
        if not annotations:
            logger.error("   - No citation annotations found")
        if not citation_markers:
            logger.error("   - No citation markers [1], [2] found in response")
    
    return success


async def main():
    """Run citation tests."""
    logger.info("🚀 Starting Citation Streaming Tests")
    logger.info("="*60)
    
    # Test with mock sources
    success = await test_citation_with_mock_sources()
    
    logger.info("\n" + "="*60)
    if success:
        logger.info("✅ All citation tests PASSED!")
    else:
        logger.error("❌ Some citation tests FAILED!")


if __name__ == "__main__":
    # Start the test server first
    import subprocess
    import sys
    import os
    
    # Add parent directory to path
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # Start server
    server_process = subprocess.Popen(
        [sys.executable, "-m", "chat.endpoints.multi_agent_endpoint_v2", "--port", "5002"],
        env={**os.environ, "PYTHONPATH": os.path.dirname(os.path.dirname(os.path.abspath(__file__)))},
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for server to start
    logger.info("⏳ Waiting for server to start...")
    time.sleep(3)
    
    try:
        # Run tests
        asyncio.run(main())
    finally:
        # Stop server
        server_process.terminate()
        server_process.wait()
        logger.info("🛑 Server stopped")