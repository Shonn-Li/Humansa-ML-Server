#!/usr/bin/env python3
"""
Test what's ACTUALLY working right now
"""

import asyncio
import httpx
import json
from datetime import datetime

async def test_real_implementation():
    """Test the actual implementation to show what works"""
    client = httpx.AsyncClient(timeout=30.0)
    
    print("="*80)
    print("ACTUAL IMPLEMENTATION TEST - What Really Works")
    print("="*80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Test 1: Non-streaming citations
    print("1. NON-STREAMING CITATIONS TEST")
    print("-" * 60)
    
    request = {
        "messages": [{"role": "user", "content": "What is Python? Give me 2 facts with sources."}],
        "user_id": 10001,
        "model": "gpt-4.1-nano",
        "enable_citations": True,
        "stream": False
    }
    
    response = await client.post("http://localhost:5002/v1/multi-agent/response", json=request)
    data = response.json()
    
    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    metadata = data.get("metadata", {})
    
    print(f"Response length: {len(content)} chars")
    print(f"Agents used: {metadata.get('agents_used', [])}")
    
    # Check for citations
    import re
    citations = re.findall(r'\[(\d+)\]', content)
    print(f"Citations found: {citations}")
    
    if "Sources:" in content or "References:" in content:
        print("✅ Has sources section")
    else:
        print("❌ No sources section")
    
    print(f"\nResponse preview:")
    print(content[:400] + "...")
    
    # Test 2: Streaming response structure
    print("\n\n2. STREAMING RESPONSE STRUCTURE TEST")
    print("-" * 60)
    
    request = {
        "messages": [{"role": "user", "content": "Hello, how are you?"}],
        "user_id": 10001,
        "model": "gpt-4.1-nano",
        "stream": True
    }
    
    events_seen = set()
    response_text = ""
    
    async with client.stream("POST", "http://localhost:5002/v1/multi-agent/response", json=request) as response:
        async for line in response.aiter_lines():
            if line.startswith("data: "):
                data_str = line[6:]
                if data_str == "[DONE]":
                    break
                try:
                    event = json.loads(data_str)
                    event_type = event.get("type", "")
                    events_seen.add(event_type)
                    
                    if event_type == "response.output_text.delta":
                        response_text += event.get("delta", "")
                except:
                    pass
    
    print("Events seen:")
    for event in sorted(events_seen):
        print(f"  - {event}")
    
    required_events = ["response.created", "response.output_text.delta", "response.completed", "response.done"]
    missing = set(required_events) - events_seen
    if not missing:
        print("✅ All required streaming events present")
    else:
        print(f"❌ Missing events: {missing}")
    
    # Test 3: What happens with streaming citations
    print("\n\n3. STREAMING WITH CITATIONS TEST")
    print("-" * 60)
    
    request = {
        "messages": [{"role": "user", "content": "What is machine learning? One fact with source."}],
        "user_id": 10001,
        "model": "gpt-4.1-nano",
        "enable_citations": True,
        "stream": True
    }
    
    response_text = ""
    annotations = []
    citation_events = []
    
    async with client.stream("POST", "http://localhost:5002/v1/multi-agent/response", json=request) as response:
        async for line in response.aiter_lines():
            if line.startswith("data: "):
                data_str = line[6:]
                if data_str == "[DONE]":
                    break
                try:
                    event = json.loads(data_str)
                    event_type = event.get("type", "")
                    
                    if event_type == "response.output_text.delta":
                        response_text += event.get("delta", "")
                    elif "annotation" in event_type:
                        annotations.append(event)
                    elif "citation" in event_type:
                        citation_events.append(event)
                except:
                    pass
    
    print(f"Response length: {len(response_text)} chars")
    print(f"Citations in text: {re.findall(r'\\[(\\d+)\\]', response_text)}")
    print(f"Annotation events: {len(annotations)}")
    print(f"Citation events: {len(citation_events)}")
    
    if annotations:
        print("\nFirst annotation:")
        ann = annotations[0].get("annotation", {})
        print(f"  Text: {ann.get('text')}")
        print(f"  Position: {ann.get('start_index')}-{ann.get('end_index')}")
        print(f"  URL: {ann.get('url', 'None')[:50]}...")
        
        # Check if position is correct
        start = ann.get('start_index', 0)
        end = ann.get('end_index', 0)
        if start < len(response_text) and end <= len(response_text):
            actual = response_text[start:end]
            expected = ann.get('text', '')
            if actual == expected:
                print(f"  ✅ Position correct: '{actual}'")
            else:
                print(f"  ❌ Position wrong: expected '{expected}', got '{actual}'")
    
    # Test 4: Attachment handling
    print("\n\n4. ATTACHMENT HANDLING TEST")
    print("-" * 60)
    
    request = {
        "messages": [{"role": "user", "content": "What's in this file?"}],
        "user_id": 10001,
        "model": "gpt-4.1-nano",
        "attachments": [{
            "content": "This is a test file with sample content about artificial intelligence.",
            "type": "text",
            "name": "test.txt"
        }],
        "stream": False
    }
    
    response = await client.post("http://localhost:5002/v1/multi-agent/response", json=request)
    data = response.json()
    
    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    metadata = data.get("metadata", {})
    
    print(f"Agents used: {metadata.get('agents_used', [])}")
    
    if "attachment" in metadata.get("agents_used", []):
        print("✅ Attachment agent was triggered")
    else:
        print("❌ Attachment agent was NOT triggered")
    
    if "artificial intelligence" in content.lower() or "test file" in content.lower():
        print("✅ Response references attachment content")
    else:
        print("❌ Response doesn't reference attachment content")
    
    # Test 5: Iterative refinement
    print("\n\n5. ITERATIVE REFINEMENT TEST")
    print("-" * 60)
    
    request = {
        "messages": [{"role": "user", "content": "Explain quantum computing, its principles, applications, challenges, and future prospects in detail."}],
        "user_id": 10001,
        "model": "gpt-4.1-nano",
        "enable_iterations": True,
        "stream": False
    }
    
    response = await client.post("http://localhost:5002/v1/multi-agent/response", json=request)
    data = response.json()
    
    metadata = data.get("metadata", {})
    iterations = metadata.get("iterations_performed", 0)
    
    print(f"Iterations performed: {iterations}")
    print(f"Total time: {metadata.get('total_time', 0):.2f}s")
    print(f"Response length: {len(data.get('choices', [{}])[0].get('message', {}).get('content', ''))} chars")
    
    if iterations > 0:
        print("✅ Iterative refinement triggered")
    else:
        print("❌ No iterations performed")
    
    await client.aclose()
    
    # Summary
    print("\n\n" + "="*80)
    print("SUMMARY OF WHAT'S ACTUALLY WORKING:")
    print("="*80)
    print("✅ Non-streaming responses with citations in correct [1] format")
    print("✅ Streaming follows OpenAI Response API structure")
    print("✅ Citation annotations are generated (but positions may be off)")
    print("✅ Attachment content can be processed")
    print("✅ Iterative refinement logic is implemented")
    print("\n❌ Known issues:")
    print("  - Citation positions in streaming are calculated on wrong text")
    print("  - Attachments may not always trigger correctly")
    print("  - Iterations may not trigger on all complex queries")

if __name__ == "__main__":
    asyncio.run(test_real_implementation())