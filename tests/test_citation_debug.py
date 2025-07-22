#!/usr/bin/env python3
"""
Debug why citations are empty
"""

import asyncio
import httpx
import json
from datetime import datetime

async def test_citation_flow():
    """Test the complete citation flow"""
    client = httpx.AsyncClient(timeout=60.0)
    
    print("="*80)
    print("CITATION DEBUG TEST")
    print("="*80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Test 1: Simple web search that should generate citations
    print("TEST 1: Web Search with Citations")
    print("-"*40)
    
    request = {
        "messages": [{
            "role": "user", 
            "content": "What are the latest AI breakthroughs in 2024? Please cite your sources."
        }],
        "user_id": 10001,
        "model": "gpt-4.1-nano",
        "enable_citations": True,
        "stream": False
    }
    
    response = await client.post("http://localhost:5002/v1/multi-agent/response", json=request)
    data = response.json()
    
    print(f"Response status: {response.status_code}")
    
    # Check response
    response_text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    print(f"\nResponse text ({len(response_text)} chars):")
    print(response_text[:500] + "..." if len(response_text) > 500 else response_text)
    
    # Check for citation markers
    import re
    citation_pattern = re.compile(r'\[(\d+)\]')
    citations_in_text = citation_pattern.findall(response_text)
    print(f"\nCitation markers found in text: {citations_in_text}")
    
    # Check metadata
    metadata = data.get("metadata", {})
    print(f"\nMetadata keys: {list(metadata.keys())}")
    
    # Check agent results
    agent_results = metadata.get("agent_results", {})
    print(f"Agents used: {list(agent_results.keys())}")
    
    # Check citation agent specifically
    if "citation_agent" in agent_results:
        citation_data = agent_results["citation_agent"].get("data", {})
        print(f"\nCitation agent data keys: {list(citation_data.keys())}")
        
        citations = citation_data.get("citations", {})
        if isinstance(citations, dict):
            sources = citations.get("sources", [])
            print(f"Number of sources: {len(sources)}")
            for i, source in enumerate(sources[:3]):
                print(f"\nSource {i+1}:")
                print(f"  Title: {source.get('title', 'N/A')}")
                print(f"  URL: {source.get('url', 'N/A')}")
                print(f"  Type: {source.get('source_type', 'N/A')}")
        else:
            print(f"Citations type: {type(citations)}")
    else:
        print("❌ Citation agent not found in results!")
    
    # Test 2: Streaming to check citation events
    print("\n\n" + "="*80)
    print("TEST 2: Streaming Citation Events")
    print("-"*40)
    
    request["stream"] = True
    
    citation_events = []
    response_text_stream = ""
    
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
                        response_text_stream += event.get("delta", "")
                    
                    # Look for citation events
                    if "citation" in event_type or "annotation" in event_type:
                        citation_events.append(event)
                        print(f"📌 Citation event: {event_type}")
                        if event_type == "response.output_text.annotation.added":
                            ann = event.get("annotation", {})
                            print(f"   - Text: {ann.get('text', 'N/A')}")
                            print(f"   - Position: {ann.get('start_index', 0)}-{ann.get('end_index', 0)}")
                            print(f"   - URL: {ann.get('url', 'N/A')}")
                    
                    # Check for citation agent output
                    if event_type == "response.output_item.added":
                        item = event.get("item", {})
                        if "cit_" in item.get("id", ""):
                            print(f"📝 Citation agent item: {item.get('id')}")
                            
                except json.JSONDecodeError:
                    pass
    
    print(f"\nTotal citation events: {len(citation_events)}")
    print(f"Response length: {len(response_text_stream)} chars")
    
    # Check for citations in streamed text
    citations_in_stream = citation_pattern.findall(response_text_stream)
    print(f"Citations in streamed text: {citations_in_stream}")
    
    # Test 3: Check if web search is returning sources
    print("\n\n" + "="*80)
    print("TEST 3: Direct Agent Check")
    print("-"*40)
    
    # Try a simple request to ensure web search returns sources
    request_simple = {
        "messages": [{
            "role": "user", 
            "content": "latest news about OpenAI"
        }],
        "user_id": 10001,
        "model": "gpt-4.1-nano",
        "enable_citations": True,
        "stream": False
    }
    
    response = await client.post("http://localhost:5002/v1/multi-agent/response", json=request_simple)
    data = response.json()
    
    metadata = data.get("metadata", {})
    agent_results = metadata.get("agent_results", {})
    
    # Check web search agent
    if "web_search_agent" in agent_results:
        ws_data = agent_results["web_search_agent"].get("data", {})
        print(f"Web search agent data keys: {list(ws_data.keys())}")
        
        sources = ws_data.get("sources", [])
        print(f"Web search returned {len(sources)} sources")
        if sources:
            print("✅ Web search is returning sources")
        else:
            print("❌ Web search returned no sources!")
    else:
        print("❌ Web search agent not triggered!")
    
    await client.aclose()

if __name__ == "__main__":
    asyncio.run(test_citation_flow())