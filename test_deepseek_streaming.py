#!/usr/bin/env python3
"""
DeepSeek R1 Streaming Analysis
Analyze the streaming events from DeepSeek R1 to understand reasoning content flow
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


async def test_deepseek_streaming():
    """Test DeepSeek R1 streaming and analyze events"""
    print("="*80)
    print("DEEPSEEK R1 STREAMING ANALYSIS")
    print("="*80)
    
    try:
        # Import endpoint
        from chat.endpoints.multi_agent_endpoint_v2 import MultiAgentChatEndpointV2
        endpoint = MultiAgentChatEndpointV2()
        
        # Test request
        request = {
            "model": "DeepSeek-R1",
            "messages": [{"role": "user", "content": "Solve this step by step: What is 15 + 27?"}],
            "stream": True,
            "user_id": 10001
        }
        
        print(f"Request: {json.dumps(request, indent=2)}")
        print("\nStreaming Events:")
        print("-" * 80)
        
        # Run request
        response = await endpoint.handle_request(request)
        
        # Track events
        event_counts = {}
        reasoning_events = []
        reasoning_content = ""
        
        if hasattr(response, '__aiter__'):
            async for event in response:
                event_type = event.get("type", "unknown")
                event_counts[event_type] = event_counts.get(event_type, 0) + 1
                
                # Print first few events of each type
                if event_counts[event_type] <= 3:
                    print(f"[{event_type}] {json.dumps(event, indent=2)}")
                    print("-" * 40)
                
                # Track reasoning specifically
                if "reasoning" in event_type.lower():
                    reasoning_events.append(event)
                    if event_type == "response.reasoning_text.delta":
                        reasoning_content += event.get("delta", "")
                
                # Also track if we get reasoning_content in delta
                if event_type == "response.output_text.delta":
                    delta = event.get("delta", "")
                    if "<think>" in delta or "</think>" in delta:
                        print(f"🧠 REASONING IN DELTA: {delta[:100]}...")
        
        print("\n" + "="*80)
        print("ANALYSIS RESULTS")
        print("="*80)
        print("Event Counts:")
        for event_type, count in sorted(event_counts.items()):
            print(f"  {event_type}: {count}")
        
        print(f"\nReasoning Events Found: {len(reasoning_events)}")
        print(f"Reasoning Content Length: {len(reasoning_content)} chars")
        
        if reasoning_content:
            print("\nReasoning Content Preview:")
            print("-" * 40)
            print(reasoning_content[:500] + ("..." if len(reasoning_content) > 500 else ""))
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    result = asyncio.run(test_deepseek_streaming())
    print(f"\nTest {'✅ PASSED' if result else '❌ FAILED'}")