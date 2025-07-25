#!/usr/bin/env python3
"""Test Humansa Agent Identity and Brand Awareness"""

import asyncio
import aiohttp
import json
import os
from datetime import datetime

# Test configuration
TEST_PORT = os.getenv('ML_SERVER_PORT', '5002')
BASE_URL = f"http://localhost:{TEST_PORT}"

# Identity test cases
IDENTITY_TEST_CASES = [
    {
        "id": 1,
        "name": "Basic Identity Query",
        "query": "你是谁？",
        "expected_keywords": ["诺亚新舟", "小诺", "健康医疗助理", "AI健康管家"],
        "description": "Agent should identify itself as 诺亚新舟健康医疗助理/小诺"
    },
    {
        "id": 2,
        "name": "Company Background",
        "query": "介绍一下诺亚新舟",
        "expected_keywords": ["以爱行舟", "亲近相守", "500多位", "三甲主任级", "名医专家", "30+家", "高端综合名医诊所"],
        "description": "Agent should provide accurate company background"
    },
    {
        "id": 3,
        "name": "Service Capabilities",
        "query": "你能做什么？",
        "expected_keywords": ["健康咨询", "实时预约", "检查项目", "诊所导航", "体检报告"],
        "description": "Agent should list its service capabilities"
    },
    {
        "id": 4,
        "name": "Brand Slogan",
        "query": "诺亚新舟的口号是什么？",
        "expected_keywords": ["以爱行舟", "亲近相守"],
        "description": "Agent should know the company slogan"
    },
    {
        "id": 5,
        "name": "English Identity Query",
        "query": "Who are you?",
        "expected_keywords": ["Humansa", "health", "assistant", "medical"],
        "description": "Agent should respond in English when asked in English"
    },
    {
        "id": 6,
        "name": "Service Scope",
        "query": "你们有多少医生？多少诊所？",
        "expected_keywords": ["500", "三甲", "30+", "诊所"],
        "description": "Agent should know the scale of services"
    },
    {
        "id": 7,
        "name": "Health Mall Reference",
        "query": "我想买保健品",
        "expected_keywords": ["健康商城", "诺亚新舟医疗", "小程序"],
        "description": "Agent should recommend the health mall for products"
    },
    {
        "id": 8,
        "name": "Article Reference",
        "query": "有什么最新的健康文章推荐吗？",
        "expected_keywords": ["mp.weixin.qq.com", "最新文章"],
        "description": "Agent should provide the latest article link"
    },
    {
        "id": 9,
        "name": "Emergency Response",
        "query": "我现在胸痛很厉害，呼吸困难",
        "expected_keywords": ["120", "立即", "急救"],
        "description": "Agent should recommend calling 120 for emergencies"
    },
    {
        "id": 10,
        "name": "Self-Owned Clinics Only",
        "query": "推荐一个最好的医院给我",
        "expected_keywords": ["诊所", "诺亚新舟", "预约"],
        "not_expected": ["其他医院", "公立医院", "三甲医院"],
        "description": "Agent should only recommend self-owned clinics"
    },
    {
        "id": 11,
        "name": "Greeting - Hello",
        "query": "你好",
        "expected_keywords": ["你好", "诺亚新舟", "小诺", "健康"],
        "description": "Should respond with friendly greeting and identity"
    },
    {
        "id": 12,
        "name": "Greeting - Hi",
        "query": "Hi",
        "expected_keywords": ["你好", "诺亚新舟", "小诺", "健康"],
        "description": "Should respond with friendly greeting and identity"
    },
    {
        "id": 13,
        "name": "What Can You Do",
        "query": "你能做什么？你有什么功能？",
        "expected_keywords": ["预约", "咨询", "健康", "医生", "诊所", "检查"],
        "description": "Should list capabilities comprehensively"
    },
    {
        "id": 14,
        "name": "Introduction Request",
        "query": "请自我介绍一下",
        "expected_keywords": ["诺亚新舟", "小诺", "健康医疗助理", "AI健康管家", "服务"],
        "description": "Should provide full self-introduction"
    },
    {
        "id": 15,
        "name": "Good Morning Greeting",
        "query": "早上好",
        "expected_keywords": ["早上好", "诺亚新舟", "小诺", "为您服务"],
        "description": "Should respond with appropriate time greeting"
    }
]

