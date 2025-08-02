#!/usr/bin/env python3
"""
Modular Test Suite for Appointment Form System
==============================================

Uses the comprehensive test framework for better organization,
parallel execution, and detailed expectations.
"""

import asyncio
import sys
from pathlib import Path
from typing import List, Dict, Any
import json
import re

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from humansa_test_framework import (
    TestCase,
    TestCategory,
    TestExpectation,
    TestCaseManager,
    ParallelTestRunner,
    TestReporter,
    TestResult
)
from appointment_test_executor import AppointmentTestExecutor

from test_environment.unified_test_config import TEST_ML_SERVER
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AppointmentFormTestSuite:
    """Modular test suite for appointment form system"""
    
    def __init__(self):
        self.manager = TestCaseManager()
        self.executor = AppointmentTestExecutor(base_url=TEST_ML_SERVER['base_url'])
        self.runner = ParallelTestRunner(max_workers=4)
        self.reporter = TestReporter()
    
    def create_test_cases(self):
        """Create all appointment form test cases"""
        
        # Test 1: Simple complete request with confirmation
        self.manager.add_test_case(TestCase(
            id="apt_001_complete_request",
            name="Complete appointment request with all info",
            category=TestCategory.APPOINTMENT,
            query="我想预约李明医生明天上午9点看头痛，我叫张三，电话13800138000",
            expectations=TestExpectation(
                keywords=["预约信息", "李明医生", "明天", "上午9点", "头痛", "张三", "13800138000"],
                agents_touched=["FormCreator"],
                required_tools=["create_appointment_form"],
                min_response_length=100,
                response_time_max=5.0
            ),
            metadata={
                "form_should_complete": True,
                "expect_form_id": True,
                "expect_confirmation_prompt": True
            }
        ))
        
        # Test 2: Multi-turn form completion
        self.manager.add_test_case(TestCase(
            id="apt_002_multi_turn_completion",
            name="Multi-turn form completion",
            category=TestCategory.MULTI_TURN,
            query="我叫李四，电话13900139000",
            previous_turns=[
                {"role": "user", "content": "我想预约看头痛"},
                {"role": "assistant", "content": "请问您想预约哪位医生？什么时间方便？"}
            ],
            expectations=TestExpectation(
                keywords=["李四", "13900139000"],
                agents_touched=["FormCreator", "FormUpdater"],
                required_tools=["update_appointment_form"],
                min_response_length=50
            ),
            metadata={
                "is_continuation": True,
                "expect_form_update": True
            }
        ))
        
        # Test 3: Form confirmation
        self.manager.add_test_case(TestCase(
            id="apt_003_confirm_appointment",
            name="Confirm complete appointment",
            category=TestCategory.APPOINTMENT,
            query="确认预约",
            previous_turns=[
                {"role": "user", "content": "我想预约李明医生明天上午9点看头痛，我叫张三，电话13800138000"},
                {"role": "assistant", "content": "您的预约信息如下：医生：李明医生...请确认"}
            ],
            expectations=TestExpectation(
                keywords=["成功", "预约成功", "APT-"],
                agents_touched=["FormSubmitter"],
                required_tools=["submit_appointment_form"],
                min_response_length=50
            ),
            metadata={
                "expect_confirmation_code": True,
                "confirmation_pattern": r"APT-\d+"
            }
        ))
        
        # Test 4: Modify appointment
        self.manager.add_test_case(TestCase(
            id="apt_004_modify_appointment",
            name="Modify appointment time",
            category=TestCategory.APPOINTMENT,
            query="改到后天下午3点",
            previous_turns=[
                {"role": "user", "content": "预约王医生明天上午10点看感冒，我叫赵六，电话13700137000"},
                {"role": "assistant", "content": "预约信息已记录..."}
            ],
            expectations=TestExpectation(
                keywords=["后天", "下午3点", "修改", "更新"],
                agents_touched=["FormUpdater"],
                required_tools=["update_appointment_form"],
                min_response_length=50
            ),
            metadata={
                "expect_form_update": True,
                "updated_fields": ["date", "time_slot"]
            }
        ))
        
        # Test 5: Cancel appointment
        self.manager.add_test_case(TestCase(
            id="apt_005_cancel_appointment",
            name="Cancel appointment",
            category=TestCategory.APPOINTMENT,
            query="取消预约",
            previous_turns=[
                {"role": "user", "content": "预约张医生明天看诊，我叫钱七，电话13600136000"},
                {"role": "assistant", "content": "预约信息已记录..."}
            ],
            expectations=TestExpectation(
                keywords=["取消", "已取消"],
                agents_touched=["FormCanceller"],
                forbidden_patterns=["APT-", "预约成功"],
                min_response_length=30
            ),
            metadata={
                "expect_cancellation": True
            }
        ))
        
        # Test 6: Urgent symptom handling
        self.manager.add_test_case(TestCase(
            id="apt_006_urgent_symptoms",
            name="Urgent symptom detection",
            category=TestCategory.EMERGENCY,
            query="我胸口剧痛，呼吸困难，需要紧急预约",
            expectations=TestExpectation(
                keywords=["紧急", "急诊", "立即", "马上"],
                agents_touched=["EmergencyDetector", "FormCreator"],
                emergency_flags=["chest_pain", "breathing_difficulty"],
                min_response_length=100
            ),
            metadata={
                "is_urgent": True,
                "expect_emergency_routing": True
            }
        ))
        
        # Test 7: Time parsing variations
        time_variations = [
            ("apt_007a_time_morning", "明天上午9点半", ["09:30", "上午9点半"]),
            ("apt_007b_time_afternoon", "后天下午2点", ["14:00", "下午2点"]),
            ("apt_007c_time_next_week", "下周一上午10点", ["下周一", "10:00"]),
            ("apt_007d_time_chinese", "明天上午九点", ["09:00", "上午九点"]),
            ("apt_007e_time_specific", "8月5号下午3点", ["8月5", "15:00"])
        ]
        
        for test_id, query, expected_keywords in time_variations:
            self.manager.add_test_case(TestCase(
                id=test_id,
                name=f"Time parsing: {query}",
                category=TestCategory.APPOINTMENT,
                query=f"预约李医生{query}看诊，我叫测试用户，电话13500135000",
                expectations=TestExpectation(
                    keywords=expected_keywords,
                    agents_touched=["FormCreator"],
                    required_tools=["create_appointment_form"],
                    min_response_length=50
                ),
                metadata={
                    "test_time_parsing": True,
                    "time_expression": query
                }
            ))
        
        # Test 8: Doctor not found handling
        self.manager.add_test_case(TestCase(
            id="apt_008_doctor_not_found",
            name="Handle invalid doctor name",
            category=TestCategory.EDGE_CASE,
            query="我想预约不存在医生明天看诊",
            expectations=TestExpectation(
                keywords=["找不到", "没有找到", "推荐", "其他医生"],
                agents_touched=["DoctorSearch", "FormCreator"],
                min_response_length=100
            ),
            metadata={
                "expect_alternatives": True
            }
        ))
        
        # Test 9: Department-based booking
        self.manager.add_test_case(TestCase(
            id="apt_009_department_booking",
            name="Book by department",
            category=TestCategory.APPOINTMENT,
            query="我想预约皮肤科明天的专家门诊，我叫孙八，电话13400134000",
            expectations=TestExpectation(
                keywords=["皮肤科", "专家", "明天"],
                agents_touched=["DepartmentSearch", "FormCreator"],
                required_tools=["search_doctors_by_department", "create_appointment_form"],
                min_response_length=100
            ),
            metadata={
                "booking_type": "department",
                "expect_doctor_suggestions": True
            }
        ))
        
        # Test 10: Form persistence across sessions
        self.manager.add_test_case(TestCase(
            id="apt_010_form_persistence",
            name="Form persists across API calls",
            category=TestCategory.INTEGRATION,
            query="查看我的预约表单",
            previous_turns=[
                {"role": "user", "content": "预约周医生后天检查，我叫吴九，电话13300133000"},
                {"role": "assistant", "content": "预约信息已记录，表单ID: FORM-123..."}
            ],
            expectations=TestExpectation(
                keywords=["周医生", "后天", "吴九"],
                agents_touched=["FormRetriever"],
                required_tools=["get_form_status"],
                min_response_length=50
            ),
            metadata={
                "test_persistence": True,
                "expect_form_retrieval": True
            }
        ))
        
        # Test 11: Multiple symptoms
        self.manager.add_test_case(TestCase(
            id="apt_011_multiple_symptoms",
            name="Handle multiple symptoms",
            category=TestCategory.MEDICAL_CONSULTATION,
            query="我头痛、发烧、咳嗽，想预约内科医生，我叫郑十，电话13200132000",
            expectations=TestExpectation(
                keywords=["头痛", "发烧", "咳嗽", "内科"],
                agents_touched=["SymptomAnalyzer", "FormCreator"],
                min_response_length=100
            ),
            metadata={
                "symptom_count": 3,
                "expect_all_symptoms": True
            }
        ))
        
        # Test 12: Natural conversation flow
        conversation_turns = [
            {"role": "user", "content": "我最近总是头晕"},
            {"role": "assistant", "content": "头晕的情况持续多久了？需要帮您预约医生检查吗？"},
            {"role": "user", "content": "已经三天了，是的请帮我预约"},
            {"role": "assistant", "content": "好的，请问您想预约哪位医生？什么时间方便？"},
            {"role": "user", "content": "李明医生吧，明天上午可以吗"},
            {"role": "assistant", "content": "好的，明天上午李明医生有号。请提供您的姓名和联系方式。"},
        ]
        
        self.manager.add_test_case(TestCase(
            id="apt_012_natural_conversation",
            name="Natural multi-turn conversation",
            category=TestCategory.MULTI_TURN,
            query="我叫陈十一，电话13100131000",
            previous_turns=conversation_turns,
            expectations=TestExpectation(
                keywords=["陈十一", "13100131000", "李明医生", "明天上午", "头晕"],
                agents_touched=["ConversationManager", "FormCreator", "FormUpdater"],
                min_response_length=100,
                response_time_max=10.0
            ),
            metadata={
                "conversation_length": len(conversation_turns) + 1,
                "expect_complete_form": True
            }
        ))
        
        logger.info(f"Created {len(self.manager.test_cases)} appointment form test cases")
    
    async def run_tests(self) -> Dict[str, Any]:
        """Run all tests and generate report"""
        # Create test cases
        self.create_test_cases()
        
        # Run tests in parallel
        logger.info("Starting parallel test execution...")
        results = await self.runner.run_tests(
            list(self.manager.test_cases.values()),
            batch_size=5
        )
        
        # Generate report
        report = self.reporter.generate_report(results)
        
        # Save detailed results
        detailed_results = {
            "summary": report,
            "test_results": [
                {
                    "test_id": result.test_case.id,
                    "test_name": result.test_case.name,
                    "passed": result.passed,
                    "response_time": result.response_time,
                    "error": result.error,
                    "validations": result.validation_results,
                    "metadata": result.metadata
                }
                for result in results
            ]
        }
        
        with open("appointment_form_modular_results.json", "w", encoding="utf-8") as f:
            json.dump(detailed_results, f, ensure_ascii=False, indent=2)
        
        return report
    
    def validate_form_response(self, response: Dict[str, Any], expectations: TestExpectation, metadata: Dict[str, Any]) -> Dict[str, bool]:
        """Custom validation for form responses"""
        validations = {}
        
        # Check for form_id in metadata
        if metadata.get("expect_form_id"):
            validations["has_form_id"] = bool(response.get("metadata", {}).get("form_id"))
        
        # Check for confirmation code
        if metadata.get("expect_confirmation_code"):
            pattern = metadata.get("confirmation_pattern", r"APT-\d+")
            output_text = " ".join([
                item.get("text", "") 
                for item in response.get("output", []) 
                if item.get("type") in ["text", "output_text"]
            ])
            validations["has_confirmation_code"] = bool(re.search(pattern, output_text))
        
        # Check for required agents
        if expectations.agents_touched:
            used_agents = response.get("usage", {}).get("agents_used", [])
            validations["correct_agents"] = any(
                agent in used_agents 
                for agent in expectations.agents_touched
            )
        
        return validations


async def main():
    """Run the modular appointment form test suite"""
    suite = AppointmentFormTestSuite()
    report = await suite.run_tests()
    
    # Print summary
    print("\n" + "="*60)
    print("APPOINTMENT FORM TEST RESULTS (MODULAR)")
    print("="*60)
    print(f"Total Tests: {report['total_tests']}")
    print(f"Passed: {report['passed_tests']}")
    print(f"Failed: {report['failed_tests']}")
    print(f"Success Rate: {report['success_rate']:.1%}")
    print(f"Average Response Time: {report['performance_metrics']['average_response_time']:.2f}s")
    print(f"Total Execution Time: {report['performance_metrics']['total_time']:.2f}s")
    
    # Print failures
    if report['failed_tests'] > 0:
        print("\nFailed Tests:")
        for failure in report['failures']:
            print(f"  - {failure['test_name']}: {failure.get('error', 'Unknown error')}")
    
    print(f"\nDetailed results saved to: appointment_form_modular_results.json")


if __name__ == "__main__":
    asyncio.run(main())