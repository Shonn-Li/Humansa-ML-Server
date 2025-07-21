#!/usr/bin/env python3
"""
Verify iterative refinement actually triggers and improves responses
"""

import asyncio
import httpx
import json
from datetime import datetime
from typing import Dict, List

async def test_iteration_system():
    """Test that iterations actually trigger and improve responses"""
    client = httpx.AsyncClient(timeout=60.0)  # Longer timeout for iterations
    
    print("="*80)
    print("ITERATIVE REFINEMENT VERIFICATION")
    print("="*80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    test_cases = [
        {
            "name": "Complex Technical Question (Should Iterate)",
            "request": {
                "messages": [{"role": "user", "content": "Explain in detail: 1) How transformers work in NLP 2) The attention mechanism 3) Differences between BERT and GPT 4) Real-world applications 5) Current limitations and future directions"}],
                "user_id": 10001,
                "model": "gpt-4o-mini",
                "enable_iterations": True,
                "max_iterations": 3,
                "stream": False
            }
        },
        {
            "name": "Simple Question (Should NOT Iterate)",
            "request": {
                "messages": [{"role": "user", "content": "What is the capital of France?"}],
                "user_id": 10001,
                "model": "gpt-4o-mini",
                "enable_iterations": True,
                "stream": False
            }
        },
        {
            "name": "Streaming with Iterations",
            "request": {
                "messages": [{"role": "user", "content": "Give me a comprehensive analysis of climate change including: causes, effects, current data, mitigation strategies, international agreements, and future projections. Be detailed and thorough."}],
                "user_id": 10001,
                "model": "gpt-4o-mini",
                "enable_iterations": True,
                "stream": True
            }
        }
    ]
    
    for test in test_cases:
        print(f"\n{'='*60}")
        print(f"TEST: {test['name']}")
        print(f"{'='*60}")
        
        if test["request"]["stream"]:
            # Streaming test
            response_text = ""
            iteration_events = []
            agents_sequence = []
            
            async with client.stream("POST", "http://localhost:5002/v1/multi-agent/response", json=test["request"]) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        
                        try:
                            event = json.loads(data_str)
                            
                            # Track response text
                            if event.get("type") == "response.output_text.delta":
                                response_text += event.get("delta", "")
                            
                            # Track iteration events
                            if "iteration" in str(event.get("item", {}).get("id", "")):
                                iteration_events.append(event)
                            
                            # Track agent sequence
                            if event.get("type") == "response.output_item.added":
                                item_id = event.get("item", {}).get("id", "")
                                if any(agent in item_id for agent in ["router", "rag", "web_search", "response", "iteration"]):
                                    agents_sequence.append(item_id)
                                    
                        except json.JSONDecodeError:
                            pass
            
            print(f"\n1. STREAMING ITERATION ANALYSIS:")
            print(f"   Response length: {len(response_text)} chars")
            print(f"   Iteration events: {len(iteration_events)}")
            print(f"   Agent sequence: {' -> '.join(agents_sequence[:10])}...")
            
            # Check if iterations happened
            iteration_count = sum(1 for agent in agents_sequence if "iteration" in agent)
            if iteration_count > 0:
                print(f"   ✅ Iterations triggered: {iteration_count} times")
            else:
                print(f"   ❌ No iterations triggered")
                
        else:
            # Non-streaming test
            response = await client.post("http://localhost:5002/v1/multi-agent/response", json=test["request"])
            data = response.json()
            
            # Extract metadata
            metadata = data.get("metadata", {})
            iterations_performed = metadata.get("iterations_performed", 0)
            agents_used = metadata.get("agents_used", [])
            agent_times = metadata.get("agent_times", {})
            total_time = metadata.get("total_time", 0)
            
            # Extract response
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            print(f"\n1. ITERATION METADATA:")
            print(f"   Iterations performed: {iterations_performed}")
            print(f"   Total time: {total_time:.2f}s")
            print(f"   Agents used: {agents_used}")
            
            print(f"\n2. ITERATION DETAILS:")
            if iterations_performed > 0:
                print(f"   ✅ Iterative refinement TRIGGERED")
                
                # Show iteration sequence
                iteration_sequence = []
                for i in range(iterations_performed + 1):
                    if i == 0:
                        iteration_sequence.append("Initial response")
                    else:
                        iteration_sequence.append(f"Iteration {i}")
                print(f"   Sequence: {' -> '.join(iteration_sequence)}")
                
                # Estimate quality improvement
                initial_length = len(content) // (iterations_performed + 1)  # Rough estimate
                print(f"   Estimated expansion: ~{iterations_performed}x more detailed")
                
            else:
                print(f"   ℹ️  No iterations (response was sufficient)")
            
            print(f"\n3. RESPONSE QUALITY:")
            print(f"   Length: {len(content)} chars")
            
            # Check for comprehensive coverage
            if "causes" in test["request"]["messages"][0]["content"].lower():
                topics = ["causes", "effects", "data", "strategies", "agreements", "projections"]
                covered = sum(1 for topic in topics if topic in content.lower())
                print(f"   Topic coverage: {covered}/{len(topics)} topics addressed")
            
            # Show response preview
            print(f"\n4. RESPONSE PREVIEW:")
            print(f"   {content[:300]}...")
    
    await client.aclose()

async def test_iteration_quality():
    """Compare responses with and without iterations"""
    client = httpx.AsyncClient(timeout=60.0)
    
    print("\n" + "="*80)
    print("ITERATION QUALITY COMPARISON")
    print("="*80)
    
    query = "Explain how neural networks learn, including backpropagation, gradient descent, and optimization techniques."
    
    # Test WITHOUT iterations
    print("\n1. WITHOUT ITERATIONS:")
    print("-" * 40)
    
    request_no_iter = {
        "messages": [{"role": "user", "content": query}],
        "user_id": 10001,
        "model": "gpt-4o-mini",
        "enable_iterations": False,
        "stream": False
    }
    
    response1 = await client.post("http://localhost:5002/v1/multi-agent/response", json=request_no_iter)
    data1 = response1.json()
    content1 = data1.get("choices", [{}])[0].get("message", {}).get("content", "")
    
    print(f"   Response length: {len(content1)} chars")
    print(f"   Time taken: {data1.get('metadata', {}).get('total_time', 0):.2f}s")
    
    # Test WITH iterations
    print("\n2. WITH ITERATIONS:")
    print("-" * 40)
    
    request_with_iter = {
        "messages": [{"role": "user", "content": query}],
        "user_id": 10001,
        "model": "gpt-4o-mini",
        "enable_iterations": True,
        "max_iterations": 3,
        "stream": False
    }
    
    response2 = await client.post("http://localhost:5002/v1/multi-agent/response", json=request_with_iter)
    data2 = response2.json()
    content2 = data2.get("choices", [{}])[0].get("message", {}).get("content", "")
    iterations = data2.get("metadata", {}).get("iterations_performed", 0)
    
    print(f"   Response length: {len(content2)} chars")
    print(f"   Iterations: {iterations}")
    print(f"   Time taken: {data2.get('metadata', {}).get('total_time', 0):.2f}s")
    
    # Compare quality
    print("\n3. QUALITY COMPARISON:")
    print("-" * 40)
    
    if len(content2) > len(content1):
        improvement = ((len(content2) - len(content1)) / len(content1)) * 100
        print(f"   ✅ Response improved by {improvement:.1f}% in length")
    else:
        print(f"   ❌ No improvement in response length")
    
    # Check for key concepts
    concepts = ["backpropagation", "gradient", "descent", "optimization", "learning rate", 
                "loss function", "weights", "bias", "activation", "chain rule"]
    
    concepts1 = sum(1 for c in concepts if c.lower() in content1.lower())
    concepts2 = sum(1 for c in concepts if c.lower() in content2.lower())
    
    print(f"   Concepts covered without iterations: {concepts1}/{len(concepts)}")
    print(f"   Concepts covered with iterations: {concepts2}/{len(concepts)}")
    
    if concepts2 > concepts1:
        print(f"   ✅ Iterations added {concepts2 - concepts1} more concepts")
    
    await client.aclose()

async def main():
    """Run all iteration verification tests"""
    await test_iteration_system()
    await test_iteration_quality()
    
    print("\n" + "="*80)
    print("ITERATION VERIFICATION COMPLETE")
    print("="*80)
    print("\nTo run this test:")
    print("cd /Users/shonnli/Non-icloudFile/YouWoAI/Code_V1/YouWoAI-ML-Server")
    print("source youwo-ml-venv/bin/activate")
    print("python tests/test_iteration_verification.py")

if __name__ == "__main__":
    asyncio.run(main())