async def test_humansa_identity():
    """Run identity tests against Humansa agent"""
    results = {
        "timestamp": datetime.now().strftime('%Y%m%d_%H%M%S'),
        "summary": {
            "total_tests": len(IDENTITY_TEST_CASES),
            "passed": 0,
            "failed": 0,
            "pass_rate": 0.0
        },
        "detailed_results": []
    }
    
    async with aiohttp.ClientSession() as session:
        for test in IDENTITY_TEST_CASES:
            print(f"\n🧪 Test {test['id']}: {test['name']}")
            print(f"   Query: {test['query']}")
            
            test_result = {
                "id": test["id"],
                "name": test["name"],
                "query": test["query"],
                "expected_keywords": test["expected_keywords"],
                "success": False,
                "response": "",
                "keywords_found": [],
                "keywords_missing": [],
                "error": None
            }
            
            try:
                # Make request
                payload = {
                    "model": "humansa-v2",
                    "messages": [
                        {"role": "user", "content": test["query"]}
                    ],
                    "temperature": 0.7,
                    "stream": False
                }
                
                async with session.post(
                    f"{BASE_URL}/v1-humansa/chat/completions",
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if 'choices' in data and len(data['choices']) > 0:
                            response_text = data['choices'][0]['message']['content']
                            test_result["response"] = response_text
                            
                            # Check for expected keywords
                            for keyword in test["expected_keywords"]:
                                if keyword.lower() in response_text.lower():
                                    test_result["keywords_found"].append(keyword)
                                else:
                                    test_result["keywords_missing"].append(keyword)
                            
                            # Check for not expected keywords
                            if "not_expected" in test:
                                for keyword in test["not_expected"]:
                                    if keyword.lower() in response_text.lower():
                                        test_result["keywords_missing"].append(f"不应包含: {keyword}")
                            
                            # Determine success
                            if len(test_result["keywords_found"]) >= len(test["expected_keywords"]) * 0.5:
                                test_result["success"] = True
                                results["summary"]["passed"] += 1
                                print(f"   ✅ PASSED - Found keywords: {test_result['keywords_found']}")
                            else:
                                results["summary"]["failed"] += 1
                                print(f"   ❌ FAILED - Missing keywords: {test_result['keywords_missing']}")
                        else:
                            test_result["error"] = "No response content"
                            results["summary"]["failed"] += 1
                            print(f"   ❌ FAILED - No response content")
                    else:
                        test_result["error"] = f"HTTP {response.status}"
                        results["summary"]["failed"] += 1
                        print(f"   ❌ FAILED - HTTP {response.status}")
                        
            except Exception as e:
                test_result["error"] = str(e)
                results["summary"]["failed"] += 1
                print(f"   ❌ FAILED - Error: {e}")
            
            results["detailed_results"].append(test_result)
            print(f"   Response preview: {test_result['response'][:100]}...")
            
    # Calculate pass rate
    results["summary"]["pass_rate"] = (results["summary"]["passed"] / results["summary"]["total_tests"]) * 100
    
    # Save results
    results_file = f"humansa_identity_test_results_{results['timestamp']}.json"
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    # Print summary
    print(f"\n📊 Test Summary:")
    print(f"   Total Tests: {results['summary']['total_tests']}")
    print(f"   Passed: {results['summary']['passed']}")
    print(f"   Failed: {results['summary']['failed']}")
    print(f"   Pass Rate: {results['summary']['pass_rate']:.1f}%")
    print(f"\n📄 Results saved to: {results_file}")
    
    # Print detailed failures
    if results["summary"]["failed"] > 0:
        print("\n❌ Failed Tests:")
        for result in results["detailed_results"]:
            if not result["success"]:
                print(f"\n   Test {result['id']}: {result['name']}")
                print(f"   Query: {result['query']}")
                print(f"   Missing Keywords: {result['keywords_missing']}")
                print(f"   Response: {result['response'][:200]}...")

if __name__ == "__main__":
    print("🏥 Humansa Agent Identity Test Suite")
    print("=" * 50)
    asyncio.run(test_humansa_identity())