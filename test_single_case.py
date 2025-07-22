#!/usr/bin/env python3
"""
Test a single case to debug
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

# Suppress most logging but keep some
import logging
logging.basicConfig(level=logging.INFO)
for logger_name in ["httpx", "httpcore", "asyncio", "aiohttp", "urllib3"]:
    logging.getLogger(logger_name).setLevel(logging.WARNING)


async def test_case_19():
    """Test case 19 with reasoning tracking"""
    from chat.endpoints.multi_agent_endpoint_v2 import MultiAgentChatEndpointV2
    endpoint = MultiAgentChatEndpointV2()
    
    print("\n" + "="*80)
    print("TEST CASE 19: Multi - All Agents")
    print("="*80)
    
    request = {
        "model": "gpt-4.1-nano",
        "messages": [{"role": "user", "content": "Compare this paper with my notes and search online for related work, then create a summary table"}],
        "attachments": ["https://arxiv.org/pdf/2505.18499.pdf"],
        "stream": True,
        "enable_citations": True,
        "user_id": 10001
    }
    
    print("\nRunning test...")
    print("-" * 80)
    
    try:
        # Track outputs
        execution_order = []
        reasoning_items = []
        tool_calls = []
        response_text = ""
        
        response = await endpoint.handle_request(request)
        
        async for event in response:
            event_type = event.get("type", "")
            
            if event_type == "response.output_item.added":
                item = event.get("item", {})
                item_type = item.get("type", "")
                item_id = item.get("id", "")
                
                if item_type == "reasoning":
                    execution_order.append(f"REASONING_{item_id}")
                elif item_type.endswith("_call"):
                    tool_calls.append(item_type)
                    execution_order.append(f"TOOL_{item_type}")
                    print(f"✓ Tool triggered: {item_type}")
            
            elif event_type == "response.output_item.done":
                item = event.get("item", {})
                if item.get("type") == "reasoning" and "content" in item:
                    reasoning_text = ""
                    for content in item["content"]:
                        if content.get("type") == "text":
                            reasoning_text += content.get("text", "")
                    
                    reasoning_items.append({
                        "id": item.get("id"),
                        "text": reasoning_text[:300] + "..." if len(reasoning_text) > 300 else reasoning_text
                    })
            
            elif event_type == "response.output_text.delta":
                response_text += event.get("delta", "")
        
        print(f"\nExecution Order:")
        for i, item in enumerate(execution_order, 1):
            print(f"  {i}. {item}")
        
        print(f"\nReasoning Items ({len(reasoning_items)}):")
        for i, reasoning in enumerate(reasoning_items, 1):
            print(f"\n  Reasoning #{i} (ID: {reasoning['id']}):")
            print(f"    {reasoning['text']}")
        
        print(f"\nTools Used: {', '.join(tool_calls)}")
        
        print("\nResponse Preview:")
        print("-" * 60)
        print(response_text[:400] + "..." if len(response_text) > 400 else response_text)
        print("-" * 60)
        
        # Validate
        expected_tools = ["context_search_call", "file_search_call", "web_search_call"]
        missing_tools = [t for t in expected_tools if t not in tool_calls]
        
        if missing_tools:
            print(f"\n❌ Missing expected tools: {missing_tools}")
        else:
            print(f"\n✅ All expected tools were triggered!")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*80)


if __name__ == "__main__":
    asyncio.run(test_case_19())