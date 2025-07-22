#!/usr/bin/env python3
"""
Test just the multi-agent case to verify the fix
"""

import asyncio
import json
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

# Set up TEST ENVIRONMENT
os.environ['DATABASE_URL'] = 'postgresql://postgres:12931@localhost:5454/youwoai_test'
os.environ['PUBLIC_ENV'] = 'test'

# Suppress verbose logging
import logging
for logger_name in ["httpx", "httpcore", "asyncio", "chat", "aiohttp", "urllib3"]:
    logging.getLogger(logger_name).setLevel(logging.WARNING)


async def test_multi_agent():
    """Test multi-agent with context + attachment"""
    from chat.endpoints.multi_agent_endpoint_v2 import MultiAgentChatEndpointV2
    endpoint = MultiAgentChatEndpointV2()
    
    print("\n" + "="*60)
    print("TESTING MULTI-AGENT (Context + Attachment)")
    print("="*60)
    
    request = {
        "model": "gpt-4.1-nano",
        "messages": [{"role": "user", "content": "Compare this paper with my notes on PARL"}],
        "attachments": ["https://arxiv.org/pdf/2505.18499.pdf"],
        "stream": True,
        "enable_citations": True,
        "user_id": 10001
    }
    
    print("\nRunning test...")
    print("-" * 60)
    
    try:
        # Track outputs
        tool_calls = []
        response_text = ""
        citations = []
        
        response = await endpoint.handle_request(request)
        
        async for event in response:
            event_type = event.get("type", "")
            
            if event_type == "response.output_item.added":
                item = event.get("item", {})
                if item.get("type", "").endswith("_call"):
                    tool_calls.append(item.get("type"))
                    print(f"Tool triggered: {item.get('type')}")
            
            elif event_type == "response.output_text.delta":
                response_text += event.get("delta", "")
            
            elif event_type == "response.output_text.annotation.added":
                ann = event.get("annotation", {})
                citations.append(f"[{ann.get('text')}] {ann.get('title', 'N/A')}")
        
        print(f"\nTools used: {', '.join(tool_calls)}")
        print(f"Citations: {len(citations)}")
        
        print("\nResponse:")
        print("-" * 60)
        print(response_text[:500] + "..." if len(response_text) > 500 else response_text)
        print("-" * 60)
        
        # Check if response mentions both PARL and the paper
        has_parl = "PARL" in response_text or "Predictability-Aware" in response_text
        has_paper = "G1" in response_text or "graph" in response_text.lower()
        mentions_comparison = any(word in response_text.lower() for word in ["compare", "comparison", "both", "while", "whereas", "different", "similar"])
        
        print("\nValidation:")
        print(f"- Uses both agents: {'✅' if all(t in tool_calls for t in ['context_search_call', 'file_search_call']) else '❌'}")
        print(f"- Mentions PARL: {'✅' if has_parl else '❌'}")
        print(f"- Mentions paper: {'✅' if has_paper else '❌'}")
        print(f"- Makes comparison: {'✅' if mentions_comparison else '❌'}")
        print(f"- Has citations: {'✅' if citations else '❌'}")
        
        if citations:
            print(f"\nFirst 3 citations:")
            for cit in citations[:3]:
                print(f"  {cit}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*60)


if __name__ == "__main__":
    asyncio.run(test_multi_agent())