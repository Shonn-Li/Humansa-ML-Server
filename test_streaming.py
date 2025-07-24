#!/usr/bin/env python
"""Test streaming with reasoning events"""

import requests
import json

def test_streaming():
    """Test multi-agent streaming with reasoning events"""
    print("Testing multi-agent streaming...")
    
    url = "http://localhost:5001/v1/multi-agent/response"
    headers = {"Content-Type": "application/json"}
    
    payload = {
        "messages": [
            {"role": "user", "content": "What notes do I have about Python programming?"}
        ],
        "user_id": 10001,  # Use test user ID if in test mode
        "query_type": "humansa",
        "llm_provider": "openai",
        "stream": True
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, stream=True)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            print("\n=== Streaming Events ===")
            event_count = 0
            reasoning_events = 0
            
            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    if line_str.startswith('data: '):
                        data = line_str[6:]  # Remove 'data: ' prefix
                        if data == '[DONE]':
                            print("\n✅ Stream completed")
                            break
                        
                        try:
                            event = json.loads(data)
                            event_count += 1
                            
                            # Check for reasoning events
                            if 'choices' in event and len(event['choices']) > 0:
                                choice = event['choices'][0]
                                if 'delta' in choice and 'reasoning_content' in choice['delta']:
                                    reasoning_events += 1
                                    print(f"\n🤔 Reasoning [{event_count}]: {choice['delta']['reasoning_content']}")
                                elif 'delta' in choice and 'content' in choice['delta']:
                                    content = choice['delta']['content']
                                    if content:
                                        print(content, end='', flush=True)
                        except json.JSONDecodeError:
                            print(f"\n⚠️  Invalid JSON: {data}")
            
            print(f"\n\n📊 Summary: {event_count} total events, {reasoning_events} reasoning events")
        else:
            print(f"❌ Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Request failed: {e}")

if __name__ == "__main__":
    print("=== Testing Multi-Agent Streaming with Reasoning Events ===")
    test_streaming()