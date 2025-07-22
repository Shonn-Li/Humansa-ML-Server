#!/usr/bin/env python3
"""
Simple validation script for YouWoAI ML Server
Run this to quickly verify the multi-agent system is working correctly
"""

import asyncio
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
for logger_name in ["httpx", "httpcore", "asyncio", "chat", "aiohttp", "urllib3"]:
    logging.getLogger(logger_name).setLevel(logging.WARNING)


async def run_validation():
    """Run validation tests"""
    from chat.endpoints.multi_agent_endpoint_v2 import MultiAgentChatEndpointV2
    endpoint = MultiAgentChatEndpointV2()
    
    print("\n" + "="*60)
    print("YouWoAI ML Server Validation")
    print("="*60)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Running direct endpoint tests (no server needed)")
    print("="*60)
    
    # Define validation tests
    tests = [
        {
            "name": "Context Search",
            "request": {
                "model": "gpt-4.1-nano",
                "messages": [{"role": "user", "content": "Search my notes for PARL"}],
                "stream": True,
                "enable_citations": True,
                "user_id": 10001
            },
            "expected": "context_search_call"
        },
        {
            "name": "File Attachment",
            "request": {
                "model": "gpt-4.1-nano",
                "messages": [{"role": "user", "content": "Summarize this paper"}],
                "attachments": ["https://arxiv.org/pdf/2505.18499.pdf"],
                "stream": True,
                "enable_citations": True,
                "user_id": 10001
            },
            "expected": "file_search_call"
        },
        {
            "name": "Multi-Agent",
            "request": {
                "model": "gpt-4.1-nano",
                "messages": [{"role": "user", "content": "Compare this paper with my notes on PARL"}],
                "attachments": ["https://arxiv.org/pdf/2505.18499.pdf"],
                "stream": True,
                "enable_citations": True,
                "user_id": 10001
            },
            "expected": ["context_search_call", "file_search_call"]
        }
    ]
    
    passed = 0
    
    for test in tests:
        print(f"\nTest: {test['name']}")
        print("-" * 40)
        
        try:
            tools_used = []
            citations = 0
            
            response = await endpoint.handle_request(test["request"])
            
            async for event in response:
                event_type = event.get("type", "")
                
                if event_type == "response.output_item.added":
                    item = event.get("item", {})
                    item_type = item.get("type")
                    if item_type and item_type.endswith("_call"):
                        tools_used.append(item_type)
                
                elif event_type == "response.output_text.annotation.added":
                    citations += 1
            
            # Validate
            expected = test["expected"]
            if isinstance(expected, str):
                expected = [expected]
            
            success = all(tool in tools_used for tool in expected)
            
            if success:
                print(f"✅ PASS - {', '.join(tools_used)}")
                if citations > 0:
                    print(f"   Citations: {citations}")
                passed += 1
            else:
                print(f"❌ FAIL - Expected {expected}, got {tools_used}")
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
    
    # Summary
    total = len(tests)
    print("\n" + "="*60)
    print("VALIDATION SUMMARY")
    print("="*60)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("\n✅ All validations passed!")
        print("\nThe multi-agent system is working correctly:")
        print("- Context search properly uses 'context_search_call'")
        print("- File attachments properly use 'file_search_call'")
        print("- Multi-agent queries can trigger both agents")
    else:
        print("\n⚠️  Some validations failed")
        print("Please check the errors above")
    
    print("="*60)
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(run_validation())
    sys.exit(0 if success else 1)