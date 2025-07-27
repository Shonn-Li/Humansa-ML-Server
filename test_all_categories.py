#!/usr/bin/env python3
"""Test all categories of Humansa V2 functionality."""
import os
import sys
import asyncio
import aiohttp
import json
from datetime import datetime

# Set test environment
os.environ['ENVIRONMENT'] = 'test'

async def test_category(session, category_name, test_cases):
    """Test a category of functionality."""
    print(f"\n{'='*60}")
    print(f"TESTING: {category_name}")
    print(f"{'='*60}")
    
    results = []
    for test in test_cases:
        test_id = test.get('id', 'N/A')
        query = test['query']
        user_id = test.get('user_id', f'test_user_{test_id}')
        
        print(f"\nTest #{test_id}: {query}")
        
        request_data = {
            "messages": [{"role": "user", "content": query}],
            "stream": False,
            "user_id": user_id,
            "conversation_id": f"test_conv_{test_id}"
        }
        
        try:
            async with session.post(
                "http://localhost:5001/v2/humansa/chat",
                json=request_data,
                headers={'Content-Type': 'application/json'},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                result = await response.json()
                
                if result.get('choices'):
                    content = result['choices'][0]['message']['content']
                    print(f"Response: {content[:200]}...")
                    
                    # Check for errors
                    if '抱歉，处理您的请求时遇到了错误' in content:
                        print("❌ FAILED: Generic error response")
                        results.append(False)
                    else:
                        print("✅ PASSED")
                        results.append(True)
                else:
                    print(f"❌ FAILED: {result}")
                    results.append(False)
                    
        except asyncio.TimeoutError:
            print("❌ FAILED: Request timed out")
            results.append(False)
        except Exception as e:
            print(f"❌ FAILED: {e}")
            results.append(False)
    
    passed = sum(results)
    total = len(results)
    print(f"\n{category_name} Results: {passed}/{total} passed")
    return passed, total

async def main():
    """Run all category tests."""
    # Test categories
    categories = {
        "Identity & Introduction": [
            {"id": 1, "query": "你好"},
            {"id": 2, "query": "你是谁？"},
            {"id": 5, "query": "你能做什么？"}
        ],
        "Doctor Search": [
            {"id": 6, "query": "我想找个骨科医生"},
            {"id": 7, "query": "张三医生在吗？"},
            {"id": 8, "query": "北京有哪些医生？"}
        ],
        "Appointment Booking": [
            {"id": 10, "query": "我想预约张三医生"},
            {"id": 11, "query": "李四医生明天有空吗？"},
            {"id": 12, "query": "帮我预约下周三的儿科"}
        ],
        "Clinic/Service Info": [
            {"id": 14, "query": "上海有哪些诊所？"},
            {"id": 15, "query": "你们提供体检服务吗？"},
            {"id": 17, "query": "体检多少钱？"}
        ],
        "Medical Consultation": [
            {"id": 19, "query": "感冒了怎么办？"},
            {"id": 20, "query": "我最近总是失眠，怎么办？"},
            {"id": 21, "query": "我发烧了，38.5度"},
            {"id": 22, "query": "胸痛怎么办？"}
        ],
        "Product Recommendation": [
            {"id": 23, "query": "你们有什么保健品推荐吗？"},
            {"id": 24, "query": "我想买维生素D"},
            {"id": 25, "query": "有500元以下的保健品吗？"}
        ],
        "Memory Test": [
            {"id": 30, "query": "我叫王五", "user_id": "memory_test_user"},
            {"id": 31, "query": "我是谁？", "user_id": "memory_test_user"},
            {"id": 32, "query": "我之前告诉过你什么？", "user_id": "memory_test_user"}
        ]
    }
    
    async with aiohttp.ClientSession() as session:
        total_passed = 0
        total_tests = 0
        
        for category, tests in categories.items():
            passed, total = await test_category(session, category, tests)
            total_passed += passed
            total_tests += total
        
        print(f"\n{'='*60}")
        print(f"FINAL RESULTS: {total_passed}/{total_tests} tests passed")
        print(f"Success Rate: {(total_passed/total_tests*100):.1f}%")
        print(f"{'='*60}")

if __name__ == "__main__":
    print("HUMANSA V2 CATEGORY TEST SUITE")
    print("="*60)
    asyncio.run(main())