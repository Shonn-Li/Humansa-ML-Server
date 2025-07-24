#!/usr/bin/env python3
"""
DeepSeek R1 Reasoning Integration Test
Test specifically for frontend ThinkingFlow integration with DeepSeek R1 reasoning content
"""

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

# Suppress verbose logging
import logging
for logger_name in ["httpx", "httpcore", "asyncio", "chat", "aiohttp"]:
    logging.getLogger(logger_name).setLevel(logging.WARNING)


async def test_deepseek_r1_reasoning():
    """Test DeepSeek R1 reasoning content for frontend integration"""
    print("="*80)
    print("DEEPSEEK R1 REASONING INTEGRATION TEST")
    print("="*80)
    
    try:
        # Import endpoint
        from chat.endpoints.multi_agent_endpoint_v2 import MultiAgentChatEndpointV2
        endpoint = MultiAgentChatEndpointV2()
        
        # Test request designed to trigger substantial reasoning
        request = {
            "model": "DeepSeek-R1",
            "messages": [{
                "role": "user", 
                "content": "I have a logic puzzle: There are 5 houses in different colors. Each house owner drinks a different beverage, smokes a different brand, and keeps a different pet. Can you help me solve this step by step?"
            }],
            "stream": True,
            "user_id": 10001
        }
        
        print(f"🎯 Testing DeepSeek R1 reasoning extraction...")
        print(f"Request: {json.dumps(request, indent=2)}")
        print(f"\n📡 Analyzing streaming events...")
        print("-" * 80)
        
        # Run request and analyze events
        response = await endpoint.handle_request(request)
        
        # Track reasoning data
        reasoning_deltas = []
        think_tag_content = []
        output_deltas = []
        event_types = set()
        
        if hasattr(response, '__aiter__'):
            async for event in response:
                event_type = event.get("type", "unknown")
                event_types.add(event_type)
                
                # Track reasoning deltas
                if event_type == "response.reasoning_text.delta":
                    delta = event.get("delta", "")
                    if delta:
                        reasoning_deltas.append(delta)
                
                # Track output deltas and extract <think> content
                elif event_type == "response.output_text.delta":
                    delta = event.get("delta", "")
                    if delta:
                        output_deltas.append(delta)
                        
                        # Extract thinking content from <think> tags
                        import re
                        think_matches = re.findall(r'<think>(.*?)</think>', delta, re.DOTALL)
                        for match in think_matches:
                            think_tag_content.append(match.strip())
        
        # Analysis results
        print("\n" + "="*80)
        print("🧠 REASONING ANALYSIS RESULTS")
        print("="*80)
        
        # Event summary
        print("📊 Event Types Found:")
        for event_type in sorted(event_types):
            print(f"  - {event_type}")
        
        # Reasoning content analysis
        reasoning_text = "".join(reasoning_deltas)
        think_text = "".join(think_tag_content)
        output_text = "".join(output_deltas)
        
        print(f"\n🔍 Content Analysis:")
        print(f"  Reasoning Deltas: {len(reasoning_deltas)} events, {len(reasoning_text)} chars")
        print(f"  Think Tag Content: {len(think_tag_content)} blocks, {len(think_text)} chars")
        print(f"  Output Deltas: {len(output_deltas)} events, {len(output_text)} chars")
        
        # Frontend integration readiness
        has_reasoning_events = len(reasoning_deltas) > 0
        has_think_content = len(think_tag_content) > 0
        has_substantial_reasoning = (len(reasoning_text) + len(think_text)) > 100
        
        print(f"\n✅ Frontend Integration Status:")
        print(f"  Has reasoning events: {'✅ YES' if has_reasoning_events else '❌ NO'}")
        print(f"  Has <think> content: {'✅ YES' if has_think_content else '❌ NO'}")
        print(f"  Substantial reasoning: {'✅ YES' if has_substantial_reasoning else '❌ NO'}")
        
        # Show sample content
        if reasoning_text:
            print(f"\n📝 Reasoning Content Sample:")
            print("-" * 40)
            print(reasoning_text[:300] + ("..." if len(reasoning_text) > 300 else ""))
        
        if think_text:
            print(f"\n🧠 Think Content Sample:")
            print("-" * 40) 
            print(think_text[:300] + ("..." if len(think_text) > 300 else ""))
        
        # Frontend recommendations
        print(f"\n🎯 Frontend ThinkingFlow Integration:")
        if has_think_content:
            print("  ✅ DeepSeek R1 <think> tags detected - Redux should extract and display")
            print("  ✅ Content should appear in ThinkingFlow component")
            print("  ✅ Final response should have <think> tags stripped")
        elif has_reasoning_events:
            print("  ✅ Standard reasoning events detected - should display normally")
        else:
            print("  ⚠️ No reasoning content found - check model configuration")
        
        # Test success criteria
        integration_ready = has_reasoning_events or has_think_content
        return integration_ready
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    result = asyncio.run(test_deepseek_r1_reasoning())
    print(f"\n{'='*80}")
    print(f"Integration Test: {'✅ READY' if result else '❌ NEEDS WORK'}")
    print(f"{'='*80}")