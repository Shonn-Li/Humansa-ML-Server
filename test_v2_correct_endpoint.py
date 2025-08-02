#!/usr/bin/env python3
"""
Test the correct V2 endpoint with workflow orchestrator
"""

import json
import urllib.request
import urllib.error
from datetime import datetime


def test_v2_chat_endpoint():
    """Test V2 chat endpoint which should use workflow orchestrator"""
    base_url = "http://localhost:6001"
    
    query = "请推荐一些儿童DHA产品，包括具体的产品名称和购买链接"
    
    request_data = {
        "messages": [{"role": "user", "content": query}],
        "user_id": "test_v2_correct",
        "stream": False
    }
    
    print(f"\n{'='*60}")
    print(f"Testing V2 Chat Endpoint (/v2/humansa/chat)")
    print(f"Query: {query}")
    print(f"Time: {datetime.now()}")
    print(f"{'='*60}\n")
    
    # Make request to V2 endpoint
    try:
        req = urllib.request.Request(
            f"{base_url}/v2/humansa/chat",  # V2 endpoint!
            data=json.dumps(request_data).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        
        with urllib.request.urlopen(req, timeout=120) as response:
            data = json.loads(response.read().decode('utf-8'))
            
            # Extract content
            content = ""
            if 'choices' in data:
                content = data['choices'][0]['message']['content']
            elif 'output' in data:
                # V2 format might be different
                output = data['output']
                if isinstance(output, list) and output:
                    content = output[0].get('text', '')
            elif 'message' in data:
                content = data['message']
            else:
                content = str(data)
            
            print("Response:")
            print("-" * 60)
            print(content)
            print("-" * 60)
            
            # Detailed analysis
            print(f"\n{'='*60}")
            print("Analysis:")
            
            # Check for workflow patterns
            workflow_patterns = [
                "call_productagent",
                "call_appointmentagent",
                "call_clinicalagent",
                "call_medicationagent",
                "call_generalagent"
            ]
            
            found_workflow = any(pattern in content.lower() for pattern in workflow_patterns)
            print(f"✅ Found workflow sub-agent calls" if found_workflow else "❌ No workflow sub-agent calls")
            
            # Check for specific products
            products = []
            product_names = ['童年故事', '爱乐维', 'Swisse', 'DHA', '藻油', '惠氏']
            for name in product_names:
                if name in content:
                    products.append(name)
            
            print(f"Products found: {products if products else 'None'}")
            
            # Check for URLs
            has_urls = 'youzan.com' in content or 'https://' in content
            print(f"✅ Has URLs" if has_urls else "❌ No URLs")
            
            # Check for specifications
            import re
            spec_patterns = [r'\d+mg', r'\d+毫克', r'\d+粒', r'\d+瓶']
            specs = []
            for pattern in spec_patterns:
                matches = re.findall(pattern, content)
                specs.extend(matches)
            
            print(f"Specifications: {specs if specs else 'None'}")
            
            # Final verdict
            success = len(products) > 0 and (has_urls or '商城' in content)
            
            print(f"\n{'='*60}")
            if success:
                print("✅ SUCCESS: V2 endpoint returned product information!")
            else:
                print("❌ FAILED: Missing product details")
            print(f"{'='*60}\n")
            
    except urllib.error.HTTPError as e:
        print(f"❌ HTTP Error {e.code}")
        error_data = e.read().decode('utf-8')
        try:
            error_json = json.loads(error_data)
            print(f"Error: {json.dumps(error_json, indent=2)}")
        except:
            print(f"Error: {error_data[:500]}")
    except Exception as e:
        print(f"❌ Error: {e}")


def test_v2_streaming():
    """Test V2 endpoint with streaming"""
    base_url = "http://localhost:6001"
    
    query = "童年故事DHA怎么样？"
    
    request_data = {
        "messages": [{"role": "user", "content": query}],
        "user_id": "test_v2_stream",
        "stream": True
    }
    
    print(f"\n{'='*60}")
    print(f"Testing V2 Streaming")
    print(f"Query: {query}")
    print(f"{'='*60}\n")
    
    try:
        req = urllib.request.Request(
            f"{base_url}/v2/humansa/chat",
            data=json.dumps(request_data).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        
        with urllib.request.urlopen(req, timeout=60) as response:
            accumulated = ""
            found_agent_call = False
            
            for line in response:
                line = line.decode('utf-8').strip()
                if line and line.startswith('data: '):
                    data_str = line[6:]
                    if data_str == '[DONE]':
                        break
                    
                    try:
                        data = json.loads(data_str)
                        
                        # Extract text content
                        if 'choices' in data:
                            content = data['choices'][0].get('delta', {}).get('content', '')
                            accumulated += content
                        elif 'chunk' in data:
                            accumulated += data['chunk']
                        
                        # Check for agent calls
                        if 'call_productagent' in accumulated.lower():
                            found_agent_call = True
                            
                    except json.JSONDecodeError:
                        continue
            
            print("Streaming result:")
            print("-" * 40)
            print(accumulated[:500] + "..." if len(accumulated) > 500 else accumulated)
            print("-" * 40)
            print(f"\n✅ Found agent call" if found_agent_call else "❌ No agent call found")
            
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    print("\n🧪 Testing V2 Endpoint with Workflow Orchestrator\n")
    
    # Test 1: V2 chat endpoint
    test_v2_chat_endpoint()
    
    # Test 2: V2 streaming
    test_v2_streaming()
    
    print("\n✅ V2 endpoint tests completed!\n")