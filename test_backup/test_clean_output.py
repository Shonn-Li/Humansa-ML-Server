#!/usr/bin/env python3
"""
Clean, human-readable test suite for multi-agent system
Shows: Query -> Agents Triggered -> Final Response
"""

import asyncio
import httpx
import json
from typing import Dict, List, Optional
from datetime import datetime
import sys

class CleanAgentTester:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=60.0)
        self.base_url = "http://localhost:5002/v1/multi-agent/response"
        
    async def test_query(self, name: str, query: str, attachments: List[str] = None) -> Dict:
        """Test a single query and return clean results"""
        request_data = {
            "messages": [{"role": "user", "content": query}],
            "user_id": 10001,
            "model": "gpt-4.1-nano",
            "stream": True,
            "enable_citations": True,
            "attachments": attachments or []
        }
        
        # Initialize result
        result = {
            "name": name,
            "query": query,
            "attachments": attachments or [],
            "agents_triggered": [],
            "response": "",
            "citations": [],
            "status": "pending",
            "error": None
        }
        
        try:
            # Collect streaming response
            events = []
            async with self.client.stream('POST', self.base_url, json=request_data) as response:
                async for line in response.aiter_lines():
                    if line.startswith('data: '):
                        event_data = line[6:]
                        if event_data == '[DONE]':
                            break
                        try:
                            event = json.loads(event_data)
                            events.append(event)
                        except:
                            pass
            
            # Process events to extract clean information
            for event in events:
                event_type = event.get('type', '')
                
                # Detect agents
                if 'reasoning' in event_type and 'router' not in result['agents_triggered']:
                    result['agents_triggered'].append('router')
                    
                if 'file_search' in event_type and 'rag' not in result['agents_triggered']:
                    result['agents_triggered'].append('rag')
                    
                if 'web_search' in event_type and 'web_search' not in result['agents_triggered']:
                    result['agents_triggered'].append('web_search')
                    
                if 'attachment' in event_type.lower() and 'attachment' not in result['agents_triggered']:
                    result['agents_triggered'].append('attachment')
                    
                if ('function_tool' in event_type or 'code' in event_type.lower()) and 'code_interpreter' not in result['agents_triggered']:
                    result['agents_triggered'].append('code_interpreter')
                    
                if 'output_text' in event_type and 'response' not in result['agents_triggered']:
                    result['agents_triggered'].append('response')
                    
                if 'citation' in event_type and 'citation' not in result['agents_triggered']:
                    result['agents_triggered'].append('citation')
                
                # Collect response text
                if event_type == 'response.output_text.delta':
                    result['response'] += event.get('delta', '')
                
                # Collect citations
                if event_type == 'response.citations':
                    result['citations'] = event.get('citations', [])
            
            # Determine status
            if result['response']:
                result['status'] = 'success'
            else:
                result['status'] = 'failed'
                result['error'] = 'No response generated'
                
        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)
            
        return result
    
    async def run_test_suite(self):
        """Run comprehensive test suite"""
        print("="*80)
        print("MULTI-AGENT SYSTEM TEST SUITE")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)
        
        # Define test cases
        test_cases = [
            # RAG Tests
            ("RAG: Note Query", "What information do I have about the PARL paper?"),
            ("RAG: Conversation Query", "What did we discuss about reinforcement learning?"),
            
            # Web Search Tests
            ("Web Search: Current Events", "What are the latest AI developments today?"),
            
            # Code Interpreter Tests
            ("Code: Simple Calculation", "Calculate the fibonacci sequence up to 10 terms"),
            ("Code: Data Visualization", "Create a bar chart showing note types: PDF=3, YouTube=4, Document=1, Audio=1"),
            
            # Attachment Tests
            ("Attachment: PDF Analysis", "Summarize this paper", ["https://arxiv.org/pdf/2505.18499.pdf"]),
            ("Attachment: Image Analysis", "What's shown in this diagram?", ["https://arxiv.org/html/2407.09124v1/x1.png"]),
            
            # Mixed Tests
            ("Mixed: Note + Code", "Analyze the metrics in my G1 paper note and create a visualization"),
            ("Mixed: Note + Web", "How do my startup notes compare to current AI startup trends?"),
        ]
        
        # Run tests
        results = []
        for test_case in test_cases:
            name = test_case[0]
            query = test_case[1]
            attachments = test_case[2] if len(test_case) > 2 else None
            
            print(f"\n{'='*80}")
            print(f"TEST: {name}")
            print(f"QUERY: {query}")
            if attachments:
                print(f"ATTACHMENTS: {attachments}")
            print("-"*80)
            
            result = await self.test_query(name, query, attachments)
            results.append(result)
            
            # Print results
            print(f"AGENTS: {' → '.join(result['agents_triggered']) if result['agents_triggered'] else 'None'}")
            print(f"STATUS: {result['status'].upper()}")
            
            if result['response']:
                # Clean response formatting
                response_preview = result['response'].strip()
                if len(response_preview) > 300:
                    response_preview = response_preview[:300] + "..."
                print(f"\nRESPONSE:\n{response_preview}")
            else:
                print(f"\nERROR: {result['error']}")
            
            if result['citations']:
                print(f"\nCITATIONS: {len(result['citations'])} sources")
            
            # Small delay between tests
            await asyncio.sleep(2)
        
        # Summary
        print(f"\n{'='*80}")
        print("TEST SUMMARY")
        print("="*80)
        
        success_count = sum(1 for r in results if r['status'] == 'success')
        total_count = len(results)
        
        print(f"Total Tests: {total_count}")
        print(f"Successful: {success_count} ({success_count/total_count*100:.1f}%)")
        print(f"Failed: {total_count - success_count} ({(total_count - success_count)/total_count*100:.1f}%)")
        
        # Agent usage statistics
        print("\nAgent Usage:")
        agent_stats = {}
        for result in results:
            for agent in result['agents_triggered']:
                agent_stats[agent] = agent_stats.get(agent, 0) + 1
        
        for agent, count in sorted(agent_stats.items(), key=lambda x: x[1], reverse=True):
            print(f"  {agent}: {count}/{total_count} ({count/total_count*100:.1f}%)")
        
        # Failed tests details
        failed_tests = [r for r in results if r['status'] != 'success']
        if failed_tests:
            print("\nFailed Tests:")
            for test in failed_tests:
                print(f"  - {test['name']}: {test['error']}")
                print(f"    Agents: {test['agents_triggered']}")
        
        await self.client.aclose()

async def main():
    tester = CleanAgentTester()
    await tester.run_test_suite()

if __name__ == "__main__":
    asyncio.run(main())