#!/usr/bin/env python3
"""Humansa V2 - 30 Comprehensive Test Cases Implementation"""

import asyncio
import aiohttp
import json
import os
from datetime import datetime
import time
import sys

# Test configuration
TEST_PORT = os.getenv('ML_SERVER_PORT', '6001')
BASE_URL = f"http://localhost:{TEST_PORT}"

# Colors for output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_colored(text, color=Colors.ENDC):
    """Print text with color"""
    print(f"{color}{text}{Colors.ENDC}")

def print_section(title):
    """Print a section header"""
    print_colored(f"\n{'='*80}", Colors.BLUE)
    print_colored(f"  {title}", Colors.BOLD + Colors.BLUE)
    print_colored(f"{'='*80}", Colors.BLUE)

# Define all 30 test cases
TEST_CASES = [
    # Category 1: Identity & Basic Interactions
    {
        "id": 1,
        "category": "Identity",
        "name": "Chinese Identity Query",
        "query": "你是谁？",
        "expected_keywords": ["诺亚新舟", "小诺", "健康医疗助理"],
        "user_id": 123
    },
    {
        "id": 2,
        "category": "Identity",
        "name": "English Identity Query",
        "query": "Who are you?",
        "expected_keywords": ["Humansa", "Health", "Medical", "Assistant"],
        "user_id": 123
    },
    {
        "id": 3,
        "category": "Identity",
        "name": "Chinese Greeting",
        "query": "你好",
        "expected_keywords": ["你好", "小诺", "帮助"],
        "user_id": 123
    },
    {
        "id": 4,
        "category": "Identity",
        "name": "Company Introduction",
        "query": "介绍一下诺亚新舟",
        "expected_keywords": ["以爱行舟", "亲近相守", "500多位", "30+家"],
        "user_id": 123
    },
    {
        "id": 5,
        "category": "Identity",
        "name": "Service Capabilities",
        "query": "你能做什么？",
        "expected_keywords": ["健康咨询", "实时预约", "检查项目", "诊所导航", "体检报告"],
        "user_id": 123
    },
    
    # Category 2: Doctor Search & Information
    {
        "id": 6,
        "category": "Doctor Search",
        "name": "Find Cardiologist",
        "query": "我想找一个心脏科医生",
        "expected_keywords": ["心脏", "医生", "预约"],
        "user_id": 124
    },
    {
        "id": 7,
        "category": "Doctor Search",
        "name": "Find Doctors by City",
        "query": "深圳有哪些医生？",
        "expected_keywords": ["深圳", "医生", "诊所"],
        "user_id": 124
    },
    {
        "id": 8,
        "category": "Doctor Search",
        "name": "Specific Doctor Info",
        "query": "张医生的信息",
        "expected_keywords": ["张", "医生", "专科"],
        "user_id": 124
    },
    {
        "id": 9,
        "category": "Doctor Search",
        "name": "Doctor Availability",
        "query": "李医生下周有空吗？",
        "expected_keywords": ["李医生", "时间", "预约"],
        "user_id": 124
    },
    {
        "id": 10,
        "category": "Doctor Search",
        "name": "Multi-criteria Search",
        "query": "北京的骨科医生，要有20年以上经验",
        "expected_keywords": ["北京", "骨科", "经验"],
        "user_id": 124
    },
    
    # Category 3: Appointment Booking Flow
    {
        "id": 11,
        "category": "Appointment",
        "name": "Complete Booking Request",
        "query": "预约王医生，我叫李明，电话13800138000，想看下周二下午",
        "expected_keywords": ["预约", "王医生", "确认"],
        "user_id": 125
    },
    {
        "id": 12,
        "category": "Appointment",
        "name": "Incomplete Booking",
        "query": "帮我预约张医生",
        "expected_keywords": ["姓名", "电话", "时间"],
        "user_id": 126
    },
    {
        "id": 13,
        "category": "Appointment",
        "name": "Follow-up Info",
        "query": "我叫王芳，电话15900159000",
        "expected_keywords": ["时间", "预约"],
        "user_id": 126  # Same as test 12 for continuity
    },
    {
        "id": 14,
        "category": "Appointment",
        "name": "Appointment Modification",
        "query": "改一下我明天的预约，改到后天同一时间",
        "expected_keywords": ["修改", "预约", "确认"],
        "user_id": 125
    },
    {
        "id": 15,
        "category": "Appointment",
        "name": "Appointment Cancellation",
        "query": "取消我下周三的预约",
        "expected_keywords": ["取消", "预约", "政策"],
        "user_id": 125
    },
    
    # Category 4: Clinic Services & Pricing
    {
        "id": 16,
        "category": "Clinic Services",
        "name": "Clinic Locations",
        "query": "广州有哪些诊所？",
        "expected_keywords": ["广州", "诊所", "地址"],
        "user_id": 127
    },
    {
        "id": 17,
        "category": "Clinic Services",
        "name": "Service Availability",
        "query": "深圳诊所提供什么服务？",
        "expected_keywords": ["深圳", "服务", "检查"],
        "user_id": 127
    },
    {
        "id": 18,
        "category": "Clinic Services",
        "name": "Service Pricing",
        "query": "肝功能检查多少钱？",
        "expected_keywords": ["肝功能", "价格", "费用"],
        "user_id": 127
    },
    {
        "id": 19,
        "category": "Clinic Services",
        "name": "Price Comparison",
        "query": "哪里的体检套餐最便宜？",
        "expected_keywords": ["体检", "价格", "比较"],
        "user_id": 127
    },
    {
        "id": 20,
        "category": "Clinic Services",
        "name": "Service Details",
        "query": "核磁共振检查需要准备什么？",
        "expected_keywords": ["核磁共振", "准备", "注意"],
        "user_id": 127
    },
    
    # Category 5: Medical Consultation & Emergency
    {
        "id": 21,
        "category": "Medical",
        "name": "Symptom Analysis",
        "query": "最近总是失眠，还头痛",
        "expected_keywords": ["失眠", "头痛", "建议"],
        "user_id": 128
    },
    {
        "id": 22,
        "category": "Medical",
        "name": "Emergency Case",
        "query": "我现在胸痛很厉害，呼吸困难",
        "expected_keywords": ["120", "急救", "立即"],
        "user_id": 128
    },
    {
        "id": 23,
        "category": "Medical",
        "name": "Medication Query",
        "query": "阿司匹林和华法林能一起吃吗？",
        "expected_keywords": ["药物", "相互作用", "医生"],
        "user_id": 128
    },
    {
        "id": 24,
        "category": "Medical",
        "name": "Health Product",
        "query": "我想买保健品",
        "expected_keywords": ["健康商城", "小程序"],
        "user_id": 128
    },
    {
        "id": 25,
        "category": "Medical",
        "name": "Department Recommendation",
        "query": "头晕应该看什么科？",
        "expected_keywords": ["神经", "内科", "建议"],
        "user_id": 128
    },
    
    # Category 6: Memory Persistence Tests
    {
        "id": 26,
        "category": "Memory",
        "name": "Store Personal Info",
        "query": "我叫张三，住在北京，今年45岁",
        "expected_keywords": ["记录", "信息"],
        "user_id": "memory_test_user_1"
    },
    {
        "id": 27,
        "category": "Memory",
        "name": "Store Medical History",
        "query": "我对花生和海鲜过敏，有高血压，每天吃降压药",
        "expected_keywords": ["过敏", "高血压", "记录"],
        "user_id": "memory_test_user_1"
    },
    {
        "id": 28,
        "category": "Memory",
        "name": "Recall Personal Info",
        "query": "你知道我的基本信息吗？",
        "expected_keywords": ["张三", "北京", "45岁"],
        "user_id": "memory_test_user_1"
    },
    {
        "id": 29,
        "category": "Memory",
        "name": "Recall Medical History",
        "query": "我有什么过敏史和慢性病？",
        "expected_keywords": ["花生", "海鲜", "高血压"],
        "user_id": "memory_test_user_1"
    },
    {
        "id": 30,
        "category": "Memory",
        "name": "Complex Memory Query",
        "query": "根据我的情况，推荐合适的医生",
        "expected_keywords": ["高血压", "内科", "医生"],
        "user_id": "memory_test_user_1"
    }
]

