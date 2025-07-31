#!/usr/bin/env python3
"""
Test script to verify Response Agent fixes for HUMANSA V2
Tests identity enforcement, error handling, and brand consistency
"""

import asyncio
import aiohttp
import json
import sys
from typing import Dict, Any

# Test configuration
BASE_URL = "http://localhost:6001"
TEST_USER_ID = "test_response_agent_001"

# Test cases
TEST_CASES = [
    {
        "id": 1,
        "name": "Identity Query - Chinese",
        "input": "你是谁？",
        "expected_keywords": ["诺亚新舟", "小诺", "健康医疗助理", "AI健康管家"]
    },
    {
        "id": 2,
        "name": "Greeting",
        "input": "你好",
        "expected_keywords": ["诺亚新舟", "小诺", "有什么可以帮助您"]
    },
    {
        "id": 3,
        "name": "Company Info",
        "input": "介绍一下诺亚新舟",
        "expected_keywords": ["以爱行舟", "亲近相守", "500多位", "30+家"]
    },
    {
        "id": 4,
        "name": "Service Capabilities",
        "input": "你能做什么？",
        "expected_keywords": ["健康咨询", "实时预约", "检查项目", "诊所导航"]
    },
    {
        "id": 5,
        "name": "Emergency",
        "input": "我现在胸痛很厉害，呼吸困难",
        "expected_keywords": ["120", "立即", "急救"]
    },
    {
        "id": 6,
        "name": "Product Query",
        "input": "我想买保健品",
        "expected_keywords": ["健康商城", "小程序", "诺亚新舟医疗"]
    },
    {
        "id": 7,
        "name": "Doctor Search",
        "input": "我想找一个心脏科医生",
        "expected_keywords": ["医生", "心", "预约"]
    },
    {
        "id": 8,
        "name": "Clinic Search",
        "input": "深圳有哪些诊所？",
        "expected_keywords": ["诊所", "诺亚新舟"]
    }
]


async def test_response_api(session: aiohttp.ClientSession, test_case: Dict[str, Any]) -> Dict[str, Any]:
    """Test a single query using the Responses API"""
    
    url = f"{BASE_URL}/v2/humansa/responses/create"
    
    payload = {
        "model": "gpt-4-turbo",
        "input": test_case["input"],
        "user_id": TEST_USER_ID,
        "metadata": {
            "test_case_id": test_case["id"],
            "test_name": test_case["name"]
        }
    }
    
    try:
        async with session.post(url, json=payload) as response:
            if response.status == 200:
                result = await response.json()
                
                # Extract final text from output array
                final_text = ""
                output_array = result.get("output", [])
                for item in reversed(output_array):
                    if item.get("type") == "text":
                        final_text = item.get("text", "")
                        break
                
                # Check for expected keywords
                found_keywords = []
                missing_keywords = []
                
                for keyword in test_case["expected_keywords"]:
                    if keyword in final_text:
                        found_keywords.append(keyword)
                    else:
                        missing_keywords.append(keyword)
                
                # Check metadata for processing
                metadata = result.get("metadata", {})
                response_agent_processed = metadata.get("response_agent_processed", False)
                response_type = metadata.get("response_type", "unknown")
                
                return {
                    "test_id": test_case["id"],
                    "test_name": test_case["name"],
                    "passed": len(missing_keywords) == 0,
                    "response": final_text,
                    "found_keywords": found_keywords,
                    "missing_keywords": missing_keywords,
                    "response_agent_processed": response_agent_processed,
                    "response_type": response_type,
                    "response_id": result.get("id")
                }
            else:
                return {
                    "test_id": test_case["id"],
                    "test_name": test_case["name"],
                    "passed": False,
                    "error": f"HTTP {response.status}",
                    "response": await response.text()
                }
                
    except Exception as e:
        return {
            "test_id": test_case["id"],
            "test_name": test_case["name"],
            "passed": False,
            "error": str(e)
        }


async def run_tests():
    """Run all test cases"""
    print("\n" + "="*80)
    print("  HUMANSA V2 Response Agent Test Suite")
    print("="*80 + "\n")
    
    # Check if server is running
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BASE_URL}/v2/humansa/health") as response:
                if response.status != 200:
                    print(f"❌ Server not responding at {BASE_URL}")
                    return
                print(f"✅ Server is running at {BASE_URL}\n")
    except:
        print(f"❌ Cannot connect to server at {BASE_URL}")
        print("Please ensure the server is running: python -m src.main")
        return
    
    # Run tests
    passed = 0
    failed = 0
    
    async with aiohttp.ClientSession() as session:
        for test_case in TEST_CASES:
            print(f"\n📋 Test {test_case['id']}: {test_case['name']}")
            print(f"   Query: {test_case['input']}")
            
            result = await run_tests_with_result(session, test_case)
            
            if result["passed"]:
                print(f"   ✅ PASSED")
                if result.get("response_agent_processed"):
                    print(f"   🤖 Response Agent: Processed as '{result.get('response_type')}'")
                print(f"   Found keywords: {', '.join(result['found_keywords'])}")
                passed += 1
            else:
                print(f"   ❌ FAILED")
                if result.get("error"):
                    print(f"   Error: {result['error']}")
                else:
                    print(f"   Missing keywords: {', '.join(result.get('missing_keywords', []))}")
                    if result.get("response"):
                        print(f"   Response preview: {result['response'][:100]}...")
                failed += 1
            
            # Small delay between tests
            await asyncio.sleep(0.5)
    
    # Summary
    print("\n" + "="*80)
    print("  TEST SUMMARY")
    print("="*80)
    print(f"\nTotal: {len(TEST_CASES)} tests")
    print(f"✅ Passed: {passed} ({passed/len(TEST_CASES)*100:.1f}%)")
    print(f"❌ Failed: {failed} ({failed/len(TEST_CASES)*100:.1f}%)")
    
    if failed == 0:
        print("\n🎉 All tests passed! Response Agent is working correctly.")
    else:
        print("\n⚠️  Some tests failed. Please check the Response Agent implementation.")
    
    return passed == len(TEST_CASES)


async def run_tests_with_result(session: aiohttp.ClientSession, test_case: Dict[str, Any]) -> Dict[str, Any]:
    """Run a single test and return result"""
    return await test_response_api(session, test_case)


if __name__ == "__main__":
    # Run the tests
    success = asyncio.run(run_tests())
    sys.exit(0 if success else 1)