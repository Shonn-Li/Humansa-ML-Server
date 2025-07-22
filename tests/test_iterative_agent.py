#!/usr/bin/env python3
"""
Test iterative agent capabilities and multi-pass processing
"""

import asyncio
import httpx
import json
from typing import Dict, List, Any
from datetime import datetime

async def test_iterative_processing():
    """Test iterative agent with complex query requiring multiple passes"""
    client = httpx.AsyncClient(timeout=60.0)
    
    print("="*80)
    print("ITERATIVE AGENT CAPABILITY TEST")
    print("="*80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Complex query that should trigger iterative processing
    request = {
        "messages": [{
            "role": "user", 
            "content": """Analyze the following problem step by step:
            
            1. First, explain the key differences between supervised and unsupervised learning
            2. Then, evaluate their effectiveness for anomaly detection specifically
            3. Consider factors like: accuracy, data requirements, computational cost, interpretability
            4. Finally, provide a clear recommendation with justification
            
            Make sure to be thorough and cite any relevant information from my notes or web sources."""
        }],
        "user_id": 10001,
        "model": "gpt-4.1-nano",
        "enable_iterations": True,
        "enable_citations": True,
        "stream": True
    }
    
    print("Request: Complex multi-step analysis requiring iterative reasoning")
    print("Features enabled: iterations=True, citations=True")
    print()
    print("STREAMING EVENTS:")
    print("-"*80)
    
    # Track events and iterations
    event_count = 0
    iteration_count = 1
    agents_triggered = set()
    reasoning_steps = []
    response_text = ""
    
    async with client.stream("POST", "http://localhost:5002/v1/multi-agent/response", json=request) as response:
        async for line in response.aiter_lines():
            if line.startswith("data: "):
                data_str = line[6:]
                if data_str == "[DONE]":
                    break
                    
                try:
                    event = json.loads(data_str)
                    event_type = event.get("type", "")
                    event_count += 1
                    
                    # Track reasoning events
                    if event_type == "response.reasoning_text.delta":
                        text = event.get("delta", "")
                        reasoning_steps.append(text)
                        
                        # Detect iteration markers
                        if "iteration" in text.lower() or "pass" in text.lower():
                            print(f"[{event_count:3d}] 🔄 Iteration marker: {text[:100]}...")
                            
                        # Detect agent routing
                        if "routed to agents:" in text:
                            print(f"[{event_count:3d}] 🧠 Agent routing: {text}")
                            agents_part = text.split("routed to agents:")[1]
                            for agent in agents_part.split(","):
                                agent_name = agent.strip()
                                if agent_name:
                                    agents_triggered.add(agent_name)
                    
                    # Track output items
                    elif event_type == "response.output_item.added":
                        item = event.get("item", {})
                        item_type = item.get("type", "")
                        item_id = item.get("id", "")
                        
                        # Detect iteration from item IDs
                        if "iteration" in item_id:
                            print(f"[{event_count:3d}] 🔄 Iteration output: {item_type} (ID: {item_id[:20]}...)")
                            
                        # Regular output
                        else:
                            print(f"[{event_count:3d}] ➕ Output: {item_type} (ID: {item_id[:20]}...)")
                    
                    # Track tool calls
                    elif "tool_call" in event_type:
                        print(f"[{event_count:3d}] 🔧 Tool call: {event_type}")
                        
                    # Track search calls
                    elif "search_call" in event_type:
                        print(f"[{event_count:3d}] 🔍 Search: {event_type}")
                        
                    # Collect response text
                    elif event_type == "response.output_text.delta":
                        response_text += event.get("delta", "")
                        
                    # Check metadata for iterations
                    elif event_type == "response.usage":
                        metadata = event.get("metadata", {})
                        actual_iterations = metadata.get("iterations", 1)
                        if actual_iterations > 1:
                            print(f"[{event_count:3d}] 📊 Metadata: {actual_iterations} iterations completed")
                            iteration_count = actual_iterations
                            
                except json.JSONDecodeError:
                    pass
    
    # Analyze reasoning for iterative patterns
    full_reasoning = "".join(reasoning_steps)
    iteration_markers = ["iteration", "refin", "improv", "pass", "round", "step"]
    iterative_indicators = sum(1 for marker in iteration_markers if marker in full_reasoning.lower())
    
    print("\n" + "="*80)
    print("ANALYSIS RESULTS")
    print("="*80)
    
    print(f"\nEvent Statistics:")
    print(f"  Total events: {event_count}")
    print(f"  Agents triggered: {', '.join(sorted(agents_triggered)) if agents_triggered else 'None'}")
    print(f"  Iterations recorded: {iteration_count}")
    print(f"  Iterative indicators in reasoning: {iterative_indicators}")
    
    print(f"\nResponse Characteristics:")
    print(f"  Response length: {len(response_text)} chars")
    print(f"  Contains numbered sections: {'1.' in response_text and '2.' in response_text}")
    print(f"  Contains recommendation: {'recommend' in response_text.lower()}")
    
    # Check response structure
    sections = []
    if "differences" in response_text.lower() or "supervised" in response_text.lower():
        sections.append("Explains supervised vs unsupervised")
    if "anomaly detection" in response_text.lower():
        sections.append("Evaluates for anomaly detection")
    if "accuracy" in response_text.lower() or "data requirement" in response_text.lower():
        sections.append("Considers multiple factors")
    if "recommend" in response_text.lower():
        sections.append("Provides recommendation")
        
    print(f"\nContent Coverage:")
    for section in sections:
        print(f"  ✓ {section}")
        
    print(f"\nIterative Processing Assessment:")
    if iteration_count > 1:
        print(f"  ✅ CONFIRMED: System performed {iteration_count} iterations")
    elif iterative_indicators > 2:
        print(f"  🔄 LIKELY: Reasoning shows iterative patterns ({iterative_indicators} indicators)")
    else:
        print(f"  ❌ NO ITERATION: Single-pass processing")
        
    print(f"\nRESPONSE PREVIEW (first 800 chars):")
    print("-"*80)
    print(response_text[:800] + "..." if len(response_text) > 800 else response_text)
    
    await client.aclose()

async def main():
    """Run iterative agent tests"""
    await test_iterative_processing()
    
    # Additional test for edge cases
    print("\n\n")
    print("="*80)
    print("EDGE CASE TEST: Simple Query with Iterations Enabled")
    print("="*80)
    
    client = httpx.AsyncClient(timeout=30.0)
    
    # Simple query that shouldn't need iterations
    simple_request = {
        "messages": [{"role": "user", "content": "What is 2+2?"}],
        "user_id": 10001,
        "model": "gpt-4.1-nano",
        "enable_iterations": True,
        "stream": False
    }
    
    response = await client.post("http://localhost:5002/v1/multi-agent/response", json=simple_request)
    data = response.json()
    
    metadata = data.get("metadata", {})
    iterations = metadata.get("iterations", 1)
    
    print(f"Simple query iterations: {iterations}")
    print(f"Expected: 1 (no iteration needed for simple query)")
    print(f"Result: {'✅ PASS' if iterations == 1 else '❌ FAIL'}")
    
    await client.aclose()

if __name__ == "__main__":
    asyncio.run(main())