#!/usr/bin/env python3
"""
Test context search functionality specifically
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


async def test_context_search():
    """Test context search tool specifically"""
    
    print("\n" + "="*60)
    print("CONTEXT SEARCH TEST")
    print("="*60)
    
    # Import endpoint
    from chat.endpoints.multi_agent_endpoint_v2 import MultiAgentChatEndpointV2
    endpoint = MultiAgentChatEndpointV2()
    
    # Test cases
    test_cases = [
        {
            "name": "Context Search (Notes)",
            "content": "Search my notes for information about PARL",
            "expected_tool": "context_search_call"
        },
        {
            "name": "File Attachment",
            "content": "Summarize this paper",
            "attachments": ["https://arxiv.org/pdf/2505.18499.pdf"],
            "expected_tool": "file_search_call"
        },
        {
            "name": "Web Search",
            "content": "Search the web for quantum computing 2025",
            "expected_tool": "web_search_call"
        }
    ]
    
    for test in test_cases:
        print(f"\n{'='*40}")
        print(f"Test: {test['name']}")
        print(f"Query: {test['content']}")
        print("-"*40)
        
        request = {
            "model": "gpt-4.1-nano",
            "messages": [{"role": "user", "content": test["content"]}],
            "stream": True,
            "enable_citations": True,
            "user_id": 10001
        }
        
        if "attachments" in test:
            request["attachments"] = test["attachments"]
        
        try:
            response = await endpoint.handle_request(request)
            
            tools_used = []
            citations = []
            response_text = ""
            
            async for event in response:
                event_type = event.get("type", "")
                
                if event_type == "response.output_item.added":
                    item = event.get("item", {})
                    item_type = item.get("type")
                    if item_type and item_type.endswith("_call"):
                        tools_used.append(item_type)
                        print(f"✅ Tool triggered: {item_type}")
                
                elif event_type == "response.output_text.delta":
                    response_text += event.get("delta", "")
                
                elif event_type == "response.output_text.annotation.added":
                    annotation = event.get("annotation", {})
                    citations.append(annotation)
            
            # Validate
            if test["expected_tool"] in tools_used:
                print(f"✅ PASS: Expected tool '{test['expected_tool']}' was used")
            else:
                print(f"❌ FAIL: Expected '{test['expected_tool']}', got {tools_used}")
            
            print(f"Citations: {len(citations)}")
            print(f"Response preview: {response_text[:200]}...")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*60)
    print("KEY FINDINGS:")
    print("- context_search_call: For user's notes and conversations")
    print("- file_search_call: For file attachments only")
    print("- web_search_call: For web searches")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(test_context_search())