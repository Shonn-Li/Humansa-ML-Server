#!/usr/bin/env python3
"""
Minimal test using built-in libraries only
"""

import json
import urllib.request
import urllib.error
from datetime import datetime


def test_product_query():
    """Test product query"""
    base_url = "http://localhost:6001"
    
    query = "请推荐一些DHA产品"
    
    request_data = {
        "model": "gpt-4",
        "messages": [{"role": "user", "content": query}],
        "user_id": "test_user_fix",
        "stream": False,
        "temperature": 0.1
    }
    
    print(f"\n{'='*60}")
    print(f"Testing ReAct Product Query")
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
        
        with urllib.request.urlopen(req, timeout=60) as response:
            data = json.loads(response.read().decode('utf-8'))
            
            # Extract content
            content = ""
            if 'choices' in data:
                content = data['choices'][0]['message']['content']
            
            print("Response:")
            print("-" * 60)
            print(content)
            print("-" * 60)
            
            # Quick analysis
            print(f"\n{'='*60}")
            print("Analysis:")
            
            has_products = any(p in content for p in ['童年故事', '爱乐维', 'Swisse', 'DHA'])
            has_urls = 'youzan.com' in content or 'https://' in content
            has_specs = any(s in content for s in ['mg', '毫克', '粒'])
            
            print(f"✅ Has product names" if has_products else "❌ No product names")
            print(f"✅ Has URLs" if has_urls else "❌ No URLs")
            print(f"✅ Has specifications" if has_specs else "❌ No specifications")
            print(f"Length: {len(content)} chars")
            
            if has_products and has_urls:
                print("\n✅ SUCCESS: Product details included!")
            else:
                print("\n❌ FAILED: Missing product details")
            
            print(f"{'='*60}\n")
            
    except urllib.error.HTTPError as e:
        print(f"❌ HTTP Error {e.code}: {e.read().decode('utf-8')}")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    test_product_query()