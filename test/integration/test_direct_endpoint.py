#!/usr/bin/env python3
"""
Direct endpoint test - bypassing HTTP to test functionality
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


async def test_direct():
    """Test directly without HTTP"""
    
    print("\n" + "="*60)
    print("DIRECT ENDPOINT TEST")
    print("="*60)
    
    # Import endpoint
    from chat.endpoints.multi_agent_endpoint_v2 import MultiAgentChatEndpointV2
    endpoint = MultiAgentChatEndpointV2()
    
    # Test cases
    test_cases = [
        {
            "name": "1. Context Search",
            "request": {
                "model": "gpt-4.1-nano",
                "messages": [{"role": "user", "content": "Search my notes for PARL"}],
                "stream": True,
                "enable_citations": True,
                "user_id": 10001
            },
            "expected_tool": "context_search_call"
        },
        {
            "name": "2. File Attachment",
            "request": {
                "model": "gpt-4.1-nano",
                "messages": [{"role": "user", "content": "Summarize this paper"}],
                "attachments": ["https://arxiv.org/pdf/2505.18499.pdf"],
                "stream": True,
                "enable_citations": True,
                "user_id": 10001
            },
            "expected_tool": "file_search_call"
        },
        {
            "name": "3. Multi-Agent (Context + Attachment)",
            "request": {
                "model": "gpt-4.1-nano",
                "messages": [{"role": "user", "content": "Compare this paper with my notes on PARL"}],
                "attachments": ["https://arxiv.org/pdf/2505.18499.pdf"],
                "stream": True,
                "enable_citations": True,
                "user_id": 10001
            },
            "expected_tools": ["context_search_call", "file_search_call"]
        }
    ]
    
    for test in test_cases:
        print(f"\n{'='*40}")
        print(f"Test: {test['name']}")
        print("-"*40)
        
        try:
            response = await endpoint.handle_request(test["request"])
            
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
                
                elif event_type == "response.output_text.delta":
                    response_text += event.get("delta", "")
                
                elif event_type == "response.output_text.annotation.added":
                    citations.append(event.get("annotation", {}))
            
            # Validate
            passed = True
            errors = []
            
            if "expected_tool" in test:
                if test["expected_tool"] not in tools_used:
                    passed = False
                    errors.append(f"Expected '{test['expected_tool']}', got {tools_used}")
            
            if "expected_tools" in test:
                for tool in test["expected_tools"]:
                    if tool not in tools_used:
                        passed = False
                        errors.append(f"Missing expected tool: '{tool}'")
            
            print(f"Status: {'✅ PASS' if passed else '❌ FAIL'}")
            print(f"Tools: {', '.join(tools_used)}")
            print(f"Citations: {len(citations)}")
            
            if errors:
                for error in errors:
                    print(f"  - {error}")
            
            print(f"\nResponse preview: {response_text[:200]}...")
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print("Key validations:")
    print("- Context search should use 'context_search_call'")
    print("- File attachments should use 'file_search_call'")
    print("- Multi-agent queries should trigger both when appropriate")


if __name__ == "__main__":
    asyncio.run(test_direct())