#!/usr/bin/env python3
"""
Test DeepSeek R1 <think> tag extraction specifically
"""

import asyncio
import json
import sys
import os
import re

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

# Set up TEST ENVIRONMENT
os.environ['DATABASE_URL'] = 'postgresql://postgres:12931@localhost:5454/youwoai_test'
os.environ['PUBLIC_ENV'] = 'test'

# Suppress verbose logging
import logging
for logger_name in ["httpx", "httpcore", "asyncio", "chat", "aiohttp"]:
    logging.getLogger(logger_name).setLevel(logging.WARNING)


async def test_think_tag_extraction():
    """Test extraction of <think> tags from DeepSeek R1 responses"""
    print("="*80)
    print("DEEPSEEK R1 <THINK> TAG EXTRACTION TEST")
    print("="*80)
    
    try:
        # Import endpoint
        from chat.endpoints.multi_agent_endpoint_v2 import MultiAgentChatEndpointV2
        endpoint = MultiAgentChatEndpointV2()
        
        # Test request that should trigger <think> tags
        request = {
            "model": "DeepSeek-R1",
            "messages": [{
                "role": "user", 
                "content": "What's 2+2? Think through this step by step."
            }],
            "stream": True,
            "user_id": 10001
        }
        
        print(f"🎯 Testing <think> tag extraction...")
        print(f"Looking for reasoning content in output deltas...")
        print("-" * 80)
        
        # Run request
        response = await endpoint.handle_request(request)
        
        # Track all content
        all_deltas = []
        think_content_found = []
        
        if hasattr(response, '__aiter__'):
            async for event in response:
                event_type = event.get("type", "unknown")
                
                if event_type == "response.output_text.delta":
                    delta = event.get("delta", "")
                    if delta:
                        all_deltas.append(delta)
                        
                        # Test our extraction logic
                        think_matches = re.findall(r'<think>(.*?)</think>', delta, re.DOTALL)
                        for match in think_matches:
                            think_content_found.append(match.strip())
                            print(f"🧠 FOUND THINK CONTENT: {match[:100]}...")
        
        # Combine all deltas
        full_content = "".join(all_deltas)
        
        # Test full content extraction
        full_think_matches = re.findall(r'<think>([\s\S]*?)</think>', full_content)
        
        print(f"\n📊 EXTRACTION RESULTS:")
        print(f"  Total deltas: {len(all_deltas)}")
        print(f"  Think blocks found in deltas: {len(think_content_found)}")
        print(f"  Think blocks in full content: {len(full_think_matches)}")
        print(f"  Full content length: {len(full_content)} chars")
        
        if full_think_matches:
            print(f"\n🧠 FULL THINK CONTENT:")
            print("-" * 40)
            for i, match in enumerate(full_think_matches):
                print(f"Block {i+1}: {match[:200]}...")
        
        # Test content stripping (what frontend will do)
        cleaned_content = re.sub(r'<think>[\s\S]*?</think>', '', full_content).strip()
        print(f"\n✂️ CLEANED CONTENT (what user sees):")
        print(f"  Original length: {len(full_content)}")
        print(f"  Cleaned length: {len(cleaned_content)}")
        print(f"  Stripped thinking: {len(full_content) > len(cleaned_content)}")
        print("-" * 40)
        print(f"{cleaned_content[:300]}...")
        
        return len(full_think_matches) > 0 or len(think_content_found) > 0
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    result = asyncio.run(test_think_tag_extraction())
    print(f"\n{'='*80}")
    print(f"Think Tag Test: {'✅ FOUND' if result else '❌ NO TAGS'}")
    print(f"{'='*80}")