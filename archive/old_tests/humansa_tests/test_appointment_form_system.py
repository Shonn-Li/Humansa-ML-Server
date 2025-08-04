#!/usr/bin/env python3
"""
Comprehensive test suite for the Appointment Form System
Tests multi-turn conversations, form lifecycle, and edge cases
"""

import asyncio
import json
import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta
import colorama
from colorama import Fore, Style
import requests

# Initialize colorama
colorama.init()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Test configuration
BASE_URL = "http://localhost:6001"  # Using test environment port
API_KEY = "test-api-key"

class AppointmentFormTester:
    """Comprehensive tester for appointment form system"""
    
    def __init__(self):
        self.base_url = BASE_URL
        self.headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }
        self.test_results = []
        self.user_id = f"test_user_{datetime.now().timestamp()}"
        
    def log_test(self, test_name: str, passed: bool, details: str = ""):
        """Log test result"""
        result = {
            "test": test_name,
            "passed": passed,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        if passed:
            print(f"{Fore.GREEN}✓ {test_name}{Style.RESET_ALL}")
            if details:
                print(f"  {details}")
        else:
            print(f"{Fore.RED}✗ {test_name}{Style.RESET_ALL}")
            if details:
                print(f"  {Fore.YELLOW}{details}{Style.RESET_ALL}")
    
    def make_request(self, query: str, previous_response_id: str = None) -> Dict[str, Any]:
        """Make API request to Humansa"""
        payload = {
            "model": "gpt-4-turbo",
            "input": query,
            "user_id": self.user_id
        }
        
        if previous_response_id:
            payload["previous_response_id"] = previous_response_id
        
        try:
            response = requests.post(
                f"{self.base_url}/v2/humansa/responses/create",
                json=payload,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"API error: {response.status_code} - {response.text}")
                return {"error": response.text}
                
        except Exception as e:
            logger.error(f"Request error: {e}")
            return {"error": str(e)}
    
    def extract_form_id(self, response: Dict[str, Any]) -> str:
        """Extract form_id from response"""
        # Check in metadata
        if "metadata" in response and "form_id" in response["metadata"]:
            return response["metadata"]["form_id"]
        
        # Check in output items
        if "output" in response:
            for item in response["output"]:
                if item.get("type") == "text":
                    text = item.get("text", "")
                    # Look for form_id pattern
                    import re
                    match = re.search(r'form_[a-f0-9]{12}', text)
                    if match:
                        return match.group(0)
        
        return None
    
    async def test_01_simple_complete_request(self):
        """Test 1: Simple complete appointment request in one turn"""
        query = "我想预约李明医生明天上午9点看头痛，我叫张三，电话13800138000"
        
        response = self.make_request(query)
        
        # Check response structure
        if "error" in response:
            self.log_test("Test 1: Simple complete request", False, f"API error: {response['error']}")
            return
        
        # Extract form_id
        form_id = self.extract_form_id(response)
        
        # Check if form was created
        has_form = form_id is not None
        output_text = " ".join([item.get("text", "") for item in response.get("output", []) if item.get("type") in ["text", "output_text"]])
        has_preview = "预约信息" in output_text or "您的预约信息如下" in output_text
        has_confirmation_prompt = "确认" in output_text or "请确认" in output_text
        
        passed = has_form and has_preview and has_confirmation_prompt
        
        details = f"Form ID: {form_id}, Has preview: {has_preview}, Has confirmation: {has_confirmation_prompt}"
        self.log_test("Test 1: Simple complete request", passed, details)
        
        return response.get("id"), form_id
    
    async def test_02_confirm_appointment(self):
        """Test 2: Confirm appointment from Test 1"""
        # First create appointment
        response_id, form_id = await self.test_01_simple_complete_request()
        
        if not form_id:
            self.log_test("Test 2: Confirm appointment", False, "No form_id from Test 1")
            return
        
        # Confirm with context
        response = self.make_request("确认", previous_response_id=response_id)
        
        # Check for confirmation code
        output_text = " ".join([item.get("text", "") for item in response.get("output", []) if item.get("type") in ["text", "output_text"]])
        
        has_success = "成功" in output_text or "APT-" in output_text
        has_confirmation_code = bool(re.search(r'APT-\d+', output_text))
        
        passed = has_success and has_confirmation_code
        
        if has_confirmation_code:
            code = re.search(r'APT-\d+', output_text).group(0)
            details = f"Confirmation code: {code}"
        else:
            details = "No confirmation code found"
            
        self.log_test("Test 2: Confirm appointment", passed, details)
    
    async def test_03_multi_turn_missing_doctor(self):
        """Test 3: Multi-turn conversation - missing doctor"""
        # Start with incomplete info
        response1 = self.make_request("我想看医生")
        
        output_text = " ".join([item.get("text", "") for item in response1.get("output", []) if item.get("type") == "text"])
        
        # Should ask for doctor
        asks_for_doctor = "医生" in output_text and ("哪位" in output_text or "选择" in output_text)
        
        if not asks_for_doctor:
            self.log_test("Test 3: Multi-turn missing doctor", False, "Didn't ask for doctor selection")
            return
        
        # Provide doctor
        response2 = self.make_request("李明医生", response1.get("id"))
        
        output_text2 = " ".join([item.get("text", "") for item in response2.get("output", []) if item.get("type") == "text"])
        
        # Should ask for more info (date/time/symptoms)
        asks_for_more = any(keyword in output_text2 for keyword in ["什么时候", "时间", "症状", "哪里不舒服"])
        
        self.log_test("Test 3: Multi-turn missing doctor", asks_for_more, f"Asked for more info: {asks_for_more}")
        
        return response2.get("id")
    
    async def test_04_multi_turn_progressive_collection(self):
        """Test 4: Progressive information collection over multiple turns"""
        # Turn 1: Just symptoms
        response1 = self.make_request("我最近头痛")
        resp1_id = response1.get("id")
        
        # Turn 2: Add doctor
        response2 = self.make_request("想看李明医生", resp1_id)
        resp2_id = response2.get("id")
        
        # Turn 3: Add date
        response3 = self.make_request("明天可以吗", resp2_id)
        resp3_id = response3.get("id")
        
        # Turn 4: Add time
        response4 = self.make_request("上午9点", resp3_id)
        
        # Check if form was created after providing all info
        form_id = self.extract_form_id(response4)
        output_text = " ".join([item.get("text", "") for item in response4.get("output", []) if item.get("type") == "text"])
        
        has_form = form_id is not None
        has_preview = "预约信息" in output_text
        has_all_info = all(info in output_text for info in ["李明", "明天", "上午", "头痛"])
        
        passed = has_form and has_preview and has_all_info
        
        self.log_test("Test 4: Progressive collection", passed, f"Form created: {has_form}, All info captured: {has_all_info}")
    
    async def test_05_modify_appointment(self):
        """Test 5: Modify appointment after creation"""
        # Create appointment
        response1 = self.make_request("预约张伟医生后天下午3点看胃痛")
        form_id = self.extract_form_id(response1)
        
        if not form_id:
            self.log_test("Test 5: Modify appointment", False, "Failed to create initial appointment")
            return
        
        # Request modification
        response2 = self.make_request("改成明天上午吧", response1.get("id"))
        
        output_text = " ".join([item.get("text", "") for item in response2.get("output", []) if item.get("type") == "text"])
        
        # Check if modification was acknowledged
        has_update = "明天" in output_text and "上午" in output_text
        has_preview = "预约信息" in output_text
        still_has_doctor = "张伟" in output_text
        
        passed = has_update and has_preview and still_has_doctor
        
        self.log_test("Test 5: Modify appointment", passed, f"Updated to tomorrow morning: {has_update}")
    
    async def test_06_cancel_appointment(self):
        """Test 6: Cancel appointment"""
        # Create appointment
        response1 = self.make_request("预约王芳医生明天下午看孩子咳嗽")
        form_id = self.extract_form_id(response1)
        
        if not form_id:
            self.log_test("Test 6: Cancel appointment", False, "Failed to create appointment")
            return
        
        # Cancel
        response2 = self.make_request("取消预约", response1.get("id"))
        
        output_text = " ".join([item.get("text", "") for item in response2.get("output", []) if item.get("type") == "text"])
        
        cancelled = "取消" in output_text and ("已" in output_text or "成功" in output_text)
        
        self.log_test("Test 6: Cancel appointment", cancelled, "Appointment cancelled successfully")
    
    async def test_07_symptom_based_doctor_suggestion(self):
        """Test 7: Doctor suggestion based on symptoms"""
        response = self.make_request("我最近皮肤过敏很严重")
        
        output_text = " ".join([item.get("text", "") for item in response.get("output", []) if item.get("type") in ["text", "output_text"]])
        
        # Should suggest dermatology
        suggests_dept = "皮肤科" in output_text
        asks_for_doctor = "医生" in output_text
        
        passed = suggests_dept or asks_for_doctor
        
        self.log_test("Test 7: Symptom-based suggestion", passed, f"Suggested dermatology: {suggests_dept}")
    
    async def test_08_urgent_symptom_handling(self):
        """Test 8: Urgent symptom detection"""
        response = self.make_request("我胸痛呼吸困难")
        
        output_text = " ".join([item.get("text", "") for item in response.get("output", []) if item.get("type") in ["text", "output_text"]])
        
        # Should recognize urgency
        has_urgency = any(word in output_text for word in ["紧急", "急", "尽快", "立即", "严重"])
        
        self.log_test("Test 8: Urgent symptom handling", has_urgency, f"Recognized urgency: {has_urgency}")
    
    async def test_09_time_slot_variations(self):
        """Test 9: Various time slot expressions"""
        time_expressions = [
            ("今天下午", "今天", "下午"),
            ("明天早上", "明天", "早上"),
            ("后天上午10点", "后天", "10"),
            ("下周一", "周一", ""),
            ("这周五下午", "周五", "下午")
        ]
        
        passed_count = 0
        
        for expr, expected_date, expected_time in time_expressions:
            response = self.make_request(f"预约李明医生{expr}看诊")
            output_text = " ".join([item.get("text", "") for item in response.get("output", []) if item.get("type") in ["text", "output_text"]])
            
            has_date = expected_date in output_text
            has_time = expected_time in output_text if expected_time else True
            
            if has_date and has_time:
                passed_count += 1
        
        passed = passed_count >= 3  # At least 3 out of 5
        
        self.log_test("Test 9: Time slot variations", passed, f"Parsed {passed_count}/5 time expressions correctly")
    
    async def test_10_incomplete_then_abandon(self):
        """Test 10: Start appointment but abandon (test expiration)"""
        response1 = self.make_request("我想预约看医生")
        
        # Just leave it - in real system this would expire after 30 minutes
        output_text = " ".join([item.get("text", "") for item in response1.get("output", []) if item.get("type") == "text"])
        
        asks_for_info = "医生" in output_text or "症状" in output_text
        
        self.log_test("Test 10: Incomplete then abandon", asks_for_info, "System asks for information")
    
    async def test_11_multiple_symptoms(self):
        """Test 11: Multiple symptoms handling"""
        response = self.make_request("我头痛发烧还咳嗽，想看医生")
        
        output_text = " ".join([item.get("text", "") for item in response.get("output", []) if item.get("type") in ["text", "output_text"]])
        
        # Check if all symptoms are captured
        has_all_symptoms = all(symptom in output_text for symptom in ["头痛", "发烧", "咳嗽"])
        suggests_internal = "内科" in output_text
        
        passed = has_all_symptoms or suggests_internal
        
        self.log_test("Test 11: Multiple symptoms", passed, f"Captured all symptoms: {has_all_symptoms}")
    
    async def test_12_doctor_not_found(self):
        """Test 12: Non-existent doctor handling"""
        response = self.make_request("我想预约不存在医生明天看病")
        
        output_text = " ".join([item.get("text", "") for item in response.get("output", []) if item.get("type") in ["text", "output_text"]])
        
        # Should either ask for valid doctor or show available doctors
        handles_invalid = "医生" in output_text and ("哪位" in output_text or "选择" in output_text or "可选" in output_text)
        
        self.log_test("Test 12: Doctor not found", handles_invalid, "System handles invalid doctor name")
    
    async def test_13_past_date_validation(self):
        """Test 13: Past date validation"""
        response = self.make_request("预约李明医生昨天上午")
        
        output_text = " ".join([item.get("text", "") for item in response.get("output", []) if item.get("type") in ["text", "output_text"]])
        
        # Should reject past date
        rejects_past = "不能" in output_text or "已经过去" in output_text or "选择" in output_text
        
        self.log_test("Test 13: Past date validation", rejects_past, "System rejects past dates")
    
    async def test_14_form_persistence_across_turns(self):
        """Test 14: Form ID persistence across conversation"""
        # Create form
        response1 = self.make_request("预约李明医生明天上午看头痛")
        form_id1 = self.extract_form_id(response1)
        
        if not form_id1:
            self.log_test("Test 14: Form persistence", False, "Failed to create form")
            return
        
        # Ask about the form
        response2 = self.make_request("刚才的预约是几点？", response1.get("id"))
        
        # Modify the form
        response3 = self.make_request("改成下午3点", response2.get("id"))
        
        # The form_id should persist
        output_text = " ".join([item.get("text", "") for item in response3.get("output", []) if item.get("type") == "text"])
        
        has_update = "下午" in output_text and "3点" in output_text
        maintains_context = "李明" in output_text
        
        passed = has_update and maintains_context
        
        self.log_test("Test 14: Form persistence", passed, f"Form persisted and updated: {passed}")
    
    async def test_15_chinese_number_parsing(self):
        """Test 15: Chinese number parsing"""
        response = self.make_request("预约张医生明天下午三点半")
        
        output_text = " ".join([item.get("text", "") for item in response.get("output", []) if item.get("type") in ["text", "output_text"]])
        
        # Should parse "三点半"
        has_time = "3" in output_text or "三" in output_text
        has_half = "30" in output_text or "半" in output_text
        
        passed = has_time
        
        self.log_test("Test 15: Chinese number parsing", passed, f"Parsed Chinese time: {has_time}")
    
    async def test_16_department_based_booking(self):
        """Test 16: Department-based booking without specific doctor"""
        response = self.make_request("我想挂儿科门诊，孩子发烧了")
        
        output_text = " ".join([item.get("text", "") for item in response.get("output", []) if item.get("type") in ["text", "output_text"]])
        
        # Should handle department booking
        mentions_pediatrics = "儿科" in output_text
        suggests_doctors = "医生" in output_text
        
        passed = mentions_pediatrics
        
        self.log_test("Test 16: Department booking", passed, "Handles department-based booking")
    
    async def test_17_form_completion_validation(self):
        """Test 17: Form won't submit if incomplete"""
        # Create incomplete form
        response1 = self.make_request("预约李明医生")
        
        # Try to confirm without full info
        response2 = self.make_request("确认", response1.get("id"))
        
        output_text = " ".join([item.get("text", "") for item in response2.get("output", []) if item.get("type") == "text"])
        
        # Should ask for missing info
        asks_for_missing = any(word in output_text for word in ["时间", "什么时候", "症状", "哪里不舒服"])
        
        self.log_test("Test 17: Incomplete form validation", asks_for_missing, "System prevents incomplete submission")
    
    async def test_18_natural_conversation_flow(self):
        """Test 18: Natural conversation flow"""
        # Natural conversation
        response1 = self.make_request("医生，我最近老是失眠")
        resp1_id = response1.get("id")
        
        response2 = self.make_request("已经一个多星期了，想找个医生看看", resp1_id)
        resp2_id = response2.get("id")
        
        response3 = self.make_request("听说刘洋医生不错", resp2_id)
        resp3_id = response3.get("id")
        
        response4 = self.make_request("最近什么时候有号？", resp3_id)
        resp4_id = response4.get("id")
        
        response5 = self.make_request("那就明天上午吧", resp4_id)
        
        # Check final response
        form_id = self.extract_form_id(response5)
        output_text = " ".join([item.get("text", "") for item in response5.get("output", []) if item.get("type") == "text"])
        
        has_form = form_id is not None
        captured_all = all(info in output_text for info in ["失眠", "刘洋", "明天", "上午"])
        
        passed = has_form and captured_all
        
        self.log_test("Test 18: Natural conversation", passed, f"Natural flow worked: {passed}")
    
    async def test_19_multiple_forms_same_user(self):
        """Test 19: User can have multiple forms"""
        # Create first appointment
        response1 = self.make_request("给我自己预约李明医生明天上午看头痛")
        form_id1 = self.extract_form_id(response1)
        
        # Create second appointment (different conversation)
        response2 = self.make_request("给我妈妈预约王芳医生后天下午看高血压")
        form_id2 = self.extract_form_id(response2)
        
        different_forms = form_id1 != form_id2 and form_id1 and form_id2
        
        self.log_test("Test 19: Multiple forms", different_forms, f"Created 2 different forms: {different_forms}")
    
    async def test_20_edge_case_empty_confirm(self):
        """Test 20: Edge case - confirm without context"""
        response = self.make_request("确认")
        
        output_text = " ".join([item.get("text", "") for item in response.get("output", []) if item.get("type") in ["text", "output_text"]])
        
        # Should handle gracefully
        handles_gracefully = "什么" in output_text or "预约" in output_text or "没有" in output_text
        
        self.log_test("Test 20: Empty confirm", handles_gracefully, "Handles confirm without context")
    
    async def test_21_tool_usage_tracking(self):
        """Test 21: Check if appointment agent tool is being called"""
        response = self.make_request("预约李明医生明天上午看诊")
        
        # Check if response includes tool usage
        has_tool_use = False
        if "output" in response:
            for item in response["output"]:
                if item.get("type") == "tool_use":
                    tool_name = item.get("tool_use", {}).get("name", "")
                    if "appointment" in tool_name.lower():
                        has_tool_use = True
                        break
        
        self.log_test("Test 21: Tool usage tracking", has_tool_use, f"Appointment tool called: {has_tool_use}")
    
    async def test_22_response_metadata_includes_form(self):
        """Test 22: Response metadata includes form_id"""
        response = self.make_request("预约张伟医生明天下午2点看胃痛")
        
        # Check metadata
        has_metadata = "metadata" in response
        has_form_in_metadata = has_metadata and "form_id" in response.get("metadata", {})
        
        # Also check if form_id appears anywhere
        form_id = self.extract_form_id(response)
        
        passed = has_form_in_metadata or form_id is not None
        
        self.log_test("Test 22: Metadata includes form", passed, f"Form in metadata: {has_form_in_metadata}, Form found: {form_id is not None}")
    
    async def run_all_tests(self):
        """Run all tests"""
        print(f"\n{Fore.CYAN}=== Appointment Form System Test Suite ==={Style.RESET_ALL}\n")
        
        # Run tests sequentially
        await self.test_01_simple_complete_request()
        await asyncio.sleep(0.5)
        
        await self.test_02_confirm_appointment()
        await asyncio.sleep(0.5)
        
        await self.test_03_multi_turn_missing_doctor()
        await asyncio.sleep(0.5)
        
        await self.test_04_multi_turn_progressive_collection()
        await asyncio.sleep(0.5)
        
        await self.test_05_modify_appointment()
        await asyncio.sleep(0.5)
        
        await self.test_06_cancel_appointment()
        await asyncio.sleep(0.5)
        
        await self.test_07_symptom_based_doctor_suggestion()
        await asyncio.sleep(0.5)
        
        await self.test_08_urgent_symptom_handling()
        await asyncio.sleep(0.5)
        
        await self.test_09_time_slot_variations()
        await asyncio.sleep(0.5)
        
        await self.test_10_incomplete_then_abandon()
        await asyncio.sleep(0.5)
        
        await self.test_11_multiple_symptoms()
        await asyncio.sleep(0.5)
        
        await self.test_12_doctor_not_found()
        await asyncio.sleep(0.5)
        
        await self.test_13_past_date_validation()
        await asyncio.sleep(0.5)
        
        await self.test_14_form_persistence_across_turns()
        await asyncio.sleep(0.5)
        
        await self.test_15_chinese_number_parsing()
        await asyncio.sleep(0.5)
        
        await self.test_16_department_based_booking()
        await asyncio.sleep(0.5)
        
        await self.test_17_form_completion_validation()
        await asyncio.sleep(0.5)
        
        await self.test_18_natural_conversation_flow()
        await asyncio.sleep(0.5)
        
        await self.test_19_multiple_forms_same_user()
        await asyncio.sleep(0.5)
        
        await self.test_20_edge_case_empty_confirm()
        await asyncio.sleep(0.5)
        
        await self.test_21_tool_usage_tracking()
        await asyncio.sleep(0.5)
        
        await self.test_22_response_metadata_includes_form()
        
        # Summary
        passed = sum(1 for r in self.test_results if r["passed"])
        total = len(self.test_results)
        
        print(f"\n{Fore.CYAN}=== Test Summary ==={Style.RESET_ALL}")
        print(f"Total tests: {total}")
        print(f"{Fore.GREEN}Passed: {passed}{Style.RESET_ALL}")
        print(f"{Fore.RED}Failed: {total - passed}{Style.RESET_ALL}")
        print(f"Success rate: {passed/total*100:.1f}%")
        
        # Save results
        with open("appointment_form_test_results.json", "w", encoding="utf-8") as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "summary": {
                    "total": total,
                    "passed": passed,
                    "failed": total - passed,
                    "success_rate": passed/total
                },
                "results": self.test_results
            }, f, ensure_ascii=False, indent=2)
        
        print(f"\nResults saved to appointment_form_test_results.json")


async def main():
    """Main test runner"""
    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code != 200:
            print(f"{Fore.RED}Error: Server not responding at {BASE_URL}{Style.RESET_ALL}")
            print("Please ensure the test server is running on port 6001")
            return
    except:
        print(f"{Fore.RED}Error: Cannot connect to server at {BASE_URL}{Style.RESET_ALL}")
        print("Please run: ./run_humansa_test_environment_v2.sh")
        return
    
    # Run tests
    tester = AppointmentFormTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    import re  # Import re module for regex
    asyncio.run(main())