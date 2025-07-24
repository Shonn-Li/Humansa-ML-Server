#!/usr/bin/env python3
"""
Debug DeepSeek R1 Completion Events
Track what happens with response.completed events specifically for DeepSeek
"""

import asyncio
import json
import sys
import os
import time
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


async def debug_deepseek_completion():
    """Debug DeepSeek completion events specifically"""
    print("="*80)
    print("DEEPSEEK R1 COMPLETION EVENT DEBUG")
    print("="*80)
    
    try:
        # Import endpoint
        from chat.endpoints.multi_agent_endpoint_v2 import MultiAgentChatEndpointV2
        endpoint = MultiAgentChatEndpointV2()
        
        # Simple request to minimize variables
        request = {
            "model": "DeepSeek-R1",
            "messages": [{"role": "user", "content": "What is 2+2? Think step by step."}],
            "stream": True,
            "user_id": 10001
        }
        
        print(f"🎯 Debugging DeepSeek R1 completion events...")
        print(f"Request: {json.dumps(request, indent=2)}")
        print(f"\n📡 Tracking all events with timestamps...")
        print("-" * 80)
        
        # Run request
        response = await endpoint.handle_request(request)
        
        # Track all events with detailed timing
        all_events = []
        start_time = time.time()
        response_started = False
        found_completion = False
        last_event_time = start_time
        
        if hasattr(response, '__aiter__'):
            event_count = 0
            async for event in response:
                current_time = time.time()
                event_count += 1
                event_type = event.get("type", "unknown")
                
                # Calculate timing
                time_since_start = current_time - start_time
                time_since_last = current_time - last_event_time
                last_event_time = current_time
                
                event_info = {
                    "sequence": event_count,
                    "type": event_type,
                    "time_since_start": round(time_since_start, 3),
                    "time_since_last": round(time_since_last, 3),
                    "timestamp": datetime.now().strftime("%H:%M:%S.%f")[:-3]
                }
                
                # Add specific details for different event types
                if event_type == "response.created":
                    response_started = True
                    event_info["response_id"] = event.get("response", {}).get("id", "unknown")
                    print(f"🚀 {event_count:2d}. {event_type} at +{time_since_start:.3f}s (response_id: {event_info['response_id']})")
                
                elif event_type == "response.output_text.delta":
                    delta = event.get("delta", "")
                    event_info["delta_length"] = len(delta)
                    event_info["has_think_tags"] = "<think>" in delta or "</think>" in delta
                    if event_info["has_think_tags"]:
                        print(f"🧠 {event_count:2d}. {event_type} at +{time_since_start:.3f}s (delta: {len(delta)} chars, HAS <think> TAGS)")
                    elif event_count % 10 == 0:  # Show every 10th delta to reduce noise
                        print(f"💬 {event_count:2d}. {event_type} at +{time_since_start:.3f}s (delta: {len(delta)} chars)")
                
                elif event_type == "response.completed":
                    found_completion = True
                    response_info = event.get("response", {})
                    event_info["response_id"] = response_info.get("id", "unknown")
                    event_info["response_status"] = response_info.get("status", "unknown")
                    print(f"✅ {event_count:2d}. {event_type} at +{time_since_start:.3f}s (COMPLETION FOUND - status: {event_info['response_status']})")
                    
                elif event_type in ["response.error", "error"]:
                    error_info = event.get("error", event.get("message", "unknown error"))
                    event_info["error"] = str(error_info)
                    print(f"❌ {event_count:2d}. {event_type} at +{time_since_start:.3f}s (ERROR: {error_info})")
                
                else:
                    print(f"📝 {event_count:2d}. {event_type} at +{time_since_start:.3f}s")
                
                all_events.append(event_info)
                
                # Stop if we found completion
                if event_type == "response.completed":
                    break
        
        # Wait a bit more to see if any late events arrive
        print(f"\n⏳ Waiting 5 seconds to check for late events...")
        await asyncio.sleep(5)
        
        final_time = time.time()
        total_duration = final_time - start_time
        
        print(f"\n{'='*80}")
        print(f"🧪 COMPLETION EVENT ANALYSIS")
        print(f"{'='*80}")
        
        print(f"📊 Event Summary:")
        print(f"  Total events: {len(all_events)}")
        print(f"  Total duration: {total_duration:.3f} seconds")
        print(f"  Response started: {'✅ YES' if response_started else '❌ NO'}")
        print(f"  Completion found: {'✅ YES' if found_completion else '❌ NO - THIS IS THE ISSUE!'}")
        
        # Analyze event patterns
        completion_events = [e for e in all_events if e["type"] == "response.completed"]
        delta_events = [e for e in all_events if e["type"] == "response.output_text.delta"]
        think_deltas = [e for e in delta_events if e.get("has_think_tags", False)]
        
        print(f"\n🔍 Event Pattern Analysis:")
        print(f"  Output text deltas: {len(delta_events)}")
        print(f"  Deltas with <think> tags: {len(think_deltas)}")
        print(f"  Completion events: {len(completion_events)}")
        
        if completion_events:
            completion_event = completion_events[0]
            print(f"  Completion timing: +{completion_event['time_since_start']}s")
            print(f"  Completion status: {completion_event.get('response_status', 'unknown')}")
        
        # Look for any patterns in the last few events
        print(f"\n📋 Last 5 events before completion/timeout:")
        for event in all_events[-5:]:
            print(f"  {event['sequence']:2d}. {event['type']} at +{event['time_since_start']}s")
        
        # Critical issue identification
        print(f"\n🎯 Critical Issues Identified:")
        if not found_completion:
            print(f"  ❌ CRITICAL: No response.completed event found!")
            print(f"     This explains why DeepSeek conversations don't complete properly.")
            print(f"     The frontend is waiting for this event to finalize the conversation.")
        else:
            print(f"  ✅ response.completed event found - completion works properly")
        
        return found_completion
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    result = asyncio.run(debug_deepseek_completion())
    print(f"\n{'='*80}")
    print(f"DeepSeek Completion: {'✅ WORKING' if result else '❌ BROKEN - NO COMPLETION EVENT'}")
    print(f"{'='*80}")