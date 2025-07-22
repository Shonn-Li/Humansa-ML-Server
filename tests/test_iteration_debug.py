#!/usr/bin/env python3
"""
Debug test for iterative agent - understand why iterations aren't triggering
"""

import asyncio
import httpx
import json
from typing import Dict, List, Any
from datetime import datetime

async def test_iteration_with_poor_response():
    """Test with a query that should get a poor initial response"""
    client = httpx.AsyncClient(timeout=120.0)
    
    print("="*80)
    print("ITERATION DEBUG TEST")
    print("="*80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # First, let's test with a simple query to see what happens
    request = {
        "messages": [{
            "role": "user", 
            "content": "Give me just one word about Python."  # Deliberately asking for minimal response
        }],
        "user_id": 10001,
        "model": "gpt-4.1-nano",
        "enable_iterations": True,
        "stream": False
    }
    
    print("TEST 1: Minimal response query")
    print("Query: 'Give me just one word about Python.'")
    print("Expected: Should get a very short response that might trigger iteration check")
    print()
    
    response = await client.post("http://localhost:5002/v1/multi-agent/response", json=request)
    data = response.json()
    
    metadata = data.get("metadata", {})
    iterations = metadata.get("iterations", 1)
    response_text = data.get("response", "")
    agent_results = metadata.get("agent_results", {})
    
    print(f"Response: '{response_text}'")
    print(f"Response length: {len(response_text)} chars")
    print(f"Iterations: {iterations}")
    print(f"Agents used: {list(agent_results.keys())}")
    
    # Now test with a query that asks for more but might get incomplete response
    print("\n" + "-"*80)
    print("TEST 2: Query asking for detailed analysis")
    print()
    
    request2 = {
        "messages": [{
            "role": "user", 
            "content": """I need a detailed analysis with the following:
            1. Definition of machine learning
            2. Types of machine learning algorithms
            3. Real-world applications
            4. Future trends
            
            Please be thorough and include examples."""
        }],
        "user_id": 10001,
        "model": "gpt-4.1-nano",
        "enable_iterations": True,
        "stream": True
    }
    
    print("Streaming response to check for iteration markers...")
    print()
    
    reasoning_events = []
    iteration_detected = False
    event_count = 0
    
    try:
        async with client.stream("POST", "http://localhost:5002/v1/multi-agent/response", json=request2) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                        
                    try:
                        event = json.loads(data_str)
                        event_type = event.get("type", "")
                        event_count += 1
                        
                        # Capture reasoning events
                        if event_type == "response.reasoning_text.delta":
                            text = event.get("delta", "")
                            reasoning_events.append(text)
                            
                            # Look for iteration evaluation
                            if any(word in text.lower() for word in ["iteration", "evaluate", "quality", "needs_iteration"]):
                                print(f"[{event_count:3d}] ITERATION LOGIC: {text[:100]}...")
                                iteration_detected = True
                                
                    except json.JSONDecodeError:
                        pass
                        
    except Exception as e:
        print(f"Stream error (expected for long responses): {type(e).__name__}")
    
    # Analyze reasoning
    full_reasoning = "".join(reasoning_events)
    
    print("\n" + "-"*80)
    print("REASONING ANALYSIS")
    print("-"*80)
    
    if "needs_iteration" in full_reasoning:
        print("✅ Found iteration evaluation in reasoning")
        # Try to extract the evaluation result
        import re
        json_pattern = r'\{[^{}]*"needs_iteration"[^{}]*\}'
        matches = re.findall(json_pattern, full_reasoning)
        for match in matches:
            try:
                decision = json.loads(match)
                print(f"Iteration decision: {decision}")
            except:
                pass
    else:
        print("❌ No iteration evaluation found in reasoning")
        
    if iteration_detected:
        print("✅ Iteration-related reasoning detected")
    else:
        print("❌ No iteration logic detected")
        
    print(f"\nTotal events processed: {event_count}")
    
    # Test 3: Check if iterations are disabled by default
    print("\n" + "="*80)
    print("TEST 3: Check default iteration behavior")
    print("="*80)
    
    request3 = {
        "messages": [{
            "role": "user", 
            "content": "What is 2+2?"
        }],
        "user_id": 10001,
        "model": "gpt-4.1-nano",
        # Not specifying enable_iterations to check default
        "stream": False
    }
    
    response = await client.post("http://localhost:5002/v1/multi-agent/response", json=request3)
    data = response.json()
    
    metadata = data.get("metadata", {})
    print(f"Default iterations (not specified): {metadata.get('iterations', 'Not reported')}")
    
    await client.aclose()

if __name__ == "__main__":
    asyncio.run(test_iteration_with_poor_response())