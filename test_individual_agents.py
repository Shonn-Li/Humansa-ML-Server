#!/usr/bin/env python3
"""
Individual Agent Tests - Phase 1 of Multi-Agent V2 Validation
Tests each agent in isolation with specific test cases.
"""

import asyncio
import json
import logging
import sys
import os
import time
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class TestResult:
    """Container for test results"""
    agent_name: str
    test_case: str
    success: bool
    error: str = ""
    execution_time: float = 0.0
    details: Dict[str, Any] = None
    

class AgentTestSuite:
    """Test suite for individual agents"""
    
    def __init__(self):
        self.results: List[TestResult] = []
        self.endpoint = None
        
    async def setup(self):
        """Initialize the multi-agent endpoint"""
        try:
            from chat.endpoints.multi_agent_endpoint_v2 import MultiAgentChatEndpointV2
            self.endpoint = MultiAgentChatEndpointV2()
            logger.info("✅ Multi-agent endpoint initialized successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to initialize endpoint: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def test_router_agent(self) -> List[TestResult]:
        """Test RouterAgent with various query types"""
        logger.info("\n🧭 Testing RouterAgent")
        results = []
        
        test_cases = [
            {
                "name": "knowledge_base_query",
                "query": "What are my notes about machine learning?",
                "expected_tool": ["knowledge_base_notes", "knowledge_base_full"],
                "expected_agents": ["rag", "response", "citation"]
            },
            {
                "name": "web_search_query", 
                "query": "Latest news about OpenAI announcements",
                "expected_tool": ["web_search"],
                "expected_agents": ["web_search", "response", "citation"]
            },
            {
                "name": "code_query",
                "query": "Calculate fibonacci sequence in python",
                "expected_tool": ["no_context"],  # Router might not recognize, but code keywords trigger
                "expected_agents": ["code_interpreter", "response", "citation"]
            },
            {
                "name": "attachment_query",
                "query": "Analyze this document",
                "attachments": [{"type": "pdf", "url": "test.pdf", "filename": "test.pdf"}],
                "expected_tool": ["attachments"],
                "expected_agents": ["attachment", "response", "citation"]
            }
        ]
        
        for test_case in test_cases:
            start_time = time.time()
            try:
                request = {
                    "messages": [{"role": "user", "content": test_case["query"]}],
                    "model": "gpt-4o-mini",
                    "user_id": "test_user_123",
                    "attachments": test_case.get("attachments", [])
                }
                
                context = {}
                result = await self.endpoint.agents["router"].run(request, context)
                
                # Validate result
                success = (
                    result.get("status") != "error" and
                    "router_decision" in result and
                    "enabled_agents" in result and
                    len(result["enabled_agents"]) > 0
                )
                
                # Check if expected tool was selected
                selected_tool = result.get("router_decision", {}).get("selected_tool", "")
                tool_match = selected_tool in test_case["expected_tool"]
                
                # Check if expected agents were enabled
                enabled_agents = result.get("enabled_agents", [])
                agents_match = all(agent in enabled_agents for agent in test_case["expected_agents"])
                
                execution_time = time.time() - start_time
                
                test_result = TestResult(
                    agent_name="RouterAgent",
                    test_case=test_case["name"],
                    success=success and (tool_match or agents_match),
                    error="" if success else "Router failed to return valid result",
                    execution_time=execution_time,
                    details={
                        "selected_tool": selected_tool,
                        "enabled_agents": enabled_agents,
                        "expected_tool": test_case["expected_tool"],
                        "tool_match": tool_match,
                        "agents_match": agents_match
                    }
                )
                
                results.append(test_result)
                self._log_result(test_result)
                
            except Exception as e:
                execution_time = time.time() - start_time
                test_result = TestResult(
                    agent_name="RouterAgent",
                    test_case=test_case["name"],
                    success=False,
                    error=str(e),
                    execution_time=execution_time
                )
                results.append(test_result)
                self._log_result(test_result)
        
        return results
    
    async def test_rag_agent(self) -> List[TestResult]:
        """Test RAGAgent with different search types"""
        logger.info("\n🧠 Testing RAGAgent")
        results = []
        
        test_cases = [
            {
                "name": "notes_search",
                "query": "machine learning algorithms",
                "search_type": "knowledge_base_notes"
            },
            {
                "name": "conversation_search",
                "query": "previous discussions about AI",
                "search_type": "knowledge_base_conversations"
            },
            {
                "name": "mixed_search",
                "query": "all information about neural networks",
                "search_type": "knowledge_base_full"
            }
        ]
        
        for test_case in test_cases:
            start_time = time.time()
            try:
                request = {
                    "messages": [{"role": "user", "content": test_case["query"]}],
                    "model": "gpt-4o-mini",
                    "user_id": 123  # Use integer user ID
                }
                
                context = {
                    "router_agent": {
                        "condensed_query": test_case["query"],
                        "original_query": test_case["query"],
                        "search_type": test_case["search_type"]
                    }
                }
                
                result = await self.endpoint.agents["rag"].run(request, context)
                
                # Validate result
                success = (
                    result.get("status") == "success" and
                    "context" in result and
                    isinstance(result.get("context"), str) and
                    "metadata" in result
                )
                
                execution_time = time.time() - start_time
                
                test_result = TestResult(
                    agent_name="RAGAgent",
                    test_case=test_case["name"],
                    success=success,
                    error="" if success else "RAG failed to return valid context",
                    execution_time=execution_time,
                    details={
                        "context_length": len(result.get("context", "")),
                        "total_chunks": result.get("metadata", {}).get("total_chunks", 0),
                        "search_type": test_case["search_type"]
                    }
                )
                
                results.append(test_result)
                self._log_result(test_result)
                
            except Exception as e:
                execution_time = time.time() - start_time
                test_result = TestResult(
                    agent_name="RAGAgent",
                    test_case=test_case["name"],
                    success=False,
                    error=str(e),
                    execution_time=execution_time
                )
                results.append(test_result)
                self._log_result(test_result)
        
        return results
    
    async def test_web_search_agent(self) -> List[TestResult]:
        """Test WebSearchAgent with various queries"""
        logger.info("\n🌐 Testing WebSearchAgent")
        results = []
        
        test_cases = [
            {
                "name": "current_events",
                "query": "Latest AI developments 2025"
            },
            {
                "name": "technical_query",
                "query": "How does transformer architecture work?"
            },
            {
                "name": "local_query",
                "query": "Weather in San Francisco today"
            }
        ]
        
        for test_case in test_cases:
            start_time = time.time()
            try:
                request = {
                    "messages": [{"role": "user", "content": test_case["query"]}],
                    "model": "gpt-4o-mini",
                    "user_id": 123  # Use integer user ID
                }
                
                context = {
                    "router_agent": {
                        "condensed_query": test_case["query"],
                        "original_query": test_case["query"]
                    }
                }
                
                result = await self.endpoint.agents["web_search"].run(request, context)
                
                # Validate result
                success = (
                    result.get("status") == "success" and
                    "results" in result and
                    isinstance(result.get("results"), list) and
                    len(result.get("results", [])) > 0 and
                    "context" in result
                )
                
                execution_time = time.time() - start_time
                
                test_result = TestResult(
                    agent_name="WebSearchAgent",
                    test_case=test_case["name"],
                    success=success,
                    error="" if success else "Web search failed to return results",
                    execution_time=execution_time,
                    details={
                        "result_count": len(result.get("results", [])),
                        "context_length": len(result.get("context", "")),
                        "cache_hit": result.get("metadata", {}).get("cache_hit", False)
                    }
                )
                
                results.append(test_result)
                self._log_result(test_result)
                
            except Exception as e:
                execution_time = time.time() - start_time
                test_result = TestResult(
                    agent_name="WebSearchAgent",
                    test_case=test_case["name"],
                    success=False,
                    error=str(e),
                    execution_time=execution_time
                )
                results.append(test_result)
                self._log_result(test_result)
        
        return results
    
    async def test_attachment_agent(self) -> List[TestResult]:
        """Test AttachmentAgent with different file types"""
        logger.info("\n📎 Testing AttachmentAgent")
        results = []
        
        test_cases = [
            {
                "name": "pdf_attachment",
                "attachments": [{"type": "pdf", "url": "test.pdf", "filename": "test.pdf"}]
            },
            {
                "name": "image_attachment",
                "attachments": [{"type": "image", "url": "test.png", "filename": "test.png"}]
            },
            {
                "name": "multiple_attachments",
                "attachments": [
                    {"type": "pdf", "url": "doc1.pdf", "filename": "doc1.pdf"},
                    {"type": "image", "url": "img1.png", "filename": "img1.png"}
                ]
            },
            {
                "name": "no_attachments",
                "attachments": []
            }
        ]
        
        for test_case in test_cases:
            start_time = time.time()
            try:
                request = {
                    "messages": [{"role": "user", "content": "Process these attachments"}],
                    "model": "gpt-4o-mini",
                    "user_id": "test_user_123",
                    "attachments": test_case["attachments"]
                }
                
                context = {
                    "router_agent": {
                        "condensed_query": "analyze attachments",
                        "original_query": "Process these attachments"
                    }
                }
                
                result = await self.endpoint.agents["attachment"].run(request, context)
                
                # Validate result
                expected_count = len(test_case["attachments"])
                actual_count = result.get("metadata", {}).get("attachment_count", -1)
                
                success = (
                    result.get("status") == "success" and
                    "context" in result and
                    actual_count == expected_count
                )
                
                execution_time = time.time() - start_time
                
                test_result = TestResult(
                    agent_name="AttachmentAgent",
                    test_case=test_case["name"],
                    success=success,
                    error="" if success else f"Expected {expected_count} attachments, got {actual_count}",
                    execution_time=execution_time,
                    details={
                        "attachment_count": actual_count,
                        "context_length": len(result.get("context", ""))
                    }
                )
                
                results.append(test_result)
                self._log_result(test_result)
                
            except Exception as e:
                execution_time = time.time() - start_time
                test_result = TestResult(
                    agent_name="AttachmentAgent",
                    test_case=test_case["name"],
                    success=False,
                    error=str(e),
                    execution_time=execution_time
                )
                results.append(test_result)
                self._log_result(test_result)
        
        return results
    
    async def test_code_interpreter_agent(self) -> List[TestResult]:
        """Test CodeInterpreterAgent with various code requests"""
        logger.info("\n💻 Testing CodeInterpreterAgent")
        results = []
        
        test_cases = [
            {
                "name": "simple_print",
                "query": "print('Hello World')"
            },
            {
                "name": "math_calculation",
                "query": "import math\nprint(math.sqrt(144))"
            },
            {
                "name": "code_block",
                "query": "Execute this code:\n```python\nresult = 2 + 2\nprint(f'Result is {result}')\n```"
            },
            {
                "name": "data_analysis",
                "query": "# Simple mean calculation without numpy\nnumbers = [1,2,3,4,5]\nmean = sum(numbers) / len(numbers)\nprint(f'Mean: {mean}')"
            }
        ]
        
        for test_case in test_cases:
            start_time = time.time()
            try:
                request = {
                    "messages": [{"role": "user", "content": test_case["query"]}],
                    "model": "gpt-4o-mini",
                    "user_id": 123  # Use integer user ID
                }
                
                context = {}
                
                result = await self.endpoint.agents["code_interpreter"].run(request, context)
                
                # Validate result
                success = (
                    result.get("status") == "success" and
                    result.get("code_blocks", 0) > 0 and
                    "results" in result and
                    len(result.get("results", [])) > 0
                )
                
                # Check if any code execution was successful
                any_success = any(
                    r.get("result", {}).get("success", False) 
                    for r in result.get("results", [])
                )
                
                execution_time = time.time() - start_time
                
                test_result = TestResult(
                    agent_name="CodeInterpreterAgent",
                    test_case=test_case["name"],
                    success=success and any_success,
                    error="" if success else "Code execution failed",
                    execution_time=execution_time,
                    details={
                        "code_blocks": result.get("code_blocks", 0),
                        "successful_executions": result.get("metadata", {}).get("successful_executions", 0),
                        "total_execution_time": result.get("metadata", {}).get("total_execution_time", 0)
                    }
                )
                
                results.append(test_result)
                self._log_result(test_result)
                
            except Exception as e:
                execution_time = time.time() - start_time
                test_result = TestResult(
                    agent_name="CodeInterpreterAgent",
                    test_case=test_case["name"],
                    success=False,
                    error=str(e),
                    execution_time=execution_time
                )
                results.append(test_result)
                self._log_result(test_result)
        
        return results
    
    async def test_response_agent(self) -> List[TestResult]:
        """Test ResponseAgent with different context combinations"""
        logger.info("\n🎯 Testing ResponseAgent")
        results = []
        
        # Mock the LLM response to avoid actual API calls
        from unittest.mock import AsyncMock, MagicMock
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.message.content = "This is a mocked AI response for testing."
        mock_llm.achat = AsyncMock(return_value=mock_response)
        
        # Replace the LLM provider selector
        original_get_provider = self.endpoint.agents["response"].llm_provider_manager.get_provider
        self.endpoint.agents["response"].llm_provider_manager.get_provider = lambda _, model: {"llm": mock_llm}
        
        test_cases = [
            {
                "name": "no_context",
                "context": {}
            },
            {
                "name": "with_rag_context",
                "context": {
                    "rag_agent": {
                        "context": "This is some knowledge base context about AI and machine learning.",
                        "status": "success"
                    }
                }
            },
            {
                "name": "with_web_context",
                "context": {
                    "web_search_agent": {
                        "context": "Recent news: OpenAI announced new features. Google released Gemini updates.",
                        "status": "success"
                    }
                }
            },
            {
                "name": "with_all_contexts",
                "context": {
                    "rag_agent": {
                        "context": "Knowledge base: AI fundamentals and best practices.",
                        "status": "success"
                    },
                    "web_search_agent": {
                        "context": "Web results: Latest AI developments in 2025.",
                        "status": "success"
                    },
                    "attachment_agent": {
                        "context": "Document analysis: The PDF contains research on neural networks.",
                        "status": "success"
                    }
                }
            }
        ]
        
        for test_case in test_cases:
            start_time = time.time()
            try:
                request = {
                    "messages": [{"role": "user", "content": "Tell me about AI"}],
                    "model": "gpt-4o-mini",
                    "user_id": 123  # Use integer user ID
                }
                
                context = test_case["context"]
                
                result = await self.endpoint.agents["response"].run(request, context)
                
                # Validate result
                success = (
                    result.get("status") == "success" and
                    "response" in result and
                    isinstance(result.get("response"), str) and
                    len(result.get("response", "")) > 10
                )
                
                execution_time = time.time() - start_time
                
                test_result = TestResult(
                    agent_name="ResponseAgent",
                    test_case=test_case["name"],
                    success=success,
                    error="" if success else "Response generation failed",
                    execution_time=execution_time,
                    details={
                        "response_length": len(result.get("response", "")),
                        "context_used": result.get("metadata", {}).get("context_used", False),
                        "model": result.get("metadata", {}).get("model", "unknown")
                    }
                )
                
                results.append(test_result)
                self._log_result(test_result)
                
            except Exception as e:
                execution_time = time.time() - start_time
                test_result = TestResult(
                    agent_name="ResponseAgent",
                    test_case=test_case["name"],
                    success=False,
                    error=str(e),
                    execution_time=execution_time
                )
                results.append(test_result)
                self._log_result(test_result)
        
        # Restore original provider
        self.endpoint.agents["response"].llm_provider_manager.get_provider = original_get_provider
        
        return results
    
    async def test_citation_agent(self) -> List[TestResult]:
        """Test CitationAgent with different source types"""
        logger.info("\n📚 Testing CitationAgent")
        results = []
        
        # Mock the LLM provider to avoid actual API calls
        from unittest.mock import MagicMock
        mock_provider_info = {"llm": MagicMock()}
        original_get_provider = self.endpoint.agents["citation"].llm_provider_manager.get_provider
        self.endpoint.agents["citation"].llm_provider_manager.get_provider = lambda _, model: mock_provider_info
        
        test_cases = [
            {
                "name": "no_sources",
                "context": {
                    "response_agent": {
                        "response": "AI is a field of computer science.",
                        "status": "success"
                    }
                }
            },
            {
                "name": "with_rag_sources",
                "context": {
                    "response_agent": {
                        "response": "According to my notes, AI uses neural networks.",
                        "status": "success"
                    },
                    "rag_agent": {
                        "sources": [
                            {"chunk_id": 1, "content": "Neural networks are..."}
                        ],
                        "status": "success"
                    }
                }
            },
            {
                "name": "with_web_sources",
                "context": {
                    "response_agent": {
                        "response": "Recent developments show AI advancing rapidly.",
                        "status": "success"
                    },
                    "web_search_agent": {
                        "results": [
                            {"title": "AI News", "link": "https://example.com", "snippet": "AI advances..."}
                        ],
                        "status": "success"
                    }
                }
            },
            {
                "name": "with_mixed_sources",
                "context": {
                    "response_agent": {
                        "response": "Based on research and recent news, AI is transforming industries.",
                        "status": "success"
                    },
                    "rag_agent": {
                        "sources": [
                            {"chunk_id": 1, "content": "AI transformation..."}
                        ],
                        "status": "success"
                    },
                    "web_search_agent": {
                        "results": [
                            {"title": "Industry Impact", "link": "https://example.com", "snippet": "Industries..."}
                        ],
                        "status": "success"
                    }
                }
            }
        ]
        
        for test_case in test_cases:
            start_time = time.time()
            try:
                request = {
                    "messages": [{"role": "user", "content": "Tell me about AI"}],
                    "model": "gpt-4o-mini",
                    "user_id": 123  # Use integer user ID
                }
                
                context = test_case["context"]
                
                result = await self.endpoint.agents["citation"].run(request, context)
                
                # Validate result
                success = (
                    result.get("status") == "success" and
                    "citations" in result and
                    isinstance(result.get("citations"), dict)
                )
                
                execution_time = time.time() - start_time
                
                test_result = TestResult(
                    agent_name="CitationAgent",
                    test_case=test_case["name"],
                    success=success,
                    error="" if success else "Citation generation failed",
                    execution_time=execution_time,
                    details={
                        "citation_count": len(result.get("citations", {}).get("sources", [])),
                        "source_count": result.get("metadata", {}).get("source_count", 0)
                    }
                )
                
                results.append(test_result)
                self._log_result(test_result)
                
            except Exception as e:
                execution_time = time.time() - start_time
                test_result = TestResult(
                    agent_name="CitationAgent",
                    test_case=test_case["name"],
                    success=False,
                    error=str(e),
                    execution_time=execution_time
                )
                results.append(test_result)
                self._log_result(test_result)
        
        # Restore original provider
        self.endpoint.agents["citation"].llm_provider_manager.get_provider = original_get_provider
        
        return results
    
    def _log_result(self, result: TestResult):
        """Log individual test result"""
        status = "✅" if result.success else "❌"
        logger.info(f"{status} {result.agent_name}.{result.test_case}: "
                   f"{'PASS' if result.success else 'FAIL'} "
                   f"({result.execution_time:.2f}s)")
        if not result.success and result.error:
            logger.error(f"   Error: {result.error}")
        if result.details:
            logger.info(f"   Details: {result.details}")
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report"""
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.success)
        failed_tests = total_tests - passed_tests
        
        # Group results by agent
        agent_results = {}
        for result in self.results:
            if result.agent_name not in agent_results:
                agent_results[result.agent_name] = {
                    "total": 0,
                    "passed": 0,
                    "failed": 0,
                    "tests": []
                }
            
            agent_results[result.agent_name]["total"] += 1
            if result.success:
                agent_results[result.agent_name]["passed"] += 1
            else:
                agent_results[result.agent_name]["failed"] += 1
            
            agent_results[result.agent_name]["tests"].append({
                "test_case": result.test_case,
                "success": result.success,
                "error": result.error,
                "execution_time": result.execution_time,
                "details": result.details
            })
        
        # Calculate performance metrics
        total_time = sum(r.execution_time for r in self.results)
        avg_time = total_time / total_tests if total_tests > 0 else 0
        
        report = {
            "summary": {
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0,
                "total_execution_time": total_time,
                "average_execution_time": avg_time
            },
            "agents": agent_results,
            "phase_1_success": passed_tests == total_tests,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        return report
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all individual agent tests"""
        logger.info("🚀 Starting Phase 1: Individual Agent Tests")
        logger.info("=" * 80)
        
        # Initialize endpoint
        if not await self.setup():
            return {
                "summary": {"error": "Failed to initialize endpoint"},
                "phase_1_success": False
            }
        
        # Run tests for each agent
        self.results.extend(await self.test_router_agent())
        self.results.extend(await self.test_rag_agent())
        self.results.extend(await self.test_web_search_agent())
        self.results.extend(await self.test_attachment_agent())
        self.results.extend(await self.test_code_interpreter_agent())
        self.results.extend(await self.test_response_agent())
        self.results.extend(await self.test_citation_agent())
        
        # Generate report
        report = self.generate_report()
        
        # Log summary
        logger.info("\n" + "=" * 80)
        logger.info("📊 PHASE 1 TEST SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Total Tests: {report['summary']['total_tests']}")
        logger.info(f"Passed: {report['summary']['passed']} ✅")
        logger.info(f"Failed: {report['summary']['failed']} ❌")
        logger.info(f"Success Rate: {report['summary']['success_rate']:.1f}%")
        logger.info(f"Total Time: {report['summary']['total_execution_time']:.2f}s")
        
        # Log per-agent summary
        logger.info("\n📈 Per-Agent Results:")
        for agent_name, agent_data in report['agents'].items():
            logger.info(f"\n{agent_name}:")
            logger.info(f"  Total: {agent_data['total']}")
            logger.info(f"  Passed: {agent_data['passed']} ✅")
            logger.info(f"  Failed: {agent_data['failed']} ❌")
            
            # Log failed tests
            failed_tests = [t for t in agent_data['tests'] if not t['success']]
            if failed_tests:
                logger.error(f"  Failed Tests:")
                for test in failed_tests:
                    logger.error(f"    - {test['test_case']}: {test['error']}")
        
        # Final verdict
        logger.info("\n" + "=" * 80)
        if report['phase_1_success']:
            logger.info("🎉 PHASE 1 COMPLETE: All individual agent tests passed!")
            logger.info("✅ Ready to proceed to Phase 2: Multi-Agent Workflow Tests")
        else:
            logger.error("💥 PHASE 1 FAILED: Individual agent tests have failures")
            logger.error("❌ Fix agent issues before proceeding to Phase 2")
        
        return report


async def main():
    """Main test runner"""
    test_suite = AgentTestSuite()
    report = await test_suite.run_all_tests()
    
    # Save report to file
    with open("phase1_individual_agent_test_results.json", "w") as f:
        json.dump(report, f, indent=2, default=str)
    
    logger.info(f"\n📄 Detailed results saved to: phase1_individual_agent_test_results.json")
    
    return report['phase_1_success']


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)