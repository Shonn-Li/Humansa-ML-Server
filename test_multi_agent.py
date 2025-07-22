#!/usr/bin/env python3

"""
Comprehensive Multi-Agent System Test Suite
Tests all agent combinations, features, and edge cases
"""

import asyncio
import json
import sys
import os
import re
from datetime import datetime
from typing import Dict, List, Any, Optional

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

# Set up TEST ENVIRONMENT
os.environ['DATABASE_URL'] = 'postgresql://postgres:12931@localhost:5454/youwoai_test'
os.environ['PUBLIC_ENV'] = 'test'

# Suppress verbose logging
import logging
for logger_name in ["httpx", "httpcore", "asyncio", "chat", "aiohttp"]:
    logging.getLogger(logger_name).setLevel(logging.WARNING)


class TestResult:
    """Store test results with full details"""
    def __init__(self, name: str):
        self.name = name
        self.passed = False
        self.agents_triggered = []
        self.output_types = []
        self.citations = []
        self.full_response = ""
        self.errors = []
        self.execution_time = 0
        self.metadata = {}
    
    def __str__(self):
        status = "✅ PASS" if self.passed else "❌ FAIL"
        result = f"\n{'='*80}\n"
        result += f"Test: {self.name}\n"
        result += f"Status: {status}\n"
        result += f"Time: {self.execution_time:.2f}s\n"
        
        if self.agents_triggered:
            result += f"Agents: {', '.join(self.agents_triggered)}\n"
        
        if self.output_types:
            unique_types = list(dict.fromkeys(self.output_types))
            result += f"Output Types: {', '.join(unique_types)}\n"
        
        if self.citations:
            result += f"Citations: {len(self.citations)}\n"
            for i, cit in enumerate(self.citations[:3], 1):
                result += f"  {i}. {cit.get('text', '')} - {cit.get('title', 'N/A')}\n"
        
        if self.errors:
            result += f"Errors:\n"
            for error in self.errors:
                result += f"  - {error}\n"
        
        result += f"\nFull Response:\n{'-'*40}\n"
        result += self.full_response[:1000] + ("..." if len(self.full_response) > 1000 else "")
        result += f"\n{'-'*40}\n"
        
        return result


