#!/usr/bin/env python3
"""
Test to force iterative agent to trigger by mocking a poor initial response
"""

import asyncio
import httpx
import json
from typing import Dict, List, Any
from datetime import datetime

async def test_force_iteration():
    """Test iterative agent with a query that should definitely trigger iteration"""
    client = httpx.AsyncClient(timeout=60.0)
    
    print("="*80)
    print("FORCED ITERATION TEST")
    print("="*80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Query that should trigger iteration - asking for comprehensive analysis
    request = {
        "messages": [{
            "role": "user", 
            "content": """Provide a COMPREHENSIVE and DETAILED analysis of reinforcement learning algorithms:
            
            1. History and evolution (with timeline)
            2. Mathematical foundations (with equations)
            3. Key algorithms (DQN, PPO, SAC, etc.) with pseudocode
            4. Applications in robotics, gaming, and finance
            5. Current research trends and future directions
            6. Comparison table of different RL algorithms
            7. Implementation considerations and best practices
            
            This should be at least 2000 words with proper citations from academic papers and recent research."""
        }],
        "user_id": 10001,
        "model": "gpt-4.1-nano",
        "enable_iterations": True,
        "enable_citations": True,
        "stream": True
    }
    
    print("Request: Complex query requiring comprehensive analysis")
    print("Expected: Should trigger multiple iterations to gather more information")
    print()
    print("STREAMING EVENTS:")
    print("-"*80)
    
    # Track events
    event_count = 0
    iteration_markers = []
    agents_per_iteration = {}
    current_iteration = 0
    reasoning_text = ""
    response_length = 0
    
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
                    
                    # Track reasoning
                    if event_type == "response.reasoning_text.delta":
                        text = event.get("delta", "")
                        reasoning_text += text
                        
                        # Look for iteration indicators
                        if "iteration" in text.lower():
                            print(f"[{event_count:3d}] 🔄 ITERATION MARKER: {text[:100]}...")
                            iteration_markers.append(text)
                            
                        # Look for quality evaluation
                        if any(word in text.lower() for word in ["evaluating", "quality", "needs improvement", "incomplete"]):
                            print(f"[{event_count:3d}] 📊 QUALITY CHECK: {text[:100]}...")
                    
                    # Track agent routing
                    elif event_type == "response.output_item.added":
                        item = event.get("item", {})
                        item_id = item.get("id", "")
                        
                        # Detect iteration from ID patterns
                        if "iter" in item_id:
                            iter_num = int(item_id.split("iter")[-1].split("_")[0]) if "iter" in item_id else current_iteration
                            if iter_num > current_iteration:
                                current_iteration = iter_num
                                agents_per_iteration[current_iteration] = []
                                print(f"[{event_count:3d}] 🔄 NEW ITERATION {current_iteration} DETECTED")
                        
                        # Track agents by iteration
                        if current_iteration not in agents_per_iteration:
                            agents_per_iteration[current_iteration] = []
                        
                        if item_id.startswith("rag_"):
                            agents_per_iteration[current_iteration].append("RAG")
                        elif item_id.startswith("ws_"):
                            agents_per_iteration[current_iteration].append("WebSearch")
                        
                        print(f"[{event_count:3d}] ➕ {item.get('type', 'unknown')} (ID: {item_id[:30]}...)")
                    
                    # Track response length
                    elif event_type == "response.output_text.delta":
                        response_length += len(event.get("delta", ""))
                    
                    # Check metadata
                    elif event_type == "response.usage":
                        metadata = event.get("metadata", {})
                        reported_iterations = metadata.get("iterations", 1)
                        print(f"[{event_count:3d}] 📊 METADATA: {reported_iterations} iterations reported")
                        
                except json.JSONDecodeError:
                    pass
    
    print("\n" + "="*80)
    print("ITERATION ANALYSIS")
    print("="*80)
    
    print(f"\nIteration Detection:")
    print(f"  Iteration markers found: {len(iteration_markers)}")
    print(f"  Max iteration detected: {current_iteration}")
    print(f"  Agents per iteration:")
    for iter_num, agents in sorted(agents_per_iteration.items()):
        print(f"    Iteration {iter_num}: {', '.join(agents) if agents else 'None'}")
    
    print(f"\nResponse Characteristics:")
    print(f"  Total events: {event_count}")
    print(f"  Response length: {response_length} chars")
    print(f"  Average chars per event: {response_length / max(event_count, 1):.1f}")
    
    # Analyze reasoning for iteration decisions
    iteration_decisions = []
    if "needs_iteration" in reasoning_text:
        print(f"\nIteration Decision Found in Reasoning:")
        # Extract JSON from reasoning
        import re
        json_pattern = r'\{[^{}]*"needs_iteration"[^{}]*\}'
        matches = re.findall(json_pattern, reasoning_text)
        for match in matches:
            try:
                decision = json.loads(match)
                iteration_decisions.append(decision)
                print(f"  Decision: {decision}")
            except:
                pass
    
    print(f"\nIteration Success:")
    if current_iteration > 0 or len(iteration_markers) > 0:
        print(f"  ✅ ITERATIONS DETECTED: {max(current_iteration, len(iteration_markers))}")
    else:
        print(f"  ❌ NO ITERATIONS DETECTED")
        print(f"\nDEBUG: First 500 chars of reasoning:")
        print(reasoning_text[:500])
    
    await client.aclose()

async def test_simple_iteration_check():
    """Test with a deliberately incomplete initial response"""
    client = httpx.AsyncClient(timeout=30.0)
    
    print("\n\n" + "="*80)
    print("SIMPLE ITERATION CHECK")
    print("="*80)
    
    # Very simple query that asks for multiple things
    request = {
        "messages": [{
            "role": "user", 
            "content": "Tell me three things: 1) What is Python? 2) What is JavaScript? 3) What is Rust? Be very detailed."
        }],
        "user_id": 10001,
        "model": "gpt-4.1-nano",
        "enable_iterations": True,
        "stream": False
    }
    
    response = await client.post("http://localhost:5002/v1/multi-agent/response", json=request)
    data = response.json()
    
    metadata = data.get("metadata", {})
    iterations = metadata.get("iterations", 1)
    response_text = data.get("response", "")
    
    print(f"Iterations: {iterations}")
    print(f"Response length: {len(response_text)} chars")
    print(f"Contains all three languages: Python={'Python' in response_text}, JS={'JavaScript' in response_text}, Rust={'Rust' in response_text}")
    
    await client.aclose()

if __name__ == "__main__":
    asyncio.run(test_force_iteration())
    asyncio.run(test_simple_iteration_check())