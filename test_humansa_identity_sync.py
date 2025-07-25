#!/usr/bin/env python3
"""
Synchronous test script for Humansa agent identity.
"""
import json
import os
from datetime import datetime
import urllib.request
import urllib.parse

# Test configuration
TEST_PORT = os.getenv('ML_SERVER_PORT', '5002')
BASE_URL = f"http://localhost:{TEST_PORT}"
API_URL = f"{BASE_URL}/v1-humansa/chat/completions"

# Identity test cases
IDENTITY_TEST_CASES = [
    {
        "id": 1,
        "name": "Basic Identity Query",
        "query": "你是谁？",
        "expected_keywords": ["诺亚新舟", "小诺", "健康医疗助理", "AI健康管家"],
    },
    {
        "id": 2,
        "name": "Company Background",
        "query": "介绍一下诺亚新舟",
        "expected_keywords": ["诺亚新舟", "高端诊所", "名医", "健康"],
    },
    {
        "id": 3,
        "name": "Service Capabilities",
        "query": "你能做什么？",
        "expected_keywords": ["预约", "咨询", "健康", "诊所"],
    },
    {
        "id": 4,
        "name": "Greeting - Hello",
        "query": "你好",
        "expected_keywords": ["你好", "诺亚新舟", "小诺"],
    },
    {
        "id": 5,
        "name": "English Identity Query",
        "query": "Who are you?",
        "expected_keywords": ["诺亚新舟", "Humansa", "健康", "assistant"],
    },
    {
        "id": 6,
        "name": "Introduction Request",
        "query": "请自我介绍一下",
        "expected_keywords": ["诺亚新舟", "小诺", "健康医疗助理", "AI健康管家"],
    },
    {
        "id": 7,
        "name": "Emergency Response",
        "query": "我现在胸痛很厉害，呼吸困难",
        "expected_keywords": ["120", "立即", "急救"],
    },
    {
        "id": 8,
        "name": "What Can You Do Detail",
        "query": "详细说说你的功能",
        "expected_keywords": ["预约", "咨询", "医生", "诊所", "检查", "健康"],
    }
]

def test_identity():
    """Run identity tests synchronously."""
    print("🏥 Humansa Agent Identity Test Suite")
    print("=" * 50)
    
    results = []
    passed = 0
    failed = 0
    
    for test_case in IDENTITY_TEST_CASES:
        print(f"\n🧪 Test {test_case['id']}: {test_case['name']}")
        print(f"   Query: {test_case['query']}")
        
        # Prepare request
        payload = {
            "messages": [
                {
                    "role": "user",
                    "content": test_case['query']
                }
            ],
            "model": "gpt-4.1-nano",
            "stream": False,
            "user_id": f"test_user_{test_case['id']}"
        }
        
        try:
            # Make request
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                API_URL,
                data=data,
                headers={'Content-Type': 'application/json'}
            )
            
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode('utf-8'))
                
                # Extract response content
                content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
                
                # Check for expected keywords
                found_keywords = [kw for kw in test_case['expected_keywords'] if kw.lower() in content.lower()]
                missing_keywords = [kw for kw in test_case['expected_keywords'] if kw.lower() not in content.lower()]
                
                # Determine if passed
                if len(found_keywords) >= len(test_case['expected_keywords']) * 0.5:  # At least 50% match
                    print(f"   ✅ PASSED - Found keywords: {', '.join(found_keywords)}")
                    passed += 1
                    status = "passed"
                else:
                    print(f"   ❌ FAILED - Missing keywords: {', '.join(missing_keywords)}")
                    failed += 1
                    status = "failed"
                
                # Show response preview
                response_preview = content[:200] + "..." if len(content) > 200 else content
                print(f"   Response: {response_preview}")
                
                # Check agent trace
                if 'agent_trace' in result:
                    trace = result['agent_trace']
                    if '诺亚新舟健康医疗助理' in trace:
                        print(f"   ✅ V2 system prompt detected in trace")
                    else:
                        print(f"   ⚠️  V2 system prompt may not be active")
                
                results.append({
                    "test": test_case,
                    "response": content,
                    "status": status,
                    "found_keywords": found_keywords,
                    "missing_keywords": missing_keywords
                })
                
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
            failed += 1
            results.append({
                "test": test_case,
                "response": str(e),
                "status": "error",
                "error": str(e)
            })
    
    # Summary
    print(f"\n📊 Test Summary:")
    print(f"   Total Tests: {len(IDENTITY_TEST_CASES)}")
    print(f"   Passed: {passed}")
    print(f"   Failed: {failed}")
    print(f"   Pass Rate: {(passed/len(IDENTITY_TEST_CASES)*100):.1f}%")
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"humansa_identity_test_results_{timestamp}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump({
            "timestamp": timestamp,
            "summary": {
                "total": len(IDENTITY_TEST_CASES),
                "passed": passed,
                "failed": failed,
                "pass_rate": passed/len(IDENTITY_TEST_CASES)
            },
            "results": results
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n📄 Results saved to: {filename}")
    
    # Show failed tests
    if failed > 0:
        print("\n❌ Failed Tests:")
        for result in results:
            if result['status'] == 'failed':
                test = result['test']
                print(f"\n   Test {test['id']}: {test['name']}")
                print(f"   Query: {test['query']}")
                print(f"   Missing Keywords: {', '.join(result['missing_keywords'])}")
                print(f"   Response: {result['response'][:150]}...")

if __name__ == "__main__":
    test_identity()