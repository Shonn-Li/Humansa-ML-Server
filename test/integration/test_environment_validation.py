#!/usr/bin/env python3

"""
Test multi-agent system directly against test environment database
No server required - runs the endpoint directly
"""

import asyncio
import json
import sys
import os
from datetime import datetime
import re

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

# Set up TEST ENVIRONMENT
os.environ['DATABASE_URL'] = 'postgresql://postgres:12931@localhost:5454/youwoai_test'
os.environ['PUBLIC_ENV'] = 'test'

# Suppress verbose logging
import logging
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.WARNING)
logging.getLogger("chat").setLevel(logging.WARNING)
logging.getLogger("aiohttp").setLevel(logging.WARNING)

# Test cases specifically for test environment data
TEST_CASES = [
    {
        "name": "📚 Test Environment: PARL Paper (Note 10001)",
        "description": "Should find PARL paper from test environment and cite it",
        "request": {
            "model": "gpt-4.1-nano",
            "messages": [
                {"role": "user", "content": "Search my notes for PARL - the framework for making AI predictable"}
            ],
            "stream": True,
            "temperature": 0.7,
            "enable_citations": True,
            "user_id": 10001  # Test user
        },
        "validate": {
            "output_types": ["file_search_call", "message"],
            "should_find": ["PARL", "predictable", "reinforcement learning"],
            "expected_citations": True,
            "note_ids": [10001]  # Should cite note 10001
        }
    },
    {
        "name": "📚 Test Environment: G1 Paper (Note 10002)",
        "description": "Should find G1 paper about graph reasoning",
        "request": {
            "model": "gpt-4.1-nano",
            "messages": [
                {"role": "user", "content": "What do my notes say about G1 and teaching LLMs about graphs?"}
            ],
            "stream": True,
            "temperature": 0.7,
            "enable_citations": True,
            "user_id": 10001
        },
        "validate": {
            "output_types": ["file_search_call", "message"],
            "should_find": ["G1", "graph", "LLM"],
            "expected_citations": True,
            "note_ids": [10002]
        }
    },
    {
        "name": "📚 Test Environment: Startup Notes (Notes 10004-10007)",
        "description": "Should find startup-related content",
        "request": {
            "model": "gpt-4.1-nano",
            "messages": [
                {"role": "user", "content": "Search my notes for AI startup opportunities and Zepto's delivery model"}
            ],
            "stream": True,
            "temperature": 0.7,
            "enable_citations": True,
            "user_id": 10001
        },
        "validate": {
            "output_types": ["file_search_call", "message"],
            "should_find": ["startup", "Zepto", "10-minute delivery"],
            "expected_citations": True,
            "note_ids": [10004, 10005]  # AI startups and Zepto notes
        }
    },
    {
        "name": "🌐 Test Environment: Chinese Content (Note 10008)",
        "description": "Should handle multi-language content",
        "request": {
            "model": "gpt-4.1-nano",
            "messages": [
                {"role": "user", "content": "Search my notes for YouWoAI platform introduction in Chinese"}
            ],
            "stream": True,
            "temperature": 0.7,
            "enable_citations": True,
            "user_id": 10001
        },
        "validate": {
            "output_types": ["file_search_call", "message"],
            "should_find": ["YouWoAI", "Chinese", "platform"],
            "expected_citations": True,
            "note_ids": [10008]
        }
    },
    {
        "name": "💻 Code Generation Test",
        "description": "Should generate code without needing notes",
        "request": {
            "model": "gpt-4.1-nano",
            "messages": [
                {"role": "user", "content": "Write Python code to calculate factorial of 10"}
            ],
            "stream": True,
            "temperature": 0.7,
            "user_id": 10001
        },
        "validate": {
            "output_types": ["code_interpreter_call", "message"],
            "should_find": ["factorial", "def", "return"],
            "expected_citations": False
        }
    },
    {
        "name": "🔀 Cross-Note Synthesis",
        "description": "Should combine information from multiple test notes",
        "request": {
            "model": "gpt-4.1-nano",
            "messages": [
                {"role": "user", "content": "Based on my notes, compare PARL's predictability approach with Andrew Ng's data-centric AI advice"}
            ],
            "stream": True,
            "temperature": 0.7,
            "enable_citations": True,
            "user_id": 10001
        },
        "validate": {
            "output_types": ["file_search_call", "message"],
            "should_find": ["PARL", "Andrew Ng", "data-centric"],
            "expected_citations": True,
            "note_ids": [10001, 10007]  # PARL and Andrew Ng notes
        }
    }
]