async def test_endpoint(session, test_case, stream=True):
    """Test V2 endpoint with a single test case"""
    try:
        request_data = {
            "user_id": test_case["user_id"],
            "messages": [{"role": "user", "content": test_case["query"]}],
            "stream": stream
        }
        
        start_time = time.time()
        
        async with session.post(
            f"{BASE_URL}/v2/humansa/chat",
            json=request_data,
            timeout=aiohttp.ClientTimeout(total=30)
        ) as response:
            
            if response.status != 200:
                return {
                    "success": False,
                    "error": f"HTTP {response.status}",
                    "response_time": time.time() - start_time
                }
            
            # Process response
            full_response = ""
            has_thoughts = False
            
            if stream:
                async for line in response.content:
                    if line:
                        decoded = line.decode('utf-8').strip()
                        if decoded.startswith('data: '):
                            data_str = decoded[6:]
                            if data_str == '[DONE]':
                                break
                            try:
                                data = json.loads(data_str)
                                if 'choices' in data:
                                    for choice in data.get('choices', []):
                                        delta = choice.get('delta', {})
                                        if 'content' in delta:
                                            content = delta['content']
                                            full_response += content
                                            # Check for thought markers
                                            if any(marker in content for marker in ['💭', '🔧', '📊']):
                                                has_thoughts = True
                            except json.JSONDecodeError:
                                pass
            else:
                result = await response.json()
                if 'choices' in result:
                    full_response = result['choices'][0]['message']['content']
            
            # Check for expected keywords
            found_keywords = []
            missing_keywords = []
            
            for keyword in test_case.get('expected_keywords', []):
                if keyword.lower() in full_response.lower():
                    found_keywords.append(keyword)
                else:
                    missing_keywords.append(keyword)
            
            return {
                "success": len(missing_keywords) == 0,
                "response": full_response,
                "found_keywords": found_keywords,
                "missing_keywords": missing_keywords,
                "response_time": time.time() - start_time,
                "has_thoughts": has_thoughts
            }
            
    except asyncio.TimeoutError:
        return {
            "success": False,
            "error": "Request timeout (30s)",
            "response_time": 30.0
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "response_time": 0
        }

