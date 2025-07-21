#!/usr/bin/env python3
"""Final comprehensive test for all three features"""

import httpx
import asyncio
import json
from datetime import datetime

async def run_test(name: str, request_data: dict) -> dict:
    """Run a single test and return results"""
    print(f"\n{'='*60}")
    print(f"TEST: {name}")
    print(f"{'='*60}")
    print(f"Query: {request_data['messages'][0]['content']}")
    
    async with httpx.AsyncClient(timeout=45.0) as client:
        start_time = asyncio.get_event_loop().time()
        
        try:
            response = await client.post(
                "http://localhost:5001/v1/multi-agent/response",
                json=request_data
            )
            
            elapsed = asyncio.get_event_loop().time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract metadata
                metadata = data.get('metadata', {})
                agent_results = metadata.get('agent_results', {})
                agents = [k for k in agent_results.keys() if k.endswith('_agent')]
                
                # Extract response
                content = data['choices'][0]['message']['content']
                
                # Check for features
                has_citations = any(f"[{i}]" in content for i in range(1, 10))
                has_sources = "Sources:" in content or "References:" in content
                iteration_count = sum(1 for k in agent_results if k.startswith('iteration_'))
                
                print(f"\n✅ SUCCESS (took {elapsed:.1f}s)")
                print(f"Agents triggered: {len(agents)}")
                print(f"  - {', '.join(agents)}")
                
                if 'attachment_agent' in agents:
                    print(f"✅ Attachment processing: Active")
                
                if 'citation_agent' in agents:
                    print(f"✅ Citation agent: Active")
                    print(f"  - Has citation markers: {has_citations}")
                    print(f"  - Has sources section: {has_sources}")
                
                if iteration_count > 0:
                    print(f"✅ Iterations: {iteration_count}")
                    for i in range(1, iteration_count + 1):
                        iter_data = agent_results.get(f'iteration_{i}', {})
                        print(f"  - Iteration {i}: {iter_data.get('reason', 'N/A')}")
                
                # Show response preview
                print(f"\nResponse preview:")
                preview = content[:200] + "..." if len(content) > 200 else content
                print(f"  {preview}")
                
                # Show citation example if present
                if has_citations:
                    print(f"\nCitation example:")
                    for line in content.split('\n'):
                        if '[' in line and ']' in line:
                            print(f"  {line[:100]}...")
                            break
                
                return {
                    "success": True,
                    "agents": agents,
                    "has_citations": has_citations,
                    "iterations": iteration_count,
                    "elapsed": elapsed
                }
            else:
                print(f"\n❌ FAILED - Status: {response.status_code}")
                return {"success": False, "error": f"Status {response.status_code}"}
                
        except Exception as e:
            print(f"\n❌ FAILED - Error: {str(e)}")
            return {"success": False, "error": str(e)}

async def main():
    print("COMPREHENSIVE FEATURE TEST")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    tests = [
        # Test 1: Attachment Priority
        {
            "name": "Attachment Priority",
            "data": {
                "messages": [{"role": "user", "content": "Summarize this paper's main contributions"}],
                "user_id": 10001,
                "model": "gpt-4o-mini",
                "stream": False,
                "attachments": ["https://arxiv.org/pdf/2505.18499.pdf"]
            }
        },
        
        # Test 2: Citation with RAG
        {
            "name": "Citation with Notes",
            "data": {
                "messages": [{"role": "user", "content": "What do my notes say about reinforcement learning? Include citations."}],
                "user_id": 10001,
                "model": "gpt-4o-mini",
                "stream": False,
                "enable_citations": True
            }
        },
        
        # Test 3: Complex query with attachments for iteration
        {
            "name": "Iterative Analysis",
            "data": {
                "messages": [{"role": "user", "content": "Compare this paper with my notes on AI and suggest research improvements"}],
                "user_id": 10001,
                "model": "gpt-4o-mini",
                "stream": False,
                "enable_iterations": True,
                "attachments": ["https://arxiv.org/pdf/2311.18703.pdf"]
            }
        }
    ]
    
    results = []
    for test in tests:
        result = await run_test(test["name"], test["data"])
        results.append({
            "name": test["name"],
            **result
        })
        
        # Brief pause between tests
        await asyncio.sleep(2)
    
    # Final summary
    print(f"\n{'='*60}")
    print("FINAL SUMMARY")
    print(f"{'='*60}")
    
    for result in results:
        status = "✅ PASSED" if result["success"] else "❌ FAILED"
        print(f"\n{result['name']}: {status}")
        
        if result["success"]:
            print(f"  - Agents: {len(result['agents'])}")
            print(f"  - Time: {result['elapsed']:.1f}s")
            
            if result['name'] == "Attachment Priority":
                attachment_ok = 'attachment_agent' in result['agents']
                print(f"  - Attachment routing: {'✅' if attachment_ok else '❌'}")
            
            elif result['name'] == "Citation with Notes":
                print(f"  - Citations present: {'✅' if result['has_citations'] else '❌'}")
            
            elif result['name'] == "Iterative Analysis":
                print(f"  - Iterations: {result['iterations']}")
                print(f"  - Iterative workflow: {'✅' if result['iterations'] > 0 else '❌'}")
    
    # Overall status
    all_passed = all(r["success"] for r in results)
    attachment_works = any('attachment_agent' in r.get('agents', []) for r in results if r['name'] == "Attachment Priority")
    citations_work = any(r.get('has_citations', False) for r in results if r['name'] == "Citation with Notes")
    iterations_work = any(r.get('iterations', 0) > 0 for r in results if r['name'] == "Iterative Analysis")
    
    print(f"\n{'='*60}")
    print("FEATURE STATUS")
    print(f"{'='*60}")
    print(f"1. Attachment Priority: {'✅ WORKING' if attachment_works else '❌ NOT WORKING'}")
    print(f"2. Citation Formatting: {'✅ WORKING' if citations_work else '❌ NOT WORKING'}")
    print(f"3. Iterative Workflow:  {'✅ WORKING' if iterations_work else '❌ NOT WORKING'}")
    
    if all([attachment_works, citations_work, iterations_work]):
        print("\n🎉 ALL FEATURES WORKING!")
    else:
        print("\n⚠️  Some features need attention")

if __name__ == "__main__":
    asyncio.run(main())