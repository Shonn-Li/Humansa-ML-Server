#!/usr/bin/env python
"""Test end-to-end streaming with reasoning events through backend"""

import requests
import json

def test_through_backend():
    """Test streaming through the NestJS backend (which should forward to ML server)"""
    print("Testing end-to-end streaming through backend...")
    
    # Assuming backend is running on port 3000
    url = "http://localhost:3000/api/conversation/expand-streaming"
    headers = {
        "Content-Type": "application/json",
        # Add auth token if needed
    }
    
    payload = {
        "messages": [
            {"role": "user", "content": "What notes do I have about Python?"}
        ],
        "conversationType": "humansa",
        "llmProvider": "openai"
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, stream=True)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            print("\n=== Streaming Events from Backend ===")
            event_count = 0
            reasoning_events = 0
            
            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    print(f"Raw line: {line_str[:100]}...")  # Debug output
                    
                    if line_str.startswith('data: '):
                        data = line_str[6:]
                        if data == '[DONE]':
                            print("\n✅ Stream completed")
                            break
                        
                        try:
                            event = json.loads(data)
                            event_count += 1
                            
                            # Check event type
                            if 'type' in event:
                                event_type = event['type']
                                if 'reasoning' in event_type:
                                    reasoning_events += 1
                                    print(f"\n🤔 Reasoning event [{event_type}]")
                                    if 'delta' in event:
                                        print(f"   Content: {event['delta'][:50]}...")
                                        
                        except json.JSONDecodeError:
                            print(f"\n⚠️  Invalid JSON: {data}")
            
            print(f"\n\n📊 Summary: {event_count} total events, {reasoning_events} reasoning events")
        else:
            print(f"❌ Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Request failed: {e}")

if __name__ == "__main__":
    print("=== Testing End-to-End Streaming ===")
    test_through_backend()
    print("\n✅ Test completed")