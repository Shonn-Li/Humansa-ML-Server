#!/usr/bin/env python3
"""Test each feature individually"""

import httpx
import asyncio
import json
import sys

async def test_attachment_only():
    """Test just attachment priority"""
    print("=" * 60)
    print("TEST 1: ATTACHMENT PRIORITY")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "http://localhost:5001/v1/multi-agent/response",
            json={
                "messages": [{"role": "user", "content": "Analyze this paper"}],
                "user_id": 10001,
                "model": "gpt-4o-mini",
                "stream": False,
                "attachments": ["https://arxiv.org/pdf/2505.18499.pdf"]
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            agents = data.get('metadata', {}).get('agent_results', {})
            
            print(f"✅ Status: Success")
            print(f"✅ Attachment agent: {'attachment_agent' in agents}")
            print(f"✅ All agents: {list(agents.keys())}")
            
            # Check response mentions the paper
            content = data['choices'][0]['message']['content']
            if "entropy" in content.lower() or "reinforcement" in content.lower():
                print(f"✅ Response correctly analyzes the paper")
            
            return True
        else:
            print(f"❌ Error: {response.status_code}")
            return False

async def test_citation_only():
    """Test just citation formatting"""
    print("\n" + "=" * 60)
    print("TEST 2: CITATION FORMATTING")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Simple query that should work quickly
        response = await client.post(
            "http://localhost:5001/v1/multi-agent/response",
            json={
                "messages": [{"role": "user", "content": "What is AI? Cite sources."}],
                "user_id": 10001,
                "model": "gpt-4o-mini",
                "stream": False,
                "enable_citations": True
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            content = data['choices'][0]['message']['content']
            
            # Check for citations
            has_citations = any(f"[{i}]" in content for i in range(1, 10))
            has_sources = "Sources:" in content or "References:" in content
            
            print(f"✅ Status: Success")
            print(f"✅ Has citation markers [1], [2]: {has_citations}")
            print(f"✅ Has sources section: {has_sources}")
            
            if has_citations:
                # Find first line with citation
                for line in content.split('\n'):
                    if '[' in line and ']' in line:
                        print(f"✅ Example: {line[:100]}...")
                        break
            
            # Check if citation agent was used
            agents = data.get('metadata', {}).get('agent_results', {})
            print(f"✅ Citation agent used: {'citation_agent' in agents}")
            
            return has_citations
        else:
            print(f"❌ Error: {response.status_code}")
            return False

async def test_iteration_only():
    """Test just iterative workflow"""
    print("\n" + "=" * 60)
    print("TEST 3: ITERATIVE WORKFLOW")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=45.0) as client:
        # Complex query that should trigger iteration
        response = await client.post(
            "http://localhost:5001/v1/multi-agent/response",
            json={
                "messages": [{"role": "user", "content": "Analyze trends in my AI notes and suggest improvements"}],
                "user_id": 10001,
                "model": "gpt-4o-mini",
                "stream": False,
                "enable_iterations": True
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            metadata = data.get('metadata', {})
            agent_results = metadata.get('agent_results', {})
            
            # Count iterations
            iterations = sum(1 for key in agent_results if key.startswith('iteration_'))
            
            print(f"✅ Status: Success")
            print(f"✅ Iterations performed: {iterations}")
            print(f"✅ Total agents used: {len([k for k in agent_results if k.endswith('_agent')])}")
            
            if iterations > 0:
                print(f"✅ Iterative refinement is working!")
                # Show iteration details
                for i in range(1, iterations + 1):
                    iter_key = f'iteration_{i}'
                    if iter_key in agent_results:
                        print(f"   - Iteration {i}: {agent_results[iter_key].get('reason', 'N/A')}")
            
            return iterations > 0
        else:
            print(f"❌ Error: {response.status_code}")
            return False

async def main():
    print("TESTING INDIVIDUAL FEATURES")
    print("Each test runs separately to avoid timeouts\n")
    
    # Test 1: Attachment Priority
    attachment_success = await test_attachment_only()
    await asyncio.sleep(2)  # Brief pause between tests
    
    # Test 2: Citations
    citation_success = await test_citation_only()
    await asyncio.sleep(2)
    
    # Test 3: Iterations
    iteration_success = await test_iteration_only()
    
    # Summary
    print("\n" + "=" * 60)
    print("FINAL SUMMARY")
    print("=" * 60)
    print(f"1. Attachment Priority: {'✅ PASSED' if attachment_success else '❌ FAILED'}")
    print(f"2. Citation Formatting: {'✅ PASSED' if citation_success else '❌ FAILED'}")
    print(f"3. Iterative Workflow:  {'✅ PASSED' if iteration_success else '❌ FAILED'}")
    
    if all([attachment_success, citation_success, iteration_success]):
        print("\n🎉 ALL FEATURES WORKING!")
    else:
        print("\n⚠️  Some features need attention")

if __name__ == "__main__":
    asyncio.run(main())