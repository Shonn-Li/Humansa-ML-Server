#!/usr/bin/env python3
"""
Test DeepSeek R1 with Frontend-Style Logging
Simulate how the frontend would process the events with enhanced debug logging
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


async def test_deepseek_with_enhanced_logging():
    """Test DeepSeek with the same logging that the frontend would have"""
    print("="*80)
    print("DEEPSEEK R1 WITH ENHANCED FRONTEND LOGGING")
    print("="*80)
    
    try:
        # Import endpoint
        from chat.endpoints.multi_agent_endpoint_v2 import MultiAgentChatEndpointV2
        endpoint = MultiAgentChatEndpointV2()
        
        # Simple request
        request = {
            "model": "DeepSeek-R1",
            "messages": [{"role": "user", "content": "What is 3*4? Think step by step but be brief."}],
            "stream": True,
            "user_id": 10001
        }
        
        print(f"🎯 Testing DeepSeek with enhanced logging...")
        print(f"Request: {json.dumps(request, indent=2)}")
        print(f"\n📡 Processing with frontend-like logging...")
        print("-" * 80)
        
        # Run request
        response = await endpoint.handle_request(request)
        
        # Simulate frontend state like the Redux slice
        accumulated_content = ""
        is_inside_think_block = False
        current_thinking_content = ""
        has_active_thinking_entry = False
        agent_flow_active = False
        thinking_entries = []
        streaming_content = ""
        
        event_count = 0
        received_completion = False
        
        if hasattr(response, '__aiter__'):
            async for event in response:
                event_count += 1
                event_type = event.get("type", "unknown")
                
                # Simulate the exact frontend logging
                print(f"📨 Event {event_count}: {event_type}")
                print(f"🔀 ENTERING SWITCH for event: {event_type}")
                
                if event_type == "response.created":
                    agent_flow_active = True
                    print(f"🚀 Response created - starting agent flow")
                
                elif event_type == "response.output_text.delta":
                    delta = event.get("delta", "")
                    if delta:
                        print(f"🔄 DEEPSEEK R1: Processing delta (length: {len(delta)})")
                        
                        # Character-by-character processing like frontend
                        for i, char in enumerate(delta):
                            accumulated_content += char
                            
                            # Check for <think> opening tag
                            if not is_inside_think_block and accumulated_content.endswith('<think>'):
                                is_inside_think_block = True
                                current_thinking_content = ""
                                has_active_thinking_entry = False
                                print(f"🧠 DEEPSEEK R1: Entered thinking block")
                                if not agent_flow_active:
                                    agent_flow_active = True
                                    print(f"🧠 Starting agent flow for thinking")
                                continue
                            
                            # Check for </think> closing tag
                            if is_inside_think_block and accumulated_content.endswith('</think>'):
                                if current_thinking_content.strip():
                                    thinking_entries.append({
                                        "type": "thought",
                                        "content": current_thinking_content.strip()
                                    })
                                    print(f"🧠 DEEPSEEK R1: Completed thinking block ({len(current_thinking_content)} chars)")
                                
                                is_inside_think_block = False
                                current_thinking_content = ""
                                has_active_thinking_entry = False
                                continue
                            
                            # Accumulate thinking content and stream it
                            if is_inside_think_block:
                                current_thinking_content += char
                                
                                # Stream every 30 characters like frontend
                                if len(current_thinking_content) > 0 and len(current_thinking_content) % 30 == 0:
                                    print(f"🔄 DEEPSEEK R1: Streaming real-time thinking - DISPATCHING ACTION")
                                    if has_active_thinking_entry:
                                        print(f"🔄 UPDATING existing thinking entry")
                                        thinking_entries[-1] = {
                                            "type": "thought",
                                            "content": current_thinking_content.strip()
                                        }
                                    else:
                                        print(f"🆕 CREATING new thinking entry")
                                        thinking_entries.append({
                                            "type": "thought",
                                            "content": current_thinking_content.strip()
                                        })
                                        has_active_thinking_entry = True
                                        print(f"✅ VERIFIED thinking entry added to state (total: {len(thinking_entries)})")
                        
                        # Update streaming content (clean version)
                        clean_content = re.sub(r'<think>[\\s\\S]*?</think>', '', accumulated_content).strip()
                        if clean_content != streaming_content:
                            streaming_content = clean_content
                            print(f"💬 Updated streaming content ({len(clean_content)} chars)")
                
                elif event_type == "response.completed":
                    received_completion = True
                    print(f"🏁🏁🏁 DEEPSEEK R1: RESPONSE.COMPLETED EVENT RECEIVED - CRITICAL")
                    
                    # Handle incomplete thinking like frontend
                    if is_inside_think_block and current_thinking_content.strip():
                        print(f"🧠 DEEPSEEK R1: Finalizing incomplete thinking on completion")
                        thinking_entries.append({
                            "type": "thought",
                            "content": current_thinking_content.strip()
                        })
                        print(f"✅ VERIFIED thinking entry added to state (total: {len(thinking_entries)})")
                        
                        is_inside_think_block = False
                        current_thinking_content = ""
                        has_active_thinking_entry = False
                    
                    # Clean final content
                    final_clean_content = re.sub(r'<think>[\\s\\S]*?</think>', '', accumulated_content).strip()
                    if final_clean_content:
                        streaming_content = final_clean_content
                        print(f"🚀 DEEPSEEK R1: Setting final clean content - SAVING MESSAGE ({len(final_clean_content)} chars)")
                    else:
                        fallback_content = "Response generated successfully."
                        streaming_content = fallback_content
                        print(f"⚠️ DEEPSEEK R1: Using fallback content to prevent crash")
                    
                    # Complete agent flow
                    if agent_flow_active:
                        thinking_entries.append({"type": "conclusion", "content": ""})
                        agent_flow_active = False
                        print(f"🏁 DEEPSEEK R1: Completing agent flow - FINAL STEP")
                        print(f"✅ DEEPSEEK R1: Agent flow completed successfully (total entries: {len(thinking_entries)})")
                    
                    print(f"✅ Response processing completed successfully")
                    break
        
        # Analysis
        thinking_count = len([e for e in thinking_entries if e["type"] == "thought"])
        conclusion_count = len([e for e in thinking_entries if e["type"] == "conclusion"])
        
        print(f"\n{'='*80}")
        print(f"🧪 FRONTEND PROCESSING RESULTS")
        print(f"{'='*80}")
        
        print(f"📊 Event Processing:")
        print(f"  Total events: {event_count}")
        print(f"  Completion event received: {'✅ YES' if received_completion else '❌ NO'}")
        print(f"  Agent flow activated: {'✅ YES' if thinking_count > 0 else '❌ NO'}")
        
        print(f"\n🧠 ThinkingFlow Entries:")
        print(f"  Thinking entries: {thinking_count}")
        print(f"  Conclusion entries: {conclusion_count}")
        print(f"  Total entries: {len(thinking_entries)}")
        
        if thinking_count > 0:
            total_thinking = " ".join([e["content"] for e in thinking_entries if e["type"] == "thought"])
            print(f"  Total thinking content: {len(total_thinking)} chars")
            print(f"  First thinking: {total_thinking[:100]}...")
        
        print(f"\n💬 Final Message:")
        print(f"  Content length: {len(streaming_content)} chars")
        print(f"  Has content: {'✅ YES' if len(streaming_content) > 0 else '❌ NO - CRASH RISK'}")
        
        if streaming_content:
            print(f"  Content preview: {streaming_content[:150]}...")
        
        # Success criteria
        has_thinking = thinking_count > 0
        has_final_content = len(streaming_content) > 0
        completed_properly = received_completion
        
        print(f"\n🎯 Critical Issues Check:")
        print(f"  ThinkingFlow displays: {'✅ WORKING' if has_thinking else '❌ BROKEN'}")
        print(f"  Message displays: {'✅ WORKING' if has_final_content else '❌ BROKEN'}")
        print(f"  Completion works: {'✅ WORKING' if completed_properly else '❌ BROKEN'}")
        
        overall_success = has_thinking and has_final_content and completed_properly
        return overall_success
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    result = asyncio.run(test_deepseek_with_enhanced_logging())
    print(f"\n{'='*80}")
    print(f"Frontend Processing: {'✅ ALL WORKING' if result else '❌ ISSUES FOUND'}")
    print(f"{'='*80}")