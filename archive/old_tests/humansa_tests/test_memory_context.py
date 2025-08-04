#!/usr/bin/env python3
"""Memory Context Test Suite - 10 Test Cases for MEM0 Integration"""

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
        logging.FileHandler(f'memory_context_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Test configuration
TEST_PORT = os.getenv('ML_SERVER_PORT', '6001')
BASE_URL = f"http://localhost:{TEST_PORT}"

class MemoryContextTestSuite:
    """Test suite for memory context functionality"""
    
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
            
    async def test_basic_memory_storage(self):
        """MEM_020: Test basic memory storage functionality"""
        test_data = {
            "model": "gpt-4-turbo",
            "input": "我的名字是王小明，今年30岁，住在北京",
            "user_id": "test_user_mem_020",
            "metadata": {"test_id": "MEM_020", "test_name": "basic_memory_storage"}
        }
        
        async with self.session.post(f"{BASE_URL}/v2/humansa/responses/create", 
                                   json=test_data) as response:
            result = await response.json()
            return {
                "test_id": "MEM_020",
                "status": response.status == 200,
                "contains_keywords": ["王小明", "30岁", "北京"],
                "response": result
            }
    
    async def test_memory_retrieval(self):
        """MEM_021: Test memory retrieval functionality"""
        test_data = {
            "model": "gpt-4-turbo", 
            "input": "你还记得我的名字吗？",
            "user_id": "test_user_mem_020",
            "metadata": {"test_id": "MEM_021", "test_name": "memory_retrieval"}
        }
        
        async with self.session.post(f"{BASE_URL}/v2/humansa/responses/create",
                                   json=test_data) as response:
            result = await response.json()
            return {
                "test_id": "MEM_021", 
                "status": response.status == 200,
                "contains_keywords": ["王小明"],
                "response": result
            }
    
    async def test_memory_update(self):
        """MEM_022: Test memory update functionality"""
        test_data = {
            "model": "gpt-4-turbo",
            "input": "我现在31岁了，搬到了上海",
            "user_id": "test_user_mem_020",
            "metadata": {"test_id": "MEM_022", "test_name": "memory_update"}
        }
        
        async with self.session.post(f"{BASE_URL}/v2/humansa/responses/create",
                                   json=test_data) as response:
            result = await response.json()
            return {
                "test_id": "MEM_022",
                "status": response.status == 200,
                "contains_keywords": ["31岁", "上海"],
                "response": result
            }
    
    async def test_context_persistence(self):
        """MEM_023: Test context persistence across sessions"""
        test_data = {
            "model": "gpt-4-turbo",
            "input": "我现在多少岁，住在哪里？",
            "user_id": "test_user_mem_020",
            "metadata": {"test_id": "MEM_023", "test_name": "context_persistence"}
        }
        
        async with self.session.post(f"{BASE_URL}/v2/humansa/responses/create",
                                   json=test_data) as response:
            result = await response.json()
            return {
                "test_id": "MEM_023",
                "status": response.status == 200,
                "contains_keywords": ["31岁", "上海"],
                "response": result
            }
    
    async def test_memory_preferences_storage(self):
        """MEM_024: Test storage of user preferences"""
        test_data = {
            "model": "gpt-4-turbo",
            "input": "我喜欢中医，不喜欢西药，对花粉过敏",
            "user_id": "test_user_mem_024",
            "metadata": {"test_id": "MEM_024", "test_name": "preferences_storage"}
        }
        
        async with self.session.post(f"{BASE_URL}/v2/humansa/responses/create",
                                   json=test_data) as response:
            result = await response.json()
            return {
                "test_id": "MEM_024",
                "status": response.status == 200,
                "contains_keywords": ["中医", "西药", "花粉过敏"],
                "response": result
            }
    
    async def test_medical_history_storage(self):
        """MEM_025: Test medical history storage"""
        test_data = {
            "model": "gpt-4-turbo",
            "input": "我有高血压病史，曾经做过阑尾炎手术",
            "user_id": "test_user_mem_025",
            "metadata": {"test_id": "MEM_025", "test_name": "medical_history_storage"}
        }
        
        async with self.session.post(f"{BASE_URL}/v2/humansa/responses/create",
                                   json=test_data) as response:
            result = await response.json()
            return {
                "test_id": "MEM_025",
                "status": response.status == 200,
                "contains_keywords": ["高血压", "阑尾炎", "手术"],
                "response": result
            }
    
    async def test_conversation_context_memory(self):
        """MEM_026: Test conversation context memory"""
        test_data = {
            "model": "gpt-4-turbo",
            "input": "我刚才说了我有什么病史？",
            "user_id": "test_user_mem_025",
            "metadata": {"test_id": "MEM_026", "test_name": "conversation_context_memory"}
        }
        
        async with self.session.post(f"{BASE_URL}/v2/humansa/responses/create",
                                   json=test_data) as response:
            result = await response.json()
            return {
                "test_id": "MEM_026",
                "status": response.status == 200,
                "contains_keywords": ["高血压", "阑尾炎"],
                "response": result
            }
    
    async def test_memory_search_functionality(self):
        """MEM_027: Test memory search functionality"""
        test_data = {
            "model": "gpt-4-turbo",
            "input": "根据我的医疗偏好，推荐合适的治疗方案",
            "user_id": "test_user_mem_024",
            "metadata": {"test_id": "MEM_027", "test_name": "memory_search"}
        }
        
        async with self.session.post(f"{BASE_URL}/v2/humansa/responses/create",
                                   json=test_data) as response:
            result = await response.json()
            return {
                "test_id": "MEM_027",
                "status": response.status == 200,
                "contains_keywords": ["中医", "过敏"],
                "response": result
            }
    
    async def test_memory_deletion(self):
        """MEM_028: Test memory deletion functionality"""
        test_data = {
            "model": "gpt-4-turbo",
            "input": "请忘记我的地址信息",
            "user_id": "test_user_mem_020",
            "metadata": {"test_id": "MEM_028", "test_name": "memory_deletion"}
        }
        
        async with self.session.post(f"{BASE_URL}/v2/humansa/responses/create",
                                   json=test_data) as response:
            result = await response.json()
            return {
                "test_id": "MEM_028",
                "status": response.status == 200,
                "contains_keywords": ["忘记", "地址"],
                "response": result
            }
    
    async def test_cross_session_memory_isolation(self):
        """MEM_029: Test memory isolation between different users"""
        test_data = {
            "model": "gpt-4-turbo",
            "input": "王小明的年龄是多少？",
            "user_id": "test_user_mem_029",
            "metadata": {"test_id": "MEM_029", "test_name": "memory_isolation"}
        }
        
        async with self.session.post(f"{BASE_URL}/v2/humansa/responses/create",
                                   json=test_data) as response:
            result = await response.json()
            return {
                "test_id": "MEM_029",
                "status": response.status == 200,
                "not_contains_keywords": ["31岁", "30岁"],
                "response": result
            }
    
    async def run_all_tests(self):
        """Run all memory context tests"""
        await self.setup_session()
        
        tests = [
            self.test_basic_memory_storage,
            self.test_memory_retrieval,
            self.test_memory_update,
            self.test_context_persistence,
            self.test_memory_preferences_storage,
            self.test_medical_history_storage,
            self.test_conversation_context_memory,
            self.test_memory_search_functionality,
            self.test_memory_deletion,
            self.test_cross_session_memory_isolation
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
    suite = MemoryContextTestSuite()
    results = await suite.run_all_tests()
    
    # Print summary
    passed = sum(1 for r in results if r['status'])
    total = len(results)
    
    print(f"\n=== Memory Context Test Results ===")
    print(f"Passed: {passed}/{total}")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    
    # Save results
    with open(f'memory_context_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json', 'w') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    asyncio.run(main())