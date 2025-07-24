#!/usr/bin/env python3
"""
Detailed test of Humansa endpoints - shows full responses.
"""

import json
import urllib.request
import urllib.error
import ssl

# Disable SSL verification for local testing
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

BASE_URL = "http://localhost:5001"

def make_request(endpoint, data=None, method="POST"):
    """Make HTTP request and return full response."""
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
            response_data = response.read().decode('utf-8')
            try:
                parsed_data = json.loads(response_data)
            except:
                parsed_data = response_data
            
            return {
                "status": response.status,
                "headers": dict(response.headers),
                "data": parsed_data,
                "raw": response_data[:500]  # First 500 chars
            }
    except urllib.error.HTTPError as e:
        error_data = e.read().decode('utf-8')
        return {
            "status": e.code,
            "error": error_data,
            "raw": error_data[:500]
        }
    except Exception as e:
        return {
            "status": 0,
            "error": str(e)
        }


def test_v1_humansa_detailed():
    """Test V1 endpoint with detailed output."""
    print("\n🔍 Detailed V1 Humansa Test")
    print("-" * 60)
    
    payload = {
        "model": "gpt-4",
        "messages": [
            {"role": "user", "content": "I need to see a doctor for my headache"}
        ],
        "stream": False
    }
    
    print(f"Request payload: {json.dumps(payload, indent=2)}")
    
    result = make_request("/v1-humansa/chat/completions", payload)
    
    print(f"\nResponse status: {result['status']}")
    print(f"Response type: {type(result.get('data'))}")
    
    if result["status"] == 200:
        if isinstance(result['data'], dict):
            print(f"Response keys: {list(result['data'].keys())}")
            print(f"\nFull response (first 500 chars):")
            print(result['raw'])
        else:
            print(f"Response is not JSON: {result['raw']}")
    else:
        print(f"Error response: {result.get('error', 'Unknown')}")


def test_simple_endpoint():
    """Test a simple endpoint to verify connectivity."""
    print("\n🔍 Testing Simple Endpoint")
    print("-" * 60)
    
    # Try a simple GET request
    result = make_request("/", method="GET")
    print(f"Root endpoint status: {result['status']}")
    
    # Try health endpoint
    result = make_request("/health", method="GET")
    print(f"Health endpoint status: {result['status']}")
    if result['status'] == 200:
        print(f"Health response: {result.get('data')}")


def test_with_curl():
    """Show equivalent curl commands for manual testing."""
    print("\n🔍 Equivalent curl commands for manual testing:")
    print("-" * 60)
    
    print("\n1. Test V1 Humansa endpoint:")
    print("""curl -X POST http://localhost:5001/v1-humansa/chat/completions \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer test-api-key" \\
  -d '{
    "model": "gpt-4",
    "messages": [{"role": "user", "content": "I need a doctor"}],
    "stream": false
  }'""")
    
    print("\n2. Test Humansa backend:")
    print("""curl -X POST http://localhost:5001/humansa/response \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer test-api-key" \\
  -d '{
    "query": "Find a doctor",
    "conversation_id": "test-123"
  }'""")


def check_endpoints_in_code():
    """Check if endpoints are registered in main.py."""
    print("\n🔍 Checking endpoint registration in code")
    print("-" * 60)
    
    try:
        with open("src/main.py", "r") as f:
            content = f.read()
        
        endpoints = [
            "/v1-humansa/chat/completions",
            "/humansa/response",
            "/v2/humansa"
        ]
        
        for endpoint in endpoints:
            if endpoint in content:
                print(f"✅ {endpoint} - Found in main.py")
            else:
                print(f"❌ {endpoint} - Not found in main.py")
                
        # Check for blueprint registration
        if "humansa" in content.lower():
            print("\n✅ Humansa references found in main.py")
            # Count occurrences
            count = content.lower().count("humansa")
            print(f"   Total Humansa references: {count}")
            
    except Exception as e:
        print(f"❌ Error reading main.py: {e}")


def main():
    """Run detailed tests."""
    print("🏥 Humansa Detailed API Test")
    print("=" * 60)
    
    # Check basic connectivity
    test_simple_endpoint()
    
    # Check endpoint registration
    check_endpoints_in_code()
    
    # Test with detailed output
    test_v1_humansa_detailed()
    
    # Show curl commands
    test_with_curl()
    
    print("\n" + "=" * 60)
    print("✅ Detailed test completed")


if __name__ == "__main__":
    main()