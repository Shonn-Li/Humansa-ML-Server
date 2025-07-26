#!/usr/bin/env python3
"""
Simple test to verify Mem0 is working with ML server
"""

import subprocess
import json
import time

BASE_URL = "http://localhost:6001"

def run_test():
    print("=== Simple Mem0 Integration Test ===\n")
    
    # Test 1: Check health
    print("1. Checking ML server health...")
    cmd = ['curl', '-s', f'{BASE_URL}/health']
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        try:
            health = json.loads(result.stdout)
            print(f"✓ Server healthy on port {health.get('port', 'unknown')}")
        except:
            print(f"✗ Invalid health response: {result.stdout[:100]}")
    else:
        print("✗ Server not responding")
        return
    
    # Test 2: Check v2 health
    print("\n2. Checking Humansa v2 health...")
    cmd = ['curl', '-s', f'{BASE_URL}/v2/humansa/health']
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        try:
            v2_health = json.loads(result.stdout)
            print(f"✓ V2 Status: {v2_health.get('status')}")
            components = v2_health.get('components', {})
            print(f"  - Orchestrator: {components.get('orchestrator')}")
            print(f"  - Memory Manager: {components.get('memory_manager')}")
            print(f"  - Appointment Workflow: {components.get('appointment_workflow')}")
        except:
            print(f"Response: {result.stdout[:200]}")
    
    # Test 3: Try v1 chat (should work)
    print("\n3. Testing v1 chat endpoint...")
    data = {
        "messages": [{"role": "user", "content": "hello"}],
        "model": "gpt-4",
        "user_id": 123
    }
    cmd = [
        'curl', '-X', 'POST',
        f'{BASE_URL}/v1/chat/completions',
        '-H', 'Content-Type: application/json',
        '-d', json.dumps(data),
        '-s'
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        try:
            response = json.loads(result.stdout)
            if 'error' in response:
                print(f"✗ Error: {response['error']}")
            else:
                print("✓ v1 chat working")
                print(f"  Response preview: {str(response)[:100]}...")
        except:
            print(f"✗ Invalid response: {result.stdout[:100]}")
    
    # Test 4: Try v2 chat
    print("\n4. Testing v2 chat endpoint...")
    data = {
        "user_id": 123,
        "messages": [{"role": "user", "content": "I have diabetes"}],
        "stream": False
    }
    cmd = [
        'curl', '-X', 'POST',
        f'{BASE_URL}/v2/humansa/chat',
        '-H', 'Content-Type: application/json',
        '-d', json.dumps(data),
        '-s'
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        try:
            response = json.loads(result.stdout)
            if 'error' in response:
                print(f"✗ V2 Error: {response['error']}")
                
                # Try to get more info
                if "NoneType" in response['error']:
                    print("  → Orchestrator not initialized properly")
            else:
                print("✓ v2 chat working")
        except:
            print(f"✗ Invalid response: {result.stdout[:100]}")
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    run_test()