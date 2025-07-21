#!/usr/bin/env python3
"""
Final status test - clean, readable output showing agent functionality
"""

import asyncio
import httpx
import json
from typing import Dict, List
from datetime import datetime

class FinalAgentTest:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.base_url = "http://localhost:5001/v1/multi-agent/response"
        
    async def test_agent(self, name: str, query: str, attachments: List[str] = None) -> Dict:
        """Test a single agent configuration"""
        request_data = {
            "messages": [{"role": "user", "content": query}],
            "user_id": 10001,
            "model": "gpt-4o-mini",
            "stream": True,
            "enable_citations": True,
            "attachments": attachments or []
        }
        
        result = {
            "test": name,
            "query": query,
            "agents": [],
            "response_length": 0,
            "has_response": False,
            "has_citations": False,
            "error": None
        }
        
        try:
            agents_detected = set()
            response_text = ""
            citations = []
            
            async with self.client.stream('POST', self.base_url, json=request_data) as response:
                async for line in response.aiter_lines():
                    if line.startswith('data: '):
                        event_data = line[6:]
                        if event_data == '[DONE]':
                            break
                        try:
                            event = json.loads(event_data)
                            event_type = event.get('type', '')
                            
                            # Detect agents from events
                            if 'reasoning' in event_type:
                                agents_detected.add('router')
                            if 'file_search' in event_type:
                                agents_detected.add('rag')
                            if 'web_search' in event_type:
                                agents_detected.add('web_search')
                            if 'attachment' in event_type.lower():
                                agents_detected.add('attachment')
                            if 'function_tool' in event_type or 'code' in event_type.lower():
                                agents_detected.add('code_interpreter')
                            if 'output_text' in event_type:
                                agents_detected.add('response')
                            if 'citation' in event_type:
                                agents_detected.add('citation')
                                citations = event.get('citations', [])
                            
                            # Collect response
                            if event_type == 'response.output_text.delta':
                                response_text += event.get('delta', '')
                                
                        except: pass
            
            result['agents'] = sorted(list(agents_detected))
            result['response_length'] = len(response_text)
            result['has_response'] = len(response_text) > 0
            result['has_citations'] = len(citations) > 0
            
        except Exception as e:
            result['error'] = str(e)
            
        return result
    
    async def run_all_tests(self):
        """Run comprehensive agent tests"""
        print("="*80)
        print(f"MULTI-AGENT SYSTEM STATUS CHECK")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)
        
        # Test cases designed to trigger specific agents
        test_cases = [
            # RAG Tests
            {
                "name": "RAG - Note Search",
                "query": "What information is in my PARL paper note?",
                "attachments": None,
                "expected": ["router", "rag", "response"]
            },
            {
                "name": "RAG - Conversation Search", 
                "query": "What did we discuss about reinforcement learning?",
                "attachments": None,
                "expected": ["router", "rag", "response"]
            },
            
            # Web Search Test
            {
                "name": "Web Search",
                "query": "What are the latest AI developments in 2024?",
                "attachments": None,
                "expected": ["router", "web_search", "response"]
            },
            
            # Code Interpreter Tests
            {
                "name": "Code - Calculation",
                "query": "Write Python code to calculate the fibonacci sequence",
                "attachments": None,
                "expected": ["router", "code_interpreter", "response"]
            },
            {
                "name": "Code - Visualization",
                "query": "Create a matplotlib bar chart with data: A=10, B=20, C=15",
                "attachments": None,
                "expected": ["router", "code_interpreter", "response"]
            },
            
            # Attachment Tests
            {
                "name": "Attachment - PDF",
                "query": "Analyze this PDF document",
                "attachments": ["https://arxiv.org/pdf/2505.18499.pdf"],
                "expected": ["router", "attachment", "response"]
            },
            {
                "name": "Attachment - Image",
                "query": "What's shown in this image?",
                "attachments": ["https://arxiv.org/html/2407.09124v1/x1.png"],
                "expected": ["router", "attachment", "response"]
            }
        ]
        
        # Run tests
        results = []
        for test_case in test_cases:
            print(f"\nTesting: {test_case['name']}")
            print(f"Query: {test_case['query']}")
            if test_case['attachments']:
                print(f"Attachments: {test_case['attachments']}")
            
            result = await self.test_agent(
                test_case['name'],
                test_case['query'],
                test_case['attachments']
            )
            results.append({**result, "expected": test_case['expected']})
            
            # Print immediate results
            status = "✅" if result['has_response'] else "❌"
            print(f"Result: {status}")
            print(f"Agents: {' → '.join(result['agents'])}")
            if not result['has_response'] and result['error']:
                print(f"Error: {result['error']}")
            
            await asyncio.sleep(1)  # Small delay between tests
        
        # Summary
        print(f"\n{'='*80}")
        print("SUMMARY")
        print("="*80)
        
        # Success rate
        successful = sum(1 for r in results if r['has_response'])
        total = len(results)
        print(f"\nSuccess Rate: {successful}/{total} ({successful/total*100:.0f}%)")
        
        # Agent functionality
        print("\nAgent Functionality:")
        agent_counts = {}
        for result in results:
            for agent in result['agents']:
                agent_counts[agent] = agent_counts.get(agent, 0) + 1
        
        for agent, count in sorted(agent_counts.items()):
            status = "✅" if count > 0 else "❌"
            print(f"  {status} {agent}: {count}/{total} tests")
        
        # Missing expected agents
        print("\nTest Details:")
        for result in results:
            missing = set(result['expected']) - set(result['agents'])
            if missing or not result['has_response']:
                print(f"\n  {result['test']}:")
                print(f"    Expected: {result['expected']}")
                print(f"    Actual: {result['agents']}")
                if missing:
                    print(f"    Missing: {list(missing)}")
                if not result['has_response']:
                    print(f"    No response generated")
        
        # Citation status
        citation_tests = sum(1 for r in results if r['has_citations'])
        print(f"\nCitations: {citation_tests}/{total} tests had citations")
        
        await self.client.aclose()

async def main():
    tester = FinalAgentTest()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())