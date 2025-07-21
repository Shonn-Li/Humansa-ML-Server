#!/usr/bin/env python3
"""
Simple test to trigger iteration by asking for a deliberately incomplete response
"""

import asyncio
import httpx
import json
from typing import Dict, List, Any
from datetime import datetime

async def test_deliberately_incomplete():
    """Test with a query that should get incomplete response and trigger iteration"""
    client = httpx.AsyncClient(timeout=60.0)
    
    print("="*80)
    print("SIMPLE ITERATION TEST")
    print("="*80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Ask for something that will likely get an incomplete first response
    request = {
        "messages": [{
            "role": "user", 
            "content": "List 10 different programming languages with detailed explanations of their use cases, syntax examples, and popular frameworks. Be extremely thorough."
        }],
        "user_id": 10001,
        "model": "gpt-4o-mini",
        "enable_iterations": True,
        "stream": True
    }
    
    print("Request: Asking for 10 programming languages with detailed info")
    print("Expected: Initial response might be incomplete, triggering iteration")
    print()
    
    events = []
    iteration_events = []
    evaluation_found = False
    
    try:
        async with client.stream("POST", "http://localhost:5002/v1/multi-agent/response", json=request) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                        
                    try:
                        event = json.loads(data_str)
                        events.append(event)
                        
                        # Look for iteration evaluation
                        if event.get("type") == "response.reasoning_text.delta":
                            text = event.get("delta", "")
                            if "iteration" in text.lower() or "evaluation" in text.lower():
                                iteration_events.append(text)
                                evaluation_found = True
                                
                        # Look for iteration items
                        elif event.get("type") == "response.output_item.added":
                            item = event.get("item", {})
                            if "iter" in item.get("id", ""):
                                print(f"🔄 ITERATION DETECTED: {item.get('id')}")
                                
                    except json.JSONDecodeError:
                        pass
                        
    except Exception as e:
        print(f"Stream error: {type(e).__name__}")
    
    # Check logs for iteration evaluation
    print("\n" + "-"*80)
    print("CHECKING SERVER LOGS FOR ITERATION EVALUATION...")
    
    # Give server time to write logs
    await asyncio.sleep(1)
    
    # Read server logs
    try:
        with open("ml_server.log", "r") as f:
            logs = f.read()
            
        # Look for iteration evaluation in last 1000 chars
        recent_logs = logs[-2000:]
        if "Iteration evaluation raw response:" in recent_logs:
            print("✅ Found iteration evaluation in logs!")
            eval_start = recent_logs.find("Iteration evaluation raw response:")
            eval_line = recent_logs[eval_start:eval_start+300]
            print(f"Log: {eval_line}")
            
            # Check if it's valid JSON
            if "{" in eval_line and "}" in eval_line:
                json_start = eval_line.find("{")
                json_end = eval_line.find("}") + 1
                try:
                    eval_json = json.loads(eval_line[json_start:json_end])
                    print(f"Parsed evaluation: {eval_json}")
                except:
                    print("Failed to parse evaluation JSON")
        else:
            print("❌ No iteration evaluation found in logs")
            
    except Exception as e:
        print(f"Could not read logs: {e}")
    
    print("\n" + "-"*80)
    print("RESULTS:")
    print(f"Total events: {len(events)}")
    print(f"Iteration events found: {len(iteration_events)}")
    print(f"Evaluation detected: {evaluation_found}")
    
    # Count event types
    event_types = {}
    for event in events:
        event_type = event.get("type", "unknown")
        event_types[event_type] = event_types.get(event_type, 0) + 1
    
    print("\nEvent type counts:")
    for event_type, count in sorted(event_types.items()):
        print(f"  {event_type}: {count}")
    
    # Check for metadata with iterations
    for event in events:
        if event.get("type") == "response.usage" and "metadata" in event:
            metadata = event.get("metadata", {})
            iterations = metadata.get("iterations", 1)
            print(f"\nMetadata iterations: {iterations}")
            break
    
    await client.aclose()

if __name__ == "__main__":
    asyncio.run(test_deliberately_incomplete())