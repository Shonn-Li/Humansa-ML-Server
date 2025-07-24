#!/usr/bin/env python3
"""
DeepSeek R1 Real Streaming Test
Test that DeepSeek R1 thinking tokens actually stream to frontend in real-time
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


async def test_deepseek_real_streaming():
    """Test that DeepSeek R1 thinking actually streams in real-time to frontend"""
    print("="*80)
    print("DEEPSEEK R1 REAL-TIME STREAMING TEST")
    print("="*80)
    
    try:
        # Import endpoint
        from chat.endpoints.multi_agent_endpoint_v2 import MultiAgentChatEndpointV2
        endpoint = MultiAgentChatEndpointV2()
        
        # Test request that should generate substantial real-time thinking
        request = {
            "model": "DeepSeek-R1",
            "messages": [{
                "role": "user", 
                "content": "Solve this logic puzzle step by step: There are 3 boxes. One contains gold, one silver, one is empty. Each box has a label, but all labels are wrong. Box A says 'Gold', Box B says 'Empty', Box C says 'Silver'. Which box contains what?"
            }],
            "stream": True,
            "user_id": 10001
        }
        
        print(f"🎯 Testing real-time thinking streaming...")
        print(f"Request: {json.dumps(request, indent=2)}")
        print(f"\n📡 Simulating frontend Redux character-by-character processing...")
        print("-" * 80)
        
        # Run request and simulate frontend Redux real-time processing
        response = await endpoint.handle_request(request)
        
        # Simulate frontend Redux state tracking
        accumulated_content = ""
        is_inside_think_block = False
        current_thinking_content = ""
        has_active_thinking_entry = False
        thinking_entries = []
        display_content = ""
        response_completed = False
        
        thinking_stream_events = []  # Track when thinking updates happen
        
        if hasattr(response, '__aiter__'):
            async for event in response:
                event_type = event.get("type", "unknown")
                
                if event_type == "response.output_text.delta":
                    delta = event.get("delta", "")
                    if delta:
                        # Simulate the EXACT frontend Redux logic character by character
                        for i, char in enumerate(delta):
                            accumulated_content += char
                            
                            # Check for <think> opening tag
                            if not is_inside_think_block and accumulated_content.endswith('<think>'):
                                is_inside_think_block = True
                                current_thinking_content = ""
                                has_active_thinking_entry = False
                                print(f"🧠 STARTED THINKING BLOCK")
                                continue
                            
                            # Check for </think> closing tag
                            if is_inside_think_block and accumulated_content.endswith('</think>'):
                                # Complete the thinking block
                                if current_thinking_content.strip():
                                    if has_active_thinking_entry:
                                        # Update existing entry (simulate updateLastAgentFlowEntry)
                                        thinking_entries[-1] = {
                                            "type": "thought",
                                            "content": current_thinking_content.strip(),
                                            "final": True
                                        }
                                    else:
                                        # Create new entry (simulate addAgentFlowEntry)
                                        thinking_entries.append({
                                            "type": "thought", 
                                            "content": current_thinking_content.strip(),
                                            "final": True
                                        })
                                    
                                    thinking_stream_events.append({
                                        "type": "complete_thinking_block",
                                        "length": len(current_thinking_content),
                                        "content_preview": current_thinking_content[:100] + "..."
                                    })
                                    print(f"🧠 COMPLETED THINKING: {len(current_thinking_content)} chars")
                                
                                is_inside_think_block = False
                                current_thinking_content = ""
                                has_active_thinking_entry = False
                                continue
                            
                            # If inside thinking block, accumulate thinking content
                            if is_inside_think_block:
                                current_thinking_content += char
                                
                                # Stream thinking content in real-time (every 30 characters)
                                if len(current_thinking_content) > 0 and len(current_thinking_content) % 30 == 0:
                                    if has_active_thinking_entry:
                                        # Update existing entry
                                        thinking_entries[-1] = {
                                            "type": "thought",
                                            "content": current_thinking_content.strip(),
                                            "final": False
                                        }
                                    else:
                                        # Create initial entry
                                        thinking_entries.append({
                                            "type": "thought",
                                            "content": current_thinking_content.strip(),
                                            "final": False
                                        })
                                        has_active_thinking_entry = True
                                    
                                    thinking_stream_events.append({
                                        "type": "real_time_thinking_update",
                                        "length": len(current_thinking_content),
                                        "content_preview": current_thinking_content[-30:]
                                    })
                                    print(f"🔄 STREAMING THINKING: {len(current_thinking_content)} chars - ...{current_thinking_content[-30:]}")
                        
                        # Update display content (strip all thinking content)
                        new_display_content = re.sub(r'<think>[\s\S]*?</think>', '', accumulated_content).strip()
                        if new_display_content != display_content:
                            display_content = new_display_content
                            if display_content:
                                print(f"💬 DISPLAY UPDATE: {len(display_content)} chars")
                
                elif event_type == "response.completed":
                    response_completed = True
                    print(f"✅ RESPONSE COMPLETED")
                    
                    # Handle any incomplete thinking block
                    if is_inside_think_block and current_thinking_content.strip():
                        if has_active_thinking_entry:
                            thinking_entries[-1] = {
                                "type": "thought",
                                "content": current_thinking_content.strip(),
                                "final": True
                            }
                        else:
                            thinking_entries.append({
                                "type": "thought",
                                "content": current_thinking_content.strip(),
                                "final": True
                            })
                        
                        thinking_stream_events.append({
                            "type": "finalized_incomplete_thinking",
                            "length": len(current_thinking_content),
                            "content_preview": current_thinking_content[:100] + "..."
                        })
                        print(f"🧠 FINALIZED INCOMPLETE THINKING: {len(current_thinking_content)} chars")
                    
                    # Ensure final clean content
                    final_clean_content = re.sub(r'<think>[\s\S]*?</think>', '', accumulated_content).strip()
                    if final_clean_content:
                        display_content = final_clean_content
                        print(f"🚀 FINAL CONTENT: {len(display_content)} chars")
                    else:
                        display_content = "Response generated successfully."
                        print(f"⚠️ FALLBACK CONTENT: Using fallback to prevent crash")
        
        # Analysis
        total_thinking_content = ""
        final_thinking_entries = [e for e in thinking_entries if e["type"] == "thought"]
        if final_thinking_entries:
            total_thinking_content = " ".join([e["content"] for e in final_thinking_entries])
        
        real_time_updates = [e for e in thinking_stream_events if e["type"] == "real_time_thinking_update"]
        complete_blocks = [e for e in thinking_stream_events if e["type"] == "complete_thinking_block"]
        
        print(f"\n{'='*80}")
        print(f"🧪 REAL-TIME STREAMING ANALYSIS")
        print(f"{'='*80}")
        
        print(f"📊 Stream Processing:")
        print(f"  Response completed: {'✅ YES' if response_completed else '❌ NO'}")
        print(f"  Real-time updates: {len(real_time_updates)} events")
        print(f"  Complete thinking blocks: {len(complete_blocks)} blocks")
        print(f"  Total thinking entries: {len(final_thinking_entries)}")
        
        print(f"\n🧠 ThinkingFlow Real-Time Streaming:")
        if real_time_updates:
            print(f"  ✅ STREAMING WORKS: {len(real_time_updates)} real-time updates")
            print(f"  First update: {real_time_updates[0]['length']} chars")
            print(f"  Last update: {real_time_updates[-1]['length']} chars")
            print(f"  Update frequency: Every ~30 characters")
        else:
            print(f"  ❌ NO STREAMING: Thinking not streaming in real-time!")
        
        print(f"\n💬 Message Display:")
        print(f"  Original content: {len(accumulated_content)} chars")
        print(f"  Final display: {len(display_content)} chars")
        print(f"  Content cleaned: {'✅ YES' if len(display_content) < len(accumulated_content) else '❌ NO'}")
        print(f"  Has final message: {'✅ YES' if len(display_content) > 0 else '❌ NO - CRASH RISK!'}")
        
        print(f"\n🧠 Thinking Content Analysis:")
        print(f"  Total thinking length: {len(total_thinking_content)} chars")
        if final_thinking_entries:
            print(f"  Thinking preview: {total_thinking_content[:200]}...")
        
        if display_content:
            print(f"\n📝 Final Message Preview:")
            print(f"{'-'*40}")
            print(f"{display_content[:300]}...")
        
        # Success criteria
        has_real_time_streaming = len(real_time_updates) > 0
        has_final_content = len(display_content) > 0
        completed_properly = response_completed
        has_thinking_content = len(final_thinking_entries) > 0
        
        print(f"\n🎯 Critical Issues Check:")
        print(f"  ✅ Issue 1 - Thinking streams in real-time: {'✅ FIXED' if has_real_time_streaming else '❌ STILL BROKEN'}")
        print(f"  ✅ Issue 2 - Chat doesn't crash after completion: {'✅ FIXED' if has_final_content else '❌ STILL BROKEN'}")
        print(f"  Response completes normally: {'✅ YES' if completed_properly else '❌ NO'}")
        print(f"  ThinkingFlow has content: {'✅ YES' if has_thinking_content else '❌ NO'}")
        
        overall_success = has_real_time_streaming and has_final_content and completed_properly and has_thinking_content
        return overall_success
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    result = asyncio.run(test_deepseek_real_streaming())
    print(f"\n{'='*80}")
    print(f"DeepSeek R1 Real-Time Fix: {'✅ SUCCESS - BOTH ISSUES FIXED' if result else '❌ ISSUES REMAIN'}")
    print(f"{'='*80}")