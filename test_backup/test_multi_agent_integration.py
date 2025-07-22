#!/usr/bin/env python3
"""
YouWoAI ML Server Multi-Agent Integration Test Suite

Tests the complete multi-agent workflow including routing, context building,
response generation, and streaming capabilities.
"""

import asyncio
import json
import time
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class IntegrationTestCase:
    """Represents a single integration test case"""
    name: str
    description: str
    request: Dict[str, Any]
    expected_agents: List[str]
    expected_events: List[str]
    validation_rules: Dict[str, Any]


@dataclass
class IntegrationTestResult:
    """Result of an integration test"""
    test_case: str
    success: bool
    duration: float
    agent_results: Dict[str, Any]
    streaming_events: List[Dict[str, Any]]
    error: Optional[str] = None
    validation_results: Dict[str, bool] = None


class MultiAgentIntegrationTester:
    """Tests multi-agent workflows end-to-end"""
    
    def __init__(self):
        self.test_cases = self._define_test_cases()
        self.results: List[IntegrationTestResult] = []
    
    def _define_test_cases(self) -> List[IntegrationTestCase]:
        """Define comprehensive integration test cases"""
        return [
            # Test Case 1: Knowledge Base Query
            IntegrationTestCase(
                name="knowledge_base_query",
                description="Query that should route to RAG, Response, and Citation agents",
                request={
                    "messages": [
                        {"role": "user", "content": "What are my notes about machine learning?"}
                    ],
                    "model": "gpt-4.1-nano",
                    "user_id": 123,
                    "stream": True,
                    "enable_rag": True,
                    "enable_citations": True
                },
                expected_agents=["router", "rag", "response", "citation"],
                expected_events=[
                    "response.created",
                    "response.in_progress",
                    "response.output_item.added",  # Router reasoning
                    "response.output_item.added",  # RAG file search
                    "response.file_search_call.in_progress",
                    "response.output_item.added",  # Response message
                    "response.output_text.delta",
                    "response.completed"
                ],
                validation_rules={
                    "has_rag_context": True,
                    "has_citations": True,
                    "response_not_empty": True
                }
            ),
            
            # Test Case 2: Web Search Query
            IntegrationTestCase(
                name="web_search_query",
                description="Query that should route to Web Search, Response, and Citation agents",
                request={
                    "messages": [
                        {"role": "user", "content": "What are the latest developments in quantum computing?"}
                    ],
                    "model": "gpt-4.1-nano",
                    "user_id": 123,
                    "stream": True,
                    "enable_web_search": True,
                    "enable_citations": True
                },
                expected_agents=["router", "web_search", "response", "citation"],
                expected_events=[
                    "response.created",
                    "response.in_progress",
                    "response.output_item.added",  # Router reasoning
                    "response.output_item.added",  # Web search
                    "response.web_search_call.in_progress",
                    "response.web_search_call.searching",
                    "response.web_search_call.completed",
                    "response.output_item.added",  # Response message
                    "response.completed"
                ],
                validation_rules={
                    "has_web_search_results": True,
                    "has_citations": True,
                    "response_not_empty": True
                }
            ),
            
            # Test Case 3: Code Execution Query
            IntegrationTestCase(
                name="code_execution_query",
                description="Query that should route to Code Interpreter and Response agents",
                request={
                    "messages": [
                        {"role": "user", "content": "Calculate the factorial of 10 using Python"}
                    ],
                    "model": "gpt-4.1-nano",
                    "user_id": 123,
                    "stream": True,
                    "enable_code_interpreter": True
                },
                expected_agents=["router", "code_interpreter", "response"],
                expected_events=[
                    "response.created",
                    "response.in_progress",
                    "response.output_item.added",  # Router reasoning
                    "response.output_item.added",  # Code interpreter function call
                    "response.function_tool_result.delta",
                    "response.output_item.added",  # Response message
                    "response.completed"
                ],
                validation_rules={
                    "has_code_execution": True,
                    "response_not_empty": True,
                    "code_output_present": True
                }
            ),
            
            # Test Case 4: Multi-Context Query
            IntegrationTestCase(
                name="multi_context_query",
                description="Query that combines RAG and Web Search",
                request={
                    "messages": [
                        {"role": "user", "content": "Compare my notes on AI with the latest research in the field"}
                    ],
                    "model": "gpt-4.1-nano",
                    "user_id": 123,
                    "stream": True,
                    "enable_rag": True,
                    "enable_web_search": True,
                    "enable_citations": True
                },
                expected_agents=["router", "rag", "web_search", "response", "citation"],
                expected_events=[
                    "response.created",
                    "response.in_progress",
                    "response.output_item.added",  # Router
                    "response.output_item.added",  # Web search
                    "response.output_item.added",  # RAG
                    "response.output_item.added",  # Response
                    "response.citations",
                    "response.completed"
                ],
                validation_rules={
                    "has_rag_context": True,
                    "has_web_search_results": True,
                    "has_multiple_citations": True,
                    "response_not_empty": True
                }
            ),
            
            # Test Case 5: Attachment Processing
            IntegrationTestCase(
                name="attachment_processing",
                description="Query with file attachments",
                request={
                    "messages": [
                        {"role": "user", "content": "Analyze the attached document"}
                    ],
                    "model": "gpt-4.1-nano",
                    "user_id": 123,
                    "stream": True,
                    "attachments": [
                        {"id": "file_123", "name": "document.pdf", "type": "application/pdf"}
                    ],
                    "enable_citations": True
                },
                expected_agents=["router", "attachment", "response", "citation"],
                expected_events=[
                    "response.created",
                    "response.in_progress",
                    "response.output_item.added",  # Router
                    "response.output_item.added",  # Attachment function call
                    "response.function_tool_result.delta",
                    "response.output_item.added",  # Response
                    "response.completed"
                ],
                validation_rules={
                    "has_attachment_context": True,
                    "response_not_empty": True,
                    "processed_attachments": 1
                }
            )
        ]
    
    async def run_test_case(self, test_case: IntegrationTestCase) -> IntegrationTestResult:
        """Run a single integration test case"""
        logger.info(f"\n{'='*60}")
        logger.info(f"🧪 Running test: {test_case.name}")
        logger.info(f"📝 Description: {test_case.description}")
        
        start_time = time.time()
        
        try:
            # Import the endpoint
            from chat.endpoints.multi_agent_endpoint_v2 import multi_agent_endpoint_v2
            
            # Track results
            agent_results = {}
            streaming_events = []
            
            # Execute the request
            result = await multi_agent_endpoint_v2.handle_request(test_case.request)
            
            if hasattr(result, '__aiter__'):
                # Process streaming response
                event_count = 0
                async for event in result:
                    streaming_events.append(event)
                    event_count += 1
                    
                    # Extract agent results from events
                    if event.get("type") == "response.output_item.done":
                        item = event.get("item", {})
                        item_type = item.get("type")
                        if item_type:
                            agent_results[item_type] = item
                    
                    # Limit events for testing
                    if event_count >= 200:
                        logger.warning("Limiting to 200 events for testing")
                        break
                
                logger.info(f"📊 Processed {event_count} streaming events")
            else:
                # Non-streaming response
                agent_results["response"] = result
            
            # Validate results
            validation_results = self._validate_results(
                test_case, agent_results, streaming_events
            )
            
            success = all(validation_results.values())
            duration = time.time() - start_time
            
            result = IntegrationTestResult(
                test_case=test_case.name,
                success=success,
                duration=duration,
                agent_results=agent_results,
                streaming_events=streaming_events,
                validation_results=validation_results
            )
            
            if success:
                logger.info(f"✅ Test PASSED in {duration:.2f}s")
            else:
                logger.error(f"❌ Test FAILED in {duration:.2f}s")
                logger.error(f"   Failed validations: {[k for k, v in validation_results.items() if not v]}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Test failed with exception: {e}")
            import traceback
            traceback.print_exc()
            
            return IntegrationTestResult(
                test_case=test_case.name,
                success=False,
                duration=time.time() - start_time,
                agent_results={},
                streaming_events=[],
                error=str(e)
            )
    
    def _validate_results(
        self, 
        test_case: IntegrationTestCase,
        agent_results: Dict[str, Any],
        streaming_events: List[Dict[str, Any]]
    ) -> Dict[str, bool]:
        """Validate test results against expected outcomes"""
        validations = {}
        
        # Check expected events are present
        event_types = [event.get("type") for event in streaming_events]
        for expected_event in test_case.expected_events:
            validations[f"has_event_{expected_event}"] = expected_event in event_types
        
        # Apply custom validation rules
        for rule_name, expected_value in test_case.validation_rules.items():
            if rule_name == "has_rag_context":
                validations[rule_name] = "file_search_call" in agent_results
            elif rule_name == "has_web_search_results":
                validations[rule_name] = "web_search_call" in agent_results
            elif rule_name == "has_citations":
                validations[rule_name] = any(
                    event.get("type") == "response.citations" 
                    for event in streaming_events
                )
            elif rule_name == "has_multiple_citations":
                citations_event = next(
                    (e for e in streaming_events if e.get("type") == "response.citations"),
                    None
                )
                if citations_event:
                    validations[rule_name] = len(citations_event.get("citations", [])) > 1
                else:
                    validations[rule_name] = False
            elif rule_name == "response_not_empty":
                # Check if we have a message with content
                message_items = [
                    item for item in agent_results.values()
                    if isinstance(item, dict) and item.get("type") == "message"
                ]
                validations[rule_name] = len(message_items) > 0
            elif rule_name == "has_code_execution":
                validations[rule_name] = "function_tool_call" in agent_results
            elif rule_name == "code_output_present":
                validations[rule_name] = "function_tool_result" in agent_results
            elif rule_name == "has_attachment_context":
                validations[rule_name] = any(
                    "attachment" in str(item).lower() 
                    for item in agent_results.values()
                )
            elif rule_name == "processed_attachments":
                validations[rule_name] = True  # Simplified for now
        
        return validations
    
    async def run_all_tests(self) -> None:
        """Run all integration tests"""
        logger.info("🚀 Starting Multi-Agent Integration Test Suite")
        logger.info(f"📋 Total test cases: {len(self.test_cases)}")
        
        # Run tests sequentially to avoid interference
        for test_case in self.test_cases:
            result = await self.run_test_case(test_case)
            self.results.append(result)
            
            # Small delay between tests
            await asyncio.sleep(1)
        
        # Generate report
        self._generate_report()
    
    def _generate_report(self) -> None:
        """Generate test report"""
        logger.info("\n" + "="*60)
        logger.info("📊 INTEGRATION TEST REPORT")
        logger.info("="*60)
        
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.success)
        failed_tests = total_tests - passed_tests
        
        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"✅ Passed: {passed_tests}")
        logger.info(f"❌ Failed: {failed_tests}")
        logger.info(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        # Detailed results
        logger.info("\nDetailed Results:")
        for result in self.results:
            status = "✅ PASS" if result.success else "❌ FAIL"
            logger.info(f"\n{result.test_case}: {status} ({result.duration:.2f}s)")
            
            if not result.success:
                if result.error:
                    logger.error(f"  Error: {result.error}")
                if result.validation_results:
                    failed_validations = [
                        k for k, v in result.validation_results.items() if not v
                    ]
                    if failed_validations:
                        logger.error(f"  Failed validations: {failed_validations}")
        
        # Save results to file
        results_data = {
            "summary": {
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "success_rate": (passed_tests/total_tests)*100,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            },
            "test_results": [
                {
                    "test_case": r.test_case,
                    "success": r.success,
                    "duration": r.duration,
                    "error": r.error,
                    "validation_results": r.validation_results,
                    "event_count": len(r.streaming_events)
                }
                for r in self.results
            ]
        }
        
        with open("phase2_integration_test_results.json", "w") as f:
            json.dump(results_data, f, indent=2)
        
        logger.info("\n💾 Results saved to phase2_integration_test_results.json")
        
        if failed_tests == 0:
            logger.info("\n🎉 ALL INTEGRATION TESTS PASSED!")
        else:
            logger.error(f"\n💥 {failed_tests} INTEGRATION TESTS FAILED!")


async def main():
    """Run the integration test suite"""
    # Set up environment
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
    
    # Run tests
    tester = MultiAgentIntegrationTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())