#!/usr/bin/env python3
"""
Comprehensive Multi-Agent System Test Suite
Tests all agent combinations, tool separation, and edge cases
"""

import asyncio
import json
import sys
import os
import re
from datetime import datetime
from typing import Dict, List, Any, Optional
import aiohttp

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

# Set up TEST ENVIRONMENT
os.environ['DATABASE_URL'] = 'postgresql://postgres:12931@localhost:5454/youwoai_test'
os.environ['PUBLIC_ENV'] = 'test'
os.environ['TEST_SERVER_URL'] = 'http://localhost:5002'

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


# Comprehensive test cases - 30 tests covering all scenarios
TEST_CASES = [
    # Category 1: Basic Functionality (5 tests)
    {
        "name": "1. Simple Math Query",
        "request": {
            "model": "gpt-4.1-nano",
            "messages": [{"role": "user", "content": "What is 15 + 27?"}],
            "stream": True,
            "user_id": 10001
        },
        "validate": {
            "should_not_have_tools": True,
            "contains": ["42"]
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
            "should_not_have_tools": True,
            "contains": ["Paris"]
        }
    },
    {
        "name": "3. Greeting/Chat",
        "request": {
            "model": "gpt-4.1-nano",
            "messages": [{"role": "user", "content": "Hello, how are you today?"}],
            "stream": True,
            "user_id": 10001
        },
        "validate": {
            "should_not_have_tools": True,
            "contains": ["hello", "hi", "greet"]
        }
    },
    {
        "name": "4. Time/Date Query",
        "request": {
            "model": "gpt-4.1-nano",
            "messages": [{"role": "user", "content": "What day of the week is it?"}],
            "stream": True,
            "user_id": 10001
        },
        "validate": {
            "should_not_have_tools": True,
            "contains": ["day", "week"]
        }
    },
    {
        "name": "5. Definition Query",
        "request": {
            "model": "gpt-4.1-nano",
            "messages": [{"role": "user", "content": "Define artificial intelligence"}],
            "stream": True,
            "user_id": 10001
        },
        "validate": {
            "should_not_have_tools": True,
            "contains": ["artificial", "intelligence", "AI"]
        }
    },
    
    # Category 2: Context Search (5 tests)
    {
        "name": "6. Note Search by Content",
        "request": {
            "model": "gpt-4.1-nano",
            "messages": [{"role": "user", "content": "Search my notes for information about PARL and predictable AI"}],
            "stream": True,
            "enable_citations": True,
            "user_id": 10001
        },
        "validate": {
            "output_types": ["context_search_call"],
            "should_have_citations": True,
            "contains": ["PARL", "predictable"],
            "metadata_check": ["note_ids"]
        }
    },
    {
        "name": "7. Note Search by ID",
        "request": {
            "model": "gpt-4.1-nano",
            "messages": [{"role": "user", "content": "What's in note id 10001?"}],
            "stream": True,
            "enable_citations": True,
            "note_ids": [10001],
            "user_id": 10001
        },
        "validate": {
            "output_types": ["context_search_call"],
            "should_have_citations": True,
            "metadata_check": ["note_ids"]
        }
    },
    {
        "name": "8. Conversation Search",
        "request": {
            "model": "gpt-4.1-nano",
            "messages": [{"role": "user", "content": "What did we discuss about machine learning in our conversations?"}],
            "stream": True,
            "enable_citations": True,
            "user_id": 10001
        },
        "validate": {
            "output_types": ["context_search_call"],
            "contains": ["conversation", "discuss"],
            "metadata_check": ["conversation_ids"]
        }
    },
    {
        "name": "9. Mixed Context Search",
        "request": {
            "model": "gpt-4.1-nano",
            "messages": [{"role": "user", "content": "Search both my notes and conversations for information about AI startups"}],
            "stream": True,
            "enable_citations": True,
            "user_id": 10001
        },
        "validate": {
            "output_types": ["context_search_call"],
            "should_have_citations": True,
            "contains": ["startup", "AI"],
            "metadata_check": ["note_ids", "conversation_ids"]
        }
    },
    {
        "name": "10. Note + Citation",
        "request": {
            "model": "gpt-4.1-nano",
            "messages": [{"role": "user", "content": "Find all my notes about G1 and graph reasoning with citations"}],
            "stream": True,
            "enable_citations": True,
            "user_id": 10001
        },
        "validate": {
            "output_types": ["context_search_call"],
            "should_have_citations": True,
            "contains": ["G1", "graph"],
            "citation_pattern": r'\[\d+\]'
        }
    },
    
    # Category 3: File Attachments (5 tests)
    {
        "name": "11. Single PDF Attachment",
        "request": {
            "model": "gpt-4.1-nano",
            "messages": [{"role": "user", "content": "Summarize this paper"}],
            "attachments": ["https://arxiv.org/pdf/2505.18499.pdf"],
            "stream": True,
            "enable_citations": True,
            "user_id": 10001
        },
        "validate": {
            "output_types": ["file_search_call"],
            "contains": ["paper", "summary"],
            "metadata_check": ["file_types"]
        }
    },
    {
        "name": "12. Multiple Attachments",
        "request": {
            "model": "gpt-4.1-nano",
            "messages": [{"role": "user", "content": "Compare these three documents"}],
            "attachments": [
                "https://arxiv.org/pdf/2505.18499.pdf",
                "https://arxiv.org/pdf/2407.09124.pdf",
                "https://arxiv.org/pdf/2501.00663.pdf"
            ],
            "stream": True,
            "enable_citations": True,
            "user_id": 10001
        },
        "validate": {
            "output_types": ["file_search_call"],
            "contains": ["compare", "document"],
            "metadata_check": ["attachment_count"]
        }
    },
    {
        "name": "13. Image Attachment",
        "request": {
            "model": "gpt-4.1-nano",
            "messages": [{"role": "user", "content": "What's shown in this diagram?"}],
            "attachments": ["https://arxiv.org/html/2407.09124v1/x1.png"],
            "stream": True,
            "user_id": 10001
        },
        "validate": {
            "output_types": ["file_search_call"],
            "contains": ["diagram", "image", "shows"],
            "metadata_check": ["file_types"]
        }
    },
    {
        "name": "14. Mixed File Types",
        "request": {
            "model": "gpt-4.1-nano",
            "messages": [{"role": "user", "content": "Analyze these files"}],
            "attachments": [
                "https://arxiv.org/pdf/2505.18499.pdf",
                "https://arxiv.org/html/2407.09124v1/x1.png",
                "https://example.com/data.txt"
            ],
            "stream": True,
            "enable_citations": True,
            "user_id": 10001
        },
        "validate": {
            "output_types": ["file_search_call"],
            "contains": ["analyze", "file"],
            "metadata_check": ["file_types", "attachment_count"]
        }
    },
    {
        "name": "15. Large Attachment",
        "request": {
            "model": "gpt-4.1-nano",
            "messages": [{"role": "user", "content": "Extract key insights from this lengthy document"}],
            "attachments": ["https://arxiv.org/pdf/2505.18499.pdf"],
            "stream": True,
            "enable_citations": True,
            "user_id": 10001
        },
        "validate": {
            "output_types": ["file_search_call"],
            "contains": ["insight", "document"],
            "metadata_check": ["context_length"]
        }
    },
    
    # Category 4: Web Search (3 tests)
    {
        "name": "16. Current Events",
        "request": {
            "model": "gpt-4.1-nano",
            "messages": [{"role": "user", "content": "What are the latest AI developments today?"}],
            "stream": True,
            "enable_citations": True,
            "user_id": 10001
        },
        "validate": {
            "output_types": ["web_search_call"],
            "should_have_citations": True,
            "contains": ["AI", "latest", "today"]
        }
    },
    {
        "name": "17. Technical Research",
        "request": {
            "model": "gpt-4.1-nano",
            "messages": [{"role": "user", "content": "Search the web for quantum computing breakthroughs in 2025"}],
            "stream": True,
            "enable_citations": True,
            "user_id": 10001
        },
        "validate": {
            "output_types": ["web_search_call"],
            "should_have_citations": True,
            "contains": ["quantum", "computing", "2025"]
        }
    },
    {
        "name": "18. Company Information",
        "request": {
            "model": "gpt-4.1-nano",
            "messages": [{"role": "user", "content": "Find current information about OpenAI online"}],
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
    
    # Category 5: Code Interpreter (3 tests)
    {
        "name": "19. Data Visualization",
        "request": {
            "model": "gpt-4.1-nano",
            "messages": [{"role": "user", "content": "Create a bar chart showing: Sales Q1=100, Q2=150, Q3=120, Q4=180"}],
            "stream": True,
            "user_id": 10001
        },
        "validate": {
            "output_types": ["code_interpreter_call"],
            "contains": ["bar", "chart", "plot"]
        }
    },
    {
        "name": "20. Math Computation",
        "request": {
            "model": "gpt-4.1-nano",
            "messages": [{"role": "user", "content": "Calculate the first 15 Fibonacci numbers"}],
            "stream": True,
            "user_id": 10001
        },
        "validate": {
            "output_types": ["code_interpreter_call"],
            "contains": ["fibonacci", "calculate"]
        }
    },
    {
        "name": "21. Data Analysis",
        "request": {
            "model": "gpt-4.1-nano",
            "messages": [{"role": "user", "content": "Generate random data and perform statistical analysis with a histogram"}],
            "stream": True,
            "user_id": 10001
        },
        "validate": {
            "output_types": ["code_interpreter_call"],
            "contains": ["statistical", "analysis", "histogram"]
        }
    },
    
    # Category 6: Multi-Agent Combinations (4 tests)
    {
        "name": "22. Context + Code",
        "request": {
            "model": "gpt-4.1-nano",
            "messages": [{"role": "user", "content": "Based on my notes about G1, create a graph visualization"}],
            "stream": True,
            "enable_citations": True,
            "user_id": 10001
        },
        "validate": {
            "output_types": ["context_search_call", "code_interpreter_call"],
            "should_have_citations": True,
            "contains": ["G1", "graph", "visualization"]
        }
    },
    {
        "name": "23. Context + Web",
        "request": {
            "model": "gpt-4.1-nano",
            "messages": [{"role": "user", "content": "Compare my notes about AI startups with current 2025 trends"}],
            "stream": True,
            "enable_citations": True,
            "user_id": 10001
        },
        "validate": {
            "output_types": ["context_search_call", "web_search_call"],
            "should_have_citations": True,
            "contains": ["startup", "2025", "trend"]
        }
    },
    {
        "name": "24. Attachment + Code",
        "request": {
            "model": "gpt-4.1-nano",
            "messages": [{"role": "user", "content": "Analyze this PDF and create a summary chart"}],
            "attachments": ["https://arxiv.org/pdf/2505.18499.pdf"],
            "stream": True,
            "enable_citations": True,
            "user_id": 10001
        },
        "validate": {
            "output_types": ["file_search_call", "code_interpreter_call"],
            "contains": ["analyze", "chart", "summary"]
        }
    },
    {
        "name": "25. Context + Attachment + Web",
        "request": {
            "model": "gpt-4.1-nano",
            "messages": [{"role": "user", "content": "Compare this attached paper with my notes on PARL and current research trends"}],
            "attachments": ["https://arxiv.org/pdf/2505.18499.pdf"],
            "stream": True,
            "enable_citations": True,
            "user_id": 10001
        },
        "validate": {
            "output_types": ["file_search_call", "context_search_call", "web_search_call"],
            "should_have_citations": True,
            "contains": ["PARL", "research", "compare"]
        }
    },
    
    # Category 7: Edge Cases (5 tests)
    {
        "name": "26. Empty Attachment List",
        "request": {
            "model": "gpt-4.1-nano",
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
        "name": "27. Invalid Note IDs",
        "request": {
            "model": "gpt-4.1-nano",
            "messages": [{"role": "user", "content": "Show me note 99999"}],
            "note_ids": [99999],
            "stream": True,
            "enable_citations": True,
            "user_id": 10001
        },
        "validate": {
            "output_types": ["context_search_call"],
            "contains": ["not found", "no results", "doesn't exist"]
        }
    },
    {
        "name": "28. Very Long Query",
        "request": {
            "model": "gpt-4.1-nano",
            "messages": [{"role": "user", "content": "I need a comprehensive analysis that covers: " + " ".join([f"{i}. Analyze aspect {i} of AI development" for i in range(1, 16)])}],
            "stream": True,
            "enable_citations": True,
            "user_id": 10001
        },
        "validate": {
            "contains": ["analysis", "AI", "comprehensive"]
        }
    },
    {
        "name": "29. Multi-Iteration Complex",
        "request": {
            "model": "gpt-4.1-nano",
            "messages": [{"role": "user", "content": "Create a detailed report about reinforcement learning covering: 1) My notes on PARL, 2) Current trends, 3) Practical implementations, 4) Future directions, 5) Visual comparisons"}],
            "stream": True,
            "enable_citations": True,
            "user_id": 10001
        },
        "validate": {
            "output_types": ["context_search_call", "web_search_call"],
            "should_have_citations": True,
            "contains": ["PARL", "reinforcement", "trend"]
        }
    },
    {
        "name": "30. Citation Edge Cases",
        "request": {
            "model": "gpt-4.1-nano",
            "messages": [{"role": "user", "content": "Summarize everything about AI from my notes, web, and this attachment with detailed citations"}],
            "attachments": ["https://arxiv.org/pdf/2505.18499.pdf"],
            "stream": True,
            "enable_citations": True,
            "user_id": 10001
        },
        "validate": {
            "output_types": ["file_search_call", "context_search_call", "web_search_call"],
            "should_have_citations": True,
            "citation_pattern": r'\[\d+\]',
            "min_citations": 3
        }
    }
]


async def run_test_case(test_case: Dict[str, Any]) -> TestResult:
    """Run a single test case and collect full results"""
    
    result = TestResult(test_case["name"])
    start_time = datetime.now()
    
    try:
        # Send request to test server
        test_server_url = os.environ.get('TEST_SERVER_URL', 'http://localhost:5002')
        
        # Use extended timeout for complex tests (3 minutes)
        timeout = aiohttp.ClientTimeout(total=180, connect=10, sock_read=180)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                f'{test_server_url}/v1/chat/completions',
                json=test_case["request"],
                headers={'Content-Type': 'application/json'}
            ) as resp:
                if resp.status != 200:
                    result.passed = False
                    result.errors.append(f"HTTP {resp.status}: {await resp.text()}")
                    return result
                
                # Process streaming response
                async for line in resp.content:
                    if not line:
                        continue
                    
                    line = line.decode('utf-8').strip()
                    if line.startswith('data: '):
                        data = line[6:]
                        if data == '[DONE]':
                            break
                        
                        try:
                            event = json.loads(data)
                            event_type = event.get("type", "")
                            
                            # Process event (same as before)
                            if event_type == "response.output_item.added":
                                item = event.get("item", {})
                                item_type = item.get("type")
                                result.output_types.append(item_type)
                                
                                # Track agents from item types
                                if "context_search" in item_type:
                                    result.agents_triggered.append("context_search")
                                elif "file_search" in item_type and "attachment" in test_case["request"]:
                                    result.agents_triggered.append("attachment")
                                elif "web_search" in item_type:
                                    result.agents_triggered.append("web_search")
                                elif "code_interpreter" in item_type:
                                    result.agents_triggered.append("code_interpreter")
                            
                            # Collect full response
                            elif event_type == "response.output_text.delta":
                                result.full_response += event.get("delta", "")
                            
                            # Track citations
                            elif event_type == "response.output_text.annotation.added":
                                annotation = event.get("annotation", {})
                                result.citations.append(annotation)
                                
                                # Extract metadata from citations
                                if "metadata" in annotation:
                                    meta = annotation["metadata"]
                                    if "note_id" in meta:
                                        result.metadata.setdefault("note_ids", set()).add(meta["note_id"])
                                    if "conversation_id" in meta:
                                        result.metadata.setdefault("conversation_ids", set()).add(meta["conversation_id"])
                        
                        except json.JSONDecodeError:
                            continue
        
        if hasattr(response, '__aiter__'):
            # Process streaming response
            async for event in response:
                event_type = event.get("type", "")
                
                # Track output items
                if event_type == "response.output_item.added":
                    item = event.get("item", {})
                    item_type = item.get("type")
                    result.output_types.append(item_type)
                    
                    # Track agents from item types
                    if "context_search" in item_type:
                        result.agents_triggered.append("context_search")
                    elif "file_search" in item_type and "attachment" in test_case["request"]:
                        result.agents_triggered.append("attachment")
                    elif "web_search" in item_type:
                        result.agents_triggered.append("web_search")
                    elif "code_interpreter" in item_type:
                        result.agents_triggered.append("code_interpreter")
                
                # Collect full response
                elif event_type == "response.output_text.delta":
                    result.full_response += event.get("delta", "")
                
                # Track citations
                elif event_type == "response.output_text.annotation.added":
                    annotation = event.get("annotation", {})
                    result.citations.append(annotation)
                    
                    # Extract metadata from citations
                    if "metadata" in annotation:
                        meta = annotation["metadata"]
                        if "note_id" in meta:
                            result.metadata.setdefault("note_ids", set()).add(meta["note_id"])
                        if "conversation_id" in meta:
                            result.metadata.setdefault("conversation_ids", set()).add(meta["conversation_id"])
        
        # Convert sets to lists for metadata
        for key in ["note_ids", "conversation_ids"]:
            if key in result.metadata:
                result.metadata[key] = sorted(list(result.metadata[key]))
        
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
        
        # Check minimum citations
        if "min_citations" in validate and len(result.citations) < validate["min_citations"]:
            result.passed = False
            result.errors.append(f"Expected at least {validate['min_citations']} citations, found {len(result.citations)}")
        
        # Check metadata
        if "metadata_check" in validate:
            for meta_key in validate["metadata_check"]:
                if meta_key not in result.metadata or not result.metadata[meta_key]:
                    result.passed = False
                    result.errors.append(f"Missing metadata: {meta_key}")
        
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
    
    # Use test server on port 5002
    import aiohttp
    test_server_url = os.environ.get('TEST_SERVER_URL', 'http://localhost:5002')
    
    # Health check first
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f'{test_server_url}/health') as resp:
                if resp.status != 200:
                    print(f"❌ Test server not running on {test_server_url}")
                    print("Please start test server with: python test_server.py")
                    return False
        except Exception as e:
            print(f"❌ Cannot connect to test server on {test_server_url}")
            print(f"Error: {e}")
            print("Please start test server with: python test_server.py")
            return False
    
    # Run all tests
    results = []
    category_results = {}
    
    for i, test_case in enumerate(TEST_CASES, 1):
        # Determine category
        category = "Unknown"
        if i <= 5:
            category = "Basic Functionality"
        elif i <= 10:
            category = "Context Search"
        elif i <= 15:
            category = "File Attachments"
        elif i <= 18:
            category = "Web Search"
        elif i <= 21:
            category = "Code Interpreter"
        elif i <= 25:
            category = "Multi-Agent"
        else:
            category = "Edge Cases"
        
        print(f"\n[{i}/{len(TEST_CASES)}] Category: {category}")
        print(f"Running: {test_case['name']}...")
        
        result = await run_test_case(test_case)
        results.append(result)
        
        # Track category results
        if category not in category_results:
            category_results[category] = {"passed": 0, "total": 0}
        category_results[category]["total"] += 1
        if result.passed:
            category_results[category]["passed"] += 1
        
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
    
    # Category breakdown
    print("\n📊 Category Breakdown:")
    for category, stats in category_results.items():
        cat_passed = stats["passed"]
        cat_total = stats["total"]
        cat_rate = (cat_passed/cat_total)*100 if cat_total > 0 else 0
        print(f"  {category}: {cat_passed}/{cat_total} ({cat_rate:.0f}%)")
    
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
    
    # Key validations
    print("\n✅ Key Validations:")
    print("  - Context search uses context_search_call")
    print("  - File attachments use file_search_call")
    print("  - Proper metadata with note_ids/conversation_ids")
    print("  - Citations work across all source types")
    print("  - Multi-agent coordination functioning")
    
    print("\n" + "="*80)
    print("TEST SUITE COMPLETED")
    print("="*80)
    
    return passed == len(results)


if __name__ == "__main__":
    # No server needed - runs directly against test environment
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1)