#!/usr/bin/env python3
"""
Clean test output with optional detailed logs
Shows summary first, then allows viewing details
"""

import asyncio
import httpx
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List
import subprocess

class CleanDetailedTester:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=60.0)
        self.base_url = "http://localhost:5001/v1/multi-agent/response"
        self.test_dir = Path(f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        self.test_dir.mkdir(exist_ok=True)
        
    async def test_query(self, name: str, query: str, attachments: List[str] = None) -> Dict:
        """Run a single test and capture results"""
        # Create log marker
        log_marker = f"TEST_{name.replace(' ', '_')}_{datetime.now().timestamp()}"
        
        # Insert marker into ML server log
        subprocess.run(
            f"echo '\n=== {log_marker} ===' >> /Users/shonnli/Non-icloudFile/YouWoAI/Code_V1/YouWoAI-ML-Server/ml_server_test.log",
            shell=True
        )
        
        request_data = {
            "messages": [{"role": "user", "content": query}],
            "user_id": 10001,
            "model": "gpt-4.1-nano",
            "stream": True,
            "enable_citations": True,
            "attachments": attachments or []
        }
        
        result = {
            "name": name,
            "query": query,
            "attachments": attachments or [],
            "agents": [],
            "response": "",
            "citations": 0,
            "success": False,
            "log_marker": log_marker
        }
        
        try:
            async with self.client.stream('POST', self.base_url, json=request_data) as response:
                async for line in response.aiter_lines():
                    if line.startswith('data: '):
                        event_data = line[6:]
                        if event_data == '[DONE]':
                            break
                        try:
                            event = json.loads(event_data)
                            event_type = event.get('type', '')
                            
                            # Track agents
                            if 'reasoning' in event_type and 'router' not in result['agents']:
                                result['agents'].append('router')
                            if 'file_search' in event_type and 'rag' not in result['agents']:
                                result['agents'].append('rag')
                            if 'web_search' in event_type and 'web_search' not in result['agents']:
                                result['agents'].append('web_search')
                            if 'attachment' in event_type.lower() and 'attachment' not in result['agents']:
                                result['agents'].append('attachment')
                            if ('function_tool' in event_type or 'code' in event_type.lower()) and 'code_interpreter' not in result['agents']:
                                result['agents'].append('code_interpreter')
                            if 'output_text' in event_type and 'response' not in result['agents']:
                                result['agents'].append('response')
                            if 'citation' in event_type:
                                if 'citation' not in result['agents']:
                                    result['agents'].append('citation')
                                if 'citations' in event:
                                    result['citations'] = len(event.get('citations', []))
                            
                            # Collect response
                            if event_type == 'response.output_text.delta':
                                result['response'] += event.get('delta', '')
                                
                        except: pass
            
            result['success'] = len(result['response']) > 0
            
        except Exception as e:
            result['error'] = str(e)
        
        # Save ML server logs for this test
        await asyncio.sleep(0.5)  # Let logs flush
        self.save_test_logs(result)
        
        return result
    
    def save_test_logs(self, result: Dict):
        """Save ML server logs for a specific test"""
        try:
            log_file = Path("/Users/shonnli/Non-icloudFile/YouWoAI/Code_V1/YouWoAI-ML-Server/ml_server_test.log")
            if log_file.exists():
                with open(log_file, 'r') as f:
                    content = f.read()
                
                # Find logs after marker
                marker = result['log_marker']
                if marker in content:
                    relevant_logs = content.split(marker)[1].split('\n=== TEST_')[0]
                    
                    # Save to file
                    test_log_file = self.test_dir / f"{result['name'].replace(' ', '_')}_logs.txt"
                    with open(test_log_file, 'w') as f:
                        f.write(f"=== ML Server Logs for: {result['name']} ===\n")
                        f.write(f"Query: {result['query']}\n")
                        f.write(f"Timestamp: {datetime.now()}\n")
                        f.write("="*80 + "\n\n")
                        f.write(relevant_logs)
                        
        except Exception as e:
            print(f"Error saving logs: {e}")
    
    async def run_all_tests(self):
        """Run all tests with clean output"""
        print("="*80)
        print("MULTI-AGENT SYSTEM TEST SUITE")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Results saved to: {self.test_dir}")
        print("="*80)
        
        test_cases = [
            # RAG Tests
            ("RAG: My Notes", "What information is in my PARL paper note?"),
            ("RAG: Conversations", "What did we discuss about reinforcement learning?"),
            ("RAG: Mixed Search", "Show me everything about G1 from my notes and conversations"),
            
            # Multi-Agent Tests
            ("Multi: RAG + Web", "Compare my PARL notes with latest 2024 reinforcement learning research"),
            ("Multi: RAG + Code", "Create Python code based on the algorithms in my G1 paper"),
            ("Multi: Notes + Analysis", "Analyze all my startup notes and create a summary with key metrics"),
            
            # Attachment Tests
            ("Attachment: PDF", "Analyze this PDF", ["https://arxiv.org/pdf/2505.18499.pdf"]),
            ("Attachment: Multi", "Compare these papers", ["https://arxiv.org/pdf/2505.18499.pdf", "https://arxiv.org/pdf/2311.18703.pdf"]),
            
            # Edge Cases
            ("Citation Test", "Summarize my notes with proper citations"),
            ("Complex Query", "Based on all my ML papers, web research, and this attachment, create a comprehensive RL tutorial", ["https://arxiv.org/pdf/2505.18499.pdf"]),
        ]
        
        results = []
        print("\nRUNNING TESTS:")
        print("-"*80)
        
        for i, test_case in enumerate(test_cases):
            name = test_case[0]
            query = test_case[1]
            attachments = test_case[2] if len(test_case) > 2 else None
            
            print(f"\n[{i+1}/{len(test_cases)}] {name}")
            print(f"    Query: {query[:60]}{'...' if len(query) > 60 else ''}")
            
            result = await self.test_query(name, query, attachments)
            results.append(result)
            
            # Print summary
            status = "✅" if result['success'] else "❌"
            agents_str = " → ".join(result['agents']) if result['agents'] else "None"
            print(f"    {status} Agents: {agents_str}")
            print(f"    Response: {len(result['response'])} chars | Citations: {result['citations']}")
            
            await asyncio.sleep(1)
        
        # Summary
        print("\n" + "="*80)
        print("SUMMARY")
        print("="*80)
        
        successful = sum(1 for r in results if r['success'])
        print(f"\nSuccess Rate: {successful}/{len(results)} ({successful/len(results)*100:.0f}%)")
        
        # Agent statistics
        print("\nAgent Usage:")
        agent_counts = {}
        for result in results:
            for agent in result['agents']:
                agent_counts[agent] = agent_counts.get(agent, 0) + 1
        
        for agent, count in sorted(agent_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  {agent}: {count}/{len(results)} ({count/len(results)*100:.0f}%)")
        
        # Failed tests
        failed = [r for r in results if not r['success']]
        if failed:
            print("\nFailed Tests:")
            for test in failed:
                print(f"  - {test['name']}")
                print(f"    Agents triggered: {test['agents']}")
        
        # Multi-agent workflows
        multi_agent = [r for r in results if len(r['agents']) >= 3]
        print(f"\nMulti-Agent Workflows: {len(multi_agent)}/{len(results)}")
        for test in multi_agent:
            print(f"  - {test['name']}: {' → '.join(test['agents'])}")
        
        # Save detailed report
        self.save_detailed_report(results)
        
        print(f"\n📁 Detailed logs saved to: {self.test_dir}")
        print("   View individual test logs for ML server details")
        
        await self.client.aclose()
    
    def save_detailed_report(self, results: List[Dict]):
        """Save detailed report with all information"""
        report_file = self.test_dir / "DETAILED_REPORT.md"
        
        with open(report_file, 'w') as f:
            f.write("# Detailed Test Report\n\n")
            f.write(f"Generated: {datetime.now()}\n\n")
            
            for i, result in enumerate(results):
                f.write(f"## Test {i+1}: {result['name']}\n\n")
                f.write(f"**Query:** {result['query']}\n\n")
                if result['attachments']:
                    f.write(f"**Attachments:** {result['attachments']}\n\n")
                f.write(f"**Success:** {'Yes' if result['success'] else 'No'}\n\n")
                f.write(f"**Agents:** {' → '.join(result['agents']) if result['agents'] else 'None'}\n\n")
                f.write(f"**Citations:** {result['citations']}\n\n")
                
                if result['response']:
                    f.write("**Response Preview:**\n```\n")
                    f.write(result['response'][:500] + "..." if len(result['response']) > 500 else result['response'])
                    f.write("\n```\n\n")
                
                f.write(f"**ML Server Logs:** See `{result['name'].replace(' ', '_')}_logs.txt`\n\n")
                f.write("-"*80 + "\n\n")

async def main():
    tester = CleanDetailedTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())