# Comprehensive test cases
TEST_CASES = [
    # 1. Simple Queries (No Tools)
    {
        "name": "1. Simple Math Query",
        "request": {
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": "What is 25 * 4?"}],
            "stream": True,
            "user_id": 10001
        },
        "validate": {
            "should_not_have_tools": True,
            "contains": ["100"]
        }
    },
    
    # 2. Note-specific Queries (RAG)
    {
        "name": "2. RAG: PARL Paper Query",
        "request": {
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": "Search my notes for information about PARL and predictable AI"}],
            "stream": True,
            "enable_citations": True,
            "user_id": 10001
        },
        "validate": {
            "output_types": ["file_search_call"],
            "should_have_citations": True,
            "contains": ["PARL", "predictable", "reinforcement"]
        }
    },
    
    {
        "name": "3. RAG: G1 Graph Reasoning",
        "request": {
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": "What do my notes say about G1 and teaching LLMs about graphs?"}],
            "stream": True,
            "enable_citations": True,
            "user_id": 10001
        },
        "validate": {
            "output_types": ["file_search_call"],
            "should_have_citations": True,
            "contains": ["G1", "graph", "LLM"]
        }
    },
    
    {
        "name": "4. RAG: Startup Notes",
        "request": {
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": "What AI startup opportunities are mentioned in my notes?"}],
            "stream": True,
            "enable_citations": True,
            "user_id": 10001
        },
        "validate": {
            "output_types": ["file_search_call"],
            "should_have_citations": True,
            "contains": ["startup", "AI", "opportunities"]
        }
    },
    
    # 3. Conversation Queries
    {
        "name": "5. Conversation: Recent Discussions",
        "request": {
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": "What did we discuss about reinforcement learning in our conversations?"}],
            "stream": True,
            "enable_citations": True,
            "user_id": 10001
        },
        "validate": {
            "output_types": ["file_search_call"],
            "contains": ["conversation", "discuss"]
        }
    },
    
    {
        "name": "6. Mixed: Notes + Conversations",
        "request": {
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": "Search both my notes and conversations for information about machine learning frameworks"}],
            "stream": True,
            "enable_citations": True,
            "user_id": 10001
        },
        "validate": {
            "output_types": ["file_search_call"],
            "should_have_citations": True,
            "contains": ["machine learning", "framework"]
        }
    },
    
    # 4. Web Search Queries
    {
        "name": "7. Web Search: Latest AI News",
        "request": {
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": "What are the latest AI breakthroughs in 2025?"}],
            "stream": True,
            "enable_citations": True,
            "user_id": 10001
        },
        "validate": {
            "output_types": ["web_search_call"],
            "should_have_citations": True,
            "contains": ["2025", "AI"]
        }
    },
    
    {
        "name": "8. Web Search: Current Events",
        "request": {
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": "What happened with OpenAI today?"}],
            "stream": True,
            "enable_citations": True,
            "user_id": 10001
        },
        "validate": {
            "output_types": ["web_search_call"],
            "should_have_citations": True,
            "contains": ["OpenAI"]
        }
    },
    
    # 5. Code Interpreter
    {
        "name": "9. Code: Fibonacci Calculation",
        "request": {
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": "Write Python code to calculate the first 20 Fibonacci numbers"}],
            "stream": True,
            "user_id": 10001
        },
        "validate": {
            "output_types": ["code_interpreter_call"],
            "contains": ["def", "fibonacci", "return"]
        }
    },
    
    {
        "name": "10. Code: Data Visualization",
        "request": {
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": "Create a bar chart showing the distribution: PDF=3, YouTube=4, Document=1, Audio=1"}],
            "stream": True,
            "user_id": 10001
        },
        "validate": {
            "output_types": ["code_interpreter_call"],
            "contains": ["matplotlib", "bar", "plot"]
        }
    },
    
    # 6. File Attachments
    {
        "name": "11. Attachment: PDF Analysis",
        "request": {
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": "Summarize the key points from this research paper"}],
            "attachments": ["https://arxiv.org/pdf/2505.18499.pdf"],
            "stream": True,
            "enable_citations": True,
            "user_id": 10001
        },
        "validate": {
            "output_types": ["reasoning"],  # Attachment agent may not show as separate output type
            "contains": ["paper", "research"]
        }
    },
    
    {
        "name": "12. Attachment: Image Analysis",
        "request": {
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": "What does this diagram show?"}],
            "attachments": ["https://arxiv.org/html/2407.09124v1/x1.png"],
            "stream": True,
            "user_id": 10001
        },
        "validate": {
            "output_types": ["reasoning"],
            "contains": ["diagram", "image", "shows"]
        }
    },
    
    {
        "name": "13. Multiple Attachments",
        "request": {
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": "Compare these two documents"}],
            "attachments": [
                "https://arxiv.org/pdf/2505.18499.pdf",
                "https://arxiv.org/pdf/2407.09124.pdf"
            ],
            "stream": True,
            "enable_citations": True,
            "user_id": 10001
        },
        "validate": {
            "output_types": ["reasoning"],
            "contains": ["compare", "document", "both"]
        }
    },
    
    # 7. Mixed Agent Scenarios
    {
        "name": "14. Mixed: RAG + Code",
        "request": {
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": "Based on my notes about G1, create a simple graph visualization example"}],
            "stream": True,
            "enable_citations": True,
            "user_id": 10001
        },
        "validate": {
            "output_types": ["file_search_call", "code_interpreter_call"],
            "should_have_citations": True,
            "contains": ["G1", "graph", "visualization"]
        }
    },
    
    {
        "name": "15. Mixed: RAG + Web Search",
        "request": {
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": "How do my notes about AI startups compare to current 2025 trends?"}],
            "stream": True,
            "enable_citations": True,
            "user_id": 10001
        },
        "validate": {
            "output_types": ["file_search_call", "web_search_call"],
            "should_have_citations": True,
            "contains": ["startup", "2025", "trend"]
        }
    },
    
    {
        "name": "16. Mixed: Web + Code",
        "request": {
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": "Search for the latest stock prices of AI companies and create a chart"}],
            "stream": True,
            "enable_citations": True,
            "user_id": 10001
        },
        "validate": {
            "output_types": ["web_search_call", "code_interpreter_call"],
            "should_have_citations": True,
            "contains": ["stock", "AI", "chart"]
        }
    },
    
    # 8. Complex Queries
    {
        "name": "17. Complex: Multi-Source Analysis",
        "request": {
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": "Based on my PARL and G1 notes, current AI trends, and this attachment, create a comprehensive analysis of AI predictability approaches"}],
            "attachments": ["https://arxiv.org/pdf/2505.18499.pdf"],
            "stream": True,
            "enable_citations": True,
            "user_id": 10001
        },
        "validate": {
            "output_types": ["file_search_call", "web_search_call"],
            "should_have_citations": True,
            "contains": ["PARL", "G1", "predictability", "analysis"]
        }
    },
    
    # 9. Citation-specific Tests
    {
        "name": "18. Citation Format Test",
        "request": {
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": "List all the key points from my notes about Zepto's delivery model with proper citations"}],
            "stream": True,
            "enable_citations": True,
            "user_id": 10001
        },
        "validate": {
            "output_types": ["file_search_call"],
            "should_have_citations": True,
            "citation_pattern": r'\[\d+\]',
            "contains": ["Zepto", "delivery", "["]
        }
    },
    
    # 10. Edge Cases
    {
        "name": "19. Empty Attachment List",
        "request": {
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": "Analyze the attached files"}],
            "attachments": [],
            "stream": True,
            "user_id": 10001
        },
        "validate": {
            "contains": ["no files", "no attachments", "attach"]
        }
    },
    
    {
        "name": "20. Very Long Query",
        "request": {
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": "I need a comprehensive analysis that covers the following points: " + " ".join([f"{i}. Analyze aspect {i} of AI development" for i in range(1, 11)])}],
            "stream": True,
            "enable_citations": True,
            "user_id": 10001
        },
        "validate": {
            "contains": ["analysis", "AI"]
        }
    },
    
    # 11. Specific Tool Tests
    {
        "name": "21. Force Web Search Only",
        "request": {
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": "Search the web for information about quantum computing breakthroughs today"}],
            "stream": True,
            "enable_citations": True,
            "user_id": 10001
        },
        "validate": {
            "output_types": ["web_search_call"],
            "should_have_citations": True,
            "contains": ["quantum", "computing"]
        }
    },
    
    {
        "name": "22. Force RAG Only",
        "request": {
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": "Only using my notes, what do I have about Andrew Ng's advice?"}],
            "stream": True,
            "enable_citations": True,
            "user_id": 10001
        },
        "validate": {
            "output_types": ["file_search_call"],
            "should_have_citations": True,
            "contains": ["Andrew Ng", "advice"]
        }
    }
]


