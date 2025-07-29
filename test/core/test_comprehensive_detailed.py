#!/usr/bin/env python3
"""
Comprehensive Detailed Test Suite for Multi-Agent System
Shows all output items and validates proper agent execution
"""

import asyncio
import json
import sys
import os
from datetime import datetime
from typing import Dict, List, Any

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../src'))

# Set up TEST ENVIRONMENT
os.environ['DATABASE_URL'] = 'postgresql://postgres:12931@localhost:5454/youwoai_test'
os.environ['PUBLIC_ENV'] = 'test'

# Suppress verbose logging
import logging
for logger_name in ["httpx", "httpcore", "asyncio", "chat", "aiohttp", "urllib3"]:
    logging.getLogger(logger_name).setLevel(logging.WARNING)


class OutputTracker:
    """Track all output items from the stream"""
    
    def __init__(self):
        self.output_items = []
        self.reasoning_items = []  # Track reasoning with full content
        self.tool_calls = []
        self.response_text = ""
        self.citations = []
        self.full_events = []
        self.execution_order = []  # Track execution order
    
    def add_event(self, event):
        """Add an event and parse it"""
        self.full_events.append(event)
        event_type = event.get("type", "")
        
        if event_type == "response.output_item.added":
            item = event.get("item", {})
            item_type = item.get("type", "")
            item_id = item.get("id", "")
            
            self.output_items.append({
                "id": item_id,
                "type": item_type,
                "status": item.get("status"),
                "role": item.get("role")
            })
            
            # Track execution order
            if item_type == "reasoning":
                self.execution_order.append(f"REASONING_{item_id}")
            elif item_type.endswith("_call"):
                self.tool_calls.append(item_type)
                self.execution_order.append(f"TOOL_{item_type}")
        
        elif event_type == "response.output_item.done":
            item = event.get("item", {})
            item_type = item.get("type", "")
            item_id = item.get("id", "")
            
            # Update status for completed items
            for output_item in self.output_items:
                if output_item["id"] == item_id:
                    output_item["status"] = "completed"
            
            # Capture reasoning content
            if item_type == "reasoning" and "content" in item:
                reasoning_text = ""
                for content in item["content"]:
                    # Handle both "text" and "reasoning_text" types
                    if content.get("type") in ["text", "reasoning_text"]:
                        reasoning_text += content.get("text", "")
                
                self.reasoning_items.append({
                    "id": item_id,
                    "text": reasoning_text,
                    "order": len([x for x in self.execution_order if x.startswith("REASONING")])
                })
        
        elif event_type == "response.output_text.delta":
            self.response_text += event.get("delta", "")
        
        elif event_type == "response.output_text.annotation.added":
            self.citations.append(event.get("annotation", {}))
    
    def get_summary(self):
        """Get a formatted summary of all output items"""
        lines = []
        lines.append("OUTPUT ITEMS:")
        
        # Show execution order
        if self.execution_order:
            lines.append(f"\nExecution Order:")
            for i, item in enumerate(self.execution_order, 1):
                lines.append(f"  {i}. {item}")
        
        # Show reasoning with actual content
        if self.reasoning_items:
            lines.append(f"\nReasoning Details ({len(self.reasoning_items)} items):")
            for reasoning in self.reasoning_items:
                lines.append(f"\n  Reasoning #{reasoning['order']} (ID: {reasoning['id']}):")
                # Show first 300 chars of reasoning
                preview = reasoning['text'][:300] + "..." if len(reasoning['text']) > 300 else reasoning['text']
                # Indent the reasoning text
                indented = "\n    ".join(preview.split("\n"))
                lines.append(f"    {indented}")
        
        # Tool calls
        tool_items = [i for i in self.output_items if i["type"].endswith("_call")]
        if tool_items:
            lines.append(f"\nTool Calls ({len(tool_items)} items):")
            for item in tool_items:
                lines.append(f"  - Type: {item['type']}, ID: {item['id']}, Status: {item['status']}")
        
        # Messages
        message_items = [i for i in self.output_items if i["type"] == "message"]
        if message_items:
            lines.append(f"\nMessages ({len(message_items)} items):")
            for item in message_items:
                lines.append(f"  - ID: {item['id']}, Role: {item.get('role', 'assistant')}")
        
        # Citations
        if self.citations:
            lines.append(f"\nCitations ({len(self.citations)} items):")
            for i, cit in enumerate(self.citations[:3]):
                lines.append(f"  - [{cit.get('text')}] {cit.get('title', 'N/A')}")
        
        lines.append(f"\nResponse Text Length: {len(self.response_text)} chars")
        
        return "\n".join(lines)


