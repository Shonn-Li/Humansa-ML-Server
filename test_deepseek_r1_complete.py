#!/usr/bin/env python3
"""
Complete DeepSeek R1 Integration Test
Test both real-time thinking streaming and proper message completion
"""

import asyncio
import json
import sys
import os
import re
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


async def test_deepseek_r1_complete():
    """Complete test of DeepSeek R1 thinking and completion"""
    print("="*80)
    print("DEEPSEEK R1 COMPLETE INTEGRATION TEST")
    print("="*80)
    
    try:
        # Import endpoint
        from chat.endpoints.multi_agent_endpoint_v2 import MultiAgentChatEndpointV2
        endpoint = MultiAgentChatEndpointV2()
        
        # Test request that should generate substantial thinking content
        request = {
            "model": "DeepSeek-R1",
            "messages": [{
                "role": "user", 
                "content": "Calculate 123 * 456 step by step, showing your reasoning process"
            }],
            "stream": True,
            "user_id": 10001
        }
        
        print(f"🎯 Testing DeepSeek R1 complete flow...")
        print(f"Request: {json.dumps(request, indent=2)}")
        print(f"\n📡 Processing stream events...")
        print("-" * 80)
        
        # Run request and simulate frontend processing
        response = await endpoint.handle_request(request)
        
        # Simulate frontend Redux processing
        accumulated_content = ""
        current_thinking_content = ""
        is_inside_think_block = False
        thinking_segments = []
        output_deltas = []
        response_completed = False
        
        if hasattr(response, '__aiter__'):
            async for event in response:
                event_type = event.get("type", "unknown")
                
                if event_type == "response.output_text.delta":
                    delta = event.get("delta", "")
                    if delta:
                        output_deltas.append(delta)
                        
                        # Simulate the frontend character-by-character processing
                        for i, char in enumerate(delta):
                            # Check for <think> opening tag
                            if not is_inside_think_block and delta[i:].startswith('<think>'):
                                is_inside_think_block = True
                                current_thinking_content = ""
                                print(f"🧠 STARTED thinking block")
                                continue
                            
                            # Check for </think> closing tag
                            if is_inside_think_block and delta[i:].startswith('</think>'):
                                if current_thinking_content.strip():
                                    thinking_segments.append(current_thinking_content.strip())
                                    print(f"🧠 COMPLETED thinking: {current_thinking_content[:50]}...")
                                is_inside_think_block = False
                                current_thinking_content = ""
                                continue
                            
                            # Accumulate content
                            if is_inside_think_block:
                                current_thinking_content += char
                                # Simulate incremental updates every 20 chars
                                if len(current_thinking_content) % 20 == 0:
                                    print(f"🔄 STREAMING thinking: ...{current_thinking_content[-20:]}")
                            else:
                                accumulated_content += char
                
                elif event_type == "response.completed":
                    response_completed = True
                    print(f"✅ RESPONSE COMPLETED")
                    
                    # Simulate completion handling
                    if is_inside_think_block and current_thinking_content.strip():
                        thinking_segments.append(current_thinking_content.strip())
                        print(f"🧠 FINALIZED remaining thinking: {current_thinking_content[:50]}...")
                    
                    # Clean final content
                    full_content = "".join(output_deltas)
                    final_clean_content = re.sub(r'<think>[\s\S]*?</think>', '', full_content).strip()
                    
                    print(f"🧹 CLEANED final content: {len(final_clean_content)} chars")
        
        # Analysis
        full_output = "".join(output_deltas)
        all_thinking_content = " ".join(thinking_segments)
        final_display_content = re.sub(r'<think>[\s\S]*?</think>', '', full_output).strip()
        
        print(f"\n{'='*80}")
        print(f"🧪 TEST RESULTS")
        print(f"{'='*80}")
        
        print(f"📊 Stream Processing:")
        print(f"  Response completed: {'✅ YES' if response_completed else '❌ NO'}")
        print(f"  Output deltas: {len(output_deltas)} events")
        print(f"  Thinking segments: {len(thinking_segments)} blocks")
        print(f"  Full content length: {len(full_output)} chars")
        print(f"  Final display length: {len(final_display_content)} chars")
        print(f"  Content cleaned: {'✅ YES' if len(final_display_content) < len(full_output) else '❌ NO'}")
        
        print(f"\n🧠 Thinking Content Analysis:")
        if thinking_segments:
            print(f"  Total thinking length: {len(all_thinking_content)} chars")
            print(f"  First thinking segment: {thinking_segments[0][:100]}...")
            if len(thinking_segments) > 1:
                print(f"  Last thinking segment: {thinking_segments[-1][:100]}...")
        else:
            print(f"  ⚠️ No thinking content found")
        
        print(f"\n💬 Final Message Content:")
        if final_display_content:
            print(f"  Content length: {len(final_display_content)} chars")
            print(f"  Content preview: {final_display_content[:200]}...")
        else:
            print(f"  ❌ No final content - THIS IS THE ISSUE!")
        
        # Test success criteria
        has_thinking = len(thinking_segments) > 0
        has_final_content = len(final_display_content.strip()) > 0
        completed_properly = response_completed
        content_cleaned = len(final_display_content) < len(full_output)
        
        print(f"\n🎯 Integration Status:")
        print(f"  Thinking streaming: {'✅ WORKS' if has_thinking else '❌ FAILED'}")
        print(f"  Content cleaning: {'✅ WORKS' if content_cleaned else '❌ FAILED'}")
        print(f"  Response completion: {'✅ WORKS' if completed_properly else '❌ FAILED'}")
        print(f"  Final message display: {'✅ WORKS' if has_final_content else '❌ FAILED'}")
        
        overall_success = has_thinking and has_final_content and completed_properly and content_cleaned
        return overall_success
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    result = asyncio.run(test_deepseek_r1_complete())
    print(f"\n{'='*80}")
    print(f"Complete Integration: {'✅ SUCCESS' if result else '❌ NEEDS FIXING'}")
    print(f"{'='*80}")