#!/usr/bin/env python3
"""
Test script to verify that the ML server is properly sending search results
in output_item.done events.
"""

import asyncio
import json
import sys
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
import aiohttp

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../src'))

# Set up TEST ENVIRONMENT
os.environ['DATABASE_URL'] = 'postgresql://postgres:12931@localhost:5454/youwoai_test'
os.environ['PUBLIC_ENV'] = 'test'
os.environ['TEST_SERVER_URL'] = 'http://localhost:5002'

# Test cases specifically for search functionality
SEARCH_TEST_CASES = [
    {
        "name": "Context Search Test",
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
        "name": "Web Search Test",
        "request": {
            "model": "gpt-4.1-nano",
            "messages": [{"role": "user", "content": "Search the web for quantum computing 2025"}],
            "stream": True,
            "enable_citations": True,
            "user_id": 10001
        },
        "expected_tool": "web_search_call"
    }
]


async def test_search_output(test_case: Dict) -> Dict:
    """Run a test and collect ALL event data, especially output_item.done events"""
    print(f"\n{'='*60}")
    print(f"Test: {test_case['name']}")
    print(f"{'='*60}")
    
    results = {
        "name": test_case["name"],
        "passed": False,
        "events": [],
        "output_items": [],
        "tool_calls": [],
        "citations": [],
        "search_results_found": False,
        "errors": []
    }
    
    try:
        # Use HTTP request to test server
        url = "http://localhost:5002/v1/chat/completions"
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=test_case["request"]) as response:
                if response.status != 200:
                    results["errors"].append(f"HTTP {response.status}: {await response.text()}")
                    return results
                
                # Process streaming response
                async for line in response.content:
                    if line:
                        line_str = line.decode('utf-8').strip()
                        if line_str.startswith('data: '):
                            data_str = line_str[6:]
                            if data_str == '[DONE]':
                                break
                            
                            try:
                                event = json.loads(data_str)
                            except json.JSONDecodeError:
                                continue
                                
                            event_type = event.get("type", "")
                            results["events"].append({"type": event_type, "data": event})
                            
                            # Track output items
                            if event_type == "response.output_item.added":
                                item = event.get("item", {})
                                item_type = item.get("type")
                                print(f"  → Output item added: {item_type}")
                                if item_type and item_type.endswith("_call"):
                                    results["tool_calls"].append(item_type)
                            
                            # CRITICAL: Check for output_item.done events
                            elif event_type == "response.output_item.done":
                                item = event.get("item", {})
                                print(f"\n  🔍 OUTPUT_ITEM.DONE EVENT:")
                                print(f"     Type: {item.get('type')}")
                                print(f"     ID: {item.get('id')}")
                                
                                # Check if this contains search results
                                if 'result' in item:
                                    result = item['result']
                                    print(f"     Has result: YES")
                                    print(f"     Result type: {type(result)}")
                                    
                                    # Check for search results structure
                                    if isinstance(result, dict):
                                        if 'results' in result or 'search_results' in result:
                                            results["search_results_found"] = True
                                            print(f"     ✅ SEARCH RESULTS FOUND!")
                                            print(f"     Number of results: {len(result.get('results', result.get('search_results', [])))}")
                                            
                                            # Sample first result
                                            search_results = result.get('results', result.get('search_results', []))
                                            if search_results:
                                                first_result = search_results[0]
                                                print(f"     First result preview:")
                                                print(f"       - Title: {first_result.get('title', 'N/A')}")
                                                print(f"       - Score: {first_result.get('score', 'N/A')}")
                                                print(f"       - Content: {str(first_result.get('content', ''))[:100]}...")
                                    
                                    # Store full result for inspection
                                    results["output_items"].append({
                                        "type": item.get('type'),
                                        "id": item.get('id'),
                                        "result": result
                                    })
                                else:
                                    print(f"     Has result: NO")
                            
                            # Track citations
                            elif event_type == "response.output_text.annotation.added":
                                annotation = event.get("annotation", {})
                                results["citations"].append(annotation)
        
        # Validate results
        if test_case["expected_tool"] in results["tool_calls"]:
            print(f"\n✅ Expected tool '{test_case['expected_tool']}' was triggered")
        else:
            results["errors"].append(f"Expected tool '{test_case['expected_tool']}' not found")
        
        if results["search_results_found"]:
            print(f"✅ Search results were found in output_item.done event")
            results["passed"] = True
        else:
            print(f"❌ No search results found in output_item.done events")
            results["errors"].append("No search results in output_item.done")
        
        # Print summary of all events
        print(f"\nEvent Summary:")
        event_counts = {}
        for event in results["events"]:
            event_type = event["type"]
            event_counts[event_type] = event_counts.get(event_type, 0) + 1
        
        for event_type, count in sorted(event_counts.items()):
            print(f"  - {event_type}: {count}")
        
        return results
        
    except Exception as e:
        results["errors"].append(f"Exception: {str(e)}")
        import traceback
        traceback.print_exc()
        return results


async def main():
    """Run all search tests"""
    print("\n" + "="*80)
    print("SEARCH OUTPUT VERIFICATION TEST")
    print("="*80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Target: http://localhost:5002")
    print(f"Focus: Verifying search results in output_item.done events")
    
    all_results = []
    
    for test_case in SEARCH_TEST_CASES:
        result = await test_search_output(test_case)
        all_results.append(result)
        await asyncio.sleep(1)  # Small delay between tests
    
    # Summary
    print("\n" + "="*80)
    print("FINAL SUMMARY")
    print("="*80)
    
    passed = sum(1 for r in all_results if r["passed"])
    total = len(all_results)
    
    print(f"Passed: {passed}/{total}")
    
    for result in all_results:
        status = "✅" if result["passed"] else "❌"
        print(f"\n{status} {result['name']}:")
        print(f"   - Tool calls: {', '.join(result['tool_calls'])}")
        print(f"   - Citations: {len(result['citations'])}")
        print(f"   - Search results in output_item.done: {'YES' if result['search_results_found'] else 'NO'}")
        print(f"   - Output items collected: {len(result['output_items'])}")
        
        if result["errors"]:
            print(f"   - Errors:")
            for error in result["errors"]:
                print(f"     • {error}")
    
    # Detailed output item inspection
    print("\n" + "="*80)
    print("DETAILED OUTPUT ITEM INSPECTION")
    print("="*80)
    
    for result in all_results:
        if result["output_items"]:
            print(f"\n{result['name']} - Output Items:")
            for idx, item in enumerate(result["output_items"]):
                print(f"\n  Item {idx + 1}:")
                print(f"    Type: {item['type']}")
                print(f"    ID: {item['id']}")
                print(f"    Result structure: {json.dumps(item['result'], indent=4)[:500]}...")
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)