async def run_test_case(test_case: Dict[str, Any]) -> Dict[str, Any]:
    """Run a single test case with detailed output tracking"""
    from chat.endpoints.multi_agent_endpoint_v2 import MultiAgentChatEndpointV2
    endpoint = MultiAgentChatEndpointV2()
    
    tracker = OutputTracker()
    start_time = datetime.now()
    
    result = {
        "name": test_case["name"],
        "passed": True,
        "errors": [],
        "execution_time": 0,
        "tracker": tracker
    }
    
    try:
        response = await endpoint.handle_request(test_case["request"])
        
        async for event in response:
            tracker.add_event(event)
        
        # Validate results
        validate = test_case.get("validate", {})
        
        # Check expected tools
        if "expected_tools" in validate:
            for expected_tool in validate["expected_tools"]:
                if expected_tool not in tracker.tool_calls:
                    result["passed"] = False
                    result["errors"].append(f"Expected tool '{expected_tool}' not found. Found: {tracker.tool_calls}")
        
        # Check should NOT have tools
        if validate.get("no_tools") and tracker.tool_calls:
            result["passed"] = False
            result["errors"].append(f"Expected no tools but found: {tracker.tool_calls}")
        
        # Check citations
        if validate.get("should_have_citations") and not tracker.citations:
            result["passed"] = False
            result["errors"].append("Expected citations but none found")
        
        # Check response content
        if "response_contains" in validate:
            for expected_content in validate["response_contains"]:
                if expected_content.lower() not in tracker.response_text.lower():
                    result["passed"] = False
                    result["errors"].append(f"Response missing expected content: '{expected_content}'")
        
        # Check response is not empty
        if validate.get("response_not_empty") and len(tracker.response_text.strip()) < 10:
            result["passed"] = False
            result["errors"].append("Response is empty or too short")
        
    except Exception as e:
        result["passed"] = False
        result["errors"].append(f"Exception: {str(e)}")
        import traceback
        result["errors"].append(traceback.format_exc())
    
    result["execution_time"] = (datetime.now() - start_time).total_seconds()
    return result


