#!/usr/bin/env python
"""Quick test to validate database column names are fixed"""

import requests
import json

def test_context_search():
    """Test context search with database queries"""
    print("Testing context search agent...")
    
    url = "http://localhost:5002/v1/multi-agent/response"
    headers = {"Content-Type": "application/json"}
    
    payload = {
        "messages": [
            {"role": "user", "content": "Search for notes about AI and machine learning"}
        ],
        "user_id": 10001,
        "query_type": "humansa",
        "llm_provider": "openai",
        "stream": False
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Context search successful!")
            print(f"Response preview: {str(result)[:200]}...")
        else:
            print(f"❌ Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Request failed: {e}")

def test_conversation_search():
    """Test conversation search with database queries"""
    print("\nTesting conversation search...")
    
    url = "http://localhost:5002/v1/multi-agent/response"
    headers = {"Content-Type": "application/json"}
    
    payload = {
        "messages": [
            {"role": "user", "content": "Find conversations about testing"}
        ],
        "user_id": 10001,
        "query_type": "humansa",
        "llm_provider": "openai",
        "stream": False
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Conversation search successful!")
            print(f"Response preview: {str(result)[:200]}...")
        else:
            print(f"❌ Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Request failed: {e}")

if __name__ == "__main__":
    print("=== Column Name Validation Test ===")
    test_context_search()
    test_conversation_search()
    print("\n✅ All tests completed!")