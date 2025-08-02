#!/usr/bin/env python3
"""
Test V2 endpoint with workflow orchestrator focus
"""

import json
import urllib.request
import urllib.error
from datetime import datetime


def test_v2_product_workflow():
    """Test V2 endpoint specifically for product queries using workflow orchestrator"""
    base_url = "http://localhost:6001"
    
    # Simple product query
    query = "童年故事DHA"
    
    request_data = {
        "messages": [{"role": "user", "content": query}],
        "user_id": "test_v2_product",
        "stream": False  # Start with non-streaming to see full response
    }
    
    print(f"\n{'='*60}")
    print(f"Testing V2 Workflow Orchestrator - Product Query")
    print(f"Endpoint: /v2/humansa/chat")
    print(f"Query: {query}")
    print(f"Time: {datetime.now()}")
    print(f"{'='*60}\n")
    
    try:
        req = urllib.request.Request(
            f"{base_url}/v2/humansa/chat",
            data=json.dumps(request_data).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        
        with urllib.request.urlopen(req, timeout=120) as response:
            raw_data = response.read().decode('utf-8')
            print("Raw response:")
            print("-" * 40)
            print(raw_data[:500] + "..." if len(raw_data) > 500 else raw_data)
            print("-" * 40)
            
            data = json.loads(raw_data)
            
            # Print the full response structure
            print("\nResponse structure:")
            print(json.dumps(data, indent=2, ensure_ascii=False)[:1000])
            
            # Extract content based on response format
            content = ""
            if 'choices' in data:
                content = data['choices'][0]['message']['content']
            elif 'output' in data:
                output = data['output']
                if isinstance(output, list) and output:
                    content = output[0].get('text', '')
            elif 'response' in data:
                content = data['response']
            else:
                content = str(data)
            
            print(f"\n{'='*60}")
            print("Extracted content:")
            print(content)
            print(f"{'='*60}")
            
            # Analysis
            success = '童年故事' in content or 'DHA' in content
            print(f"\n✅ Product info found" if success else "❌ No product info found")
            
    except urllib.error.HTTPError as e:
        print(f"❌ HTTP Error {e.code}")
        error_data = e.read().decode('utf-8')
        print(f"Error response: {error_data}")
        
        # Try to parse error details
        try:
            error_json = json.loads(error_data)
            if 'error' in error_json:
                print(f"\nError message: {error_json['error']}")
                
                # Check server logs for more details
                print("\nCheck server logs for full stack trace")
        except:
            pass
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


def test_v2_streaming():
    """Test V2 streaming to see ReAct reasoning"""
    base_url = "http://localhost:6001"
    
    query = "请推荐儿童DHA产品"
    
    request_data = {
        "messages": [{"role": "user", "content": query}],
        "user_id": "test_v2_stream",
        "stream": True
    }
    
    print(f"\n{'='*60}")
    print(f"Testing V2 Streaming with Workflow Orchestrator")
    print(f"Query: {query}")
    print(f"{'='*60}\n")
    
    try:
        req = urllib.request.Request(
            f"{base_url}/v2/humansa/chat",
            data=json.dumps(request_data).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        
        with urllib.request.urlopen(req, timeout=120) as response:
            print("Streaming response:")
            print("-" * 60)
            
            accumulated = ""
            event_count = 0
            
            for line in response:
                line = line.decode('utf-8').strip()
                if line and line.startswith('data: '):
                    data_str = line[6:]
                    if data_str == '[DONE]':
                        print("\n[STREAMING DONE]")
                        break
                    
                    event_count += 1
                    
                    try:
                        data = json.loads(data_str)
                        
                        # Show first few events in detail
                        if event_count <= 3:
                            print(f"\nEvent {event_count}:")
                            print(json.dumps(data, indent=2, ensure_ascii=False)[:300])
                        
                        # Extract text content
                        if 'type' in data:
                            # V2 response format
                            if data['type'] == 'response.output_text.delta':
                                text = data.get('text', '')
                                if text:
                                    print(text, end='', flush=True)
                                    accumulated += text
                            elif data['type'] == 'response.output_text.done':
                                final_text = data.get('text', '')
                                if final_text and not accumulated:
                                    print(final_text)
                                    accumulated = final_text
                        elif 'choices' in data:
                            # OpenAI format
                            content = data['choices'][0].get('delta', {}).get('content', '')
                            if content:
                                print(content, end='', flush=True)
                                accumulated += content
                                
                    except json.JSONDecodeError as e:
                        print(f"\nJSON decode error: {e}")
                        print(f"Data: {data_str[:100]}")
            
            print("-" * 60)
            print(f"\nTotal events: {event_count}")
            print(f"Accumulated text length: {len(accumulated)}")
            
            # Check for workflow patterns
            if 'call_productagent' in accumulated.lower():
                print("✅ Found ProductAgent call!")
            else:
                print("❌ No ProductAgent call found")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("\n🧪 Testing V2 Endpoint with Workflow Orchestrator Focus\n")
    
    # Test 1: Non-streaming to see full response
    test_v2_product_workflow()
    
    print("\n" + "="*80 + "\n")
    
    # Test 2: Streaming to see reasoning steps
    test_v2_streaming()
    
    print("\n✅ Tests completed!\n")