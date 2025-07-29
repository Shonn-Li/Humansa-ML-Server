#!/usr/bin/env python3
"""
Quick Multi-Agent System Test Suite
Tests critical functionality with faster execution
"""

import asyncio
import json
import sys
import os
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../src'))

# Set up TEST ENVIRONMENT
os.environ['DATABASE_URL'] = 'postgresql://postgres:12931@localhost:5454/youwoai_test'
os.environ['PUBLIC_ENV'] = 'test'

# Suppress verbose logging
import logging
for logger_name in ["httpx", "httpcore", "asyncio", "chat", "aiohttp"]:
    logging.getLogger(logger_name).setLevel(logging.WARNING)


# Critical test cases - focusing on tool separation
CRITICAL_TESTS = [
    {
        "name": "1. Context Search (Notes)",
        "request": {
            "model": "gpt-4.1-nano",
            "messages": [{"role": "user", "content": "Search my notes for PARL"}],
            "stream": True,
            "enable_citations": True,
            "user_id": 10001
        },
        "validate": {
            "expected_tool": "context_search_call",
            "should_have_citations": True
        }
    },
    {
        "name": "2. File Attachment Search",
        "request": {
            "model": "gpt-4.1-nano",
            "messages": [{"role": "user", "content": "Summarize this paper"}],
            "attachments": ["https://arxiv.org/pdf/2505.18499.pdf"],
            "stream": True,
            "enable_citations": True,
            "user_id": 10001
        },
        "validate": {
            "expected_tool": "file_search_call",
            "should_have_citations": True
        }
    },
    {
        "name": "3. Web Search",
        "request": {
            "model": "gpt-4.1-nano",
            "messages": [{"role": "user", "content": "Search the web for quantum computing 2025"}],
            "stream": True,
            "enable_citations": True,
            "user_id": 10001
        },
        "validate": {
            "expected_tool": "web_search_call",
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
            "expected_tool": "code_interpreter_call"
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
            "expected_tools": ["context_search_call", "file_search_call"],
            "should_have_citations": True
        }
    },
    {
        "name": "6. DeepSeek R1 Reasoning Test",
        "request": {
            "model": "DeepSeek-R1",
            "messages": [{"role": "user", "content": "Explain quantum entanglement in simple terms with step-by-step reasoning"}],
            "stream": True,
            "user_id": 10001
        },
        "validate": {
            "should_have_reasoning": True,
            "min_reasoning_length": 100
        }
    }
]


async def run_test(test_case):
    """Run a single test case"""
    print(f"\n{'='*60}")
    print(f"Test: {test_case['name']}")
    print(f"{'='*60}")
    
    try:
        # Import endpoint
        from chat.endpoints.multi_agent_endpoint_v2 import MultiAgentChatEndpointV2
        endpoint = MultiAgentChatEndpointV2()
        
        # Run request
        response = await endpoint.handle_request(test_case["request"])
        
        # Process streaming response
        tools_used = []
        citations_found = []
        full_response = ""
        reasoning_content = ""
        
        if hasattr(response, '__aiter__'):
            async for event in response:
                event_type = event.get("type", "")
                
                # Track output items
                if event_type == "response.output_item.added":
                    item = event.get("item", {})
                    item_type = item.get("type")
                    if item_type and item_type.endswith("_call"):
                        tools_used.append(item_type)
                
                # Collect response text
                elif event_type == "response.output_text.delta":
                    full_response += event.get("delta", "")
                
                # Track reasoning content
                elif event_type == "response.reasoning_text.delta":
                    reasoning_content += event.get("delta", "")
                
                # Track citations
                elif event_type == "response.output_text.annotation.added":
                    annotation = event.get("annotation", {})
                    citations_found.append(annotation)
        
        # Validate results
        validate = test_case.get("validate", {})
        passed = True
        errors = []
        
        # Check expected tool(s)
        if "expected_tool" in validate:
            if validate["expected_tool"] not in tools_used:
                passed = False
                errors.append(f"Expected tool '{validate['expected_tool']}' not found. Found: {tools_used}")
        
        if "expected_tools" in validate:
            for tool in validate["expected_tools"]:
                if tool not in tools_used:
                    passed = False
                    errors.append(f"Expected tool '{tool}' not found. Found: {tools_used}")
        
        # Check citations
        if validate.get("should_have_citations") and not citations_found:
            passed = False
            errors.append("No citations found")
        
        # Check reasoning content
        if validate.get("should_have_reasoning") and not reasoning_content:
            passed = False
            errors.append("No reasoning content found")
        
        if validate.get("min_reasoning_length") and len(reasoning_content) < validate["min_reasoning_length"]:
            passed = False
            errors.append(f"Reasoning content too short: {len(reasoning_content)} < {validate['min_reasoning_length']}")
        
        # Print results
        print(f"Status: {'✅ PASS' if passed else '❌ FAIL'}")
        print(f"Tools Used: {', '.join(tools_used)}")
        print(f"Citations: {len(citations_found)}")
        print(f"Reasoning Length: {len(reasoning_content)} chars")
        
        if not passed:
            print(f"Errors:")
            for error in errors:
                print(f"  - {error}")
        
        print(f"\nResponse Preview:")
        print(f"{'-'*60}")
        print(full_response[:500] + ("..." if len(full_response) > 500 else ""))
        print(f"{'-'*60}")
        
        return passed
        
    except Exception as e:
        print(f"Status: ❌ ERROR")
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all critical tests"""
    print("\n" + "="*60)
    print("CRITICAL MULTI-AGENT TESTS")
    print("="*60)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Tests: {len(CRITICAL_TESTS)}")
    
    # Run tests
    results = []
    for test in CRITICAL_TESTS:
        passed = await run_test(test)
        results.append(passed)
        # Small delay between tests
        await asyncio.sleep(1)
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total} ({(passed/total)*100:.0f}%)")
    
    if passed < total:
        print("\n❌ Some tests failed. Key findings:")
        print("- Context search should use 'context_search_call'")
        print("- File attachments should use 'file_search_call'")
        print("- Web search should use 'web_search_call'")
        print("- Code interpreter should use 'code_interpreter_call'")
    else:
        print("\n✅ All critical tests passed!")
        print("- Tool separation working correctly")
        print("- Citations functioning properly")
        print("- Multi-agent coordination successful")
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)