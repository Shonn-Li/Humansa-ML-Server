#!/usr/bin/env python3
"""
Test citation tracking and annotation events
"""

import asyncio
import httpx
import json
from typing import Dict, List, Any

async def test_citation_tracking():
    """Test citation position tracking"""
    client = httpx.AsyncClient(timeout=30.0)
    
    # Test with web search - should generate citations
    request = {
        "messages": [{"role": "user", "content": "What are the benefits of machine learning in healthcare? Cite sources."}],
        "user_id": 10001,
        "model": "gpt-4.1-nano",
        "stream": True,
        "enable_citations": True
    }
    
    print("Testing Citation Tracking")
    print("="*60)
    print("Request: Web search query asking for sources")
    print()
    
    response_text = ""
    citations = []
    metadata = {}
    
    async with client.stream("POST", "http://localhost:5002/v1/multi-agent/response", json=request) as response:
        async for line in response.aiter_lines():
            if line.startswith("data: "):
                data_str = line[6:]
                if data_str == "[DONE]":
                    break
                    
                try:
                    event = json.loads(data_str)
                    event_type = event.get("type", "")
                    
                    # Collect response text
                    if event_type == "response.output_text.delta":
                        response_text += event.get("delta", "")
                        
                    # Look for citation annotations
                    elif event_type == "response.output_text.annotation.added":
                        ann = event.get("annotation", {})
                        citations.append(ann)
                        print(f"📌 Citation Annotation Found:")
                        print(f"   Text: {ann.get('text', 'N/A')}")
                        print(f"   Position: {ann.get('start_index', 0)}-{ann.get('end_index', 0)}")
                        print(f"   URL: {ann.get('url', 'N/A')}")
                        print(f"   Title: {ann.get('title', 'N/A')}")
                        print()
                        
                    # Collect metadata
                    elif event_type == "response.usage" and "metadata" in event:
                        metadata = event.get("metadata", {})
                        
                except json.JSONDecodeError:
                    pass
    
    print("\nRESULTS:")
    print("-"*60)
    print(f"Response length: {len(response_text)} chars")
    print(f"Citations found in annotations: {len(citations)}")
    
    # Check for citation markers in text
    import re
    citation_pattern = re.compile(r'\[(\d+)\]')
    text_citations = citation_pattern.findall(response_text)
    print(f"Citation markers in text: {text_citations}")
    
    # Check metadata for sources
    if metadata.get("agent_results", {}).get("citation_agent"):
        citation_data = metadata["agent_results"]["citation_agent"].get("data", {})
        sources = citation_data.get("citations", {}).get("sources", [])
        print(f"Sources in metadata: {len(sources)}")
        for i, source in enumerate(sources[:3]):
            print(f"  [{i+1}] {source.get('title', 'N/A')}")
            print(f"      URL: {source.get('url', 'N/A')}")
    
    print("\nRESPONSE TEXT (first 500 chars):")
    print("-"*60)
    print(response_text[:500] + "..." if len(response_text) > 500 else response_text)
    
    await client.aclose()

if __name__ == "__main__":
    asyncio.run(test_citation_tracking())