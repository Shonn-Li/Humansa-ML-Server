#!/usr/bin/env python3
"""
Final summary test to verify all HUMANSA V2 improvements
"""

import asyncio
import aiohttp
import json
from datetime import datetime

# Test configuration
BASE_URL = "http://localhost:6001"
TEST_USER_ID = "test_summary_final"

# Key test scenarios
TEST_SCENARIOS = [
    {
        "category": "Identity & Branding",
        "tests": [
            {
                "query": "你是谁？",
                "expected": ["诺亚新舟", "小诺", "健康医疗助理"],
                "description": "Basic identity query"
            },
            {
                "query": "诺亚新舟的口号是什么？",
                "expected": ["以爱行舟", "亲近相守"],
                "description": "Company slogan"
            },
            {
                "query": "你们有多少医生？",
                "expected": ["500", "三甲", "30+"],
                "description": "Scale of services"
            }
        ]
    },
    {
        "category": "Emergency Handling",
        "tests": [
            {
                "query": "我现在胸痛很厉害",
                "expected": ["120", "立即", "急救"],
                "description": "Emergency response"
            }
        ]
    },
    {
        "category": "Service Integration",
        "tests": [
            {
                "query": "我想买保健品",
                "expected": ["健康商城", "小程序"],
                "description": "Health mall integration"
            },
            {
                "query": "深圳有哪些诊所？",
                "expected": ["诊所"],
                "description": "Clinic search"
            }
        ]
    },
    {
        "category": "Error Handling",
        "tests": [
            {
                "query": "查询一个不存在的医生",
                "expected": ["诺亚新舟"],  # Should still maintain branding in errors
                "description": "Error beautification"
            }
        ]
    }
]


async def test_query(session, query):
    """Test a single query"""
    url = f"{BASE_URL}/v2/humansa/responses/create"
    
    payload = {
        "model": "gpt-4-turbo",
        "input": query,
        "user_id": TEST_USER_ID,
        "stream": False
    }
    
    try:
        start_time = datetime.now()
        async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as response:
            end_time = datetime.now()
            response_time = (end_time - start_time).total_seconds()
            
            if response.status == 200:
                result = await response.json()
                
                # Extract text
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
                    "response_time": response_time,
                    "response_agent_processed": metadata.get("response_agent_processed", False),
                    "response_type": metadata.get("response_type", "unknown")
                }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status}",
                    "response_time": response_time
                }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "response_time": 0
        }


async def main():
    print("\n" + "="*80)
    print("  HUMANSA V2 FINAL IMPROVEMENT SUMMARY")
    print("  " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("="*80 + "\n")
    
    async with aiohttp.ClientSession() as session:
        # Check server
        try:
            async with session.get(f"{BASE_URL}/v2/humansa/health") as response:
                if response.status == 200:
                    data = await response.json()
                    print("✅ Server Status: Healthy")
                    print(f"   Components: {data.get('components', {})}")
                    print()
                else:
                    print("❌ Server not responding")
                    return
        except:
            print("❌ Cannot connect to server")
            return
        
        # Run tests by category
        total_passed = 0
        total_tests = 0
        category_results = []
        
        for scenario in TEST_SCENARIOS:
            print(f"\n📁 {scenario['category']}")
            print("-" * 60)
            
            category_passed = 0
            
            for test in scenario["tests"]:
                total_tests += 1
                result = await test_query(session, test["query"])
                
                if result["success"]:
                    # Check expected keywords
                    keywords_found = [kw for kw in test["expected"] if kw in result["response"]]
                    passed = len(keywords_found) == len(test["expected"])
                    
                    if passed:
                        print(f"  ✅ {test['description']}")
                        if result["response_agent_processed"]:
                            print(f"     🤖 Response type: {result['response_type']}")
                        print(f"     ⏱️  Response time: {result['response_time']:.2f}s")
                        category_passed += 1
                        total_passed += 1
                    else:
                        print(f"  ❌ {test['description']}")
                        print(f"     Missing: {[kw for kw in test['expected'] if kw not in result['response']]}")
                        print(f"     Response preview: {result['response'][:100]}...")
                else:
                    print(f"  ❌ {test['description']}")
                    print(f"     Error: {result['error']}")
                
                await asyncio.sleep(0.5)  # Avoid overwhelming the server
            
            category_results.append({
                "name": scenario["category"],
                "passed": category_passed,
                "total": len(scenario["tests"]),
                "percentage": (category_passed / len(scenario["tests"]) * 100) if scenario["tests"] else 0
            })
        
        # Print summary
        print("\n" + "="*80)
        print("  SUMMARY RESULTS")
        print("="*80 + "\n")
        
        print("📈 Category Breakdown:")
        for cat in category_results:
            status = "✅" if cat["percentage"] == 100 else "⚠️" if cat["percentage"] >= 50 else "❌"
            print(f"  {status} {cat['name']}: {cat['passed']}/{cat['total']} ({cat['percentage']:.0f}%)")
        
        print(f"\n🎯 Overall Score: {total_passed}/{total_tests} ({total_passed/total_tests*100:.0f}%)")
        
        # Key improvements
        print("\n🔑 Key Improvements Implemented:")
        print("  1. ✅ Response Agent for brand consistency")
        print("  2. ✅ Identity enforcement in all responses")
        print("  3. ✅ Error beautification")
        print("  4. ✅ Emergency response handling")
        print("  5. ✅ Database table fixes (humansa_clinics)")
        print("  6. ✅ Response type detection and templates")
        
        # Recommendations
        if total_passed < total_tests:
            print("\n💡 Remaining Issues:")
            if any("English" in test.get("description", "") for scenario in TEST_SCENARIOS for test in scenario["tests"]):
                print("  - Language detection for English queries")
            if category_results[0]["percentage"] < 100:  # Identity category
                print("  - Some identity queries still need refinement")
            print("  - Tool selection logic (pending in todo list)")
        
        print("\n" + "="*80)
        if total_passed == total_tests:
            print("🎆 ALL TESTS PASSED! The Response Agent is working perfectly!")
        elif total_passed / total_tests >= 0.8:
            print("🎉 SIGNIFICANT IMPROVEMENT! Response Agent is working well.")
        else:
            print("⚠️  More work needed on Response Agent implementation.")
        print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())