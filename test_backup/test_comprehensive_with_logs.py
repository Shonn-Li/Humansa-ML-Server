#!/usr/bin/env python3
"""
Comprehensive test suite with detailed logging and multi-agent workflows
"""

import asyncio
import httpx
import json
import os
import sys
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import subprocess
import time

class ComprehensiveAgentTester:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=120.0)
        self.base_url = "http://localhost:5001/v1/multi-agent/response"
        
        # Create test output directory with timestamp
        self.test_run_dir = Path(f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        self.test_run_dir.mkdir(exist_ok=True)
        
        # Set up logging
        self.setup_logging()
        
    def setup_logging(self):
        """Set up comprehensive logging"""
        log_file = self.test_run_dir / "test_run.log"
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def capture_ml_server_logs(self, test_name: str, start_marker: str) -> str:
        """Capture ML server logs for a specific test"""
        try:
            # Read the ML server log file
            log_file = Path("/Users/shonnli/Non-icloudFile/YouWoAI/Code_V1/YouWoAI-ML-Server/ml_server_test.log")
            if not log_file.exists():
                return "ML server log file not found"
            
            # Find logs after the start marker
            with open(log_file, 'r') as f:
                lines = f.readlines()
            
            # Find the start position
            start_idx = -1
            for i in range(len(lines)-1, -1, -1):
                if start_marker in lines[i]:
                    start_idx = i
                    break
            
            if start_idx == -1:
                return "Start marker not found in logs"
            
            # Extract logs from start marker to end
            relevant_logs = ''.join(lines[start_idx:])
            
            # Save to test-specific file
            test_log_file = self.test_run_dir / f"{test_name.replace(' ', '_')}_ml_server.log"
            with open(test_log_file, 'w') as f:
                f.write(relevant_logs)
            
            return relevant_logs
            
        except Exception as e:
            return f"Error capturing logs: {str(e)}"
    
    async def test_query(self, test_case: Dict) -> Dict:
        """Execute a single test case with comprehensive logging"""
        test_name = test_case['name']
        query = test_case['query']
        attachments = test_case.get('attachments', [])
        expected_agents = test_case.get('expected_agents', [])
        
        # Create unique marker for log capture
        log_marker = f"TEST_START_{test_name}_{datetime.now().timestamp()}"
        self.logger.info(f"\n{'='*80}")
        self.logger.info(f"Starting test: {test_name}")
        self.logger.info(f"Query: {query}")
        if attachments:
            self.logger.info(f"Attachments: {attachments}")
        self.logger.info(f"Expected agents: {expected_agents}")
        self.logger.info(f"Log marker: {log_marker}")
        
        # Insert marker into ML server logs
        subprocess.run(["echo", f"\n\n=== {log_marker} ===\n", ">>", "/Users/shonnli/Non-icloudFile/YouWoAI/Code_V1/YouWoAI-ML-Server/ml_server_test.log"], shell=True)
        
        # Prepare request
        request_data = {
            "messages": [{"role": "user", "content": query}],
            "user_id": 10001,
            "model": "gpt-4.1-nano",
            "stream": True,
            "enable_citations": True,
            "attachments": attachments
        }
        
        # Initialize result
        result = {
            "test_name": test_name,
            "query": query,
            "attachments": attachments,
            "expected_agents": expected_agents,
            "actual_agents": [],
            "agent_sequence": [],  # Track order of agent execution
            "response": "",
            "citations": [],
            "status": "pending",
            "error": None,
            "events": [],
            "ml_server_logs": "",
            "duration": 0
        }
        
        start_time = time.time()
        
        try:
            # Collect streaming response
            event_count = 0
            async with self.client.stream('POST', self.base_url, json=request_data) as response:
                async for line in response.aiter_lines():
                    if line.startswith('data: '):
                        event_data = line[6:]
                        if event_data == '[DONE]':
                            break
                        try:
                            event = json.loads(event_data)
                            event_count += 1
                            
                            # Store event for analysis
                            result['events'].append({
                                "index": event_count,
                                "type": event.get('type', 'unknown'),
                                "data": event
                            })
                            
                            # Detailed agent tracking
                            event_type = event.get('type', '')
                            
                            # Track agent activation sequence
                            if 'reasoning' in event_type and 'router' not in result['actual_agents']:
                                result['actual_agents'].append('router')
                                result['agent_sequence'].append(('router', event_count))
                                
                            if 'file_search' in event_type and 'rag' not in result['actual_agents']:
                                result['actual_agents'].append('rag')
                                result['agent_sequence'].append(('rag', event_count))
                                
                            if 'web_search' in event_type and 'web_search' not in result['actual_agents']:
                                result['actual_agents'].append('web_search')
                                result['agent_sequence'].append(('web_search', event_count))
                                
                            if 'attachment' in event_type.lower() and 'attachment' not in result['actual_agents']:
                                result['actual_agents'].append('attachment')
                                result['agent_sequence'].append(('attachment', event_count))
                                
                            if ('function_tool' in event_type or 'code' in event_type.lower()) and 'code_interpreter' not in result['actual_agents']:
                                result['actual_agents'].append('code_interpreter')
                                result['agent_sequence'].append(('code_interpreter', event_count))
                                
                            if 'output_text' in event_type and 'response' not in result['actual_agents']:
                                result['actual_agents'].append('response')
                                result['agent_sequence'].append(('response', event_count))
                                
                            if 'citation' in event_type and 'citation' not in result['actual_agents']:
                                result['actual_agents'].append('citation')
                                result['agent_sequence'].append(('citation', event_count))
                                if 'citations' in event:
                                    result['citations'] = event['citations']
                            
                            # Collect response text
                            if event_type == 'response.output_text.delta':
                                result['response'] += event.get('delta', '')
                                
                        except json.JSONDecodeError as e:
                            self.logger.warning(f"Failed to parse event: {e}")
            
            # Determine status
            if result['response']:
                result['status'] = 'success'
            else:
                result['status'] = 'failed'
                result['error'] = 'No response generated'
                
        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)
            self.logger.error(f"Test error: {e}")
            
        result['duration'] = time.time() - start_time
        
        # Capture ML server logs for this test
        await asyncio.sleep(0.5)  # Give logs time to flush
        result['ml_server_logs'] = self.capture_ml_server_logs(test_name, log_marker)
        
        # Save individual test result
        self.save_test_result(result)
        
        return result
    
    def save_test_result(self, result: Dict):
        """Save individual test result to file"""
        test_file = self.test_run_dir / f"{result['test_name'].replace(' ', '_')}_result.json"
        with open(test_file, 'w') as f:
            # Create a serializable version
            serializable_result = {
                k: v for k, v in result.items() 
                if k not in ['ml_server_logs']  # Exclude large log data from JSON
            }
            json.dump(serializable_result, f, indent=2)
    
    async def run_test_suite(self):
        """Run comprehensive test suite"""
        print("="*80)
        print(f"COMPREHENSIVE MULTI-AGENT TEST SUITE")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Results directory: {self.test_run_dir}")
        print("="*80)
        
        # Define comprehensive test cases
        test_cases = [
            # Basic RAG Tests
            {
                "name": "RAG Notes Simple",
                "query": "What information do I have about the PARL paper?",
                "expected_agents": ["router", "rag", "response", "citation"]
            },
            {
                "name": "RAG Conversations",
                "query": "What did we discuss about predictability in reinforcement learning?",
                "expected_agents": ["router", "rag", "response", "citation"]
            },
            {
                "name": "RAG Mixed Search",
                "query": "Show me everything about reinforcement learning from my notes and our conversations",
                "expected_agents": ["router", "rag", "response", "citation"]
            },
            
            # Multi-Agent Workflows
            {
                "name": "Multi RAG Plus Web",
                "query": "Compare the reinforcement learning approaches in my PARL and G1 notes with the latest RL research from 2024",
                "expected_agents": ["router", "rag", "web_search", "response", "citation"]
            },
            {
                "name": "RAG Plus Code Analysis",
                "query": "Analyze the performance metrics in my G1 paper note and create Python code to visualize them",
                "expected_agents": ["router", "rag", "code_interpreter", "response", "citation"]
            },
            {
                "name": "Attachment Plus RAG",
                "query": "How does this attached paper compare to my existing notes on reinforcement learning?",
                "attachments": ["https://arxiv.org/pdf/2505.18499.pdf"],
                "expected_agents": ["router", "attachment", "rag", "response", "citation"]
            },
            
            # Complex Multi-Step Queries
            {
                "name": "Research Synthesis",
                "query": "Based on my notes about startup growth strategies and current AI market trends, create a business plan outline with key metrics",
                "expected_agents": ["router", "rag", "web_search", "response", "citation"]
            },
            {
                "name": "Technical Implementation",
                "query": "Using the algorithms described in my ML papers, write Python code to implement a simple reinforcement learning agent",
                "expected_agents": ["router", "rag", "code_interpreter", "response", "citation"]
            },
            
            # Citation-Heavy Tests
            {
                "name": "Academic Summary",
                "query": "Create a literature review summary of all my reinforcement learning papers with proper citations",
                "expected_agents": ["router", "rag", "response", "citation"]
            },
            
            # Edge Cases
            {
                "name": "Empty Query RAG",
                "query": "Show me all my notes",
                "expected_agents": ["router", "rag", "response", "citation"]
            },
            {
                "name": "Multiple Attachments",
                "query": "Compare these papers and relate them to my notes",
                "attachments": [
                    "https://arxiv.org/pdf/2505.18499.pdf",
                    "https://arxiv.org/pdf/2311.18703.pdf"
                ],
                "expected_agents": ["router", "attachment", "rag", "response", "citation"]
            }
        ]
        
        # Run tests
        results = []
        for i, test_case in enumerate(test_cases):
            print(f"\n[{i+1}/{len(test_cases)}] Running: {test_case['name']}")
            result = await self.test_query(test_case)
            results.append(result)
            
            # Print immediate feedback
            status_icon = "✅" if result['status'] == 'success' else "❌"
            print(f"Status: {status_icon} {result['status']}")
            print(f"Agents: {' → '.join([f'{agent}({idx})' for agent, idx in result['agent_sequence']])}")
            print(f"Response length: {len(result['response'])} chars")
            print(f"Citations: {len(result['citations'])}")
            print(f"Duration: {result['duration']:.2f}s")
            
            # Small delay between tests
            await asyncio.sleep(2)
        
        # Generate summary report
        self.generate_summary_report(results)
        
        await self.client.aclose()
        
    def generate_summary_report(self, results: List[Dict]):
        """Generate comprehensive summary report"""
        report_path = self.test_run_dir / "SUMMARY_REPORT.md"
        
        with open(report_path, 'w') as f:
            f.write(f"# Multi-Agent Test Suite Summary\n\n")
            f.write(f"**Test Run:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**Total Tests:** {len(results)}\n")
            
            # Success metrics
            successful = sum(1 for r in results if r['status'] == 'success')
            f.write(f"**Success Rate:** {successful}/{len(results)} ({successful/len(results)*100:.1f}%)\n\n")
            
            # Agent usage statistics
            f.write("## Agent Usage Statistics\n\n")
            agent_stats = {}
            for result in results:
                for agent in result['actual_agents']:
                    agent_stats[agent] = agent_stats.get(agent, 0) + 1
            
            f.write("| Agent | Usage Count | Percentage |\n")
            f.write("|-------|-------------|------------|\n")
            for agent, count in sorted(agent_stats.items(), key=lambda x: x[1], reverse=True):
                f.write(f"| {agent} | {count} | {count/len(results)*100:.1f}% |\n")
            
            # Multi-agent workflows
            f.write("\n## Multi-Agent Workflows\n\n")
            multi_agent_tests = [r for r in results if len(r['actual_agents']) > 3]
            f.write(f"Tests triggering 3+ agents: {len(multi_agent_tests)}\n\n")
            for test in multi_agent_tests:
                f.write(f"- **{test['test_name']}**: {' → '.join(test['actual_agents'])}\n")
            
            # Citation analysis
            f.write("\n## Citation Analysis\n\n")
            citation_tests = [r for r in results if r['citations']]
            f.write(f"Tests with citations: {len(citation_tests)}/{len(results)}\n")
            if not citation_tests:
                f.write("⚠️ **No tests generated citations!**\n")
            
            # Failed tests
            f.write("\n## Failed Tests\n\n")
            failed_tests = [r for r in results if r['status'] != 'success']
            if failed_tests:
                for test in failed_tests:
                    f.write(f"### {test['test_name']}\n")
                    f.write(f"- **Status:** {test['status']}\n")
                    f.write(f"- **Error:** {test['error']}\n")
                    f.write(f"- **Agents triggered:** {test['actual_agents']}\n")
                    f.write(f"- **Expected agents:** {test['expected_agents']}\n")
                    f.write(f"- **Missing agents:** {set(test['expected_agents']) - set(test['actual_agents'])}\n\n")
            else:
                f.write("All tests passed! 🎉\n")
            
            # Individual test details
            f.write("\n## Detailed Test Results\n\n")
            for result in results:
                status_icon = "✅" if result['status'] == 'success' else "❌"
                f.write(f"### {status_icon} {result['test_name']}\n")
                f.write(f"- **Query:** {result['query']}\n")
                if result['attachments']:
                    f.write(f"- **Attachments:** {result['attachments']}\n")
                f.write(f"- **Expected agents:** {result['expected_agents']}\n")
                f.write(f"- **Actual agents:** {result['actual_agents']}\n")
                f.write(f"- **Agent sequence:** {' → '.join([f'{a}({i})' for a, i in result['agent_sequence']])}\n")
                f.write(f"- **Response length:** {len(result['response'])} chars\n")
                f.write(f"- **Citations:** {len(result['citations'])}\n")
                f.write(f"- **Duration:** {result['duration']:.2f}s\n")
                f.write(f"- **Events captured:** {len(result['events'])}\n")
                
                # Show response preview
                if result['response']:
                    preview = result['response'][:200] + "..." if len(result['response']) > 200 else result['response']
                    f.write(f"- **Response preview:** {preview}\n")
                
                f.write(f"- **Log file:** {result['test_name'].replace(' ', '_')}_ml_server.log\n\n")
        
        print(f"\n\nSummary report saved to: {report_path}")
        print(f"All test results saved to: {self.test_run_dir}")

async def main():
    tester = ComprehensiveAgentTester()
    await tester.run_test_suite()

if __name__ == "__main__":
    asyncio.run(main())