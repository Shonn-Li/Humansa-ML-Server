#!/usr/bin/env python3

"""
Test OpenAI Response API output types
"""

import asyncio
import json
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

# Set up environment
os.environ['DATABASE_URL'] = os.environ.get('DATABASE_URL', 'postgresql://postgres:12931@localhost:5454/youwoai_test')

# Suppress verbose logging
import logging
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.WARNING)
logging.getLogger("chat").setLevel(logging.WARNING)

async def test_output_types():
    """Test that output types match OpenAI Response API"""
    
    print("\n" + "="*70)
    print("OPENAI RESPONSE API OUTPUT TYPE VALIDATION")
    print("="*70)
    
    # Import the endpoint
    from chat.endpoints.multi_agent_endpoint_v2 import MultiAgentChatEndpointV2
    endpoint = MultiAgentChatEndpointV2()
    
    # Test cases
    tests = [
        {
            "name": "File Search (RAG)",
            "query": "Search my notes for information about PARL and machine learning",
            "expect_output_type": "file_search_call"
        },
        {
            "name": "Web Search",
            "query": "What are the latest OpenAI announcements in 2025?",
            "expect_output_type": "web_search_call"
        },
        {
            "name": "Code Interpreter",
            "query": "Calculate the fibonacci sequence up to 10",
            "expect_output_type": "code_interpreter_call"
        }
    ]
    
    results = []
    
    for test in tests:
        print(f"\n📋 {test['name']}")
        print("-" * 50)
        
        request = {
            "model": "gpt-4.1-nano",
            "messages": [{"role": "user", "content": test['query']}],
            "stream": True,
            "temperature": 0.7,
            "enable_citations": True,
            "user_id": 10001
        }
        
        try:
            response = await endpoint.handle_request(request)
            
            # Track output items
            output_items = []
            found_expected_type = False
            
            async for event in response:
                # Collect output item types
                if event.get("type") == "response.output_item.added":
                    item = event.get("item", {})
                    item_type = item.get("type")
                    item_id = item.get("id", "")
                    output_items.append({
                        "type": item_type,
                        "id": item_id,
                        "status": item.get("status")
                    })
                    
                    if item_type == test["expect_output_type"]:
                        found_expected_type = True
                        print(f"✅ Found {item_type} (id: {item_id})")
                
                # Check completion status
                elif event.get("type") == "response.output_item.done":
                    item = event.get("item", {})
                    if item.get("type") == test["expect_output_type"]:
                        status = item.get("status")
                        print(f"   Status: {status}")
            
            # Results
            if found_expected_type:
                print(f"✅ PASS: Found expected output type '{test['expect_output_type']}'")
                results.append({"test": test['name'], "status": "PASS"})
            else:
                print(f"❌ FAIL: Expected '{test['expect_output_type']}' not found")
                print(f"   Found output types: {[item['type'] for item in output_items]}")
                results.append({"test": test['name'], "status": "FAIL"})
            
        except Exception as e:
            print(f"❌ ERROR: {str(e)[:100]}...")
            results.append({"test": test['name'], "status": "ERROR"})
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    passed = sum(1 for r in results if r['status'] == "PASS")
    total = len(results)
    
    print(f"Total: {total} tests")
    print(f"Passed: {passed}")
    print(f"Failed: {total - passed}")
    
    if passed == total:
        print("\n✅ All output types match OpenAI Response API!")
    else:
        print("\n❌ Some output types don't match OpenAI Response API")
    
    print("="*70)
    print()
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(test_output_types())
    exit(0 if success else 1)