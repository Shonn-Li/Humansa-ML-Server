#!/usr/bin/env python3
"""
Test Redux State Tracking for DeepSeek
Create a detailed test that shows what should happen with the Redux state
"""

import asyncio
import json
import sys
import os
import re
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


async def test_redux_state_tracking():
    """Test what should happen with Redux state for DeepSeek"""
    print("="*80)
    print("REDUX STATE TRACKING FOR DEEPSEEK R1")
    print("="*80)
    
    try:
        # Import endpoint
        from chat.endpoints.multi_agent_endpoint_v2 import MultiAgentChatEndpointV2
        endpoint = MultiAgentChatEndpointV2()
        
        # Simple request for clear testing
        request = {
            "model": "DeepSeek-R1",
            "messages": [{"role": "user", "content": "What is 5+5? Think briefly."}],
            "stream": True,
            "user_id": 10001
        }
        
        print(f"🎯 Testing Redux state changes for DeepSeek R1...")
        print(f"Request: {json.dumps(request, indent=2)}")
        print(f"\n🧠 Tracking what should happen to Redux state...")
        print("-" * 80)
        
        # Simulate the Redux state as it should change
        redux_state = {
            "currentAgentFlow": {
                "isActive": False,
                "entries": [],
                "duration": 0
            },
            "streamingMessageId": None,
            "streamingContent": ""
        }
        
        # Track Redux actions that should be dispatched
        actions_dispatched = []
        
        # Run request
        response = await endpoint.handle_request(request)
        
        # Process events and track expected Redux changes
        accumulated_content = ""
        is_inside_think_block = False
        current_thinking_content = ""
        has_active_thinking_entry = False
        
        event_count = 0
        thinking_updates = 0
        
        if hasattr(response, '__aiter__'):
            async for event in response:
                event_count += 1
                event_type = event.get("type", "unknown")
                
                print(f"📨 Event {event_count}: {event_type}")
                
                if event_type == "response.created":
                    # Should dispatch: startAgentFlow()
                    redux_state["currentAgentFlow"]["isActive"] = True
                    actions_dispatched.append("startAgentFlow()")
                    print(f"  🔄 Redux action: startAgentFlow()")
                    print(f"  📊 Redux state: currentAgentFlow.isActive = True")
                
                elif event_type == "response.output_text.delta":
                    delta = event.get("delta", "")
                    if delta:
                        # Process character by character
                        for char in delta:
                            accumulated_content += char
                            
                            # Check for <think> opening
                            if not is_inside_think_block and accumulated_content.endswith('<think>'):
                                is_inside_think_block = True
                                current_thinking_content = ""
                                has_active_thinking_entry = False
                                print(f"  🧠 Started thinking block")
                                
                                # Ensure agent flow is active
                                if not redux_state["currentAgentFlow"]["isActive"]:
                                    redux_state["currentAgentFlow"]["isActive"] = True
                                    actions_dispatched.append("startAgentFlow()")
                                    print(f"    🔄 Redux action: startAgentFlow()")
                                continue
                            
                            # Check for </think> closing
                            if is_inside_think_block and accumulated_content.endswith('</think>'):
                                if current_thinking_content.strip():
                                    # Should add thinking entry
                                    thinking_entry = {
                                        "type": "thought",
                                        "content": current_thinking_content.strip()
                                    }
                                    redux_state["currentAgentFlow"]["entries"].append(thinking_entry)
                                    
                                    if has_active_thinking_entry:
                                        actions_dispatched.append(f"updateLastAgentFlowEntry(thought, {len(current_thinking_content)} chars)")
                                        print(f"    🔄 Redux action: updateLastAgentFlowEntry()")
                                    else:
                                        actions_dispatched.append(f"addAgentFlowEntry(thought, {len(current_thinking_content)} chars)")
                                        print(f"    🔄 Redux action: addAgentFlowEntry()")
                                    
                                    print(f"    📊 Redux state: entries.length = {len(redux_state['currentAgentFlow']['entries'])}")
                                    print(f"  🧠 Completed thinking block ({len(current_thinking_content)} chars)")
                                
                                is_inside_think_block = False
                                current_thinking_content = ""
                                has_active_thinking_entry = False
                                continue
                            
                            # Accumulate thinking content
                            if is_inside_think_block:
                                current_thinking_content += char
                                
                                # Stream every 30 characters
                                if len(current_thinking_content) > 0 and len(current_thinking_content) % 30 == 0:
                                    thinking_updates += 1
                                    
                                    if has_active_thinking_entry:
                                        # Update existing entry
                                        if redux_state["currentAgentFlow"]["entries"]:
                                            redux_state["currentAgentFlow"]["entries"][-1]["content"] = current_thinking_content.strip()
                                        actions_dispatched.append(f"updateLastAgentFlowEntry(streaming {len(current_thinking_content)} chars)")
                                        print(f"    🔄 Redux action: updateLastAgentFlowEntry() [streaming update #{thinking_updates}]")
                                    else:
                                        # Create new entry
                                        thinking_entry = {
                                            "type": "thought",
                                            "content": current_thinking_content.strip()
                                        }
                                        redux_state["currentAgentFlow"]["entries"].append(thinking_entry)
                                        has_active_thinking_entry = True
                                        actions_dispatched.append(f"addAgentFlowEntry(streaming {len(current_thinking_content)} chars)")
                                        print(f"    🔄 Redux action: addAgentFlowEntry() [streaming update #{thinking_updates}]")
                                        print(f"    📊 Redux state: entries.length = {len(redux_state['currentAgentFlow']['entries'])}")
                        
                        # Update streaming content (clean version)
                        clean_content = re.sub(r'<think>[\\s\\S]*?</think>', '', accumulated_content).strip()
                        if clean_content != redux_state["streamingContent"]:
                            redux_state["streamingContent"] = clean_content
                            actions_dispatched.append(f"setStreamingContent({len(clean_content)} chars)")
                            print(f"  🔄 Redux action: setStreamingContent()")
                
                elif event_type == "response.completed":
                    print(f"  🏁 Processing completion...")
                    
                    # Handle incomplete thinking
                    if is_inside_think_block and current_thinking_content.strip():
                        thinking_entry = {
                            "type": "thought",
                            "content": current_thinking_content.strip()
                        }
                        redux_state["currentAgentFlow"]["entries"].append(thinking_entry)
                        
                        if has_active_thinking_entry:
                            actions_dispatched.append(f"updateLastAgentFlowEntry(final {len(current_thinking_content)} chars)")
                            print(f"    🔄 Redux action: updateLastAgentFlowEntry() [completion]")
                        else:
                            actions_dispatched.append(f"addAgentFlowEntry(final {len(current_thinking_content)} chars)")
                            print(f"    🔄 Redux action: addAgentFlowEntry() [completion]")
                        
                        print(f"    📊 Redux state: entries.length = {len(redux_state['currentAgentFlow']['entries'])}")
                    
                    # Set final content
                    final_clean_content = re.sub(r'<think>[\\s\\S]*?</think>', '', accumulated_content).strip()
                    if final_clean_content:
                        redux_state["streamingContent"] = final_clean_content
                        actions_dispatched.append(f"setStreamingContent(final {len(final_clean_content)} chars)")
                        print(f"    🔄 Redux action: setStreamingContent() [final]")
                    
                    # Complete agent flow
                    if redux_state["currentAgentFlow"]["isActive"]:
                        conclusion_entry = {"type": "conclusion", "content": ""}
                        redux_state["currentAgentFlow"]["entries"].append(conclusion_entry)
                        redux_state["currentAgentFlow"]["isActive"] = False
                        
                        actions_dispatched.append("addAgentFlowEntry(conclusion)")
                        actions_dispatched.append("completeAgentFlow()")
                        print(f"    🔄 Redux action: addAgentFlowEntry(conclusion)")
                        print(f"    🔄 Redux action: completeAgentFlow()")
                        print(f"    📊 Redux state: currentAgentFlow.isActive = False")
                        print(f"    📊 Redux state: entries.length = {len(redux_state['currentAgentFlow']['entries'])}")
                    
                    break
        
        # Final analysis
        thinking_entries = [e for e in redux_state["currentAgentFlow"]["entries"] if e["type"] == "thought"]
        conclusion_entries = [e for e in redux_state["currentAgentFlow"]["entries"] if e["type"] == "conclusion"]
        
        print(f"\n{'='*80}")
        print(f"🧪 EXPECTED REDUX STATE AFTER COMPLETION")
        print(f"{'='*80}")
        
        print(f"📊 Final Redux State:")
        print(f"  currentAgentFlow.isActive: {redux_state['currentAgentFlow']['isActive']}")
        print(f"  currentAgentFlow.entries.length: {len(redux_state['currentAgentFlow']['entries'])}")
        print(f"  thinking entries: {len(thinking_entries)}")
        print(f"  conclusion entries: {len(conclusion_entries)}")
        print(f"  streamingContent.length: {len(redux_state['streamingContent'])}")
        
        print(f"\n📋 Redux Actions Dispatched ({len(actions_dispatched)} total):")
        for i, action in enumerate(actions_dispatched, 1):
            print(f"  {i:2d}. {action}")
        
        print(f"\n🧠 ThinkingFlow Should Receive:")
        print(f"  entries: {len(redux_state['currentAgentFlow']['entries'])} items")
        print(f"  isActive: {redux_state['currentAgentFlow']['isActive']}")
        print(f"  duration: {redux_state['currentAgentFlow']['duration']}")
        
        if thinking_entries:
            total_thinking = " ".join([e["content"] for e in thinking_entries])
            print(f"  thinking content: {len(total_thinking)} chars")
            print(f"  first thinking: {total_thinking[:100]}...")
        
        print(f"\n💬 Final Message Content:")
        print(f"  length: {len(redux_state['streamingContent'])} chars")
        if redux_state['streamingContent']:
            print(f"  preview: {redux_state['streamingContent'][:150]}...")
        
        print(f"\n🎯 ThinkingFlow Visibility:")
        should_render = len(redux_state['currentAgentFlow']['entries']) > 0 or redux_state['currentAgentFlow']['isActive']
        print(f"  Should render: {'✅ YES' if should_render else '❌ NO'}")
        print(f"  Render reason: {'Has entries' if len(redux_state['currentAgentFlow']['entries']) > 0 else 'Is active' if redux_state['currentAgentFlow']['isActive'] else 'No reason'}")
        
        return should_render and len(thinking_entries) > 0
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    result = asyncio.run(test_redux_state_tracking())
    print(f"\n{'='*80}")
    print(f"Redux State Tracking: {'✅ SHOULD WORK' if result else '❌ ISSUE FOUND'}")
    print(f"{'='*80}")
    print()
    print("If ThinkingFlow is still not displaying, the issue is likely:")
    print("1. Redux actions not being dispatched properly")
    print("2. Redux selectors not updating component")
    print("3. Component not re-rendering when state changes")
    print("4. Logging configuration hiding the debug output")
    print()
    print("Next steps:")
    print("- Run the mobile app with DeepSeek R1")
    print("- Check console logs for the enhanced debug output")
    print("- Look for the specific log messages added to Redux slice")
    print("- Check if ThinkingFlow component logs appear")