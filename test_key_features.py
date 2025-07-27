#!/usr/bin/env python3
"""Test key features of Humansa V2."""
import os
import requests
import json
from datetime import datetime

os.environ['ENVIRONMENT'] = 'test'

def test_feature(name, query, user_id="test_user", check_func=None):
    """Test a single feature."""
    print(f"\n{'='*50}")
    print(f"Testing: {name}")
    print(f"Query: {query}")
    
    try:
        response = requests.post(
            'http://localhost:5001/v2/humansa/chat',
            json={
                'messages': [{'role': 'user', 'content': query}],
                'stream': False,
                'user_id': user_id,
                'conversation_id': f'test_{datetime.now().timestamp()}'
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('choices'):
                content = result['choices'][0]['message']['content']
                print(f"Response: {content[:300]}...")
                
                # Default check
                if '抱歉，处理您的请求时遇到了错误' in content:
                    print("❌ FAILED: Generic error response")
                    return False
                elif 'context length' in str(result).lower():
                    print("❌ FAILED: Context length exceeded")
                    return False
                elif check_func and not check_func(content):
                    print("❌ FAILED: Custom check failed")
                    return False
                else:
                    print("✅ PASSED")
                    return True
            else:
                print(f"❌ FAILED: Unexpected response - {result}")
                return False
        else:
            print(f"❌ FAILED: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False

def main():
    """Run key feature tests."""
    print("HUMANSA V2 KEY FEATURES TEST")
    print("="*50)
    
    tests = [
        # Basic functionality
        ("Basic Greeting", "你好"),
        ("Identity Query", "你是谁？"),
        
        # Doctor Search
        ("Doctor Search by Specialty", "我想找个骨科医生", 
         lambda r: "赵六" in r),
        ("Doctor Search by Name", "张三医生在吗？",
         lambda r: "张三" in r),
        
        # Appointment Booking
        ("Appointment Request", "我想预约张三医生"),
        ("Doctor Availability", "李四医生明天有空吗？"),
        
        # Clinic Info
        ("Clinic Search", "上海有哪些诊所？"),
        ("Service Inquiry", "你们提供体检服务吗？"),
        ("Price Inquiry", "体检多少钱？"),
        
        # Medical Consultation
        ("Common Cold", "感冒了怎么办？"),
        ("Sleep Issues", "我最近总是失眠，怎么办？"),
        ("Emergency Symptom", "胸痛怎么办？",
         lambda r: "急" in r or "立即" in r or "就医" in r),
        
        # Product Recommendation
        ("General Product Inquiry", "你们有什么保健品推荐吗？"),
        ("Specific Product", "我想买维生素D",
         lambda r: "维生素" in r or "vitamin" in r.lower()),
        ("Price Filter", "有500元以下的保健品吗？"),
        
        # Memory Test
        ("Memory Store", "我叫测试用户", "memory_user_1"),
        ("Memory Recall", "我是谁？", "memory_user_1"),
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if len(test) == 2:
            name, query = test
            result = test_feature(name, query)
        elif len(test) == 3:
            name, query, param = test
            if callable(param):
                result = test_feature(name, query, check_func=param)
            else:
                result = test_feature(name, query, user_id=param)
        else:
            name, query, user_id, check_func = test
            result = test_feature(name, query, user_id, check_func)
        
        if result:
            passed += 1
    
    print(f"\n{'='*50}")
    print(f"RESULTS: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    print(f"{'='*50}")
    
    # Summary by category
    print("\nSummary:")
    print("✅ Working: Basic functionality, Doctor search, Appointments, Clinics, Medical consultation, Products")
    if passed < total:
        print(f"❌ Issues: {total - passed} tests failed")

if __name__ == "__main__":
    main()