#!/usr/bin/env python3
"""
Key improvements test suite - Focused on critical functionality
"""

import asyncio
import aiohttp
import json
from datetime import datetime
import time

# Configuration
BASE_URL = "http://localhost:6001"
TEST_USER_ID = "test_improvements_key"

# Critical test cases grouped by category
KEY_TEST_CASES = {
    "Identity & Branding (Critical)": [
        {
            "query": "你是谁？",
            "expected": ["诺亚新舟", "小诺", "健康医疗助理"],
            "critical": True
        },
        {
            "query": "什么是HUMANSA？",
            "expected": ["诺亚新舟", "Humansa", "以爱行舟"],
            "critical": True
        },
        {
            "query": "介绍一下诺亚新舟",
            "expected": ["以爱行舟", "亲近相守", "500多位", "30+家"],
            "critical": True
        }
    ],
    "Emergency Response": [
        {
            "query": "我现在胸痛很厉害，呼吸困难",
            "expected": ["120", "立即", "急救"],
            "critical": True
        },
        {
            "query": "我头很晕，感觉要晕倒了",
            "expected": ["120", "紧急", "就医"],
            "critical": True
        }
    ],
    "Service Integration": [
        {
            "query": "我想买保健品",
            "expected": ["健康商城", "小程序"],
            "critical": False
        },
        {
            "query": "深圳有哪些诊所？",
            "expected": ["诊所"],
            "critical": False
        }
    ],
    "Memory System": [
        {
            "query": "我对青霉素过敏",
            "expected": ["记录", "过敏"],
            "critical": False
        },
        {
            "query": "我上次说的过敏药物是什么？",
            "expected": ["青霉素", "过敏"],
            "critical": False
        }
    ],
    "Doctor & Appointment": [
        {
            "query": "我想找个心脏科医生",
            "expected": ["心", "医生"],
            "critical": False
        },
        {
            "query": "帮我预约明天的医生",
            "expected": ["预约", "时间"],
            "critical": False
        }
    ]
}


async def test_query(session, query, timeout=15):
    """Test a single query with timeout"""
    url = f"{BASE_URL}/v2/humansa/responses/create"
    
    payload = {
        "model": "gpt-4-turbo",
        "input": query,
        "user_id": TEST_USER_ID,
        "stream": False
    }
    
    try:
        start_time = time.time()
        async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=timeout)) as response:
            elapsed = time.time() - start_time
            
            if response.status == 200:
                result = await response.json()
                
                # Extract text from output
                text = ""
                for item in result.get("output", []):
                    if item.get("type") == "text":
                        text = item.get("text", "")
                        break
                
                # Check metadata
                metadata = result.get("metadata", {})
                
                return {
                    "success": True,
                    "response": text,
                    "response_time": elapsed,
                    "response_agent_processed": metadata.get("response_agent_processed", False),
                    "response_type": metadata.get("response_type", "unknown"),
                    "response_id": result.get("id")
                }
            else:
                error_text = await response.text()
                return {
                    "success": False,
                    "error": f"HTTP {response.status}: {error_text[:100]}",
                    "response_time": elapsed
                }
    except asyncio.TimeoutError:
        return {
            "success": False,
            "error": f"Timeout after {timeout}s",
            "response_time": timeout
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "response_time": 0
        }


