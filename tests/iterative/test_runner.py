"""
IterativeTestRunner - Main test orchestration with continuous improvement loop
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
import httpx
import traceback

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.iterative.validators.streaming_validator import StreamingValidator, OpenAIFormatValidator
from tests.iterative.generators.edge_case_generator import EdgeCaseGenerator
from tests.iterative.metrics.performance_tracker import PerformanceTracker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class TestResult:
    """Result of a single test execution"""
    test_name: str
    success: bool
    attempts: int
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    
@dataclass 
class TestSuite:
    """Collection of related tests"""
    name: str
    tests: List[Dict[str, Any]]
    priority: int = 0  # Higher priority runs first
    

class IterativeTestRunner:
    """Main test runner with continuous improvement capabilities"""
    
    def __init__(self, base_url: str = "http://localhost:5002", test_db: bool = True):
        self.base_url = base_url
        self.test_db = test_db
        self.test_results: List[TestResult] = []
        self.iteration_count = 0
        self.performance_tracker = PerformanceTracker()
        self.edge_case_generator = EdgeCaseGenerator()
        self.http_client = None
        
        # Test configuration
        self.max_iterations = 100
        self.fix_attempts = 3
        self.model = "gpt-4o-mini"
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.http_client = httpx.AsyncClient(timeout=60.0)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.http_client:
            await self.http_client.aclose()
            
    def git_commit(self, message: str) -> bool:
        """Commit changes to git"""
        try:
            # Stage all changes
            subprocess.run(['git', 'add', '-A'], check=True)
            
            # Commit with message
            result = subprocess.run(
                ['git', 'commit', '-m', f"🤖 Auto-fix: {message}"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                logger.info(f"✅ Git commit successful: {message}")
                return True
            else:
                logger.warning(f"Git commit failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Git operation failed: {str(e)}")
            return False
            
    def git_rollback(self) -> bool:
        """Rollback last commit"""
        try:
            subprocess.run(['git', 'reset', '--hard', 'HEAD~1'], check=True)
            logger.info("✅ Git rollback successful")
            return True
        except Exception as e:
            logger.error(f"Git rollback failed: {str(e)}")
            return False
            
    async def validate_with_retries(self, test_case: Dict[str, Any], 
                                  expected_behavior: Dict[str, Any]) -> TestResult:
        """Validate test with 3-attempt retry logic"""
        test_name = test_case.get('name', 'Unknown Test')
        
        for attempt in range(1, 4):
            try:
                # Execute test
                result = await self.execute_test(test_case)
                
                # Validate result
                is_valid = await self.validate_result(result, expected_behavior)
                
                if is_valid:
                    return TestResult(
                        test_name=test_name,
                        success=True,
                        attempts=attempt,
                        metrics=self.extract_metrics(result)
                    )
                else:
                    if attempt < 3:
                        logger.warning(f"Test {test_name} failed attempt {attempt}/3")
                        await asyncio.sleep(2)  # Brief pause between attempts
                        
            except Exception as e:
                error_msg = f"Test execution error: {str(e)}"
                logger.error(f"{error_msg}\n{traceback.format_exc()}")
                
                if attempt < 3:
                    await asyncio.sleep(2)
                else:
                    return TestResult(
                        test_name=test_name,
                        success=False,
                        attempts=attempt,
                        errors=[error_msg]
                    )
                    
        # All attempts failed
        return TestResult(
            test_name=test_name,
            success=False,
            attempts=3,
            errors=[f"Test failed after 3 attempts"]
        )
        
    async def execute_test(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single test case"""
        endpoint = test_case.get('endpoint', '/v1/multi-agent/response')
        request_data = test_case.get('request', {})
        
        # Add default values
        request_data.setdefault('model', self.model)
        request_data.setdefault('user_id', 10001)
        
        if test_case.get('stream', False):
            # Streaming test
            return await self.execute_streaming_test(endpoint, request_data)
        else:
            # Non-streaming test
            response = await self.http_client.post(
                f"{self.base_url}{endpoint}",
                json=request_data
            )
            
            if response.status_code != 200:
                raise Exception(f"HTTP {response.status_code}: {response.text}")
                
            return response.json()
            
    async def execute_streaming_test(self, endpoint: str, 
                                   request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute streaming test and validate format"""
        request_data['stream'] = True
        validator = StreamingValidator()
        content = ""
        metadata = {}
        agents_triggered = set()
        
        async with self.http_client.stream(
            'POST',
            f"{self.base_url}{endpoint}",
            json=request_data
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith('data: '):
                    data_str = line[6:]
                    if data_str == '[DONE]':
                        break
                        
                    try:
                        event = json.loads(data_str)
                        validator.track_event(event)
                        event_type = event.get('type', '')
                        
                        # Collect content from various event types
                        if 'choices' in event and event['choices']:
                            delta = event['choices'][0].get('delta', {})
                            if 'content' in delta:
                                content += delta['content']
                                
                        # Collect content from output_text.delta events
                        if event_type == 'response.output_text.delta':
                            delta_text = event.get('delta', '')
                            content += delta_text
                            
                        # Collect content from content_part.done events
                        if event_type == 'response.content_part.done':
                            part = event.get('part', {})
                            if part.get('type') == 'text':
                                content += part.get('text', '')
                                
                        # Track agents from various event types
                        
                        # Track from reasoning events
                        if event_type == 'response.reasoning_text.delta':
                            text = event.get('delta', '')
                            if 'routed to agents:' in text:
                                # Parse agent list from router output
                                agent_list = text.split('routed to agents:')[1].strip()
                                for agent in agent_list.split(','):
                                    agent_name = agent.strip()
                                    if agent_name:
                                        agents_triggered.add(agent_name)
                                        
                        # Track from reasoning done events
                        elif event_type == 'response.output_item.done':
                            item = event.get('item', {})
                            if item.get('type') == 'reasoning':
                                for content_item in item.get('content', []):
                                    if content_item.get('type') == 'reasoning_text':
                                        text = content_item.get('text', '')
                                        if 'routed to agents:' in text:
                                            agent_list = text.split('routed to agents:')[1].strip()
                                            for agent in agent_list.split(','):
                                                agent_name = agent.strip()
                                                if agent_name:
                                                    agents_triggered.add(agent_name)
                                        
                        # Track from item IDs (router_xxx, ws_xxx, etc)
                        if 'item' in event:
                            item_id = event['item'].get('id', '')
                            if item_id.startswith('router_'):
                                agents_triggered.add('router')
                            elif item_id.startswith('ws_'):
                                agents_triggered.add('web_search')
                            elif item_id.startswith('rag_'):
                                agents_triggered.add('rag')
                            elif item_id.startswith('attachment_'):
                                agents_triggered.add('attachment')
                                
                        # Track from web search calls
                        if 'web_search_call' in event_type:
                            agents_triggered.add('web_search')
                            
                        # Track from function tool calls
                        if 'function_tool_call' in event_type:
                            agents_triggered.add('response')
                            
                        # Track citation agent from content
                        if event_type in ['response.content_part.added', 'response.content_part.done']:
                            # Citation agent adds content parts
                            agents_triggered.add('citation')
                            
                        # Track response agent from message events
                        if event_type == 'response.function_tool_call.completed':
                            agents_triggered.add('response')
                                        
                        # Extract metadata from usage event
                        if event_type == 'response.usage' and 'metadata' in event:
                            metadata = event['metadata']
                            
                    except json.JSONDecodeError:
                        validator.errors.append(f"Invalid JSON: {data_str[:100]}")
                        
        # Validate streaming format
        is_valid, report = validator.validate_streaming_format()
        
        # If we have metadata, extract agents from there too
        if metadata and 'agent_results' in metadata:
            for agent_key in metadata['agent_results']:
                agent_name = agent_key.replace('_agent', '')
                agents_triggered.add(agent_name)
        
        return {
            'streaming_valid': is_valid,
            'streaming_report': report,
            'content': content,
            'total_events': len(validator.events),
            'metadata': metadata,
            'agents_triggered': list(agents_triggered)
        }
        
    async def validate_result(self, result: Dict[str, Any], 
                            expected: Dict[str, Any]) -> bool:
        """Validate test result against expected behavior"""
        # For streaming tests
        if 'streaming_valid' in result:
            if not result['streaming_valid']:
                logger.error(f"Streaming validation failed: {result['streaming_report']['errors']}")
                return False
                
        # Check expected agents triggered
        if 'expected_agents' in expected:
            actual_agents = self.extract_agents(result)
            expected_agents = set(expected['expected_agents'])
            
            if not expected_agents.issubset(actual_agents):
                logger.error(f"Expected agents {expected_agents} but got {actual_agents}")
                return False
                
        # Check response content
        if 'content_checks' in expected:
            content = result.get('content', '') or result.get('choices', [{}])[0].get('message', {}).get('content', '')
            
            for check in expected['content_checks']:
                if check['type'] == 'contains':
                    if check['value'] not in content:
                        logger.error(f"Content missing expected text: {check['value']}")
                        return False
                elif check['type'] == 'citations':
                    has_citations = any(f"[{i}]" in content for i in range(1, 10))
                    if not has_citations:
                        logger.error("Content missing citation markers")
                        return False
                        
        return True
        
    def extract_agents(self, result: Dict[str, Any]) -> set:
        """Extract agents used from result"""
        agents = set()
        
        # From metadata
        if 'metadata' in result:
            agent_results = result['metadata'].get('agent_results', {})
            agents.update(k.replace('_agent', '') for k in agent_results.keys())
            
        # From streaming test results
        if 'agents_triggered' in result:
            agents.update(result['agents_triggered'])
            
        # From streaming report
        if 'streaming_report' in result:
            event_summary = result['streaming_report'].get('event_summary', {})
            for event_type in event_summary:
                if '.agent.' in event_type:
                    agent_name = event_type.split('.')[2]
                    agents.add(agent_name)
                    
        return agents
        
    def extract_metrics(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Extract performance metrics from result"""
        metrics = {}
        
        if 'metadata' in result:
            metadata = result['metadata']
            metrics['workflow_time'] = metadata.get('workflow_time', 0)
            metrics['total_agents'] = len(metadata.get('agent_results', {}))
            metrics['iterations'] = metadata.get('iterations', 1)
            
        if 'usage' in result:
            metrics['total_tokens'] = result['usage'].get('total_tokens', 0)
            
        if 'streaming_report' in result:
            metrics['total_events'] = result['streaming_report'].get('total_events', 0)
            
        return metrics
        
    async def generate_test_suites(self) -> List[TestSuite]:
        """Generate comprehensive test suites"""
        suites = []
        
        # Critical user-facing tests (priority 10)
        suites.append(TestSuite(
            name="Critical User-Facing Features",
            priority=10,
            tests=[
                {
                    'name': 'Streaming Citations',
                    'endpoint': '/v1/multi-agent/response',
                    'stream': True,
                    'request': {
                        'messages': [{'role': 'user', 'content': 'What is machine learning? Cite sources.'}]
                    },
                    'expected': {
                        'expected_agents': ['router', 'web_search', 'response', 'citation'],
                        'content_checks': [
                            {'type': 'citations', 'value': None},
                            {'type': 'contains', 'value': 'machine learning'}
                        ]
                    }
                },
                {
                    'name': 'Attachment Priority',
                    'endpoint': '/v1/multi-agent/response',
                    'stream': False,
                    'request': {
                        'messages': [{'role': 'user', 'content': 'Analyze this document'}],
                        'attachments': ['https://arxiv.org/pdf/2311.10122.pdf']
                    },
                    'expected': {
                        'expected_agents': ['router', 'attachment', 'rag', 'response', 'citation']
                    }
                },
                {
                    'name': 'RAG with Citations',
                    'endpoint': '/v1/multi-agent/response',
                    'stream': False,
                    'request': {
                        'messages': [{'role': 'user', 'content': 'What do my notes say about PARL? Include citations.'}]
                    },
                    'expected': {
                        'expected_agents': ['router', 'rag', 'response', 'citation'],
                        'content_checks': [
                            {'type': 'citations', 'value': None},
                            {'type': 'contains', 'value': 'PARL'}
                        ]
                    }
                }
            ]
        ))
        
        # Edge cases (priority 5)
        edge_cases = await self.edge_case_generator.generate_edge_cases()
        suites.append(TestSuite(
            name="Edge Cases",
            priority=5,
            tests=edge_cases
        ))
        
        # Integration tests (priority 7)
        suites.append(TestSuite(
            name="Multi-Agent Integration",
            priority=7,
            tests=[
                {
                    'name': 'Multiple Attachments',
                    'endpoint': '/v1/multi-agent/response',
                    'stream': False,
                    'request': {
                        'messages': [{'role': 'user', 'content': 'Compare these papers'}],
                        'attachments': [
                            'https://arxiv.org/pdf/2311.10122.pdf',
                            'https://arxiv.org/pdf/2505.18499.pdf'
                        ]
                    },
                    'expected': {
                        'expected_agents': ['router', 'attachment', 'response', 'citation']
                    }
                },
                {
                    'name': 'Complex Query Iteration',
                    'endpoint': '/v1/multi-agent/response',
                    'stream': False,
                    'request': {
                        'messages': [{'role': 'user', 'content': 
                            'Provide a comprehensive analysis of reinforcement learning including: '
                            '1) Mathematical foundations 2) Key algorithms 3) Recent advances '
                            '4) Practical applications 5) Future research directions. '
                            'Be extremely detailed and cite all sources.'}]
                    },
                    'expected': {
                        'expected_agents': ['router', 'rag', 'web_search', 'response', 'citation'],
                        'content_checks': [
                            {'type': 'citations', 'value': None}
                        ]
                    }
                }
            ]
        ))
        
        return sorted(suites, key=lambda x: x.priority, reverse=True)
        
    async def run_continuous_loop(self):
        """Main continuous testing and improvement loop"""
        logger.info("🚀 Starting continuous testing loop...")
        
        while self.iteration_count < self.max_iterations:
            self.iteration_count += 1
            logger.info(f"\n{'='*60}")
            logger.info(f"Iteration {self.iteration_count}/{self.max_iterations}")
            logger.info(f"{'='*60}")
            
            # Generate test suites
            test_suites = await self.generate_test_suites()
            
            # Run all tests
            all_passed = True
            failed_tests = []
            
            for suite in test_suites:
                logger.info(f"\n📋 Running suite: {suite.name}")
                
                for test_case in suite.tests:
                    result = await self.validate_with_retries(
                        test_case,
                        test_case.get('expected', {})
                    )
                    
                    self.test_results.append(result)
                    self.performance_tracker.record_result(result)
                    
                    if not result.success:
                        all_passed = False
                        failed_tests.append((test_case, result))
                        logger.error(f"❌ Test failed: {result.test_name}")
                    else:
                        logger.info(f"✅ Test passed: {result.test_name} (attempts: {result.attempts})")
                        
            # Generate performance report
            perf_report = self.performance_tracker.generate_report()
            logger.info(f"\n📊 Performance Report:\n{json.dumps(perf_report, indent=2)}")
            
            # If all tests passed, we're done!
            if all_passed:
                logger.info("\n🎉 All tests passing! System is working perfectly.")
                self.git_commit(f"All tests passing - iteration {self.iteration_count}")
                break
                
            # Attempt to fix failures
            logger.info(f"\n🔧 Attempting to fix {len(failed_tests)} failures...")
            
            for test_case, result in failed_tests:
                fix_applied = await self.attempt_fix(test_case, result)
                
                if fix_applied:
                    # Re-run the test
                    retest_result = await self.validate_with_retries(
                        test_case,
                        test_case.get('expected', {})
                    )
                    
                    if retest_result.success:
                        logger.info(f"✅ Fix successful for: {test_case['name']}")
                        self.git_commit(f"Fixed: {test_case['name']}")
                    else:
                        logger.error(f"❌ Fix failed for: {test_case['name']}")
                        self.git_rollback()
                        
            # Brief pause before next iteration
            await asyncio.sleep(5)
            
        logger.info(f"\n🏁 Testing loop completed after {self.iteration_count} iterations")
        
    async def attempt_fix(self, test_case: Dict[str, Any], 
                         result: TestResult) -> bool:
        """Attempt to fix a failing test"""
        # This is a placeholder for the auto-fix logic
        # In a real implementation, this would analyze the failure
        # and apply appropriate fixes
        
        logger.info(f"Analyzing failure for: {test_case['name']}")
        logger.info(f"Errors: {result.errors}")
        
        # For now, we'll just return False
        # Real implementation would analyze the error and generate fixes
        return False
        
    async def run(self):
        """Main entry point"""
        try:
            await self.run_continuous_loop()
        finally:
            # Save final results
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            results_file = f"test_results_iterative_{timestamp}.json"
            
            with open(results_file, 'w') as f:
                json.dump({
                    'timestamp': timestamp,
                    'iterations': self.iteration_count,
                    'total_tests': len(self.test_results),
                    'results': [
                        {
                            'test_name': r.test_name,
                            'success': r.success,
                            'attempts': r.attempts,
                            'errors': r.errors,
                            'metrics': r.metrics,
                            'timestamp': r.timestamp.isoformat()
                        }
                        for r in self.test_results
                    ],
                    'performance_summary': self.performance_tracker.generate_report()
                }, f, indent=2)
                
            logger.info(f"\n📄 Results saved to: {results_file}")


async def main():
    """Main entry point"""
    async with IterativeTestRunner() as runner:
        await runner.run()


if __name__ == "__main__":
    asyncio.run(main())