#\!/usr/bin/env python3
"""Test single RAG query with detailed logging"""

import asyncio
import json
import sys
import os
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

# Set up TEST ENVIRONMENT
os.environ['DATABASE_URL'] = 'postgresql://postgres:12931@localhost:5454/youwoai_test'
os.environ['PUBLIC_ENV'] = 'test'

async def test_single_rag():
    """Test a single RAG query with detailed output"""
    
    print("\n" + "="*80)
    print("SINGLE RAG TEST - DETAILED OUTPUT")
    print("="*80)
    
    # Import endpoint
    from chat.endpoints.multi_agent_endpoint_v2 import MultiAgentChatEndpointV2
    endpoint = MultiAgentChatEndpointV2()
    
    request = {
        "model": "gpt-4o",
        "messages": [{"role": "user", "content": "Search my notes for information about PARL and predictable AI"}],
        "stream": True,
        "enable_citations": True,
        "user_id": 10001
    }
    
    print("Request:")
    print(json.dumps(request, indent=2))
    print("\n" + "-"*80 + "\n")
    
    print("Events:")
    
    response = await endpoint.handle_request(request)
    
    events = []
    response_text = ""
    
    async for event in response:
        events.append(event)
        event_type = event.get("type", "")
        
        # Print key events
        if event_type in ["response.output_item.added", "response.output_text.annotation.added"]:
            print(f"\n{event_type}:")
            print(json.dumps(event, indent=2))
        
        # Collect response text
        if event_type == "response.output_text.delta":
            response_text += event.get("delta", "")
    
    print("\n" + "-"*80 + "\n")
    print("Full Response:")
    print(response_text)
    
    print("\n" + "-"*80 + "\n")
    print("Event Summary:")
    event_types = {}
    for event in events:
        event_type = event.get("type", "unknown")
        event_types[event_type] = event_types.get(event_type, 0) + 1
    
    for event_type, count in sorted(event_types.items()):
        print(f"  {event_type}: {count}")
    
    # Count output items and citations
    output_items = [e for e in events if e.get("type") == "response.output_item.added"]
    citations = [e for e in events if e.get("type") == "response.output_text.annotation.added"]
    
    print(f"\nOutput Items: {len(output_items)}")
    print(f"Citations: {len(citations)}")

if __name__ == "__main__":
    asyncio.run(test_single_rag())
