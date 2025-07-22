#!/usr/bin/env python3
"""
Final verification that multi-agent works correctly with proper context
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


async def test_multi_agent_final():
    """Final test with better prompt"""
    from chat.endpoints.multi_agent_endpoint_v2 import MultiAgentChatEndpointV2
    endpoint = MultiAgentChatEndpointV2()
    
    print("\n" + "="*80)
    print("FINAL MULTI-AGENT VERIFICATION")
    print("="*80)
    
    # More specific prompt that should force using both contexts
    request = {
        "model": "gpt-4.1-nano",
        "messages": [{
            "role": "user", 
            "content": "Based on my saved notes about PARL and this attached paper, list 3 key differences between them"
        }],
        "attachments": ["https://arxiv.org/pdf/2505.18499.pdf"],
        "stream": True,
        "enable_citations": True,
        "user_id": 10001
    }
    
    print("\nRunning test with more specific prompt...")
    print("-" * 80)
    
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
                    print(f"✓ Tool triggered: {item.get('type')}")
            
            elif event_type == "response.output_text.delta":
                response_text += event.get("delta", "")
            
            elif event_type == "response.output_text.annotation.added":
                ann = event.get("annotation", {})
                citations.append(f"[{ann.get('text')}] {ann.get('title', 'N/A')}")
        
        print(f"\nTools used: {', '.join(tool_calls)}")
        print(f"Citations: {len(citations)}")
        
        print("\nResponse:")
        print("-" * 80)
        print(response_text)
        print("-" * 80)
        
        # Detailed validation
        has_parl = "PARL" in response_text or "Predictability-Aware" in response_text
        has_paper = "G1" in response_text or "graph" in response_text.lower() or "paper" in response_text.lower()
        has_differences = any(word in response_text.lower() for word in ["difference", "differ", "contrast", "unlike", "however", "while"])
        has_numbered_list = any(f"{i}." in response_text or f"{i})" in response_text for i in range(1, 4))
        
        print("\nValidation:")
        print(f"✓ Uses both agents: {'✅' if all(t in tool_calls for t in ['context_search_call', 'file_search_call']) else '❌'}")
        print(f"✓ Mentions PARL: {'✅' if has_parl else '❌'}")
        print(f"✓ Mentions paper content: {'✅' if has_paper else '❌'}")
        print(f"✓ Lists differences: {'✅' if has_differences else '❌'}")
        print(f"✓ Has numbered list: {'✅' if has_numbered_list else '❌'}")
        print(f"✓ Has citations: {'✅' if citations else '❌'}")
        
        if citations:
            print(f"\nCitations found ({len(citations)}):")
            for cit in citations[:5]:
                print(f"  {cit}")
        
        # Check if response actually uses content from both sources
        success = all([
            all(t in tool_calls for t in ['context_search_call', 'file_search_call']),
            has_parl,
            has_paper or has_differences,
            len(response_text) > 100
        ])
        
        print(f"\n{'✅ TEST PASSED' if success else '❌ TEST FAILED'}")
        
        if not success:
            print("\nIssues:")
            if not all(t in tool_calls for t in ['context_search_call', 'file_search_call']):
                print("- Not all agents were triggered")
            if not has_parl:
                print("- Response doesn't mention PARL")
            if not (has_paper or has_differences):
                print("- Response doesn't use paper content or list differences")
            if len(response_text) <= 100:
                print("- Response is too short")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*80)


if __name__ == "__main__":
    asyncio.run(test_multi_agent_final())