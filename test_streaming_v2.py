#!/usr/bin/env python3
"""
Test the ML server's v2 streaming response independently.
This will help identify if the issue is in the ML server itself.
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime

# Configuration
ML_SERVER_URL = "http://localhost:5002"  # Use test server port
ENDPOINT = "/humansa/response"

# Test request
test_request = {
    "messages": [
        {
            "role": "user",
            "content": "What is 2+2? Also, search for the weather in San Francisco today."
        }
    ],
    "model": "gpt-4.1-nano",
    "stream": True,
    "user_id": 10001,
    "enable_rag": False,
    "enable_web_search": True,
    "use_o3_demo": False  # Use regular Humansa implementation
}

async def test_streaming():
    """Test streaming response from ML server."""
    print(f"\n{'='*60}")
    print(f"Testing ML Server Streaming - {datetime.now()}")
    print(f"{'='*60}")
    print(f"URL: {ML_SERVER_URL}{ENDPOINT}")
    print(f"Request: {json.dumps(test_request, indent=2)}")
    print(f"{'='*60}\n")
    
    event_count = 0
    final_response_events = []
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{ML_SERVER_URL}{ENDPOINT}",
                json=test_request,
                headers={"Content-Type": "application/json"}
            ) as response:
                print(f"Response status: {response.status}")
                print(f"Response headers: {dict(response.headers)}")
                print(f"\n{'='*60}")
                print("STREAMING EVENTS:")
                print(f"{'='*60}\n")
                
                async for line in response.content:
                    if line:
                        line_str = line.decode('utf-8').strip()
                        if line_str:
                            event_count += 1
                            print(f"[Event {event_count}] Raw: {line_str[:200]}{'...' if len(line_str) > 200 else ''}")
                            
                            # Try to parse as JSON
                            try:
                                # Handle SSE format (data: prefix)
                                if line_str.startswith('data: '):
                                    json_str = line_str[6:]  # Remove 'data: ' prefix
                                    if json_str == '[DONE]':
                                        print(f"  📍 Stream finished signal received")
                                        continue
                                    event_data = json.loads(json_str)
                                else:
                                    event_data = json.loads(line_str)
                                    
                                event_type = event_data.get('type', 'unknown')
                                
                                print(f"[Event {event_count}] Type: {event_type}")
                                
                                # Track final response events
                                if event_type == "response.output_item.added":
                                    item = event_data.get('item', {})
                                    if item.get('type') == 'message' and item.get('role') == 'assistant':
                                        print(f"  🎯 FINAL RESPONSE ITEM ADDED: {item.get('id')}")
                                        final_response_events.append(event_data)
                                
                                elif event_type == "response.output_text.delta":
                                    delta = event_data.get('delta', '')
                                    print(f"  📝 TEXT DELTA: {delta[:100]}{'...' if len(delta) > 100 else ''}")
                                    final_response_events.append(event_data)
                                
                                elif event_type == "response.output_text.done":
                                    text = event_data.get('text', '')
                                    print(f"  ✅ TEXT DONE: {text[:100]}{'...' if len(text) > 100 else ''}")
                                    final_response_events.append(event_data)
                                
                                elif event_type == "response.output_item.done":
                                    item = event_data.get('item', {})
                                    if item.get('type') == 'message' and item.get('role') == 'assistant':
                                        print(f"  ✅ FINAL RESPONSE ITEM DONE: {item.get('id')}")
                                        final_response_events.append(event_data)
                                
                                # Log other important events
                                elif event_type == "response.reasoning_text.delta":
                                    delta = event_data.get('delta', '')
                                    print(f"  🧠 REASONING: {delta[:50]}...")
                                
                                elif event_type == "response.function_tool_call.delta":
                                    print(f"  🔧 TOOL CALL")
                                
                                print()
                                
                            except json.JSONDecodeError as e:
                                print(f"  ⚠️ Failed to parse JSON: {e}")
                                print()
                
                print(f"\n{'='*60}")
                print("STREAMING SUMMARY:")
                print(f"{'='*60}")
                print(f"Total events received: {event_count}")
                print(f"Final response events: {len(final_response_events)}")
                
                if final_response_events:
                    print(f"\n{'='*60}")
                    print("FINAL RESPONSE EVENTS DETAIL:")
                    print(f"{'='*60}")
                    for i, event in enumerate(final_response_events):
                        print(f"\nEvent {i+1}:")
                        print(json.dumps(event, indent=2))
                
    except Exception as e:
        print(f"\n❌ Error during streaming test: {e}")
        import traceback
        traceback.print_exc()

async def test_non_streaming():
    """Test non-streaming response for comparison."""
    print(f"\n\n{'='*60}")
    print("Testing Non-Streaming Response")
    print(f"{'='*60}\n")
    
    non_streaming_request = test_request.copy()
    non_streaming_request['stream'] = False
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{ML_SERVER_URL}{ENDPOINT}",
                json=non_streaming_request,
                headers={"Content-Type": "application/json"}
            ) as response:
                result = await response.json()
                print(f"Response status: {response.status}")
                print(f"Response:\n{json.dumps(result, indent=2)}")
                
                if 'choices' in result:
                    content = result['choices'][0]['message']['content']
                    print(f"\n📝 Final content: {content}")
                
    except Exception as e:
        print(f"\n❌ Error during non-streaming test: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Run all tests."""
    print("🚀 Starting ML Server Streaming Tests")
    
    # Test streaming
    await test_streaming()
    
    # Test non-streaming for comparison
    await test_non_streaming()
    
    print("\n✅ Tests completed")

if __name__ == "__main__":
    asyncio.run(main())