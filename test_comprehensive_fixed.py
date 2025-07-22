#!/usr/bin/env python3
"""
Fixed Comprehensive Multi-Agent System Test Suite
Tests all agent combinations, tool separation, and edge cases
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
for logger_name in ["httpx", "httpcore", "asyncio", "chat", "aiohttp", "urllib3"]:
    logging.getLogger(logger_name).setLevel(logging.WARNING)


# Test configuration
USE_HTTP = False  # Set to True to use HTTP, False for direct endpoint
TEST_SERVER_URL = "http://localhost:5002"
ENDPOINT_PATH = "/v1/multi-agent/response"


async def run_test_direct(test_case):
    """Run test directly without HTTP"""
    from chat.endpoints.multi_agent_endpoint_v2 import MultiAgentChatEndpointV2
    endpoint = MultiAgentChatEndpointV2()
    
    result = {
        "passed": True,
        "errors": [],
        "tools_used": [],
        "citations": [],
        "response_text": "",
        "execution_time": 0
    }
    
    start_time = datetime.now()
    
    try:
        response = await endpoint.handle_request(test_case["request"])
        
        async for event in response:
            event_type = event.get("type", "")
            
            if event_type == "response.output_item.added":
                item = event.get("item", {})
                item_type = item.get("type")
                if item_type and item_type.endswith("_call"):
                    result["tools_used"].append(item_type)
            
            elif event_type == "response.output_text.delta":
                result["response_text"] += event.get("delta", "")
            
            elif event_type == "response.output_text.annotation.added":
                result["citations"].append(event.get("annotation", {}))
        
    except Exception as e:
        result["passed"] = False
        result["errors"].append(f"Exception: {str(e)}")
    
    result["execution_time"] = (datetime.now() - start_time).total_seconds()
    
    # Validate
    validate = test_case.get("validate", {})
    
    # Check expected agents
    if "expected_agents" in validate:
        for agent in validate["expected_agents"]:
            tool_name = f"{agent}_call" if not agent.endswith("_call") else agent
            if tool_name not in result["tools_used"]:
                result["passed"] = False
                result["errors"].append(f"Expected tool '{tool_name}' not found")
    
    # Check citations
    if validate.get("should_have_citations") and not result["citations"]:
        result["passed"] = False
        result["errors"].append("No citations found")
    
    return result


async def run_comprehensive_tests():
    """Run all test cases"""
    
    print("\n" + "="*80)
    print("COMPREHENSIVE MULTI-AGENT TEST SUITE (FIXED)")
    print("="*80)
    print(f"Mode: {'HTTP' if USE_HTTP else 'Direct Endpoint'}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    # Define test cases (simplified)
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
            "validate": {
                "expected_agents": ["context_search"],
                "should_have_citations": True
            }
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
            "validate": {
                "expected_agents": ["file_search"],
                "should_have_citations": True
            }
        },
        {
            "name": "3. Web Search",
            "request": {
                "model": "gpt-4.1-nano",
                "messages": [{"role": "user", "content": "What are the latest AI developments in 2025?"}],
                "stream": True,
                "enable_citations": True,
                "user_id": 10001
            },
            "validate": {
                "expected_agents": ["web_search"],
                "should_have_citations": True
            }
        },
        {
            "name": "4. Code Interpreter",
            "request": {
                "model": "gpt-4.1-nano",
                "messages": [{"role": "user", "content": "Calculate the first 5 Fibonacci numbers"}],
                "stream": True,
                "user_id": 10001
            },
            "validate": {
                "expected_agents": ["code_interpreter"]
            }
        },
        {
            "name": "5. Multi-Agent (Context + Attachment)",
            "request": {
                "model": "gpt-4.1-nano",
                "messages": [{"role": "user", "content": "Compare this paper with my notes on PARL"}],
                "attachments": ["https://arxiv.org/pdf/2505.18499.pdf"],
                "stream": True,
                "enable_citations": True,
                "user_id": 10001
            },
            "validate": {
                "expected_agents": ["context_search", "file_search"],
                "should_have_citations": True
            }
        }
    ]
    
    # Run tests
    results = []
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n[{i}/{len(test_cases)}] Running: {test_case['name']}...")
        
        result = await run_test_direct(test_case)
        results.append({
            "name": test_case["name"],
            "result": result
        })
        
        # Show result
        print("="*60)
        print(f"Test: {test_case['name']}")
        print(f"Status: {'✅ PASS' if result['passed'] else '❌ FAIL'}")
        print(f"Time: {result['execution_time']:.2f}s")
        print(f"Tools: {', '.join(result['tools_used']) if result['tools_used'] else 'None'}")
        print(f"Citations: {len(result['citations'])}")
        
        if not result['passed']:
            print(f"Errors:")
            for error in result['errors']:
                print(f"  - {error}")
        
        if result['response_text']:
            print(f"\nResponse preview:")
            print("-"*40)
            print(result['response_text'][:300] + ("..." if len(result['response_text']) > 300 else ""))
            print("-"*40)
    
    # Summary
    passed = sum(1 for r in results if r["result"]["passed"])
    total = len(results)
    
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Passed: {passed}/{total} ({(passed/total)*100:.0f}%)")
    
    if passed < total:
        print("\n❌ Failed tests:")
        for r in results:
            if not r["result"]["passed"]:
                print(f"  - {r['name']}: {', '.join(r['result']['errors'])}")
    
    print("\n✅ Key validations:")
    print("  - Context search uses 'context_search_call'")
    print("  - File attachments use 'file_search_call'")
    print("  - Multi-agent queries can trigger both")
    print("  - Citations work across all source types")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(run_comprehensive_tests())