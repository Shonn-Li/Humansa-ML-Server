#!/usr/bin/env python
"""
Test WorkflowOrchestrator integration with API endpoint
Verifies that reasoning events are properly streamed
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime


async def test_workflow_api():
    """Test the API endpoint with WorkflowOrchestrator"""
    
    print("🧪 Testing WorkflowOrchestrator API Integration")
    print("=" * 60)
    
    # API endpoint
    url = "http://localhost:6001/v2/humansa/chat"
    
    # Test payload with debug flag
    payload = {
        "user_id": "test_user_workflow",
        "messages": [
            {"role": "user", "content": "我想买一些维生素C，有什么推荐吗？"}
        ],
        "stream": True,
        "debug": True,
        "use_workflow": True  # Flag to enable workflow orchestrator
    }
    
    print(f"📝 Query: {payload['messages'][0]['content']}")
    print(f"🔗 URL: {url}")
    print(f"🎛️  Stream: {payload['stream']}")
    print("=" * 60)
    
    # Track events
    event_types = {}
    reasoning_text = ""
    final_response = ""
    
    async with aiohttp.ClientSession() as session:
        try:
            print("\n🔄 Streaming Events:")
            print("-" * 60)
            
            async with session.post(url, json=payload) as response:
                print(f"📊 HTTP Status: {response.status}")
                
                if response.status != 200:
                    error_text = await response.text()
                    print(f"❌ Error: {error_text}")
                    return
                
                # Read streaming response
                async for line in response.content:
                    line = line.decode('utf-8').strip()
                    
                    if line.startswith('data: '):
                        data = line[6:]  # Remove 'data: ' prefix
                        
                        if data == '[DONE]':
                            print("\n✅ Stream completed")
                            break
                        
                        try:
                            event = json.loads(data)
                            event_type = event.get('type', 'unknown')
                            event_types[event_type] = event_types.get(event_type, 0) + 1
                            
                            # Display different event types
                            if event_type == 'response.created':
                                print(f"\n✅ Response Created: {event.get('response', {}).get('id', 'N/A')}")
                                
                            elif event_type == 'response.reasoning_text.delta':
                                # Capture reasoning
                                delta = event.get('delta', '')
                                reasoning_text += delta
                                print(f"💭 {delta}", end="", flush=True)
                                
                            elif event_type == 'response.output_item.added':
                                item = event.get('item', {})
                                item_type = item.get('type', 'unknown')
                                if item_type == 'reasoning':
                                    print(f"\n\n🧠 REASONING STARTS (ID: {item.get('id', 'N/A')})")
                                elif item_type == 'function_tool_call':
                                    print(f"\n\n🔧 CALLING TOOL: {item.get('name', 'Unknown')}")
                                elif item_type == 'message':
                                    print(f"\n\n💬 FINAL RESPONSE:")
                                    
                            elif event_type == 'response.output_text.delta':
                                # Capture final response
                                delta = event.get('delta', '')
                                final_response += delta
                                print(f"{delta}", end="", flush=True)
                                
                            elif event_type == 'response.usage':
                                usage = event.get('usage', {})
                                print(f"\n\n📊 Usage Stats:")
                                print(f"   - Agents Used: {usage.get('agents_used', [])}")
                                print(f"   - Duration: {usage.get('duration', 0):.2f}s")
                                
                            elif event_type == 'response.completed':
                                print(f"\n\n✅ Response Completed!")
                                
                        except json.JSONDecodeError:
                            print(f"⚠️  Invalid JSON: {data}")
            
            # Show summary
            print("\n" + "=" * 60)
            print("📈 Event Summary:")
            for event_type, count in sorted(event_types.items()):
                print(f"   - {event_type}: {count}")
            
            print(f"\n📝 Reasoning Length: {len(reasoning_text)} chars")
            print(f"📝 Response Length: {len(final_response)} chars")
            
            # Check if we got reasoning
            if reasoning_text:
                print("\n✅ SUCCESS: Reasoning events captured!")
                print(f"💭 Sample reasoning: {reasoning_text[:100]}...")
            else:
                print("\n❌ ISSUE: No reasoning events captured")
            
        except Exception as e:
            print(f"❌ Exception: {e}")
            import traceback
            traceback.print_exc()


async def test_non_streaming():
    """Test non-streaming mode"""
    
    print("\n\n🧪 Testing Non-Streaming Mode")
    print("=" * 60)
    
    url = "http://localhost:6001/v2/humansa/chat"
    
    payload = {
        "user_id": "test_user_workflow",
        "messages": [
            {"role": "user", "content": "我需要预约心内科医生"}
        ],
        "stream": False,
        "use_workflow": True
    }
    
    print(f"📝 Query: {payload['messages'][0]['content']}")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"\n📄 Response Keys: {list(data.keys())}")
                    
                    if "choices" in data:
                        content = data["choices"][0]["message"]["content"]
                        print(f"\n💬 Response Preview: {content[:200]}...")
                        
                    if "usage" in data:
                        usage = data["usage"]
                        print(f"\n📊 Agents Used: {usage.get('agents_used', [])}")
                        
                else:
                    error_text = await response.text()
                    print(f"❌ Error {response.status}: {error_text}")
                    
        except Exception as e:
            print(f"❌ Exception: {e}")


if __name__ == "__main__":
    print(f"🚀 Starting WorkflowOrchestrator Integration Test")
    print(f"📅 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"⚠️  Make sure server is running with use_workflow_orchestrator=True")
    
    # Run tests
    asyncio.run(test_workflow_api())
    asyncio.run(test_non_streaming())
    
    print("\n✅ Integration test completed!")
    print("\n📌 Expected Results:")
    print("- Should see response.reasoning_text.delta events")
    print("- Should see response.output_item.added events")
    print("- Should capture agent thinking process")
    print("- This is what test results should show!")