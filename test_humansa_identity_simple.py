#!/usr/bin/env python3
"""
Simple test script to verify Humansa agent identity without async.
"""
import requests
import json
import os

# Test configuration
TEST_PORT = os.getenv('ML_SERVER_PORT', '5001')
BASE_URL = f"http://localhost:{TEST_PORT}"
API_URL = f"{BASE_URL}/v1-humansa/chat/completions"

def test_identity():
    """Test basic identity query."""
    print("🧪 Testing Humansa Agent Identity...")
    
    # Test data
    test_query = "你是谁？"
    
    # Request payload
    payload = {
        "messages": [
            {
                "role": "user",
                "content": test_query
            }
        ],
        "model": "gpt-4.1-nano",
        "stream": False,
        "user_id": "test_identity_user",
        "enable_rag": False,
        "enable_web_search": False
    }
    
    try:
        # Make request
        response = requests.post(
            API_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
            
            print(f"\n📝 Query: {test_query}")
            print(f"✅ Response: {content}")
            
            # Check for key identity markers
            identity_keywords = ["诺亚新舟", "小诺", "健康医疗助理", "AI健康管家"]
            found_keywords = [kw for kw in identity_keywords if kw in content]
            
            if found_keywords:
                print(f"\n✅ Identity confirmed! Found keywords: {', '.join(found_keywords)}")
                
                # Check agent trace for v2 prompt usage
                if 'agent_trace' in result:
                    trace = result['agent_trace']
                    if '诺亚新舟健康医疗助理' in trace:
                        print("✅ V2 system prompt is being used!")
                    else:
                        print("⚠️  V2 system prompt may not be properly integrated")
            else:
                print(f"\n❌ Identity not confirmed. Expected keywords: {', '.join(identity_keywords)}")
        else:
            print(f"\n❌ Request failed with status: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print(f"\n❌ Cannot connect to server at {API_URL}")
        print("Please ensure the ML server is running on port 5001")
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    test_identity()