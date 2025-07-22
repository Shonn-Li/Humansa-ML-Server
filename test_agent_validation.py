#!/usr/bin/env python3

"""
Comprehensive test case to validate multi-agent system with OpenAI Response API output items
"""

import asyncio
import json
import httpx
from datetime import datetime
from typing import Dict, List, Any

# Configuration
API_URL = "http://localhost:5001/v1/multi-agent/response"  # or 5002 if using test server
API_KEY = "test-key"

# Test cases covering all agent types
TEST_CASES = [
    {
        "name": "📚 RAG/File Search Test",
        "description": "Should trigger file_search_call and return citations from notes",
        "request": {
            "model": "gpt-4.1-nano",
            "messages": [
                {"role": "user", "content": "Search my notes for information about PARL and predictable AI"}
            ],
            "stream": True,
            "temperature": 0.7,
            "enable_citations": True,
            "user_id": 10001  # Test user with notes
        },
        "expected_output_items": [
            {
                "type": "reasoning",
                "validates": "Router agent reasoning"
            },
            {
                "type": "file_search_call",
                "validates": "RAG agent file search",
                "expected_status": "completed"
            },
            {
                "type": "message",
                "validates": "Response with citations",
                "should_contain_annotations": True
            }
        ]
    },
    {
        "name": "🌐 Web Search Test",
        "description": "Should trigger web_search_call for current information",
        "request": {
            "model": "gpt-4.1-nano",
            "messages": [
                {"role": "user", "content": "What are the latest OpenAI announcements in 2025?"}
            ],
            "stream": True,
            "temperature": 0.7,
            "enable_citations": True,
            "user_id": 10001
        },
        "expected_output_items": [
            {
                "type": "reasoning",
                "validates": "Router agent reasoning"
            },
            {
                "type": "web_search_call",
                "validates": "Web search agent",
                "expected_status": "completed"
            },
            {
                "type": "message",
                "validates": "Response with web citations",
                "should_contain_annotations": True
            }
        ]
    },
    {
        "name": "💻 Code Interpreter Test",
        "description": "Should trigger code_interpreter_call for calculations",
        "request": {
            "model": "gpt-4.1-nano",
            "messages": [
                {"role": "user", "content": "Calculate the first 10 fibonacci numbers and show the code"}
            ],
            "stream": True,
            "temperature": 0.7,
            "user_id": 10001
        },
        "expected_output_items": [
            {
                "type": "reasoning",
                "validates": "Router agent reasoning"
            },
            {
                "type": "code_interpreter_call",
                "validates": "Code interpreter agent",
                "expected_status": "completed"
            },
            {
                "type": "message",
                "validates": "Response with code output"
            }
        ]
    },
    {
        "name": "🔀 Multi-Agent Test",
        "description": "Should trigger multiple agents for complex query",
        "request": {
            "model": "gpt-4.1-nano",
            "messages": [
                {"role": "user", "content": "Based on my notes about AI frameworks and current 2025 trends, create a Python visualization comparing different approaches"}
            ],
            "stream": True,
            "temperature": 0.7,
            "enable_citations": True,
            "user_id": 10001
        },
        "expected_output_items": [
            {
                "type": "reasoning",
                "validates": "Router agent reasoning"
            },
            {
                "type": "file_search_call",
                "validates": "RAG search for notes"
            },
            {
                "type": "web_search_call",
                "validates": "Web search for trends"
            },
            {
                "type": "code_interpreter_call",
                "validates": "Code for visualization"
            },
            {
                "type": "message",
                "validates": "Combined response",
                "should_contain_annotations": True
            }
        ]
    }
]


