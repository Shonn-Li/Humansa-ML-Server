#!/usr/bin/env python3
"""
Test backend search functionality directly
"""
import requests
import json

def test_backend_search():
    """Test the backend's multi-agent endpoint with search"""
    
    # Test against the NestJS backend, not ML server directly
    backend_url = "http://localhost:3000/v1/conversation/expand"
    
    # Simple test request that should trigger context search
    test_request = {
        "prompt": "What are the main themes in my notes?",
        "conversationId": 1,
        "model": "openai/gpt-4o-mini",
        "modelProvider": "openai",
        "useMultiAgent": True,
        "streamResponse": True
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer test-token"  # Replace with actual auth token if needed
    }
    
    print("Sending request to backend...")
    print(f"URL: {backend_url}")
    print(f"Request: {json.dumps(test_request, indent=2)}")
    print("-" * 80)
    
    try:
        response = requests.post(backend_url, json=test_request, headers=headers, stream=True)
        
        print(f"Response status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"Error response: {response.text}")
            return
        
        print("Streaming response:")
        print("-" * 80)
        
        found_search_events = []
        
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('data: '):
                    try:
                        data = json.loads(line_str[6:])
                        
                        # Look for search-related events
                        event_type = data.get('type', '')
                        
                        if 'search' in event_type.lower() or 'search' in str(data).lower():
                            print(f"\n🔍 SEARCH EVENT: {event_type}")
                            print(json.dumps(data, indent=2))
                            found_search_events.append(data)
                        
                        # Look for output_item.done events
                        if event_type == 'response.output_item.done':
                            item = data.get('item', {})
                            item_type = item.get('type', '')
                            
                            if 'search' in item_type:
                                print(f"\n📦 SEARCH DONE EVENT:")
                                print(json.dumps(item, indent=2))
                                
                                has_results = 'results' in item or 'sources' in item
                                result_count = len(item.get('results', item.get('sources', [])))
                                
                                print(f"Has results: {has_results}")
                                print(f"Result count: {result_count}")
                    
                    except json.JSONDecodeError:
                        pass
                    except Exception as e:
                        print(f"Error processing line: {e}")
        
        print("\n" + "-" * 80)
        print(f"\nFound {len(found_search_events)} search-related events")
        
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    test_backend_search()