async def run_all_tests():
    """Run all 30 test cases"""
    print_section("Humansa V2 - 30 Comprehensive Test Cases")
    print(f"Total test cases: {len(TEST_CASES)}")
    
    async with aiohttp.ClientSession() as session:
        # Check health first
        try:
            async with session.get(f"{BASE_URL}/v2/humansa/health") as resp:
                if resp.status == 200:
                    health = await resp.json()
                    print_colored(f"\n✅ V2 Health Check: {health['status']}", Colors.GREEN)
                else:
                    print_colored(f"❌ V2 Health Check Failed", Colors.RED)
                    return
        except Exception as e:
            print_colored(f"❌ Cannot connect to V2 endpoint: {e}", Colors.RED)
            return
        
        # Run tests by category
        results = []
        category_stats = {}
        
        for test_case in TEST_CASES:
            category = test_case['category']
            if category not in category_stats:
                category_stats[category] = {"total": 0, "passed": 0}
                print_section(f"Category: {category}")
            
            print(f"\n📋 Test {test_case['id']}: {test_case['name']}")
            print(f"   Query: {test_case['query']}")
            
            # Add delay for memory tests to ensure persistence
            if category == "Memory" and test_case['id'] in [27, 28, 29, 30]:
                await asyncio.sleep(2)
            
            result = await test_endpoint(session, test_case)
            results.append({
                "test": test_case,
                "result": result
            })
            
            category_stats[category]["total"] += 1
            
            if result['success']:
                category_stats[category]["passed"] += 1
                print_colored(f"   ✅ PASSED ({result['response_time']:.2f}s)", Colors.GREEN)
                if result.get('found_keywords'):
                    print(f"   Found: {', '.join(result['found_keywords'])}")
            else:
                print_colored(f"   ❌ FAILED", Colors.RED)
                if result.get('error'):
                    print(f"   Error: {result['error']}")
                if result.get('missing_keywords'):
                    print(f"   Missing: {', '.join(result['missing_keywords'])}")
                if result.get('response'):
                    print(f"   Response: {result['response'][:200]}...")
            
            # Show if thoughts were displayed (for streaming)
            if result.get('has_thoughts'):
                print_colored(f"   💭 Agent thoughts displayed", Colors.CYAN)
        
        # Summary
        print_section("TEST SUMMARY")
        
        total_tests = len(TEST_CASES)
        total_passed = sum(stat["passed"] for stat in category_stats.values())
        
        print(f"\nOverall: {total_passed}/{total_tests} passed ({total_passed/total_tests*100:.1f}%)")
        
        print("\nBy Category:")
        for category, stats in category_stats.items():
            passed = stats["passed"]
            total = stats["total"]
            percentage = passed/total*100 if total > 0 else 0
            status = "✅" if percentage == 100 else "⚠️" if percentage >= 80 else "❌"
            print(f"  {status} {category}: {passed}/{total} ({percentage:.1f}%)")
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"humansa_v2_test_results_30cases_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump({
                "timestamp": timestamp,
                "total_tests": total_tests,
                "passed": total_passed,
                "failed": total_tests - total_passed,
                "success_rate": total_passed/total_tests,
                "category_stats": category_stats,
                "detailed_results": [
                    {
                        "id": r["test"]["id"],
                        "name": r["test"]["name"],
                        "category": r["test"]["category"],
                        "query": r["test"]["query"],
                        "success": r["result"]["success"],
                        "response_time": r["result"].get("response_time", 0),
                        "missing_keywords": r["result"].get("missing_keywords", []),
                        "error": r["result"].get("error")
                    }
                    for r in results
                ]
            }, f, ensure_ascii=False, indent=2)
        
        print(f"\nResults saved to: {filename}")
        
        # Pass/Fail determination
        if total_passed == total_tests:
            print_colored("\n🎉 ALL TESTS PASSED! System is fully functional.", Colors.GREEN)
        elif total_passed >= total_tests * 0.9:
            print_colored(f"\n✅ GOOD: {total_passed}/{total_tests} tests passed", Colors.GREEN)
        elif total_passed >= total_tests * 0.8:
            print_colored(f"\n⚠️ NEEDS IMPROVEMENT: {total_passed}/{total_tests} tests passed", Colors.YELLOW)
        else:
            print_colored(f"\n❌ CRITICAL: Only {total_passed}/{total_tests} tests passed", Colors.RED)

if __name__ == "__main__":
    asyncio.run(run_all_tests())
