#!/usr/bin/env python3
"""
Test script to validate multi-agent streaming with thinking/reasoning visibility
"""

import asyncio
import json
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

# Set up TEST ENVIRONMENT
os.environ['DATABASE_URL'] = 'postgresql://postgres:12931@localhost:5454/youwoai_test'
os.environ['PUBLIC_ENV'] = 'test'


async def test_multi_agent_streaming():
    """Test multi-agent streaming with different types of queries"""
    from chat.endpoints.multi_agent_endpoint_v2 import MultiAgentChatEndpointV2
    
    endpoint = MultiAgentChatEndpointV2()
    
    # Test cases
    test_cases = [
        {
            "name": "Simple Question",
            "request": {
                "model": "gpt-4.1-nano",
                "messages": [{"role": "user", "content": "What is the capital of France?"}],
                "stream": True,
                "user_id": 10001
            }
        },
        {
            "name": "Context Search with Reasoning",
            "request": {
                "model": "gpt-4.1-nano",
                "messages": [{"role": "user", "content": "What do my notes say about AI startup ideas?"}],
                "stream": True,
                "enable_rag": True,
                "enable_citations": True,
                "user_id": 10001
            }
        },
        {
            "name": "Multi-Agent with Attachment",
            "request": {
                "model": "gpt-4.1-nano",
                "messages": [{"role": "user", "content": "Summarize this paper and compare with my notes on PARL"}],
                "attachments": ["https://arxiv.org/pdf/2505.18499.pdf"],
                "stream": True,
                "enable_rag": True,
                "enable_citations": True,
                "user_id": 10001
            }
        }
    ]
    
    for test_case in test_cases:
        print("\n" + "="*80)
        print(f"TEST: {test_case['name']}")
        print("="*80)
        
        request = test_case['request']
        
        try:
            # Track events
            events_log = []
            reasoning_text = ""
            output_text = ""
            thinking_duration = 0
            tool_calls = []
            
            print("\nStreaming response:")
            print("-" * 40)
            
            response = await endpoint.handle_request(request)
            
            async for event in response:
                events_log.append(event)
                event_type = event.get("type", "")
                
                # Show key events
                if event_type == "response.created":
                    print(f"🚀 Response started (ID: {event['response']['id']})")
                
                elif event_type == "response.output_item.added":
                    item = event.get("item", {})
                    if item.get("type") == "reasoning":
                        print(f"🤔 Thinking started...")
                    elif item.get("type", "").endswith("_call"):
                        tool_calls.append(item.get("type"))
                        print(f"🔧 Tool call: {item.get('type')}")
                
                elif event_type in ["response.reasoning_text.delta", "response.reasoning.delta"]:
                    delta = event.get("delta", "")
                    reasoning_text += delta
                    # Show reasoning progress (first 50 chars of each delta)
                    if delta:
                        preview = delta[:50] + "..." if len(delta) > 50 else delta
                        print(f"💭 {preview}")
                
                elif event_type == "response.output_text.delta":
                    delta = event.get("delta", "")
                    output_text += delta
                    # Show output progress
                    if delta:
                        print(delta, end="", flush=True)
                
                elif event_type == "response.output_item.done":
                    item = event.get("item", {})
                    if item.get("type") == "reasoning":
                        print(f"\n✅ Thinking complete")
                
                elif event_type == "response.completed":
                    print(f"\n\n🎉 Response completed")
                    if event.get("response", {}).get("metadata", {}).get("generated_title"):
                        print(f"📝 Title: {event['response']['metadata']['generated_title']}")
            
            print("\n" + "-" * 40)
            print("\nSummary:")
            print(f"- Total events: {len(events_log)}")
            print(f"- Reasoning length: {len(reasoning_text)} chars")
            print(f"- Output length: {len(output_text)} chars")
            print(f"- Tool calls: {tool_calls}")
            
            # Show reasoning preview if available
            if reasoning_text:
                print(f"\nReasoning preview:")
                print(f"{reasoning_text[:200]}..." if len(reasoning_text) > 200 else reasoning_text)
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()


async def test_event_sequence():
    """Test and display the exact sequence of events"""
    from chat.endpoints.multi_agent_endpoint_v2 import MultiAgentChatEndpointV2
    
    endpoint = MultiAgentChatEndpointV2()
    
    print("\n" + "="*80)
    print("EVENT SEQUENCE TEST")
    print("="*80)
    
    request = {
        "model": "gpt-4.1-nano",
        "messages": [{"role": "user", "content": "What are the main benefits of using React?"}],
        "stream": True,
        "enable_rag": True,
        "user_id": 10001
    }
    
    event_sequence = []
    
    response = await endpoint.handle_request(request)
    
    async for event in response:
        event_type = event.get("type", "")
        event_sequence.append({
            "type": event_type,
            "has_item": "item" in event,
            "has_delta": "delta" in event,
            "item_type": event.get("item", {}).get("type") if "item" in event else None
        })
    
    print("\nEvent Sequence:")
    for i, evt in enumerate(event_sequence, 1):
        print(f"{i:3d}. {evt['type']:<40}", end="")
        if evt['has_item']:
            print(f" [item: {evt['item_type']}]", end="")
        if evt['has_delta']:
            print(f" [has delta]", end="")
        print()
    
    # Analyze the sequence
    print("\nSequence Analysis:")
    reasoning_events = [e for e in event_sequence if "reasoning" in e['type']]
    output_events = [e for e in event_sequence if "output_text" in e['type']]
    tool_events = [e for e in event_sequence if e['item_type'] and e['item_type'].endswith('_call')]
    
    print(f"- Reasoning events: {len(reasoning_events)}")
    print(f"- Output text events: {len(output_events)}")
    print(f"- Tool call events: {len(tool_events)}")


if __name__ == "__main__":
    print("Testing Multi-Agent Streaming Implementation")
    print("=" * 80)
    
    # Run both tests
    asyncio.run(test_multi_agent_streaming())
    asyncio.run(test_event_sequence())