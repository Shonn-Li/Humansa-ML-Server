#!/usr/bin/env python3
"""
Live test of Humansa endpoints - tests actual API functionality.
"""

import json
import urllib.request
import urllib.error
import ssl
from datetime import datetime

# Disable SSL verification for local testing
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

BASE_URL = "http://localhost:5001"

def make_request(endpoint, data=None, method="POST"):
    """Make HTTP request to the server."""
    url = f"{BASE_URL}{endpoint}"
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer test-api-key"
    }
    
    if data:
        data = json.dumps(data).encode('utf-8')
    
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    
    try:
        with urllib.request.urlopen(req, context=ssl_context) as response:
            return {
                "status": response.status,
                "data": json.loads(response.read().decode('utf-8'))
            }
    except urllib.error.HTTPError as e:
        return {
            "status": e.code,
            "error": e.read().decode('utf-8')
        }
    except Exception as e:
        return {
            "status": 0,
            "error": str(e)
        }


def test_v1_humansa_chat():
    """Test V1 Humansa chat completions endpoint."""
    print("\n🔍 Testing V1 Humansa Chat Completions")
    print("-" * 50)
    
    test_cases = [
        {
            "name": "General health query",
            "message": "I have a headache that's been lasting for 3 days. What should I do?"
        },
        {
            "name": "Doctor search",
            "message": "I need to find a cardiologist in Singapore"
        },
        {
            "name": "Appointment booking",
            "message": "Can you help me book an appointment with Dr. Sarah Chen?"
        }
    ]
    
    for test in test_cases:
        print(f"\n📝 Test: {test['name']}")
        
        payload = {
            "model": "gpt-4",
            "messages": [
                {"role": "user", "content": test['message']}
            ],
            "stream": False,
            "temperature": 0.7
        }
        
        result = make_request("/v1-humansa/chat/completions", payload)
        
        if result["status"] == 200:
            print(f"✅ Status: {result['status']}")
            data = result["data"]
            
            # Check response structure
            if "choices" in data and len(data["choices"]) > 0:
                choice = data["choices"][0]
                message = choice.get("message", {})
                
                # Check for content
                if "content" in message:
                    print(f"✅ Response received: {len(message['content'])} characters")
                
                # Check for tool calls
                if "tool_calls" in message and message["tool_calls"]:
                    print(f"✅ Tool calls: {len(message['tool_calls'])} tools invoked")
                    for tool in message["tool_calls"]:
                        print(f"   - {tool.get('function', {}).get('name', 'Unknown')}")
            else:
                print("❌ Invalid response structure")
        else:
            print(f"❌ Status: {result['status']}")
            print(f"   Error: {result.get('error', 'Unknown error')}")


def test_v2_humansa_endpoints():
    """Test V2 Humansa multi-agent endpoints."""
    print("\n\n🔍 Testing V2 Humansa Multi-Agent System")
    print("-" * 50)
    
    # Test multi-agent chat
    print("\n📝 Test: Multi-agent medical consultation")
    
    payload = {
        "messages": [
            {"role": "user", "content": "I'm feeling dizzy and have high blood pressure. What specialists should I see?"}
        ],
        "user_id": "test-user-123",
        "session_id": f"test-{datetime.now().timestamp()}"
    }
    
    result = make_request("/v2/humansa/chat", payload)
    
    if result["status"] == 200:
        print(f"✅ Status: {result['status']}")
        print("✅ Multi-agent response received")
    else:
        print(f"❌ Status: {result['status']}")
        print(f"   Note: V2 endpoints may not be fully implemented yet")


def test_humansa_backend():
    """Test Humansa backend endpoint."""
    print("\n\n🔍 Testing Humansa Backend Endpoint")
    print("-" * 50)
    
    payload = {
        "query": "Find me a general practitioner near Orchard",
        "conversation_id": "test-conv-123"
    }
    
    result = make_request("/humansa/response", payload)
    
    if result["status"] == 200:
        print(f"✅ Status: {result['status']}")
        data = result["data"]
        if "response" in data:
            print(f"✅ Backend response received")
    else:
        print(f"❌ Status: {result['status']}")


def test_health_check():
    """Test if server is healthy."""
    print("\n🔍 Testing Server Health")
    print("-" * 50)
    
    result = make_request("/health", method="GET")
    
    if result["status"] == 200:
        print(f"✅ Server is healthy")
        return True
    else:
        print(f"❌ Server health check failed")
        return False


def main():
    """Run all live tests."""
    print("🏥 Humansa Live API Tests")
    print("=" * 60)
    print(f"Server: {BASE_URL}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check server health first
    if not test_health_check():
        print("\n❌ Server is not responding. Please ensure it's running.")
        return
    
    # Run all tests
    test_v1_humansa_chat()
    test_v2_humansa_endpoints()
    test_humansa_backend()
    
    print("\n" + "=" * 60)
    print("✅ Test execution completed")
    print("\nNote: Some endpoints may return errors if dependencies are missing.")
    print("The key validation is that the endpoints exist and are reachable.")


if __name__ == "__main__":
    main()