#!/usr/bin/env python
"""Debug streaming to see all events"""

import requests
import json

def test_streaming_debug():
    """Test multi-agent streaming with detailed debug output"""
    print("Testing multi-agent streaming with debug...")
    
    url = "http://localhost:5001/v1/multi-agent/response"
    headers = {"Content-Type": "application/json"}
    
    payload = {
        "messages": [
            {"role": "user", "content": "Tell me about machine learning in my notes"}
        ],
        "user_id": 10001,
        "query_type": "humansa",
        "llm_provider": "openai",
        "stream": True
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, stream=True)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            print("\n=== All Streaming Events ===")
            
            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    if line_str.startswith('data: '):
                        data = line_str[6:]
                        if data == '[DONE]':
                            print("\n[DONE]")
                            break
                        
                        try:
                            event = json.loads(data)
                            print(f"\nEvent: {json.dumps(event, indent=2)}")
                        except json.JSONDecodeError:
                            print(f"\nRaw data: {data}")
        else:
            print(f"❌ Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Request failed: {e}")

if __name__ == "__main__":
    test_streaming_debug()