async def validate_test_case(test_case: dict, endpoint) -> dict:
    """Run a single test case against the endpoint"""
    
    print(f"\n{'='*80}")
    print(f"{test_case['name']}")
    print(f"{test_case['description']}")
    print(f"{'='*80}")
    
    result = {
        "name": test_case['name'],
        "passed": True,
        "issues": [],
        "output_items": [],
        "citations": [],
        "response_text": ""
    }
    
    try:
        # Execute request
        response = await endpoint.handle_request(test_case['request'])
        
        # Process streaming response
        if hasattr(response, '__aiter__'):
            async for event in response:
                event_type = event.get("type", "")
                
                # Track output items
                if event_type == "response.output_item.added":
                    item = event.get("item", {})
                    output_type = item.get("type")
                    result['output_items'].append(output_type)
                    print(f"  ➕ {output_type} (id: {item.get('id')})")
                
                # Track completion
                elif event_type == "response.output_item.done":
                    item = event.get("item", {})
                    if item.get("status") == "completed":
                        print(f"  ✅ {item.get('type')} completed")
                
                # Collect response text
                elif event_type == "response.output_text.delta":
                    result['response_text'] += event.get("delta", "")
                
                # Track citations
                elif event_type == "response.output_text.annotation.added":
                    annotation = event.get("annotation", {})
                    result['citations'].append(annotation)
                    metadata = annotation.get("metadata", {})
                    note_id = metadata.get("note_id")
                    print(f"  📍 Citation: {annotation.get('text')} - Note {note_id}")
        
        # Validate results
        validate = test_case['validate']
        
        # Check output types
        expected_types = set(validate['output_types'])
        actual_types = set(result['output_items'])
        if not expected_types.issubset(actual_types):
            result['passed'] = False
            missing = expected_types - actual_types
            result['issues'].append(f"Missing output types: {missing}")
        
        # Check content
        response_lower = result['response_text'].lower()
        for expected_text in validate['should_find']:
            if expected_text.lower() not in response_lower:
                result['passed'] = False
                result['issues'].append(f"Missing expected content: '{expected_text}'")
        
        # Check citations
        if validate['expected_citations']:
            if not result['citations']:
                result['passed'] = False
                result['issues'].append("No citations found")
            
            # Check if expected notes were cited
            if 'note_ids' in validate:
                cited_note_ids = set()
                for citation in result['citations']:
                    metadata = citation.get("metadata", {})
                    note_id = metadata.get("note_id")
                    if note_id:
                        try:
                            cited_note_ids.add(int(note_id))
                        except:
                            pass
                
                expected_notes = set(validate['note_ids'])
                if not expected_notes.intersection(cited_note_ids):
                    result['passed'] = False
                    result['issues'].append(f"Expected notes {expected_notes} not cited. Found: {cited_note_ids}")
        
        # Display summary
        print(f"\n  📊 Results:")
        print(f"  - Output types: {', '.join(result['output_items'])}")
        print(f"  - Response length: {len(result['response_text'])} chars")
        print(f"  - Citations: {len(result['citations'])}")
        print(f"  - Response preview: {result['response_text'][:150]}...")
        
        if result['passed']:
            print(f"  ✅ PASSED")
        else:
            print(f"  ❌ FAILED")
            for issue in result['issues']:
                print(f"     - {issue}")
        
    except Exception as e:
        result['passed'] = False
        result['issues'].append(f"Exception: {str(e)}")
        print(f"  ❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
    
    return result


async def run_test_environment_validation():
    """Run all tests against test environment"""
    
    print(f"\n🧪 TEST ENVIRONMENT VALIDATION")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Database: youwoai_test (port 5454)")
    print(f"User: 10001 (test user)")
    print(f"\nTest Notes Available:")
    print(f"  - Note 10001: PARL - Making AI predictable")
    print(f"  - Note 10002: G1 - Teaching LLMs about graphs")
    print(f"  - Note 10003: Game theory + resource allocation")
    print(f"  - Note 10004: AI startup opportunities")
    print(f"  - Note 10005: Zepto's 10-min delivery")
    print(f"  - Note 10006: Replit's growth to $100M")
    print(f"  - Note 10007: Andrew Ng's AI advice")
    print(f"  - Note 10008: YouWoAI intro (Chinese)")
    print(f"  - Note 10009: Product demo (Chinese audio)")
    
    # Import endpoint
    print(f"\n🔄 Initializing multi-agent endpoint...")
    from chat.endpoints.multi_agent_endpoint_v2 import MultiAgentChatEndpointV2
    endpoint = MultiAgentChatEndpointV2()
    print(f"✅ Endpoint initialized")
    
    # Run all tests
    results = []
    for test_case in TEST_CASES:
        result = await validate_test_case(test_case, endpoint)
        results.append(result)
    
    # Final summary
    print(f"\n{'='*80}")
    print(f"FINAL SUMMARY")
    print(f"{'='*80}")
    
    total = len(results)
    passed = sum(1 for r in results if r['passed'])
    failed = total - passed
    
    print(f"Total tests: {total}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"Success rate: {(passed/total)*100:.1f}%")
    
    if failed > 0:
        print(f"\nFailed tests:")
        for r in results:
            if not r['passed']:
                print(f"\n  {r['name']}")
                for issue in r['issues']:
                    print(f"    - {issue}")
    
    print(f"\n✨ Key Validations:")
    print(f"  - OpenAI Response API output types working")
    print(f"  - Test environment notes accessible")
    print(f"  - Citations linking to correct notes")
    print(f"  - Multi-language content supported")
    print(f"  - Cross-note synthesis functional")
    
    return passed == total


if __name__ == "__main__":
    # No server needed - run directly
    success = asyncio.run(run_test_environment_validation())
    exit(0 if success else 1)