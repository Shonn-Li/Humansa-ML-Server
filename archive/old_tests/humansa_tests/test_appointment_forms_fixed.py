#!/usr/bin/env python3
"""
Fixed Modular Test Suite for Appointment Form System
====================================================

Uses the comprehensive test framework properly with context managers
and simplified test execution.
"""

import asyncio
import aiohttp
import json
import re
import time
from typing import List, Dict, Any
from datetime import datetime

# Test configuration
TEST_ML_SERVER = "http://localhost:6001"
TEST_USER_BASE = "apt_test_user"


class AppointmentFormTestRunner:
    """Simplified test runner for appointment forms"""
    
    def __init__(self):
        self.results = []
        self.test_cases = []
        
    def add_test(self, test_id: str, name: str, query: str, 
                 expected_keywords: List[str] = None,
                 previous_turns: List[Dict[str, str]] = None,
                 metadata: Dict[str, Any] = None):
        """Add a test case"""
        self.test_cases.append({
            "id": test_id,
            "name": name,
            "query": query,
            "expected_keywords": expected_keywords or [],
            "previous_turns": previous_turns or [],
            "metadata": metadata or {}
        })
    
    async def execute_test(self, session: aiohttp.ClientSession, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single test case"""
        start_time = time.time()
        result = {
            "test_id": test_case["id"],
            "test_name": test_case["name"],
            "passed": False,
            "error": None,
            "response_time": 0,
            "validations": {}
        }
        
        try:
            # Generate unique user ID for test isolation
            user_id = f"{TEST_USER_BASE}_{test_case['id']}_{int(time.time())}"
            previous_response_id = None
            
            # Execute previous turns if any
            for turn in test_case.get("previous_turns", []):
                if turn["role"] == "user":
                    turn_data = {
                        "model": "gpt-4-turbo",
                        "input": turn["content"],
                        "user_id": user_id
                    }
                    
                    if previous_response_id:
                        turn_data["previous_response_id"] = previous_response_id
                    
                    async with session.post(
                        f"{TEST_ML_SERVER}/v2/humansa/responses/create",
                        json=turn_data,
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as resp:
                        if resp.status == 200:
                            turn_response = await resp.json()
                            previous_response_id = turn_response.get("id")
            
            # Execute main query
            request_data = {
                "model": "gpt-4-turbo",
                "input": test_case["query"],
                "user_id": user_id,
                "metadata": {
                    "test_id": test_case["id"],
                    "test_name": test_case["name"]
                }
            }
            
            if previous_response_id:
                request_data["previous_response_id"] = previous_response_id
            
            async with session.post(
                f"{TEST_ML_SERVER}/v2/humansa/responses/create",
                json=request_data,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                result["response_time"] = time.time() - start_time
                
                if response.status == 200:
                    response_data = await response.json()
                    
                    # Extract output text
                    output_text = " ".join([
                        item.get("text", "") 
                        for item in response_data.get("output", []) 
                        if item.get("type") in ["text", "output_text"]
                    ])
                    
                    # Validate response
                    validations = {}
                    
                    # Check keywords
                    if test_case["expected_keywords"]:
                        validations["has_keywords"] = all(
                            keyword.lower() in output_text.lower() 
                            for keyword in test_case["expected_keywords"]
                        )
                    
                    # Check form_id
                    if test_case["metadata"].get("expect_form_id"):
                        validations["has_form_id"] = bool(
                            response_data.get("metadata", {}).get("form_id")
                        )
                    
                    # Check confirmation code
                    if test_case["metadata"].get("expect_confirmation_code"):
                        validations["has_confirmation_code"] = bool(
                            re.search(r"APT-\d+", output_text)
                        )
                    
                    # Check agents used
                    if test_case["metadata"].get("expected_agents"):
                        agents_used = response_data.get("usage", {}).get("agents_used", [])
                        validations["correct_agents"] = any(
                            expected in str(agents_used)
                            for expected in test_case["metadata"]["expected_agents"]
                        )
                    
                    result["validations"] = validations
                    result["passed"] = all(validations.values()) if validations else True
                    result["response_data"] = response_data
                    result["output_text"] = output_text
                else:
                    result["error"] = f"HTTP {response.status}"
                    
        except Exception as e:
            result["error"] = str(e)
            result["response_time"] = time.time() - start_time
        
        return result
    
    async def run_all_tests(self):
        """Run all tests in parallel batches"""
        async with aiohttp.ClientSession() as session:
            # Run in batches of 5
            batch_size = 5
            for i in range(0, len(self.test_cases), batch_size):
                batch = self.test_cases[i:i + batch_size]
                print(f"\nRunning batch {i//batch_size + 1}/{(len(self.test_cases) + batch_size - 1)//batch_size}")
                
                # Execute batch in parallel
                tasks = [self.execute_test(session, test) for test in batch]
                batch_results = await asyncio.gather(*tasks)
                self.results.extend(batch_results)
                
                # Small delay between batches
                await asyncio.sleep(0.5)
        
        return self.results
    
    def print_summary(self):
        """Print test summary"""
        total = len(self.results)
        passed = sum(1 for r in self.results if r["passed"])
        failed = total - passed
        
        print("\n" + "="*60)
        print("APPOINTMENT FORM TEST RESULTS")
        print("="*60)
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Success Rate: {passed/total*100:.1f}%")
        
        # Average response time
        avg_time = sum(r["response_time"] for r in self.results) / total
        print(f"Average Response Time: {avg_time:.2f}s")
        
        # Failed tests details
        if failed > 0:
            print("\nFailed Tests:")
            for result in self.results:
                if not result["passed"]:
                    print(f"  - {result['test_name']}")
                    if result["error"]:
                        print(f"    Error: {result['error']}")
                    elif result["validations"]:
                        failed_checks = [k for k, v in result["validations"].items() if not v]
                        print(f"    Failed checks: {', '.join(failed_checks)}")
        
        # Save detailed results
        with open("appointment_form_test_results_modular.json", "w", encoding="utf-8") as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "summary": {
                    "total": total,
                    "passed": passed,
                    "failed": failed,
                    "success_rate": passed/total if total > 0 else 0
                },
                "results": self.results
            }, f, ensure_ascii=False, indent=2)
        
        print(f"\nDetailed results saved to: appointment_form_test_results_modular.json")


async def main():
    """Run appointment form tests"""
    runner = AppointmentFormTestRunner()
    
    # Add test cases
    
    # Test 1: Complete appointment request
    runner.add_test(
        "apt_001",
        "Complete appointment request",
        "我想预约李明医生明天上午9点看头痛，我叫张三，电话13800138000",
        expected_keywords=["预约信息", "李明医生", "明天", "张三", "13800138000"],
        metadata={"expect_form_id": True}
    )
    
    # Test 2: Confirm appointment (with context)
    runner.add_test(
        "apt_002",
        "Confirm appointment with context",
        "确认预约",
        expected_keywords=["成功", "APT"],
        previous_turns=[
            {"role": "user", "content": "我想预约李明医生明天上午9点看头痛，我叫张三，电话13800138000"},
            {"role": "assistant", "content": "您的预约信息如下..."}
        ],
        metadata={"expect_confirmation_code": True}
    )
    
    # Test 3: Multi-turn doctor selection
    runner.add_test(
        "apt_003",
        "Multi-turn missing doctor",
        "李明医生",
        expected_keywords=["李明医生"],
        previous_turns=[
            {"role": "user", "content": "我想预约明天上午看头痛"},
            {"role": "assistant", "content": "请问您想预约哪位医生？"}
        ],
        metadata={"expect_form_id": True}
    )
    
    # Test 4: Progressive information collection
    runner.add_test(
        "apt_004",
        "Progressive info collection",
        "张四，13900139000",
        expected_keywords=["张四", "13900139000"],
        previous_turns=[
            {"role": "user", "content": "我想预约明天"},
            {"role": "assistant", "content": "请问看什么症状？"},
            {"role": "user", "content": "头痛"},
            {"role": "assistant", "content": "请问您想预约哪位医生？"},
            {"role": "user", "content": "李明医生"},
            {"role": "assistant", "content": "好的，请提供您的姓名和联系方式"}
        ],
        metadata={"expect_form_id": True}
    )
    
    # Test 5: Modify appointment
    runner.add_test(
        "apt_005",
        "Modify appointment time",
        "改到后天下午3点",
        expected_keywords=["后天", "下午3点", "修改", "更新"],
        previous_turns=[
            {"role": "user", "content": "预约王医生明天上午看诊，我叫赵六，电话13700137000"},
            {"role": "assistant", "content": "预约信息已记录"}
        ],
        metadata={"expect_form_id": True}
    )
    
    # Test 6: Cancel appointment
    runner.add_test(
        "apt_006",
        "Cancel appointment",
        "取消预约",
        expected_keywords=["取消", "已取消"],
        previous_turns=[
            {"role": "user", "content": "预约张医生明天看诊，我叫钱七，电话13600136000"},
            {"role": "assistant", "content": "预约信息已记录"}
        ],
        metadata={"expect_form_id": False}
    )
    
    # Test 7: Urgent symptoms
    runner.add_test(
        "apt_007",
        "Urgent symptom handling",
        "我胸口剧痛，呼吸困难，需要紧急预约",
        expected_keywords=["紧急", "急诊", "立即", "马上"],
        metadata={"expect_form_id": True}
    )
    
    # Test 8: Time parsing - morning
    runner.add_test(
        "apt_008",
        "Time parsing - morning",
        "预约李医生明天上午9点半看诊，我叫测试用户，电话13500135000",
        expected_keywords=["明天", "上午", "9", "30"],
        metadata={"expect_form_id": True}
    )
    
    # Test 9: Department booking
    runner.add_test(
        "apt_009",
        "Department-based booking",
        "我想预约皮肤科明天的专家门诊，我叫孙八，电话13400134000",
        expected_keywords=["皮肤科", "专家", "明天"],
        metadata={"expect_form_id": True, "expected_agents": ["FormCreator"]}
    )
    
    # Test 10: Form persistence
    runner.add_test(
        "apt_010",
        "Form persistence check",
        "查看我的预约信息",
        expected_keywords=["周医生", "后天", "吴九"],
        previous_turns=[
            {"role": "user", "content": "预约周医生后天检查，我叫吴九，电话13300133000"},
            {"role": "assistant", "content": "预约信息已记录"}
        ],
        metadata={"expect_form_id": True}
    )
    
    # Test 11: Multiple symptoms
    runner.add_test(
        "apt_011",
        "Multiple symptoms",
        "我头痛、发烧、咳嗽，想预约内科医生，我叫郑十，电话13200132000",
        expected_keywords=["头痛", "发烧", "咳嗽", "内科"],
        metadata={"expect_form_id": True}
    )
    
    # Test 12: Natural conversation
    runner.add_test(
        "apt_012",
        "Natural conversation flow",
        "我叫陈十一，电话13100131000",
        expected_keywords=["陈十一", "13100131000", "李明医生", "明天上午", "头晕"],
        previous_turns=[
            {"role": "user", "content": "我最近总是头晕"},
            {"role": "assistant", "content": "头晕的情况持续多久了？需要帮您预约医生检查吗？"},
            {"role": "user", "content": "已经三天了，是的请帮我预约"},
            {"role": "assistant", "content": "好的，请问您想预约哪位医生？什么时间方便？"},
            {"role": "user", "content": "李明医生吧，明天上午可以吗"},
            {"role": "assistant", "content": "好的，明天上午李明医生有号。请提供您的姓名和联系方式。"}
        ],
        metadata={"expect_form_id": True}
    )
    
    # Run tests
    print("Starting appointment form tests...")
    await runner.run_all_tests()
    
    # Print summary
    runner.print_summary()


if __name__ == "__main__":
    asyncio.run(main())