#!/usr/bin/env python3
"""Debug test for iterative workflow"""

import httpx
import asyncio
import json

async def test_iteration_with_logging():
    """Test iteration with detailed logging"""
    
    queries = [
        # Query 1: Simple incomplete query
        {
            "name": "Incomplete Query",
            "query": "Tell me about machine learning but I need more details",
            "description": "Should trigger iteration due to incomplete response"
        },
        
        # Query 2: Complex analysis
        {
            "name": "Complex Analysis", 
            "query": "Analyze all my notes about AI, find gaps in coverage, and suggest three specific research directions with detailed explanations",
            "description": "Complex multi-part query that should need refinement"
        },
        
        # Query 3: Missing citations
        {
            "name": "Missing Citations",
            "query": "What are the latest developments in AI according to my notes?",
            "description": "Should trigger iteration to add citations"
        },
        
        # Query 4: Comparison request
        {
            "name": "Comparison Request",
            "query": "Compare transformer models with RNNs based on my notes and suggest which is better for my use case",
            "description": "Needs additional context gathering"
        }
    ]
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        for test in queries:
            print(f"\n{'='*70}")
            print(f"TEST: {test['name']}")
            print(f"{'='*70}")
            print(f"Query: {test['query']}")
            print(f"Expected: {test['description']}")
            
            request_data = {
                "messages": [{"role": "user", "content": test['query']}],
                "user_id": 10001,
                "model": "gpt-4.1-nano",
                "stream": False,
                "enable_iterations": True
            }
            
            try:
                response = await client.post(
                    "http://localhost:5001/v1/multi-agent/response",
                    json=request_data
                )
                
                if response.status_code == 200:
                    data = response.json()
                    metadata = data.get('metadata', {})
                    agent_results = metadata.get('agent_results', {})
                    
                    # Check for iterations
                    iterations = []
                    for key in sorted(agent_results.keys()):
                        if key.startswith('iteration_'):
                            iterations.append(key)
                    
                    print(f"\n✅ Response received")
                    print(f"Iterations found: {len(iterations)}")
                    
                    if iterations:
                        print("\nIteration details:")
                        for iter_key in iterations:
                            iter_data = agent_results[iter_key]
                            print(f"  - {iter_key}:")
                            print(f"    Reason: {iter_data.get('reason', 'N/A')}")
                            print(f"    Agents: {iter_data.get('agents', [])}")
                    else:
                        print("\n❌ No iterations triggered")
                        
                        # Show initial agents used
                        initial_agents = [k for k in agent_results.keys() if k.endswith('_agent')]
                        print(f"Initial agents: {initial_agents}")
                        
                        # Show response length
                        response_text = data['choices'][0]['message']['content']
                        print(f"Response length: {len(response_text)} chars")
                        
                        # Check if evaluation happened
                        if 'evaluation' in metadata:
                            print(f"Evaluation result: {metadata['evaluation']}")
                    
                    # Show response preview
                    response_text = data['choices'][0]['message']['content']
                    print(f"\nResponse preview:")
                    print(f"  {response_text[:200]}...")
                    
                else:
                    print(f"❌ Error: {response.status_code}")
                    print(f"Response: {response.text}")
                    
            except Exception as e:
                print(f"❌ Exception: {str(e)}")
            
            # Pause between tests
            await asyncio.sleep(3)

async def check_logs():
    """Check ML server logs for iteration-related messages"""
    print(f"\n{'='*70}")
    print("CHECKING ML SERVER LOGS")
    print(f"{'='*70}")
    
    proc = await asyncio.create_subprocess_exec(
        'tail', '-100', 'ml_server_iteration_debug.log',
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, _ = await proc.communicate()
    
    log_lines = stdout.decode().split('\n')
    
    # Look for iteration-related logs
    iteration_logs = []
    evaluation_logs = []
    error_logs = []
    
    for line in log_lines:
        if 'iteration' in line.lower():
            iteration_logs.append(line)
        if 'evaluation' in line.lower() or 'evaluate' in line.lower():
            evaluation_logs.append(line)
        if 'ERROR' in line or 'Exception' in line or 'failed' in line.lower():
            error_logs.append(line)
    
    if evaluation_logs:
        print("\nEvaluation logs found:")
        for log in evaluation_logs[-5:]:  # Last 5
            print(f"  {log}")
    
    if iteration_logs:
        print("\nIteration logs found:")
        for log in iteration_logs[-5:]:  # Last 5
            print(f"  {log}")
    
    if error_logs:
        print("\nError logs found:")
        for log in error_logs[-5:]:  # Last 5
            print(f"  {log}")
    
    if not any([evaluation_logs, iteration_logs, error_logs]):
        print("\nNo iteration-related logs found")

async def main():
    print("ITERATIVE WORKFLOW DEBUG TEST")
    print("Testing various queries to trigger iterations")
    
    # Wait for server to be ready
    await asyncio.sleep(5)
    
    # Run tests
    await test_iteration_with_logging()
    
    # Check logs
    await check_logs()
    
    print(f"\n{'='*70}")
    print("DEBUG TEST COMPLETE")
    print("Check the output above to understand why iterations aren't triggering")

if __name__ == "__main__":
    asyncio.run(main())