async def run_test_case(test_case: Dict[str, Any], endpoint) -> TestResult:
    """Run a single test case and collect full results"""
    
    result = TestResult(test_case["name"])
    start_time = datetime.now()
    
    try:
        response = await endpoint.handle_request(test_case["request"])
        
        if hasattr(response, '__aiter__'):
            # Process streaming response
            async for event in response:
                event_type = event.get("type", "")
                
                # Track output items
                if event_type == "response.output_item.added":
                    item = event.get("item", {})
                    item_type = item.get("type")
                    result.output_types.append(item_type)
                    
                    # Track agents from item IDs
                    item_id = item.get("id", "")
                    if "router" in item_id:
                        result.agents_triggered.append("router")
                    elif "fs_" in item_id or "file_search" in item_type:
                        result.agents_triggered.append("rag")
                    elif "ws_" in item_id or "web_search" in item_type:
                        result.agents_triggered.append("web_search")
                    elif "ci_" in item_id or "code_interpreter" in item_type:
                        result.agents_triggered.append("code_interpreter")
                
                # Collect full response
                elif event_type == "response.output_text.delta":
                    result.full_response += event.get("delta", "")
                
                # Track citations
                elif event_type == "response.output_text.annotation.added":
                    annotation = event.get("annotation", {})
                    result.citations.append(annotation)
        
        # Validate results
        validate = test_case.get("validate", {})
        result.passed = True
        
        # Check output types
        if "output_types" in validate:
            expected = set(validate["output_types"])
            actual = set(result.output_types)
            if not expected.issubset(actual):
                result.passed = False
                result.errors.append(f"Missing output types: {expected - actual}")
        
        # Check if should NOT have tools
        if validate.get("should_not_have_tools"):
            tool_types = [t for t in result.output_types if t not in ["reasoning", "message"]]
            if tool_types:
                result.passed = False
                result.errors.append(f"Unexpected tool usage: {tool_types}")
        
        # Check content
        if "contains" in validate:
            response_lower = result.full_response.lower()
            for expected in validate["contains"]:
                if expected.lower() not in response_lower:
                    result.passed = False
                    result.errors.append(f"Missing expected content: '{expected}'")
        
        # Check citations
        if validate.get("should_have_citations") and not result.citations:
            result.passed = False
            result.errors.append("No citations found")
        
        # Check citation pattern
        if "citation_pattern" in validate:
            pattern = re.compile(validate["citation_pattern"])
            if not pattern.search(result.full_response):
                result.passed = False
                result.errors.append("Citation pattern not found in response")
        
    except Exception as e:
        result.passed = False
        result.errors.append(f"Exception: {str(e)}")
    
    result.execution_time = (datetime.now() - start_time).total_seconds()
    return result


