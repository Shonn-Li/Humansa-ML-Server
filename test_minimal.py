#!/usr/bin/env python3
"""
Minimal test to verify multi-agent system functionality
"""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

# Set up TEST ENVIRONMENT
os.environ['DATABASE_URL'] = 'postgresql://postgres:12931@localhost:5454/youwoai_test'
os.environ['PUBLIC_ENV'] = 'test'

# Suppress verbose logging
import logging
for logger_name in ["httpx", "httpcore", "asyncio", "chat", "aiohttp"]:
    logging.getLogger(logger_name).setLevel(logging.WARNING)


async def test_minimal():
    """Run a minimal test directly"""
    
    print("\n" + "="*60)
    print("MINIMAL MULTI-AGENT TEST")
    print("="*60)
    
    # Import endpoint
    from chat.endpoints.multi_agent_endpoint_v2 import MultiAgentChatEndpointV2
    endpoint = MultiAgentChatEndpointV2()
    
    # Simple test request
    request = {
        "model": "gpt-4.1-nano",
        "messages": [{"role": "user", "content": "What is 2+2?"}],
        "stream": True,
        "user_id": 10001
    }
    
    print("Request:", request["messages"][0]["content"])
    print("-"*60)
    
    try:
        response = await endpoint.handle_request(request)
        
        tools_used = []
        response_text = ""
        
        async for event in response:
            event_type = event.get("type", "")
            
            if event_type == "response.output_item.added":
                item = event.get("item", {})
                item_type = item.get("type")
                if item_type and item_type != "reasoning" and item_type != "message":
                    tools_used.append(item_type)
                    print(f"✅ Tool: {item_type}")
            
            elif event_type == "response.output_text.delta":
                response_text += event.get("delta", "")
        
        print(f"\nTools used: {tools_used if tools_used else 'None (direct response)'}")
        print(f"Response: {response_text}")
        print("\n✅ Test completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_minimal())