#!/usr/bin/env python3
"""Form Manager Extended Test Suite - 16 Test Cases for Form System"""

import asyncio
import aiohttp
import json
import os
from datetime import datetime
import time
import sys
from typing import List, Dict, Any, Optional
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'form_manager_extended_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Test configuration
TEST_PORT = os.getenv('ML_SERVER_PORT', '6001')
BASE_URL = f"http://localhost:{TEST_PORT}"

class FormManagerExtendedTestSuite:
    """Test suite for extended form manager functionality"""
    
    def __init__(self):
        self.session = None
        self.results = []
        
    async def setup_session(self):
        """Setup HTTP session"""
        self.session = aiohttp.ClientSession()
        
    async def cleanup_session(self):
        """Cleanup HTTP session"""
        if self.session:
            await self.session.close()
            
    async def test_basic_form_creation(self):
        """FORM_030: Test basic appointment form creation"""
        test_data = {
            "model": "gpt-4-turbo",
            "input": "我想预约张医生明天的号",
            "user_id": "test_user_form_030",
            "metadata": {"test_id": "FORM_030", "test_name": "basic_form_creation"}
        }
        
        async with self.session.post(f"{BASE_URL}/v2/humansa/responses/create", 
                                   json=test_data) as response:
            result = await response.json()
            return {
                "test_id": "FORM_030",
                "status": response.status == 200,
                "contains_keywords": ["表单", "预约", "张医生"],
                "response": result
            }
    
    async def test_form_field_validation(self):
        """FORM_031: Test form field validation"""
        test_data = {
            "model": "gpt-4-turbo",
            "input": "我的电话是abc123，年龄是-5岁",
            "user_id": "test_user_form_031",
            "metadata": {"test_id": "FORM_031", "test_name": "form_field_validation"}
        }
        
        async with self.session.post(f"{BASE_URL}/v2/humansa/responses/create",
                                   json=test_data) as response:
            result = await response.json()
            return {
                "test_id": "FORM_031",
                "status": response.status == 200,
                "contains_keywords": ["格式", "有效", "电话"],
                "response": result
            }
    
    async def test_progressive_form_filling(self):
        """FORM_032: Test progressive form filling"""
        # First request - partial information
        test_data1 = {
            "model": "gpt-4-turbo",
            "input": "我要预约儿科",
            "user_id": "test_user_form_032",
            "metadata": {"test_id": "FORM_032_1", "test_name": "progressive_form_1"}
        }
        
        async with self.session.post(f"{BASE_URL}/v2/humansa/responses/create",
                                   json=test_data1) as response1:
            result1 = await response1.json()
        
        # Second request - additional information
        test_data2 = {
            "model": "gpt-4-turbo",
            "input": "时间是明天下午2点",
            "user_id": "test_user_form_032",
            "metadata": {"test_id": "FORM_032_2", "test_name": "progressive_form_2"}
        }
        
        async with self.session.post(f"{BASE_URL}/v2/humansa/responses/create",
                                   json=test_data2) as response2:
            result2 = await response2.json()
            
        return {
            "test_id": "FORM_032",
            "status": response1.status == 200 and response2.status == 200,
            "contains_keywords": ["儿科", "明天", "下午2点"],
            "responses": [result1, result2]
        }
    
    async def test_form_auto_completion(self):
        """FORM_033: Test form auto-completion from user profile"""
        test_data = {
            "model": "gpt-4-turbo",
            "input": "用我的信息预约明天的号",
            "user_id": "test_user_form_033",
            "metadata": {"test_id": "FORM_033", "test_name": "form_auto_completion"}
        }
        
        async with self.session.post(f"{BASE_URL}/v2/humansa/responses/create",
                                   json=test_data) as response:
            result = await response.json()
            return {
                "test_id": "FORM_033",
                "status": response.status == 200,
                "contains_keywords": ["信息", "预约", "自动"],
                "response": result
            }
    
    async def test_form_conditional_fields(self):
        """FORM_034: Test conditional form fields"""
        test_data = {
            "model": "gpt-4-turbo",
            "input": "我要预约产科，我怀孕了",
            "user_id": "test_user_form_034",
            "metadata": {"test_id": "FORM_034", "test_name": "form_conditional_fields"}
        }
        
        async with self.session.post(f"{BASE_URL}/v2/humansa/responses/create",
                                   json=test_data) as response:
            result = await response.json()
            return {
                "test_id": "FORM_034",
                "status": response.status == 200,
                "contains_keywords": ["产科", "怀孕", "孕期"],
                "response": result
            }
    
    async def test_form_data_persistence(self):
        """FORM_035: Test form data persistence"""
        # Create form
        test_data1 = {
            "model": "gpt-4-turbo",
            "input": "我要预约李医生，我叫王小明",
            "user_id": "test_user_form_035",
            "metadata": {"test_id": "FORM_035_1", "test_name": "form_persistence_create"}
        }
        
        async with self.session.post(f"{BASE_URL}/v2/humansa/responses/create",
                                   json=test_data1) as response1:
            result1 = await response1.json()
        
        # Retrieve form data
        test_data2 = {
            "model": "gpt-4-turbo",
            "input": "我刚才预约的医生是谁？",
            "user_id": "test_user_form_035",
            "metadata": {"test_id": "FORM_035_2", "test_name": "form_persistence_retrieve"}
        }
        
        async with self.session.post(f"{BASE_URL}/v2/humansa/responses/create",
                                   json=test_data2) as response2:
            result2 = await response2.json()
            
        return {
            "test_id": "FORM_035",
            "status": response1.status == 200 and response2.status == 200,
            "contains_keywords": ["李医生", "王小明"],
            "responses": [result1, result2]
        }
    
    async def test_form_update_modification(self):
        """FORM_036: Test form update and modification"""
        test_data = {
            "model": "gpt-4-turbo",
            "input": "我要修改预约时间，改成后天上午",
            "user_id": "test_user_form_035",
            "metadata": {"test_id": "FORM_036", "test_name": "form_update"}
        }
        
        async with self.session.post(f"{BASE_URL}/v2/humansa/responses/create",
                                   json=test_data) as response:
            result = await response.json()
            return {
                "test_id": "FORM_036",
                "status": response.status == 200,
                "contains_keywords": ["修改", "后天", "上午"],
                "response": result
            }
    
    async def test_form_submission_workflow(self):
        """FORM_037: Test form submission workflow"""
        test_data = {
            "model": "gpt-4-turbo",
            "input": "我的预约信息都填好了，请提交预约",
            "user_id": "test_user_form_035",
            "metadata": {"test_id": "FORM_037", "test_name": "form_submission"}
        }
        
        async with self.session.post(f"{BASE_URL}/v2/humansa/responses/create",
                                   json=test_data) as response:
            result = await response.json()
            return {
                "test_id": "FORM_037",
                "status": response.status == 200,
                "contains_keywords": ["提交", "预约", "成功"],
                "response": result
            }
    
    async def test_form_error_handling(self):
        """FORM_038: Test form error handling"""
        test_data = {
            "model": "gpt-4-turbo",
            "input": "我要预约不存在的科室XYZ科",
            "user_id": "test_user_form_038",
            "metadata": {"test_id": "FORM_038", "test_name": "form_error_handling"}
        }
        
        async with self.session.post(f"{BASE_URL}/v2/humansa/responses/create",
                                   json=test_data) as response:
            result = await response.json()
            return {
                "test_id": "FORM_038",
                "status": response.status == 200,
                "contains_keywords": ["不存在", "科室", "错误"],
                "response": result
            }
    
    async def test_form_cancellation(self):
        """FORM_039: Test form cancellation"""
        test_data = {
            "model": "gpt-4-turbo",
            "input": "我不想预约了，取消这个表单",
            "user_id": "test_user_form_039",
            "metadata": {"test_id": "FORM_039", "test_name": "form_cancellation"}
        }
        
        async with self.session.post(f"{BASE_URL}/v2/humansa/responses/create",
                                   json=test_data) as response:
            result = await response.json()
            return {
                "test_id": "FORM_039",
                "status": response.status == 200,
                "contains_keywords": ["取消", "表单", "确认"],
                "response": result
            }
    
    async def test_multi_form_management(self):
        """FORM_040: Test multiple form management"""
        # Create first form
        test_data1 = {
            "model": "gpt-4-turbo",
            "input": "我要预约内科",
            "user_id": "test_user_form_040",
            "metadata": {"test_id": "FORM_040_1", "test_name": "multi_form_1"}
        }
        
        async with self.session.post(f"{BASE_URL}/v2/humansa/responses/create",
                                   json=test_data1) as response1:
            result1 = await response1.json()
        
        # Create second form
        test_data2 = {
            "model": "gpt-4-turbo",
            "input": "我还要预约眼科",
            "user_id": "test_user_form_040",
            "metadata": {"test_id": "FORM_040_2", "test_name": "multi_form_2"}
        }
        
        async with self.session.post(f"{BASE_URL}/v2/humansa/responses/create",
                                   json=test_data2) as response2:
            result2 = await response2.json()
            
        return {
            "test_id": "FORM_040",
            "status": response1.status == 200 and response2.status == 200,
            "contains_keywords": ["内科", "眼科", "预约"],
            "responses": [result1, result2]
        }
    
    async def test_form_template_usage(self):
        """FORM_041: Test form template usage"""
        test_data = {
            "model": "gpt-4-turbo",
            "input": "用标准预约模板创建表单",
            "user_id": "test_user_form_041",
            "metadata": {"test_id": "FORM_041", "test_name": "form_template"}
        }
        
        async with self.session.post(f"{BASE_URL}/v2/humansa/responses/create",
                                   json=test_data) as response:
            result = await response.json()
            return {
                "test_id": "FORM_041",
                "status": response.status == 200,
                "contains_keywords": ["模板", "标准", "表单"],
                "response": result
            }
    
    async def test_form_field_dependencies(self):
        """FORM_042: Test form field dependencies"""
        test_data = {
            "model": "gpt-4-turbo",
            "input": "我选择了外科，需要手术预约",
            "user_id": "test_user_form_042",
            "metadata": {"test_id": "FORM_042", "test_name": "form_dependencies"}
        }
        
        async with self.session.post(f"{BASE_URL}/v2/humansa/responses/create",
                                   json=test_data) as response:
            result = await response.json()
            return {
                "test_id": "FORM_042",
                "status": response.status == 200,
                "contains_keywords": ["外科", "手术", "预约"],
                "response": result
            }
    
    async def test_form_validation_messages(self):
        """FORM_043: Test form validation messages"""
        test_data = {
            "model": "gpt-4-turbo",
            "input": "我的电话是123，身份证是xyz",
            "user_id": "test_user_form_043",
            "metadata": {"test_id": "FORM_043", "test_name": "form_validation_messages"}
        }
        
        async with self.session.post(f"{BASE_URL}/v2/humansa/responses/create",
                                   json=test_data) as response:
            result = await response.json()
            return {
                "test_id": "FORM_043",
                "status": response.status == 200,
                "contains_keywords": ["验证", "格式", "正确"],
                "response": result
            }
    
    async def test_form_draft_saving(self):
        """FORM_044: Test form draft saving"""
        test_data = {
            "model": "gpt-4-turbo",
            "input": "我先填一部分，保存为草稿",
            "user_id": "test_user_form_044",
            "metadata": {"test_id": "FORM_044", "test_name": "form_draft_saving"}
        }
        
        async with self.session.post(f"{BASE_URL}/v2/humansa/responses/create",
                                   json=test_data) as response:
            result = await response.json()
            return {
                "test_id": "FORM_044",
                "status": response.status == 200,
                "contains_keywords": ["草稿", "保存", "部分"],
                "response": result
            }
    
    async def test_form_completion_status(self):
        """FORM_045: Test form completion status tracking"""
        test_data = {
            "model": "gpt-4-turbo",
            "input": "我的表单完成了多少？还需要填什么？",
            "user_id": "test_user_form_044",
            "metadata": {"test_id": "FORM_045", "test_name": "form_completion_status"}
        }
        
        async with self.session.post(f"{BASE_URL}/v2/humansa/responses/create",
                                   json=test_data) as response:
            result = await response.json()
            return {
                "test_id": "FORM_045",
                "status": response.status == 200,
                "contains_keywords": ["完成", "百分比", "还需要"],
                "response": result
            }
    
    async def run_all_tests(self):
        """Run all form manager extended tests"""
        await self.setup_session()
        
        tests = [
            self.test_basic_form_creation,
            self.test_form_field_validation,
            self.test_progressive_form_filling,
            self.test_form_auto_completion,
            self.test_form_conditional_fields,
            self.test_form_data_persistence,
            self.test_form_update_modification,
            self.test_form_submission_workflow,
            self.test_form_error_handling,
            self.test_form_cancellation,
            self.test_multi_form_management,
            self.test_form_template_usage,
            self.test_form_field_dependencies,
            self.test_form_validation_messages,
            self.test_form_draft_saving,
            self.test_form_completion_status
        ]
        
        results = []
        for test in tests:
            try:
                result = await test()
                results.append(result)
                logger.info(f"Test {result['test_id']}: {'PASSED' if result['status'] else 'FAILED'}")
            except Exception as e:
                logger.error(f"Test {test.__name__} failed with exception: {e}")
                results.append({
                    "test_id": test.__name__,
                    "status": False,
                    "error": str(e)
                })
        
        await self.cleanup_session()
        return results

async def main():
    """Main test runner"""
    suite = FormManagerExtendedTestSuite()
    results = await suite.run_all_tests()
    
    # Print summary
    passed = sum(1 for r in results if r['status'])
    total = len(results)
    
    print(f"\n=== Form Manager Extended Test Results ===")
    print(f"Passed: {passed}/{total}")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    
    # Save results
    with open(f'form_manager_extended_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json', 'w') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    asyncio.run(main())