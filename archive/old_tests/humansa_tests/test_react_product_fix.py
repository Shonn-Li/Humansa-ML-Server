#!/usr/bin/env python3
"""
Test script to verify ReAct agent properly includes product details in final answers
"""

import asyncio
import json
import aiohttp
from datetime import datetime


async def test_product_query():
    """Test product query to ensure tool outputs are included in final answer"""
    base_url = "http://localhost:6001"
    headers = {"Content-Type": "application/json"}
    
    # Test product query
    query = "请推荐一些DHA产品，包括具体的产品名称和购买链接"
    
    request_data = {
        "model": "gpt-4",
        "messages": [{"role": "user", "content": query}],
        "user_id": "test_user_product_fix",
        "stream": True,
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
    
    # Make streaming request
    async with httpx.AsyncClient(timeout=60.0) as client:
        print("Sending request to HUMANSA V2...\n")
        
        accumulated_content = ""
        found_product_details = False
        found_urls = False
        
        async with client.stream('POST', f"{base_url}/v1-humansa/chat/completions", 
                               json=request_data, headers=headers) as response:
            
            async for line in response.aiter_lines():
                if line.strip() and line.startswith('data: '):
                    data_str = line[6:]  # Remove 'data: ' prefix
                    
                    if data_str == '[DONE]':
                        break
                    
                    try:
                        data = json.loads(data_str)
                        
                        # Handle streaming format
                        if 'choices' in data:
                            choice = data['choices'][0]
                            if 'delta' in choice:
                                content = choice['delta'].get('content', '')
                                if content:
                                    print(content, end='', flush=True)
                                    accumulated_content += content
                                    
                                    # Check for product details
                                    if any(keyword in content for keyword in ['童年故事', '爱乐维', 'Swisse', '产品名称']):
                                        found_product_details = True
                                    
                                    # Check for URLs
                                    if 'youzan.com' in content or '购买链接' in content:
                                        found_urls = True
                        
                        # Handle response API format
                        elif 'type' in data:
                            if data['type'] == 'response.output_text.delta':
                                content = data.get('text', '')
                                if content:
                                    print(content, end='', flush=True)
                                    accumulated_content += content
                                    
                                    # Check for product details
                                    if any(keyword in content for keyword in ['童年故事', '爱乐维', 'Swisse', '产品名称']):
                                        found_product_details = True
                                    
                                    # Check for URLs
                                    if 'youzan.com' in content or '购买链接' in content:
                                        found_urls = True
                            
                            elif data['type'] == 'response.output_text.done':
                                final_text = data.get('text', '')
                                if final_text and not accumulated_content:
                                    print(final_text)
                                    accumulated_content = final_text
                    
                    except json.JSONDecodeError:
                        continue
    
    print(f"\n\n{'='*60}")
    print("Test Results:")
    print(f"{'='*60}")
    
    # Analyze response
    success = True
    issues = []
    
    if not found_product_details:
        success = False
        issues.append("❌ No specific product names found in response")
    else:
        print("✅ Found specific product names")
    
    if not found_urls:
        success = False
        issues.append("❌ No product URLs found in response")
    else:
        print("✅ Found product URLs")
    
    # Check for generic advice patterns
    generic_patterns = [
        "建议您咨询",
        "可以考虑",
        "一般来说",
        "通常包括",
        "请根据自身需求"
    ]
    
    has_generic = any(pattern in accumulated_content for pattern in generic_patterns)
    
    if has_generic and not found_product_details:
        success = False
        issues.append("❌ Response contains only generic advice without specific products")
    elif not has_generic:
        print("✅ Response is specific, not generic")
    
    # Check response length
    if len(accumulated_content) < 200:
        success = False
        issues.append(f"❌ Response too short ({len(accumulated_content)} chars)")
    else:
        print(f"✅ Response length adequate ({len(accumulated_content)} chars)")
    
    print(f"\n{'='*60}")
    if success:
        print("✅ TEST PASSED: ReAct agent correctly includes product details!")
    else:
        print("❌ TEST FAILED: Issues found:")
        for issue in issues:
            print(f"  {issue}")
    print(f"{'='*60}\n")
    
    # Show a sample of the response for debugging
    print("Sample of response content:")
    print("-" * 40)
    print(accumulated_content[:500] + "..." if len(accumulated_content) > 500 else accumulated_content)
    print("-" * 40)


async def test_reasoning_visibility():
    """Test that reasoning steps are visible in enhanced mode"""
    base_url = "http://localhost:6001"
    headers = {"Content-Type": "application/json"}
    
    query = "我想买一些儿童DHA，有什么推荐吗？"
    
    request_data = {
        "model": "gpt-4",
        "messages": [{"role": "user", "content": query}],
        "user_id": "test_user_reasoning",
        "stream": True,
        "temperature": 0.1,
        "debug": True,  # Enable debug mode
        "metadata": {
            "source": "test_reasoning_visibility"
        }
    }
    
    print(f"\n{'='*60}")
    print(f"Testing Reasoning Visibility")
    print(f"{'='*60}")
    print(f"Query: {query}")
    print(f"Debug mode: ON")
    print(f"{'='*60}\n")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        found_thinking = False
        found_action = False
        found_observation = False
        
        async with client.stream('POST', f"{base_url}/v1-humansa/chat/completions", 
                               json=request_data, headers=headers) as response:
            
            async for line in response.aiter_lines():
                if line.strip() and line.startswith('data: '):
                    data_str = line[6:]
                    
                    if data_str == '[DONE]':
                        break
                    
                    try:
                        data = json.loads(data_str)
                        
                        # Check for reasoning steps
                        content = ""
                        if 'choices' in data:
                            content = data['choices'][0].get('delta', {}).get('content', '')
                        elif 'type' in data and 'text' in data:
                            content = data.get('text', '')
                        
                        if content:
                            if 'Thought:' in content or '思考:' in content:
                                found_thinking = True
                            if 'Action:' in content or '行动:' in content:
                                found_action = True
                            if 'Observation:' in content or '观察:' in content:
                                found_observation = True
                    
                    except json.JSONDecodeError:
                        continue
    
    print(f"\n{'='*60}")
    print("Reasoning Visibility Results:")
    print(f"{'='*60}")
    print(f"✅ Found thinking steps" if found_thinking else "❌ No thinking steps found")
    print(f"✅ Found action steps" if found_action else "❌ No action steps found")
    print(f"✅ Found observation steps" if found_observation else "❌ No observation steps found")
    print(f"{'='*60}\n")


async def main():
    """Run all tests"""
    print("\n🧪 Testing ReAct Agent Fixes for Product Queries\n")
    
    # Test 1: Product query with details
    await test_product_query()
    
    # Test 2: Reasoning visibility
    await test_reasoning_visibility()
    
    print("\n✅ All tests completed!\n")


if __name__ == "__main__":
    asyncio.run(main())