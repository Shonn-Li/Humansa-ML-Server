#!/usr/bin/env python3
"""
Simple test to verify ReAct agent includes product details
"""

import json
import requests
from datetime import datetime


def test_product_query():
    """Test product query to ensure tool outputs are included"""
    base_url = "http://localhost:6001"
    headers = {"Content-Type": "application/json"}
    
    query = "请推荐一些DHA产品，包括具体的产品名称和购买链接"
    
    request_data = {
        "model": "gpt-4",
        "messages": [{"role": "user", "content": query}],
        "user_id": "test_user_product_fix",
        "stream": False,  # Non-streaming for simplicity
        "temperature": 0.1,
        "metadata": {
            "source": "test_react_fix",
            "test_type": "product_detail_inclusion"
        }
    }
    
    print(f"\n{'='*60}")
    print(f"Testing ReAct Product Query Fix")
    print(f"{'='*60}")
    print(f"Query: {query}")
    print(f"Time: {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*60}\n")
    
    # Make request
    print("Sending request to HUMANSA V2...\n")
    
    try:
        response = requests.post(
            f"{base_url}/v1-humansa/chat/completions",
            json=request_data,
            headers=headers,
            timeout=60
        )
        
        if response.status_code != 200:
            print(f"❌ Error: HTTP {response.status_code}")
            print(response.text)
            return
        
        data = response.json()
        
        # Extract content
        content = ""
        if 'choices' in data:
            content = data['choices'][0]['message']['content']
        elif 'response' in data:
            content = data['response']
        
        print("Response:")
        print("-" * 60)
        print(content)
        print("-" * 60)
        
        # Analyze response
        print(f"\n{'='*60}")
        print("Test Results:")
        print(f"{'='*60}")
        
        success = True
        issues = []
        
        # Check for specific product names
        product_names = ['童年故事', '爱乐维', 'Swisse', 'DHA', '藻油']
        found_products = [p for p in product_names if p in content]
        
        if not found_products:
            success = False
            issues.append("❌ No specific product names found")
        else:
            print(f"✅ Found product names: {', '.join(found_products)}")
        
        # Check for URLs
        if 'youzan.com' in content or 'https://' in content:
            print("✅ Found product URLs")
        else:
            success = False
            issues.append("❌ No product URLs found")
        
        # Check for dosage/specs
        if any(keyword in content for keyword in ['mg', '毫克', '粒', '瓶', '规格']):
            print("✅ Found product specifications")
        else:
            issues.append("⚠️  No product specifications found")
        
        # Check for generic patterns
        generic_patterns = [
            "建议您咨询",
            "可以考虑",
            "一般来说",
            "通常包括"
        ]
        
        has_generic = any(pattern in content for pattern in generic_patterns)
        
        if has_generic and not found_products:
            success = False
            issues.append("❌ Response is too generic")
        elif not has_generic:
            print("✅ Response is specific")
        
        # Check length
        if len(content) < 200:
            success = False
            issues.append(f"❌ Response too short ({len(content)} chars)")
        else:
            print(f"✅ Response length: {len(content)} chars")
        
        print(f"\n{'='*60}")
        if success:
            print("✅ TEST PASSED: ReAct agent includes product details!")
        else:
            print("❌ TEST FAILED:")
            for issue in issues:
                print(f"  {issue}")
        print(f"{'='*60}\n")
        
    except Exception as e:
        print(f"❌ Error: {e}")


def test_reasoning_steps():
    """Test streaming to see reasoning steps"""
    base_url = "http://localhost:6001"
    headers = {"Content-Type": "application/json"}
    
    query = "我想买儿童DHA"
    
    request_data = {
        "model": "gpt-4",
        "messages": [{"role": "user", "content": query}],
        "user_id": "test_reasoning",
        "stream": True,
        "temperature": 0.1,
        "debug": True
    }
    
    print(f"\n{'='*60}")
    print(f"Testing Reasoning Steps (Streaming)")
    print(f"{'='*60}")
    print(f"Query: {query}")
    print(f"{'='*60}\n")
    
    try:
        response = requests.post(
            f"{base_url}/v1-humansa/chat/completions",
            json=request_data,
            headers=headers,
            stream=True,
            timeout=60
        )
        
        found_thinking = False
        found_action = False
        accumulated = ""
        
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith('data: '):
                    data_str = line[6:]
                    if data_str == '[DONE]':
                        break
                    
                    try:
                        data = json.loads(data_str)
                        content = ""
                        
                        if 'choices' in data:
                            content = data['choices'][0].get('delta', {}).get('content', '')
                        elif 'type' in data and data['type'] == 'response.output_text.delta':
                            content = data.get('text', '')
                        
                        if content:
                            accumulated += content
                            if 'Thought:' in content or '思考' in content:
                                found_thinking = True
                            if 'Action:' in content or 'call_' in content:
                                found_action = True
                                
                    except json.JSONDecodeError:
                        continue
        
        print("\nFull response:")
        print("-" * 60)
        print(accumulated[:1000] + "..." if len(accumulated) > 1000 else accumulated)
        print("-" * 60)
        
        print(f"\n{'='*60}")
        print("Reasoning Visibility:")
        print(f"✅ Found thinking" if found_thinking else "❌ No thinking found")
        print(f"✅ Found actions" if found_action else "❌ No actions found")
        print(f"{'='*60}\n")
        
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    print("\n🧪 Testing ReAct Agent Fixes\n")
    
    # Test 1: Non-streaming product query
    test_product_query()
    
    # Test 2: Streaming to see reasoning
    test_reasoning_steps()
    
    print("\n✅ Tests completed!\n")