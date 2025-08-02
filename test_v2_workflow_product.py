#!/usr/bin/env python3
"""
Test V2 Workflow Orchestrator with product queries
"""

import json
import urllib.request
import urllib.error
from datetime import datetime


def test_v2_product_query():
    """Test V2 workflow orchestrator product query"""
    base_url = "http://localhost:6001"
    
    query = "请推荐一些儿童DHA产品，需要具体的产品名称和购买链接"
    
    request_data = {
        "model": "gpt-4",
        "messages": [{"role": "user", "content": query}],
        "user_id": "test_v2_workflow",
        "stream": False,
        "temperature": 0.1,
        "metadata": {
            "orchestrator": "workflow"  # Force V2 workflow orchestrator
        }
    }
    
    print(f"\n{'='*60}")
    print(f"Testing V2 Workflow Orchestrator - Product Query")
    print(f"Query: {query}")
    print(f"Time: {datetime.now()}")
    print(f"{'='*60}\n")
    
    # Make request
    try:
        req = urllib.request.Request(
            f"{base_url}/v1-humansa/chat/completions",
            data=json.dumps(request_data).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        
        with urllib.request.urlopen(req, timeout=120) as response:
            data = json.loads(response.read().decode('utf-8'))
            
            # Extract content
            content = ""
            if 'choices' in data:
                content = data['choices'][0]['message']['content']
            
            print("Response:")
            print("-" * 60)
            print(content)
            print("-" * 60)
            
            # Detailed analysis
            print(f"\n{'='*60}")
            print("Analysis:")
            
            # Check for specific products
            products = []
            if '童年故事' in content:
                products.append('童年故事')
            if '爱乐维' in content:
                products.append('爱乐维')
            if 'Swisse' in content:
                products.append('Swisse')
            if '惠氏' in content:
                products.append('惠氏')
            
            print(f"Found products: {products if products else 'None'}")
            
            # Check for URLs
            urls = []
            if 'youzan.com' in content:
                # Extract URLs
                import re
                url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+youzan\.com[^\s<>"{}|\\^`\[\]]*'
                urls = re.findall(url_pattern, content)
            
            print(f"Found URLs: {len(urls)} URLs" if urls else "No URLs found")
            
            # Check for specifications
            specs = []
            import re
            spec_patterns = [
                r'\d+mg',
                r'\d+毫克',
                r'\d+粒',
                r'\d+瓶',
                r'\d+ml',
                r'\d+支'
            ]
            for pattern in spec_patterns:
                matches = re.findall(pattern, content)
                specs.extend(matches)
            
            print(f"Found specifications: {specs if specs else 'None'}")
            
            # Check for price info
            has_price = any(p in content for p in ['¥', '元', '价格', '售价'])
            print(f"Has price info: {'Yes' if has_price else 'No'}")
            
            # Final verdict
            success = len(products) > 0 and len(urls) > 0
            
            print(f"\n{'='*60}")
            if success:
                print("✅ SUCCESS: V2 Workflow correctly returned product details!")
                print(f"   - {len(products)} specific products")
                print(f"   - {len(urls)} purchase URLs")
                print(f"   - {len(specs)} specifications")
            else:
                print("❌ FAILED: Missing critical product information")
                if not products:
                    print("   - No specific product names")
                if not urls:
                    print("   - No purchase URLs")
            
            print(f"{'='*60}\n")
            
            # Show sample URLs if found
            if urls:
                print("Sample URLs found:")
                for i, url in enumerate(urls[:3]):
                    print(f"  {i+1}. {url}")
                print()
            
    except urllib.error.HTTPError as e:
        print(f"❌ HTTP Error {e.code}")
        error_data = e.read().decode('utf-8')
        try:
            error_json = json.loads(error_data)
            print(f"Error: {error_json.get('error', error_data)}")
        except:
            print(f"Error: {error_data}")
    except Exception as e:
        print(f"❌ Error: {e}")


def test_v2_reasoning_visibility():
    """Test V2 workflow reasoning visibility"""
    base_url = "http://localhost:6001"
    
    query = "我想给3岁的孩子买DHA"
    
    # Use Response API for full visibility
    request_data = {
        "messages": [{"role": "user", "content": query}],
        "user": "test_v2_reasoning",
        "stream": True,
        "debug": True,
        "metadata": {
            "orchestrator": "workflow"
        }
    }
    
    print(f"\n{'='*60}")
    print(f"Testing V2 Workflow Reasoning (Response API)")
    print(f"Query: {query}")
    print(f"{'='*60}\n")
    
    try:
        req = urllib.request.Request(
            f"{base_url}/v1-humansa/multi-agent/response",
            data=json.dumps(request_data).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        
        with urllib.request.urlopen(req, timeout=120) as response:
            accumulated = ""
            found_call_product = False
            found_observation = False
            
            for line in response:
                line = line.decode('utf-8').strip()
                if line and line.startswith('data: '):
                    data_str = line[6:]
                    if data_str == '[DONE]':
                        break
                    
                    try:
                        data = json.loads(data_str)
                        
                        # Look for text content
                        if data.get('type') == 'response.output_text.delta':
                            text = data.get('text', '')
                            accumulated += text
                            
                            if 'call_productagent' in text.lower():
                                found_call_product = True
                            if 'Observation:' in text or '观察' in text:
                                found_observation = True
                                
                    except json.JSONDecodeError:
                        continue
            
            print("Reasoning visibility:")
            print(f"✅ Found ProductAgent call" if found_call_product else "❌ No ProductAgent call found")
            print(f"✅ Found observations" if found_observation else "❌ No observations found")
            
            # Show sample of reasoning
            if accumulated:
                print(f"\nSample reasoning (first 500 chars):")
                print("-" * 40)
                print(accumulated[:500] + "..." if len(accumulated) > 500 else accumulated)
                print("-" * 40)
                
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    print("\n🧪 Testing V2 Workflow Orchestrator Product Queries\n")
    
    # Test 1: Product query with V2 workflow
    test_v2_product_query()
    
    # Test 2: Reasoning visibility with Response API
    test_v2_reasoning_visibility()
    
    print("\n✅ V2 Workflow tests completed!\n")