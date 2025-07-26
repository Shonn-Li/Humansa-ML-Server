#!/usr/bin/env python3
"""
Test the actual orchestrator behavior to see if it's truly orchestrating
or just doing simple routing
"""

import json
import subprocess
import time

def run_curl_command(data):
    """Run curl command and return response"""
    cmd = [
        'curl', '-X', 'POST',
        'http://localhost:5001/v2/humansa/chat',
        '-H', 'Content-Type: application/json',
        '-d', json.dumps(data),
        '-s'
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            try:
                return json.loads(result.stdout)
            except:
                return {"raw_output": result.stdout}
        else:
            return {"error": result.stderr}
    except Exception as e:
        return {"error": str(e)}

def test_orchestrator():
    print("=== Humansa V2 Orchestrator Behavior Test ===\n")
    
    # Test 1: Simple single-agent query
    print("Test 1: Simple diagnosis query")
    print("-" * 50)
    response = run_curl_command({
        "user_id": 123,
        "messages": [{"role": "user", "content": "What are the symptoms of diabetes?"}],
        "stream": False
    })
    print(f"Response: {json.dumps(response, indent=2)}\n")
    
    # Test 2: Multi-agent query
    print("Test 2: Complex multi-aspect query")
    print("-" * 50)
    response = run_curl_command({
        "user_id": 123,
        "messages": [{"role": "user", "content": "I have diabetes symptoms, need treatment options, and want to schedule an appointment"}],
        "stream": False
    })
    print(f"Response: {json.dumps(response, indent=2)}\n")
    
    # Test 3: Vague query that should trigger iteration
    print("Test 3: Vague symptoms requiring clarification")
    print("-" * 50)
    response = run_curl_command({
        "user_id": 123,
        "messages": [{"role": "user", "content": "I feel tired and thirsty often"}],
        "stream": False
    })
    print(f"Response: {json.dumps(response, indent=2)}\n")
    
    # Test 4: Check system health
    print("Test 4: System health check")
    print("-" * 50)
    health_cmd = ['curl', '-s', 'http://localhost:5001/v2/humansa/health']
    result = subprocess.run(health_cmd, capture_output=True, text=True)
    if result.returncode == 0:
        try:
            health = json.loads(result.stdout)
            print(f"Health: {json.dumps(health, indent=2)}")
        except:
            print(f"Health response: {result.stdout}")
    
    print("\n=== Analysis ===")
    print("If orchestrator is working properly:")
    print("- Test 2 should show multiple agents being used")
    print("- Test 3 should show iterative refinement")
    print("- Responses should mention which agents were involved")
    print("\nIf it's just simple routing:")
    print("- Each test triggers only one agent")
    print("- No mention of multiple agents or iterations")
    print("- Keyword-based selection only")

if __name__ == "__main__":
    test_orchestrator()