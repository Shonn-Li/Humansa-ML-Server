#!/usr/bin/env python3
"""
Test citation streaming annotations
"""

import asyncio
import httpx
import json
from typing import Dict, List, Any
from datetime import datetime

async def test_citation_streaming():
    """Test citation annotation streaming events"""
    client = httpx.AsyncClient(timeout=30.0)
    
    print("="*80)
    print("CITATION STREAMING TEST")
    print("="*80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Simple request that should get citations quickly
    request = {
        "messages": [{
            "role": "user", 
            "content": "What is OpenAI's GPT-4? Give me one sentence with a source."
        }],
        "user_id": 10001,
        "model": "gpt-4.1-nano",
        "enable_citations": True,
        "stream": True
    }
    
    print("Request: Simple query for quick citation test")
    print()
    
    events = []
    annotation_events = []
    citation_events = []
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
                    events.append(event)
                    
                    # Collect response text
                    if event_type == "response.output_text.delta":
                        response_text += event.get("delta", "")
                    
                    # Look for annotation events
                    if "annotation" in event_type:
                        annotation_events.append(event)
                        print(f"📌 Annotation Event: {event_type}")
                        
                        if event_type == "response.output_text.annotation.added":
                            ann = event.get("annotation", {})
                            print(f"   Citation: {ann.get('text', 'N/A')}")
                            print(f"   Position: {ann.get('start_index', 0)}-{ann.get('end_index', 0)}") 
                            print(f"   URL: {ann.get('url', 'N/A')}")
                            print(f"   Title: {ann.get('title', 'N/A')}")
                            print()
                    
                    # Look for citation events
                    if "citation" in event_type.lower() or event_type == "response.citations":
                        citation_events.append(event)
                        print(f"📚 Citation Event: {event_type}")
                        if "citations" in event:
                            cits = event.get("citations", [])
                            print(f"   Found {len(cits)} citations")
                            
                except json.JSONDecodeError:
                    pass
    
    print("\n" + "-"*80)
    print("RESULTS:")
    print(f"Total events: {len(events)}")
    print(f"Annotation events: {len(annotation_events)}")
    print(f"Citation events: {len(citation_events)}")
    print(f"Response length: {len(response_text)} chars")
    
    # Check for citations in text
    import re
    citation_pattern = re.compile(r'\[(\d+)\]')
    text_citations = citation_pattern.findall(response_text)
    print(f"Citation markers in text: {text_citations}")
    
    print(f"\nResponse text:")
    print(response_text)
    
    # Verify annotations match citations in text
    if annotation_events and text_citations:
        print("\n✅ Citations are being streamed as annotations!")
    elif text_citations and not annotation_events:
        print("\n❌ Citations found in text but no annotation events!")
    else:
        print("\n⚠️  No citations found")
    
    await client.aclose()

if __name__ == "__main__":
    asyncio.run(test_citation_streaming())