async def run_all_tests():
    """Run all test cases"""
    
    print("\n" + "="*80)
    print("COMPREHENSIVE MULTI-AGENT TEST SUITE")
    print("="*80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Environment: Test Database (postgresql://localhost:5454/youwoai_test)")
    print(f"Total Test Cases: {len(TEST_CASES)}")
    print("="*80)
    
    # Import endpoint
    from chat.endpoints.multi_agent_endpoint_v2 import MultiAgentChatEndpointV2
    endpoint = MultiAgentChatEndpointV2()
    
    # Run all tests
    results = []
    for i, test_case in enumerate(TEST_CASES, 1):
        print(f"\n[{i}/{len(TEST_CASES)}] Running: {test_case['name']}...")
        result = await run_test_case(test_case, endpoint)
        results.append(result)
        print(result)
    
    # Summary statistics
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    passed = sum(1 for r in results if r.passed)
    failed = len(results) - passed
    
    print(f"Total: {len(results)}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"Success Rate: {(passed/len(results))*100:.1f}%")
    
    # Agent usage statistics
    print("\n📊 Agent Usage Statistics:")
    agent_counts = {}
    for result in results:
        for agent in result.agents_triggered:
            agent_counts[agent] = agent_counts.get(agent, 0) + 1
    
    for agent, count in sorted(agent_counts.items()):
        print(f"  - {agent}: {count} times")
    
    # Output type statistics
    print("\n📋 Output Type Statistics:")
    output_counts = {}
    for result in results:
        for output_type in set(result.output_types):
            output_counts[output_type] = output_counts.get(output_type, 0) + 1
    
    for output_type, count in sorted(output_counts.items()):
        print(f"  - {output_type}: {count} times")
    
    # Citation statistics
    total_citations = sum(len(r.citations) for r in results)
    tests_with_citations = sum(1 for r in results if r.citations)
    print(f"\n📍 Citation Statistics:")
    print(f"  - Total citations: {total_citations}")
    print(f"  - Tests with citations: {tests_with_citations}")
    
    # Failed test details
    if failed > 0:
        print("\n❌ Failed Tests:")
        for r in results:
            if not r.passed:
                print(f"\n  {r.name}:")
                for error in r.errors:
                    print(f"    - {error}")
    
    print("\n" + "="*80)
    print("TEST SUITE COMPLETED")
    print("="*80)
    
    return passed == len(results)


if __name__ == "__main__":
    # No server needed - runs directly against test environment
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1)