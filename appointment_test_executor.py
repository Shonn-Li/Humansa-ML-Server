"""
Enhanced Test Executor for Appointment Forms
============================================

Extends the base TestExecutor to support conversation context
and form-specific validation.
"""

import asyncio
import aiohttp
import time
import json
import re
from typing import Dict, Any, Optional, List
from humansa_test_framework import TestExecutor, TestResult, TestCase
from test_environment.unified_test_config import TEST_ML_SERVER, TEST_USER_IDS
import logging

logger = logging.getLogger(__name__)


class AppointmentTestExecutor(TestExecutor):
    """Enhanced executor for appointment form tests with conversation support"""
    
    def __init__(self, base_url: str = None):
        super().__init__(base_url)
        self.conversation_context = {}  # Store response_ids for multi-turn
        
    async def execute_test_case(self, test_case: TestCase) -> TestResult:
        """Execute a test case with support for multi-turn conversations"""
        start_time = time.time()
        
        try:
            # Handle multi-turn conversations
            previous_response_id = None
            conversation_id = None
            
            if test_case.previous_turns:
                # Execute previous turns first
                user_id = test_case.user_context.get('user_id', TEST_USER_IDS['humansa_v2'])
                
                for i, turn in enumerate(test_case.previous_turns):
                    if turn["role"] == "user":
                        turn_data = {
                            "model": "gpt-4-turbo",
                            "input": turn["content"],
                            "user_id": user_id
                        }
                        
                        if previous_response_id:
                            turn_data["previous_response_id"] = previous_response_id
                        
                        # Execute turn
                        async with self.session.post(
                            f"{self.base_url}/v2/humansa/responses/create",
                            json=turn_data,
                            timeout=aiohttp.ClientTimeout(total=30)
                        ) as resp:
                            if resp.status == 200:
                                turn_response = await resp.json()
                                previous_response_id = turn_response.get("id")
                                conversation_id = turn_response.get("conversation_id")
                                logger.debug(f"Turn {i} executed: {previous_response_id}")
            
            # Prepare main request
            request_data = {
                "model": "gpt-4-turbo",
                "input": test_case.query,
                "user_id": test_case.user_context.get('user_id', TEST_USER_IDS['humansa_v2']),
                "metadata": {
                    "test_id": test_case.id,
                    "test_name": test_case.name,
                    "test_category": test_case.category.value
                }
            }
            
            # Add conversation context if available
            if previous_response_id:
                request_data["previous_response_id"] = previous_response_id
            
            # Make request
            async with self.session.post(
                f"{self.base_url}/v2/humansa/responses/create",
                json=request_data,
                timeout=aiohttp.ClientTimeout(total=test_case.expectations.response_time_max)
            ) as response:
                response_time = time.time() - start_time
                
                if response.status == 200:
                    response_data = await response.json()
                    
                    # Store context for future tests
                    self.conversation_context[test_case.id] = {
                        "response_id": response_data.get("id"),
                        "conversation_id": response_data.get("conversation_id"),
                        "form_id": response_data.get("metadata", {}).get("form_id")
                    }
                    
                    # Validate response
                    validation_results = await self.validate_response(
                        response_data,
                        test_case
                    )
                    
                    # Extract additional metadata
                    metadata = {
                        "status_code": response.status,
                        "response_id": response_data.get("id"),
                        "conversation_id": response_data.get("conversation_id"),
                        "form_id": response_data.get("metadata", {}).get("form_id"),
                        "agents_used": response_data.get("usage", {}).get("agents_used", []),
                        "processing_time": response_data.get("metadata", {}).get("processing_time", 0)
                    }
                    
                    return TestResult(
                        test_case=test_case,
                        passed=all(validation_results.values()),
                        response_time=response_time,
                        response_data=response_data,
                        validation_results=validation_results,
                        metadata=metadata
                    )
                else:
                    error_text = await response.text()
                    return TestResult(
                        test_case=test_case,
                        passed=False,
                        response_time=response_time,
                        error=f"HTTP {response.status}: {error_text}",
                        metadata={"status_code": response.status}
                    )
                    
        except asyncio.TimeoutError:
            return TestResult(
                test_case=test_case,
                passed=False,
                response_time=time.time() - start_time,
                error=f"Timeout after {test_case.expectations.response_time_max}s"
            )
        except Exception as e:
            return TestResult(
                test_case=test_case,
                passed=False,
                response_time=time.time() - start_time,
                error=str(e)
            )
    
    async def validate_response(self, response_data: Dict[str, Any], test_case: TestCase) -> Dict[str, bool]:
        """Enhanced validation for appointment form responses"""
        validations = {}
        expectations = test_case.expectations
        
        # Extract output text
        output_text = " ".join([
            item.get("text", "") 
            for item in response_data.get("output", []) 
            if item.get("type") in ["text", "output_text"]
        ])
        
        # Check keywords
        if expectations.keywords:
            validations["has_keywords"] = all(
                keyword.lower() in output_text.lower() 
                for keyword in expectations.keywords
            )
        
        # Check forbidden patterns
        if expectations.forbidden_patterns:
            validations["no_forbidden"] = not any(
                re.search(pattern, output_text) 
                for pattern in expectations.forbidden_patterns
            )
        
        # Check agents touched
        if expectations.agents_touched:
            agents_used = response_data.get("usage", {}).get("agents_used", [])
            validations["correct_agents"] = any(
                expected in agent 
                for expected in expectations.agents_touched 
                for agent in agents_used
            )
        
        # Check response length
        response_length = len(output_text)
        validations["length_ok"] = (
            expectations.min_response_length <= response_length <= expectations.max_response_length
        )
        
        # Form-specific validations
        metadata = test_case.metadata
        
        # Check form_id
        if metadata.get("expect_form_id"):
            validations["has_form_id"] = bool(
                response_data.get("metadata", {}).get("form_id")
            )
        
        # Check confirmation code
        if metadata.get("expect_confirmation_code"):
            pattern = metadata.get("confirmation_pattern", r"APT-\d+")
            validations["has_confirmation_code"] = bool(
                re.search(pattern, output_text)
            )
        
        # Check form completion
        if metadata.get("form_should_complete"):
            # A complete form should mention all required fields
            required_mentions = ["医生", "时间", "症状", "姓名", "电话"]
            validations["form_complete"] = all(
                field in output_text for field in required_mentions
            )
        
        # Check for alternatives/suggestions
        if metadata.get("expect_alternatives"):
            suggestion_keywords = ["推荐", "建议", "其他", "可以选择"]
            validations["has_alternatives"] = any(
                keyword in output_text for keyword in suggestion_keywords
            )
        
        # Check emergency handling
        if metadata.get("is_urgent"):
            emergency_keywords = ["紧急", "急诊", "立即", "马上", "危急"]
            validations["emergency_handled"] = any(
                keyword in output_text for keyword in emergency_keywords
            )
        
        # Log validation details for debugging
        logger.debug(f"Test {test_case.id} validations: {validations}")
        
        return validations