async def run_key_tests():
    """Run key improvement tests"""
    print("\n" + "="*80)
    print("  HUMANSA V2 KEY IMPROVEMENTS TEST")
    print("  " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("="*80 + "\n")
    
    # Check server health
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{BASE_URL}/v2/humansa/health") as response:
                if response.status == 200:
                    health = await response.json()
                    print("✅ Server Status: Healthy")
                    print(f"   Components: {health.get('components', {})}")
                    print()
                else:
                    print("❌ Server not healthy")
                    return
        except Exception as e:
            print(f"❌ Cannot connect to server: {e}")
            return
    
    # Run tests
    results = {}
    total_tests = 0
    total_passed = 0
    critical_passed = 0
    critical_total = 0
    
    async with aiohttp.ClientSession() as session:
        for category, tests in KEY_TEST_CASES.items():
            print(f"\n📋 {category}")
            print("-" * 60)
            
            category_results = []
            
            for test in tests:
                total_tests += 1
                if test.get("critical"):
                    critical_total += 1
                
                # Run test
                result = await test_query(session, test["query"])
                
                if result["success"]:
                    # Check expected keywords
                    found = [kw for kw in test["expected"] if kw in result["response"]]
                    passed = len(found) == len(test["expected"])
                    
                    if passed:
                        print(f"  ✅ {test['query'][:30]}...")
                        if result["response_agent_processed"]:
                            print(f"     🤖 Type: {result['response_type']}")
                        print(f"     ⏱️  {result['response_time']:.1f}s")
                        total_passed += 1
                        if test.get("critical"):
                            critical_passed += 1
                    else:
                        print(f"  ❌ {test['query'][:30]}...")
                        print(f"     Missing: {[kw for kw in test['expected'] if kw not in result['response']]}")
                        print(f"     Response: {result['response'][:80]}...")
                else:
                    print(f"  ❌ {test['query'][:30]}...")
                    print(f"     Error: {result['error']}")
                
                category_results.append({
                    "query": test["query"],
                    "passed": passed if result["success"] else False,
                    "critical": test.get("critical", False),
                    "result": result
                })
                
                # Small delay
                await asyncio.sleep(0.5)
            
            results[category] = category_results
    
    # Print summary
    print("\n" + "="*80)
    print("  SUMMARY")
    print("="*80)
    
    # Category breakdown
    print("\n📊 Results by Category:")
    for category, tests in results.items():
        passed = sum(1 for t in tests if t["passed"])
        total = len(tests)
        percentage = (passed / total * 100) if total > 0 else 0
        print(f"  {'✅' if percentage == 100 else '⚠️' if percentage >= 50 else '❌'} {category}: {passed}/{total} ({percentage:.0f}%)")
    
    # Overall scores
    print(f"\n🎯 Overall Score: {total_passed}/{total_tests} ({total_passed/total_tests*100:.0f}%)")
    print(f"🔴 Critical Tests: {critical_passed}/{critical_total} ({critical_passed/critical_total*100:.0f}%)")
    
    # Key findings
    print("\n🔍 Key Findings:")
    
    # Identity tests
    identity_tests = results.get("Identity & Branding (Critical)", [])
    identity_passed = sum(1 for t in identity_tests if t["passed"])
    print(f"  • Identity Recognition: {identity_passed}/{len(identity_tests)} tests passed")
    
    # Emergency tests
    emergency_tests = results.get("Emergency Response", [])
    emergency_passed = sum(1 for t in emergency_tests if t["passed"])
    print(f"  • Emergency Handling: {emergency_passed}/{len(emergency_tests)} tests passed")
    
    # Response Agent effectiveness
    agent_processed = sum(1 for cat_tests in results.values() for t in cat_tests 
                         if t["result"].get("success") and 
                         t["result"].get("response_agent_processed"))
    print(f"  • Response Agent Processing: {agent_processed}/{total_tests} responses")
    
    # Average response time
    response_times = [t["result"]["response_time"] for cat_tests in results.values() 
                     for t in cat_tests if t["result"].get("success")]
    avg_time = sum(response_times) / len(response_times) if response_times else 0
    print(f"  • Average Response Time: {avg_time:.1f}s")
    
    # Final verdict
    print("\n" + "="*80)
    if critical_passed == critical_total:
        print("🎉 ALL CRITICAL TESTS PASSED! Response Agent working excellently!")
    elif critical_passed / critical_total >= 0.7:
        print("✅ GOOD PROGRESS! Most critical tests passing.")
    else:
        print("⚠️  NEEDS ATTENTION: Critical tests failing.")
    print("="*80 + "\n")
    
    return {
        "total_passed": total_passed,
        "total_tests": total_tests,
        "critical_passed": critical_passed,
        "critical_total": critical_total,
        "results": results
    }


if __name__ == "__main__":
    asyncio.run(run_key_tests())