#!/usr/bin/env python3
"""
Test new features: attachment priority, citations, and iterative workflows
"""

import asyncio
import httpx
import json
from datetime import datetime
from typing import Dict, List

class NewFeaturesTester:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=120.0)
        self.base_url = "http://localhost:5001/v1/multi-agent/response"
        self.results = []
        
    async def test_attachment_priority(self):
        """Test that attachments get priority routing"""
        print("\n" + "="*80)
        print("TEST: Attachment Priority")
        print("="*80)
        
        test_cases = [
            {
                "name": "Attachment with generic query",
                "query": "What is this?",  # Generic query that would normally go elsewhere
                "attachments": ["https://arxiv.org/pdf/2505.18499.pdf"]
            },
            {
                "name": "Attachment with note query",
                "query": "Compare this to my notes",
                "attachments": ["https://arxiv.org/pdf/2311.18703.pdf"]
            },
            {
                "name": "Multiple attachments",
                "query": "Analyze these",
                "attachments": [
                    "https://arxiv.org/pdf/2505.18499.pdf",
                    "https://arxiv.org/pdf/2311.18703.pdf"
                ]
            }
        ]
        
        for test in test_cases:
            print(f"\nTest: {test['name']}")
            print(f"Query: {test['query']}")
            print(f"Attachments: {test['attachments']}")
            
            result = await self._run_test(test['query'], test['attachments'])
            
            # Check if attachment agent was triggered
            attachment_triggered = 'attachment' in result['agents']
            print(f"Attachment agent triggered: {'✅' if attachment_triggered else '❌'}")
            print(f"All agents: {' → '.join(result['agents'])}")
            
            self.results.append({
                "test": "attachment_priority",
                "case": test['name'],
                "success": attachment_triggered,
                "agents": result['agents']
            })
    
    async def test_citation_formatting(self):
        """Test that citations are properly formatted"""
        print("\n" + "="*80)
        print("TEST: Citation Formatting")
        print("="*80)
        
        test_cases = [
            {
                "name": "RAG with citations",
                "query": "What do my notes say about reinforcement learning? Include citations."
            },
            {
                "name": "Web search with citations",
                "query": "What are the latest AI developments in 2024? Cite your sources."
            },
            {
                "name": "Mixed sources citation",
                "query": "Compare information from my notes with this paper and cite all sources",
                "attachments": ["https://arxiv.org/pdf/2505.18499.pdf"]
            }
        ]
        
        for test in test_cases:
            print(f"\nTest: {test['name']}")
            print(f"Query: {test['query']}")
            
            result = await self._run_test(
                test['query'], 
                test.get('attachments', []),
                enable_citations=True
            )
            
            # Check for citation markers
            has_citations = False
            has_sources = False
            if result['response']:
                # Look for [1], [2], etc.
                for i in range(1, 10):
                    if f"[{i}]" in result['response']:
                        has_citations = True
                        break
                
                # Look for Sources section
                has_sources = "Sources:" in result['response'] or "References:" in result['response']
                
            print(f"Citation markers found: {'✅' if has_citations else '❌'}")
            print(f"Sources section found: {'✅' if has_sources else '❌'}")
            print(f"Citation agent triggered: {'✅' if 'citation' in result['agents'] else '❌'}")
            
            if has_citations:
                # Show a preview of the cited response
                print("\nResponse preview with citations:")
                lines = result['response'].split('\n')
                for line in lines[:5]:  # First 5 lines
                    if '[' in line and ']' in line:
                        print(f"  {line}")
            
            self.results.append({
                "test": "citation_formatting",
                "case": test['name'],
                "success": has_citations and 'citation' in result['agents'],
                "has_markers": has_citations,
                "has_sources": has_sources
            })
    
    async def test_iterative_workflows(self):
        """Test iterative agent workflows"""
        print("\n" + "="*80)
        print("TEST: Iterative Workflows")
        print("="*80)
        
        test_cases = [
            {
                "name": "Complex query requiring iteration",
                "query": "Analyze all my ML papers, find gaps in the research, and suggest new research directions based on current trends"
            },
            {
                "name": "Incomplete initial response",
                "query": "Create a comprehensive tutorial on reinforcement learning based on all available sources"
            }
        ]
        
        for test in test_cases:
            print(f"\nTest: {test['name']}")
            print(f"Query: {test['query']}")
            
            result = await self._run_test(
                test['query'],
                enable_iterations=True,
                capture_metadata=True
            )
            
            # Check for iterations in metadata
            iterations = 0
            if result.get('metadata'):
                agent_results = result['metadata'].get('agent_results', {})
                for key in agent_results:
                    if key.startswith('iteration_'):
                        iterations += 1
            
            print(f"Iterations performed: {iterations}")
            print(f"Total agents triggered: {len(result['agents'])}")
            
            if iterations > 0:
                print("Iteration details:")
                for i in range(1, iterations + 1):
                    iter_data = agent_results.get(f'iteration_{i}', {})
                    print(f"  Iteration {i}: {iter_data.get('agents', [])}")
            
            self.results.append({
                "test": "iterative_workflows",
                "case": test['name'],
                "success": iterations > 0,
                "iterations": iterations,
                "total_agents": len(result['agents'])
            })
    
    async def _run_test(self, query: str, attachments: List[str] = None, 
                       enable_citations: bool = True, enable_iterations: bool = True,
                       capture_metadata: bool = False) -> Dict:
        """Run a single test and return results"""
        request_data = {
            "messages": [{"role": "user", "content": query}],
            "user_id": 10001,
            "model": "gpt-4o-mini",
            "stream": False,  # Non-streaming for easier testing
            "enable_citations": enable_citations,
            "enable_iterations": enable_iterations,
            "attachments": attachments or []
        }
        
        result = {
            "query": query,
            "agents": [],
            "response": "",
            "error": None,
            "metadata": None
        }
        
        try:
            response = await self.client.post(self.base_url, json=request_data)
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract agents from metadata
                if 'metadata' in data:
                    result['metadata'] = data['metadata']
                    agent_results = data['metadata'].get('agent_results', {})
                    
                    # Extract agent names
                    for key in agent_results:
                        if key.endswith('_agent') and agent_results[key].get('status') == 'success':
                            agent_name = key.replace('_agent', '')
                            if agent_name not in result['agents']:
                                result['agents'].append(agent_name)
                
                # Extract response
                if 'choices' in data and data['choices']:
                    result['response'] = data['choices'][0].get('message', {}).get('content', '')
            else:
                result['error'] = f"Status {response.status_code}: {response.text}"
                
        except Exception as e:
            result['error'] = str(e)
            
        return result
    
    async def run_all_tests(self):
        """Run all feature tests"""
        print("NEW FEATURES TEST SUITE")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Run tests
        await self.test_attachment_priority()
        await self.test_citation_formatting()
        await self.test_iterative_workflows()
        
        # Summary
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)
        
        # Group by test type
        test_groups = {}
        for result in self.results:
            test_type = result['test']
            if test_type not in test_groups:
                test_groups[test_type] = []
            test_groups[test_type].append(result)
        
        for test_type, results in test_groups.items():
            successful = sum(1 for r in results if r['success'])
            total = len(results)
            print(f"\n{test_type.replace('_', ' ').title()}:")
            print(f"  Success rate: {successful}/{total} ({successful/total*100:.0f}%)")
            
            for result in results:
                status = "✅" if result['success'] else "❌"
                print(f"  {status} {result['case']}")
        
        await self.client.aclose()

async def main():
    tester = NewFeaturesTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    # First, ensure ML server is running
    print("Make sure:")
    print("1. ML server is running with the new code")
    print("2. Test database is active on port 5454")
    print("\nStarting tests in 3 seconds...")
    asyncio.run(asyncio.sleep(3))
    
    asyncio.run(main())