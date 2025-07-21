#!/usr/bin/env python3
"""Comprehensive test for all features including streaming"""

import httpx
import asyncio
import json
from datetime import datetime
from typing import Dict, Any, List

class FeatureTester:
    def __init__(self):
        self.base_url = "http://localhost:5001/v1/multi-agent/response"
        self.results = []
        
    async def test_attachment_priority(self, stream: bool = False) -> Dict[str, Any]:
        """Test attachment priority routing"""
        print(f"\n{'='*60}")
        print(f"ATTACHMENT PRIORITY TEST (stream={stream})")
        print(f"{'='*60}")
        
        request = {
            "messages": [{"role": "user", "content": "What is this document about?"}],
            "user_id": 10001,
            "model": "gpt-4o-mini",
            "stream": stream,
            "attachments": ["https://arxiv.org/pdf/2505.18499.pdf"]
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                if stream:
                    content = ""
                    agents = set()
                    async with client.stream('POST', self.base_url, json=request) as response:
                        async for line in response.aiter_lines():
                            if line.startswith('data: '):
                                data_str = line[6:]
                                if data_str == '[DONE]':
                                    break
                                try:
                                    data = json.loads(data_str)
                                    if 'choices' in data and data['choices']:
                                        delta = data['choices'][0].get('delta', {})
                                        if 'content' in delta:
                                            content += delta['content']
                                    # Track agent usage from events
                                    if data.get('type') == 'response.agent.start':
                                        agents.add(data.get('agent'))
                                except json.JSONDecodeError:
                                    pass
                    
                    result = {
                        "success": True,
                        "content": content[:200] + "...",
                        "agents": list(agents),
                        "attachment_agent": "attachment" in agents
                    }
                else:
                    response = await client.post(self.base_url, json=request)
                    if response.status_code == 200:
                        data = response.json()
                        agent_results = data.get("metadata", {}).get("agent_results", {})
                        agents = [k.replace("_agent", "") for k in agent_results.keys()]
                        
                        result = {
                            "success": True,
                            "content": data['choices'][0]['message']['content'][:200] + "...",
                            "agents": agents,
                            "attachment_agent": "attachment" in agents
                        }
                    else:
                        result = {"success": False, "error": f"Status {response.status_code}"}
                        
                print(f"✅ Success: {result.get('success')}")
                print(f"Agents used: {result.get('agents', [])}")
                print(f"Attachment agent triggered: {'✅ YES' if result.get('attachment_agent') else '❌ NO'}")
                print(f"\nResponse preview: {result.get('content', 'N/A')}")
                
                return result
                
            except Exception as e:
                print(f"❌ Error: {str(e)}")
                return {"success": False, "error": str(e)}
    
    async def test_citation_formatting(self, stream: bool = False) -> Dict[str, Any]:
        """Test citation formatting with sources"""
        print(f"\n{'='*60}")
        print(f"CITATION FORMATTING TEST (stream={stream})")
        print(f"{'='*60}")
        
        request = {
            "messages": [{"role": "user", "content": "What are transformers in AI? Please include citations."}],
            "user_id": 10001,
            "model": "gpt-4o-mini",
            "stream": stream
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                if stream:
                    content = ""
                    agents = set()
                    citations = []
                    
                    async with client.stream('POST', self.base_url, json=request) as response:
                        async for line in response.aiter_lines():
                            if line.startswith('data: '):
                                data_str = line[6:]
                                if data_str == '[DONE]':
                                    break
                                try:
                                    data = json.loads(data_str)
                                    # Collect content
                                    if 'choices' in data and data['choices']:
                                        delta = data['choices'][0].get('delta', {})
                                        if 'content' in delta:
                                            content += delta['content']
                                    # Track agents
                                    if data.get('type') == 'response.agent.start':
                                        agents.add(data.get('agent'))
                                    # Collect citations
                                    if data.get('type') == 'response.citations':
                                        citations = data.get('citations', [])
                                except json.JSONDecodeError:
                                    pass
                    
                    has_markers = any(f"[{i}]" in content for i in range(1, 10))
                    has_sources = "Sources:" in content or "References:" in content
                    
                    result = {
                        "success": True,
                        "content": content,
                        "agents": list(agents),
                        "citation_agent": "citation" in agents,
                        "has_markers": has_markers,
                        "has_sources": has_sources,
                        "citation_count": len(citations)
                    }
                else:
                    response = await client.post(self.base_url, json=request)
                    if response.status_code == 200:
                        data = response.json()
                        content = data['choices'][0]['message']['content']
                        agent_results = data.get("metadata", {}).get("agent_results", {})
                        agents = [k.replace("_agent", "") for k in agent_results.keys()]
                        
                        has_markers = any(f"[{i}]" in content for i in range(1, 10))
                        has_sources = "Sources:" in content or "References:" in content
                        
                        result = {
                            "success": True,
                            "content": content,
                            "agents": agents,
                            "citation_agent": "citation" in agents,
                            "has_markers": has_markers,
                            "has_sources": has_sources
                        }
                    else:
                        result = {"success": False, "error": f"Status {response.status_code}"}
                
                print(f"✅ Success: {result.get('success')}")
                print(f"Agents used: {result.get('agents', [])}")
                print(f"Citation agent triggered: {'✅ YES' if result.get('citation_agent') else '❌ NO'}")
                print(f"Has citation markers [1], [2]: {'✅ YES' if result.get('has_markers') else '❌ NO'}")
                print(f"Has sources section: {'✅ YES' if result.get('has_sources') else '❌ NO'}")
                
                if result.get('has_markers'):
                    # Show example citation
                    content = result['content']
                    for line in content.split('\n'):
                        if '[' in line and ']' in line:
                            print(f"\nExample citation: {line[:100]}...")
                            break
                
                return result
                
            except Exception as e:
                print(f"❌ Error: {str(e)}")
                return {"success": False, "error": str(e)}
    
    async def test_iterative_workflow(self, stream: bool = False) -> Dict[str, Any]:
        """Test iterative agent workflow"""
        print(f"\n{'='*60}")
        print(f"ITERATIVE WORKFLOW TEST (stream={stream})")
        print(f"{'='*60}")
        
        request = {
            "messages": [{"role": "user", "content": "Provide a comprehensive analysis of quantum computing applications in cryptography, including current research, challenges, and future prospects. Be very thorough and detailed."}],
            "user_id": 10001,
            "model": "gpt-4o-mini",
            "stream": stream
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                if stream:
                    content = ""
                    agents = set()
                    iterations = 0
                    
                    async with client.stream('POST', self.base_url, json=request) as response:
                        async for line in response.aiter_lines():
                            if line.startswith('data: '):
                                data_str = line[6:]
                                if data_str == '[DONE]':
                                    break
                                try:
                                    data = json.loads(data_str)
                                    if 'choices' in data and data['choices']:
                                        delta = data['choices'][0].get('delta', {})
                                        if 'content' in delta:
                                            content += delta['content']
                                    if data.get('type') == 'response.agent.start':
                                        agents.add(data.get('agent'))
                                    if data.get('type') == 'response.iteration':
                                        iterations = data.get('iteration', 1)
                                except json.JSONDecodeError:
                                    pass
                    
                    word_count = len(content.split())
                    result = {
                        "success": True,
                        "content": content[:300] + "...",
                        "agents": list(agents),
                        "iterations": max(1, iterations),
                        "word_count": word_count,
                        "is_comprehensive": word_count > 300
                    }
                else:
                    response = await client.post(self.base_url, json=request)
                    if response.status_code == 200:
                        data = response.json()
                        content = data['choices'][0]['message']['content']
                        metadata = data.get("metadata", {})
                        agent_results = metadata.get("agent_results", {})
                        agents = [k.replace("_agent", "") for k in agent_results.keys()]
                        iterations = metadata.get("iterations", 1)
                        word_count = len(content.split())
                        
                        result = {
                            "success": True,
                            "content": content[:300] + "...",
                            "agents": agents,
                            "iterations": iterations,
                            "word_count": word_count,
                            "is_comprehensive": word_count > 300
                        }
                    else:
                        result = {"success": False, "error": f"Status {response.status_code}"}
                
                print(f"✅ Success: {result.get('success')}")
                print(f"Agents used: {result.get('agents', [])}")
                print(f"Total agents: {len(result.get('agents', []))}")
                print(f"Iterations: {result.get('iterations', 0)}")
                print(f"Word count: {result.get('word_count', 0)}")
                print(f"Comprehensive response: {'✅ YES' if result.get('is_comprehensive') else '❌ NO'}")
                
                return result
                
            except Exception as e:
                print(f"❌ Error: {str(e)}")
                return {"success": False, "error": str(e)}
    
    async def run_all_tests(self):
        """Run all tests in both streaming and non-streaming modes"""
        print("\n" + "="*80)
        print("COMPREHENSIVE FEATURE TEST SUITE")
        print("="*80)
        
        # Test each feature in both modes
        test_methods = [
            ("Attachment Priority", self.test_attachment_priority),
            ("Citation Formatting", self.test_citation_formatting),
            ("Iterative Workflow", self.test_iterative_workflow)
        ]
        
        for test_name, test_method in test_methods:
            for stream in [False, True]:
                result = await test_method(stream=stream)
                self.results.append({
                    "test": test_name,
                    "stream": stream,
                    "result": result
                })
        
        # Summary
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)
        
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r['result'].get('success'))
        
        print(f"\nTotal tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")
        print(f"Success rate: {(passed_tests/total_tests)*100:.1f}%")
        
        # Detailed results by feature
        for test_name, _ in test_methods:
            print(f"\n{test_name}:")
            for mode in ["non-streaming", "streaming"]:
                stream = mode == "streaming"
                result = next((r for r in self.results if r['test'] == test_name and r['stream'] == stream), None)
                if result:
                    status = "✅ PASS" if result['result'].get('success') else "❌ FAIL"
                    print(f"  {mode}: {status}")
                    
                    # Feature-specific checks
                    if test_name == "Attachment Priority":
                        if result['result'].get('attachment_agent'):
                            print(f"    - Attachment agent triggered: ✅")
                        else:
                            print(f"    - Attachment agent triggered: ❌")
                    elif test_name == "Citation Formatting":
                        if result['result'].get('has_markers'):
                            print(f"    - Citation markers present: ✅")
                        else:
                            print(f"    - Citation markers present: ❌")
                    elif test_name == "Iterative Workflow":
                        iterations = result['result'].get('iterations', 0)
                        print(f"    - Iterations: {iterations}")
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"test_results_comprehensive_{timestamp}.json"
        with open(filename, 'w') as f:
            json.dump({
                "timestamp": timestamp,
                "summary": {
                    "total": total_tests,
                    "passed": passed_tests,
                    "failed": total_tests - passed_tests,
                    "success_rate": f"{(passed_tests/total_tests)*100:.1f}%"
                },
                "results": self.results
            }, f, indent=2)
        
        print(f"\n📄 Results saved to: {filename}")

async def main():
    tester = FeatureTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())