#!/usr/bin/env python3
"""
Simple test to check if search results are included
"""
import requests
import json

def test_simple():
    """Simple test of the multi-agent endpoint"""
    
    url = "http://localhost:5002/v1/multi-agent/chat/stream"
    
    # Simple test request
    test_request = {
        "messages": [
            {
                "role": "user",
                "content": "Tell me about my notes"
            }
        ],
        "user_id": 10001,
        "model": "openai/gpt-4o-mini",
        "enable_rag": True
    }
    
    print("Sending request...")
    
    response = requests.post(url, json=test_request, stream=True)
    
    if response.status_code != 200:
        print(f"Error: {response.status_code}")
        print(response.text)
        return
    
    print("Streaming response:")
    print("-" * 80)
    
    found_done_events = []
    
    for line in response.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            if line_str.startswith('data: '):
                try:
                    data = json.loads(line_str[6:])
                    
                    # Look for output_item.done events
                    if data.get('type') == 'response.output_item.done':
                        item = data.get('item', {})
                        item_type = item.get('type', '')
                        
                        if item_type in ['web_search_call', 'context_search_call', 'file_search_call']:
                            print(f"\n🔍 Found {item_type} done event:")
                            print(json.dumps(item, indent=2))
                            
                            has_results = 'results' in item or 'sources' in item
                            found_done_events.append({
                                'type': item_type,
                                'has_results': has_results,
                                'result_count': len(item.get('results', item.get('sources', [])))
                            })
                    
                except json.JSONDecodeError:
                    pass
    
    print("\n" + "-" * 80)
    print("\nSummary:")
    for event in found_done_events:
        status = "✅" if event['has_results'] else "❌"
        print(f"{status} {event['type']}: has_results={event['has_results']}, count={event['result_count']}")

if __name__ == "__main__":
    test_simple()