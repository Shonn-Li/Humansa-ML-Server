#!/usr/bin/env python3
"""
Quick test to verify Mem0 is working
Uses simple HTTP requests
"""

import requests
import json
import time

BASE_URL = "http://localhost:6001"
TEST_USER_ID = 10001

def test_mem0():
    print("=== Quick Mem0 Test ===\n")
    
    # Test 1: Check if v2 endpoints exist
    print("1. Testing V2 chat endpoint...")
    try:
        response = requests.post(
            f"{BASE_URL}/v2/humansa/chat",
            json={
                "user_id": TEST_USER_ID,
                "messages": [{"role": "user", "content": "Hello"}],
                "stream": False
            },
            timeout=10
        )
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print("   ✓ V2 chat endpoint working")
        else:
            print(f"   ✗ Error: {response.text[:200]}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # Test 2: Check basic health
    print("\n2. Checking ML server health...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✓ Server healthy on port {data.get('port')}")
        else:
            print("   ✗ Health check failed")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # Test 3: Try v2 health endpoint
    print("\n3. Checking V2 system health...")
    try:
        response = requests.get(f"{BASE_URL}/v2/humansa/health")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✓ V2 system status: {data.get('status')}")
            components = data.get('components', {})
            print(f"   - Orchestrator: {components.get('orchestrator', False)}")
            print(f"   - Memory Manager: {components.get('memory_manager', False)}")
            print(f"   - Appointment Workflow: {components.get('appointment_workflow', False)}")
        else:
            print(f"   Status {response.status_code}: {response.text[:100]}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # Test 4: Simple conversation test
    print("\n4. Testing simple conversation...")
    try:
        response = requests.post(
            f"{BASE_URL}/v2/humansa/chat",
            json={
                "user_id": TEST_USER_ID,
                "messages": [
                    {"role": "user", "content": "I'm allergic to aspirin and prefer Dr. Smith for appointments"}
                ],
                "stream": False
            },
            timeout=30
        )
        
        if response.status_code == 200:
            print("   ✓ Conversation processed")
            result = response.json()
            print(f"   Response preview: {str(result)[:200]}...")
        else:
            print(f"   ✗ Error {response.status_code}: {response.text[:200]}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # Test 5: Memory recall test
    print("\n5. Testing memory recall...")
    time.sleep(2)  # Give time for memory to be stored
    
    try:
        response = requests.post(
            f"{BASE_URL}/v2/humansa/chat",
            json={
                "user_id": TEST_USER_ID,
                "messages": [
                    {"role": "user", "content": "What medications should I avoid?"}
                ],
                "stream": False
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            response_text = str(result).lower()
            
            if "aspirin" in response_text:
                print("   ✓ Memory working! Response mentions aspirin allergy")
            else:
                print("   ⚠ Response doesn't mention aspirin - memory might not be working")
                print(f"   Response preview: {str(result)[:300]}...")
        else:
            print(f"   ✗ Error {response.status_code}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    test_mem0()