async def validate_test_case(test_case: Dict[str, Any]) -> Dict[str, Any]:
    """Run a single test case and validate output items"""
    
    print(f"\n{'='*80}")
    print(f"{test_case['name']}")
    print(f"{test_case['description']}")
    print(f"{'='*80}")
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Track results
    result = {
        "test_name": test_case['name'],
        "passed": True,
        "output_items_found": [],
        "annotations_found": [],
        "response_text": "",
        "errors": []
    }
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream('POST', API_URL, json=test_case['request'], headers=headers) as response:
                if response.status_code != 200:
                    result['passed'] = False
                    result['errors'].append(f"HTTP {response.status_code}")
                    return result
                
                # Process streaming events
                event_count = 0
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        
                        try:
                            event = json.loads(data_str)
                            event_type = event.get("type", "")
                            
                            # Track output items
                            if event_type == "response.output_item.added":
                                item = event.get("item", {})
                                item_type = item.get("type")
                                item_id = item.get("id")
                                status = item.get("status", "N/A")
                                
                                output_item = {
                                    "type": item_type,
                                    "id": item_id,
                                    "status": status,
                                    "event_type": "added"
                                }
                                result['output_items_found'].append(output_item)
                                
                                print(f"  ➕ Output item added: {item_type} (id: {item_id}, status: {status})")
                            
                            # Track item completion
                            elif event_type == "response.output_item.done":
                                item = event.get("item", {})
                                item_type = item.get("type")
                                item_id = item.get("id")
                                status = item.get("status", "N/A")
                                
                                # Update status for existing item
                                for output_item in result['output_items_found']:
                                    if output_item['id'] == item_id:
                                        output_item['final_status'] = status
                                        output_item['event_type'] = "done"
                                        print(f"  ✅ Output item done: {item_type} (id: {item_id}, status: {status})")
                            
                            # Collect response text
                            elif event_type == "response.output_text.delta":
                                result['response_text'] += event.get("delta", "")
                            
                            # Track annotations (citations)
                            elif event_type == "response.output_text.annotation.added":
                                annotation = event.get("annotation", {})
                                result['annotations_found'].append(annotation)
                                print(f"  📍 Citation: {annotation.get('text')} - {annotation.get('title')}")
                            
                            event_count += 1
                            
                        except json.JSONDecodeError:
                            continue
                
                print(f"\n  Total events processed: {event_count}")
                
    except Exception as e:
        result['passed'] = False
        result['errors'].append(str(e))
        return result
    
    # Validate expected output items
    print(f"\n  Validating expected output items:")
    found_types = {item['type'] for item in result['output_items_found']}
    
    for expected in test_case['expected_output_items']:
        expected_type = expected['type']
        validates = expected['validates']
        
        if expected_type in found_types:
            print(f"  ✅ {validates} - Found {expected_type}")
            
            # Check status if specified
            if 'expected_status' in expected:
                matching_items = [item for item in result['output_items_found'] 
                                if item['type'] == expected_type]
                if matching_items:
                    actual_status = matching_items[0].get('final_status', matching_items[0].get('status'))
                    if actual_status == expected['expected_status']:
                        print(f"     Status: {actual_status} ✓")
                    else:
                        print(f"     Status: {actual_status} (expected: {expected['expected_status']}) ✗")
                        result['passed'] = False
            
            # Check annotations if expected
            if expected.get('should_contain_annotations') and not result['annotations_found']:
                print(f"     ⚠️  No annotations found (citations expected)")
                result['passed'] = False
        else:
            print(f"  ❌ {validates} - Missing {expected_type}")
            result['passed'] = False
    
    # Summary
    print(f"\n  Response preview: {result['response_text'][:150]}...")
    print(f"  Citations found: {len(result['annotations_found'])}")
    
    return result


async def run_all_tests():
    """Run all test cases"""
    print(f"\n🧪 Multi-Agent System Validation")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"API: {API_URL}")
    
    results = []
    for test_case in TEST_CASES:
        result = await validate_test_case(test_case)
        results.append(result)
    
    # Final summary
    print(f"\n{'='*80}")
    print(f"FINAL SUMMARY")
    print(f"{'='*80}")
    
    total = len(results)
    passed = sum(1 for r in results if r['passed'])
    
    print(f"Total tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {total - passed}")
    print(f"Success rate: {(passed/total)*100:.1f}%")
    
    if passed < total:
        print(f"\nFailed tests:")
        for r in results:
            if not r['passed']:
                print(f"  - {r['test_name']}: {', '.join(r['errors'])}")
    
    return passed == total


if __name__ == "__main__":
    # Run the validation
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1)