async def run_all_tests():
    """Run comprehensive test suite"""
    
    print("\n" + "="*80)
    print("COMPREHENSIVE DETAILED TEST SUITE")
    print("="*80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    # Define all test cases
    test_cases = [
        # Basic tests (no tools)
        {
            "name": "1. Simple Math",
            "request": {
                "model": "gpt-4.1-nano",
                "messages": [{"role": "user", "content": "What is 2+2?"}],
                "stream": True,
                "user_id": 10001
            },
            "validate": {
                "no_tools": True,
                "response_not_empty": True,
                "response_contains": ["4", "four"]
            }
        },
        {
            "name": "2. General Knowledge",
            "request": {
                "model": "gpt-4.1-nano",
                "messages": [{"role": "user", "content": "What is the capital of France?"}],
                "stream": True,
                "user_id": 10001
            },
            "validate": {
                "no_tools": True,
                "response_contains": ["Paris"]
            }
        },
        
        # Context Search tests
        {
            "name": "3. Context Search - PARL",
            "request": {
                "model": "gpt-4.1-nano",
                "messages": [{"role": "user", "content": "What do my notes say about PARL?"}],
                "stream": True,
                "enable_citations": True,
                "user_id": 10001
            },
            "validate": {
                "expected_tools": ["context_search_call"],
                "should_have_citations": True,
                "response_contains": ["PARL", "Predictability-Aware"]
            }
        },
        {
            "name": "4. Context Search - Note by ID",
            "request": {
                "model": "gpt-4.1-nano",
                "messages": [{"role": "user", "content": "Show me the content of note 10001"}],
                "stream": True,
                "enable_citations": True,
                "user_id": 10001
            },
            "validate": {
                "expected_tools": ["context_search_call"],
                "response_not_empty": True
            }
        },
        {
            "name": "5. Context Search - My Notes",
            "request": {
                "model": "gpt-4.1-nano",
                "messages": [{"role": "user", "content": "Search my notes for information about AI startups"}],
                "stream": True,
                "enable_citations": True,
                "user_id": 10001
            },
            "validate": {
                "expected_tools": ["context_search_call"],
                "should_have_citations": True
            }
        },
        
        # File Attachment tests
        {
            "name": "6. File Attachment - Single PDF",
            "request": {
                "model": "gpt-4.1-nano",
                "messages": [{"role": "user", "content": "Summarize this paper"}],
                "attachments": ["https://arxiv.org/pdf/2505.18499.pdf"],
                "stream": True,
                "enable_citations": True,
                "user_id": 10001
            },
            "validate": {
                "expected_tools": ["file_search_call"],
                "should_have_citations": True,
                "response_contains": ["G1", "graph"]
            }
        },
        {
            "name": "7. File Attachment - Question about PDF",
            "request": {
                "model": "gpt-4.1-nano",
                "messages": [{"role": "user", "content": "What is the main contribution of this paper?"}],
                "attachments": ["https://arxiv.org/pdf/2505.18499.pdf"],
                "stream": True,
                "enable_citations": True,
                "user_id": 10001
            },
            "validate": {
                "expected_tools": ["file_search_call"],
                "response_not_empty": True
            }
        },
        
        # Web Search tests
        {
            "name": "8. Web Search - Current Events",
            "request": {
                "model": "gpt-4.1-nano",
                "messages": [{"role": "user", "content": "What are the latest developments in quantum computing 2025?"}],
                "stream": True,
                "enable_citations": True,
                "user_id": 10001
            },
            "validate": {
                "expected_tools": ["web_search_call"],
                "should_have_citations": True,
                "response_contains": ["quantum", "2025"]
            }
        },
        {
            "name": "9. Web Search - News",
            "request": {
                "model": "gpt-4.1-nano",
                "messages": [{"role": "user", "content": "Search the web for latest AI news"}],
                "stream": True,
                "enable_citations": True,
                "user_id": 10001
            },
            "validate": {
                "expected_tools": ["web_search_call"],
                "response_not_empty": True
            }
        },
        
        # Code Interpreter tests
        {
            "name": "10. Code - Fibonacci",
            "request": {
                "model": "gpt-4.1-nano",
                "messages": [{"role": "user", "content": "Calculate the first 10 Fibonacci numbers"}],
                "stream": True,
                "user_id": 10001
            },
            "validate": {
                "expected_tools": ["code_interpreter_call"],
                "response_contains": ["0", "1", "1", "2", "3", "5", "8"]
            }
        },
        {
            "name": "11. Code - Data Analysis",
            "request": {
                "model": "gpt-4.1-nano",
                "messages": [{"role": "user", "content": "Create a Python list of squares from 1 to 10"}],
                "stream": True,
                "user_id": 10001
            },
            "validate": {
                "expected_tools": ["code_interpreter_call"],
                "response_contains": ["1", "4", "9", "16", "25"]
            }
        },
        {
            "name": "12. Code - Visualization",
            "request": {
                "model": "gpt-4.1-nano",
                "messages": [{"role": "user", "content": "Create a bar chart of values [10, 20, 15, 25, 30]"}],
                "stream": True,
                "user_id": 10001
            },
            "validate": {
                "expected_tools": ["code_interpreter_call"],
                "response_not_empty": True
            }
        },
        
        # Multi-Agent tests
        {
            "name": "13. Multi - Context + Attachment",
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
                "should_have_citations": True,
                "response_contains": ["PARL", "compare", "paper"]
            }
        },
        {
            "name": "14. Multi - Context + Web",
            "request": {
                "model": "gpt-4.1-nano",
                "messages": [{"role": "user", "content": "Compare my notes on AI startups with current trends online"}],
                "stream": True,
                "enable_citations": True,
                "user_id": 10001
            },
            "validate": {
                "expected_tools": ["context_search_call", "web_search_call"],
                "should_have_citations": True
            }
        },
        {
            "name": "15. Multi - Attachment + Code",
            "request": {
                "model": "gpt-4.1-nano",
                "messages": [{"role": "user", "content": "Analyze the data in this paper and create a summary statistics"}],
                "attachments": ["https://arxiv.org/pdf/2505.18499.pdf"],
                "stream": True,
                "user_id": 10001
            },
            "validate": {
                "expected_tools": ["file_search_call", "code_interpreter_call"],
                "response_not_empty": True
            }
        },
        
        # Edge cases
        {
            "name": "16. Edge - Empty Query",
            "request": {
                "model": "gpt-4.1-nano",
                "messages": [{"role": "user", "content": ""}],
                "stream": True,
                "user_id": 10001
            },
            "validate": {
                "response_not_empty": True
            }
        },
        {
            "name": "17. Edge - Very Long Query",
            "request": {
                "model": "gpt-4.1-nano",
                "messages": [{"role": "user", "content": "I have a very specific question about machine learning. " * 20}],
                "stream": True,
                "user_id": 10001
            },
            "validate": {
                "response_not_empty": True
            }
        },
        {
            "name": "18. Context - Conversation Search",
            "request": {
                "model": "gpt-4.1-nano",
                "messages": [{"role": "user", "content": "What did we discuss about machine learning in our conversations?"}],
                "stream": True,
                "enable_citations": True,
                "user_id": 10001
            },
            "validate": {
                "expected_tools": ["context_search_call"],
                "response_not_empty": True
            }
        },
        {
            "name": "19. Multi - All Agents",
            "request": {
                "model": "gpt-4.1-nano",
                "messages": [{"role": "user", "content": "Compare this paper with my notes and search online for related work, then create a summary table"}],
                "attachments": ["https://arxiv.org/pdf/2505.18499.pdf"],
                "stream": True,
                "enable_citations": True,
                "user_id": 10001
            },
            "validate": {
                "expected_tools": ["context_search_call", "file_search_call", "web_search_call"],
                "response_not_empty": True
            }
        },
        {
            "name": "20. Context - Specific Query",
            "request": {
                "model": "gpt-4.1-nano",
                "messages": [{"role": "user", "content": "Based on my notes, what are the main AI startup ideas I've saved?"}],
                "stream": True,
                "enable_citations": True,
                "user_id": 10001
            },
            "validate": {
                "expected_tools": ["context_search_call"],
                "should_have_citations": True,
                "response_contains": ["startup", "AI"]
            }
        }
    ]
    
    # Run all tests
    results = []
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n[{i}/{len(test_cases)}] Running: {test_case['name']}...")
        print("-" * 80)
        
        result = await run_test_case(test_case)
        results.append(result)
        
        # Display detailed results
        print(f"Status: {'✅ PASS' if result['passed'] else '❌ FAIL'}")
        print(f"Time: {result['execution_time']:.2f}s")
        
        # Show output items summary
        print("\n" + result["tracker"].get_summary())
        
        if not result["passed"]:
            print(f"\nErrors:")
            for error in result["errors"]:
                print(f"  - {error}")
        
        # Show response preview
        response_text = result["tracker"].response_text
        if response_text:
            print(f"\nResponse Preview:")
            print("-" * 40)
            preview = response_text[:300] + "..." if len(response_text) > 300 else response_text
            print(preview)
            print("-" * 40)
    
    # Summary
    passed = sum(1 for r in results if r["passed"])
    failed = len(results) - passed
    
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"Total Tests: {len(results)}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"Success Rate: {(passed/len(results))*100:.1f}%")
    
    # Group results by category
    print("\nResults by Category:")
    categories = {
        "Basic": [1, 2],
        "Context Search": [3, 4, 5, 18, 20],
        "File Attachments": [6, 7],
        "Web Search": [8, 9],
        "Code Interpreter": [10, 11, 12],
        "Multi-Agent": [13, 14, 15, 19],
        "Edge Cases": [16, 17]
    }
    
    for category, indices in categories.items():
        category_results = [results[i-1] for i in indices if i <= len(results)]
        category_passed = sum(1 for r in category_results if r["passed"])
        print(f"  {category}: {category_passed}/{len(category_results)}")
    
    if failed > 0:
        print("\n❌ Failed Tests:")
        for r in results:
            if not r["passed"]:
                print(f"\n  {r['name']}:")
                for error in r["errors"]:
                    print(f"    - {error}")
    
    print("\n" + "="*80)
    print("DETAILED TEST SUITE COMPLETED")
    print("="*80)
    
    return passed == len(results)


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)