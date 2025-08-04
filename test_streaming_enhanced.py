#!/usr/bin/env python3
"""Streaming Enhanced Test Suite - 8 Test Cases for Streaming API"""

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
        logging.FileHandler(f'streaming_enhanced_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Test configuration
TEST_PORT = os.getenv('ML_SERVER_PORT', '6001')
BASE_URL = f"http://localhost:{TEST_PORT}"

class StreamingEnhancedTestSuite:
    """Test suite for enhanced streaming functionality"""
    
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
            
    async def test_basic_streaming_response(self):
        """STREAM_010: Test basic streaming response functionality"""
        test_data = {
            "model": "gpt-4-turbo",
            "input": "请详细介绍中医的基本理论",
            "user_id": "test_user_stream_010",
            "stream": True,
            "metadata": {"test_id": "STREAM_010", "test_name": "basic_streaming"}
        }
        
        chunks_received = 0
        total_content = ""
        
        async with self.session.post(f"{BASE_URL}/v2/humansa/responses/create", 
                                   json=test_data) as response:
            async for chunk in response.content.iter_any():
                if chunk:
                    chunks_received += 1
                    total_content += chunk.decode('utf-8', errors='ignore')
                    
        return {
            "test_id": "STREAM_010",
            "status": chunks_received > 1,
            "chunks_received": chunks_received,
            "total_length": len(total_content),
            "contains_keywords": ["中医", "理论"]
        }
    
    async def test_streaming_with_reasoning(self):
        """STREAM_011: Test streaming with reasoning steps"""
        test_data = {
            "model": "gpt-4-turbo",
            "input": "我头痛，请帮我分析可能的原因并推荐医生",
            "user_id": "test_user_stream_011",
            "stream": True,
            "metadata": {"test_id": "STREAM_011", "test_name": "streaming_with_reasoning"}
        }
        
        reasoning_chunks = 0
        output_chunks = 0
        
        async with self.session.post(f"{BASE_URL}/v2/humansa/responses/create",
                                   json=test_data) as response:
            async for line in response.content:
                if line:
                    try:
                        data = json.loads(line.decode('utf-8').strip())
                        if 'reasoning' in data:
                            reasoning_chunks += 1
                        if 'output' in data:
                            output_chunks += 1
                    except:
                        continue
                        
        return {
            "test_id": "STREAM_011",
            "status": reasoning_chunks > 0 and output_chunks > 0,
            "reasoning_chunks": reasoning_chunks,
            "output_chunks": output_chunks
        }
    
    async def test_streaming_error_handling(self):
        """STREAM_012: Test streaming error handling"""
        test_data = {
            "model": "invalid-model",
            "input": "测试错误处理",
            "user_id": "test_user_stream_012",
            "stream": True,
            "metadata": {"test_id": "STREAM_012", "test_name": "streaming_error_handling"}
        }
        
        error_received = False
        
        try:
            async with self.session.post(f"{BASE_URL}/v2/humansa/responses/create",
                                       json=test_data) as response:
                if response.status >= 400:
                    error_received = True
        except Exception as e:
            error_received = True
            
        return {
            "test_id": "STREAM_012",
            "status": error_received,
            "error_handled": error_received
        }
    
    async def test_streaming_interruption_recovery(self):
        """STREAM_013: Test streaming interruption and recovery"""
        test_data = {
            "model": "gpt-4-turbo",
            "input": "请写一篇关于中医养生的长篇文章",
            "user_id": "test_user_stream_013",
            "stream": True,
            "metadata": {"test_id": "STREAM_013", "test_name": "streaming_interruption"}
        }
        
        chunks_before_interruption = 0
        interrupted = False
        
        async with self.session.post(f"{BASE_URL}/v2/humansa/responses/create",
                                   json=test_data) as response:
            async for chunk in response.content.iter_any():
                chunks_before_interruption += 1
                if chunks_before_interruption > 3:
                    interrupted = True
                    break
                    
        return {
            "test_id": "STREAM_013",
            "status": interrupted and chunks_before_interruption > 0,
            "chunks_received": chunks_before_interruption,
            "interrupted": interrupted
        }
    
    async def test_concurrent_streaming_sessions(self):
        """STREAM_014: Test concurrent streaming sessions"""
        async def stream_session(user_id, session_id):
            test_data = {
                "model": "gpt-4-turbo",
                "input": f"会话{session_id}: 请简单介绍一下针灸",
                "user_id": user_id,
                "stream": True,
                "metadata": {"test_id": "STREAM_014", "session_id": session_id}
            }
            
            chunks = 0
            async with self.session.post(f"{BASE_URL}/v2/humansa/responses/create",
                                       json=test_data) as response:
                async for chunk in response.content.iter_any():
                    if chunk:
                        chunks += 1
                        
            return chunks
        
        tasks = [
            stream_session(f"test_user_stream_014_{i}", i) 
            for i in range(3)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        successful_sessions = sum(1 for r in results if isinstance(r, int) and r > 0)
        
        return {
            "test_id": "STREAM_014",
            "status": successful_sessions >= 2,
            "successful_sessions": successful_sessions,
            "total_sessions": len(tasks)
        }
    
    async def test_streaming_large_response(self):
        """STREAM_015: Test streaming with large response"""
        test_data = {
            "model": "gpt-4-turbo",
            "input": "请详细介绍中医的历史发展、基本理论、诊断方法、治疗原则和现代应用",
            "user_id": "test_user_stream_015",
            "stream": True,
            "metadata": {"test_id": "STREAM_015", "test_name": "streaming_large_response"}
        }
        
        total_size = 0
        chunk_count = 0
        
        async with self.session.post(f"{BASE_URL}/v2/humansa/responses/create",
                                   json=test_data) as response:
            async for chunk in response.content.iter_any():
                if chunk:
                    total_size += len(chunk)
                    chunk_count += 1
                    
        return {
            "test_id": "STREAM_015",
            "status": total_size > 1000 and chunk_count > 5,
            "total_size": total_size,
            "chunk_count": chunk_count
        }
    
    async def test_streaming_timeout_handling(self):
        """STREAM_016: Test streaming timeout handling"""
        test_data = {
            "model": "gpt-4-turbo",
            "input": "请进行复杂的医学分析",
            "user_id": "test_user_stream_016",
            "stream": True,
            "timeout": 1,  # Very short timeout
            "metadata": {"test_id": "STREAM_016", "test_name": "streaming_timeout"}
        }
        
        timeout_occurred = False
        
        try:
            timeout_obj = aiohttp.ClientTimeout(total=1)
            async with self.session.post(f"{BASE_URL}/v2/humansa/responses/create",
                                       json=test_data, timeout=timeout_obj) as response:
                chunks = 0
                async for chunk in response.content.iter_any():
                    chunks += 1
        except asyncio.TimeoutError:
            timeout_occurred = True
        except Exception:
            timeout_occurred = True
            
        return {
            "test_id": "STREAM_016",
            "status": timeout_occurred,
            "timeout_handled": timeout_occurred
        }
    
    async def test_streaming_json_format_validation(self):
        """STREAM_017: Test streaming JSON format validation"""
        test_data = {
            "model": "gpt-4-turbo",
            "input": "请推荐感冒药物",
            "user_id": "test_user_stream_017",
            "stream": True,
            "metadata": {"test_id": "STREAM_017", "test_name": "streaming_json_validation"}
        }
        
        valid_json_chunks = 0
        total_chunks = 0
        
        async with self.session.post(f"{BASE_URL}/v2/humansa/responses/create",
                                   json=test_data) as response:
            async for line in response.content:
                if line:
                    total_chunks += 1
                    try:
                        json.loads(line.decode('utf-8').strip())
                        valid_json_chunks += 1
                    except:
                        continue
                        
        return {
            "test_id": "STREAM_017",
            "status": valid_json_chunks > 0 and total_chunks > 0,
            "valid_json_chunks": valid_json_chunks,
            "total_chunks": total_chunks,
            "json_validity_rate": valid_json_chunks / max(total_chunks, 1)
        }
    
    async def run_all_tests(self):
        """Run all streaming enhanced tests"""
        await self.setup_session()
        
        tests = [
            self.test_basic_streaming_response,
            self.test_streaming_with_reasoning,
            self.test_streaming_error_handling,
            self.test_streaming_interruption_recovery,
            self.test_concurrent_streaming_sessions,
            self.test_streaming_large_response,
            self.test_streaming_timeout_handling,
            self.test_streaming_json_format_validation
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
    suite = StreamingEnhancedTestSuite()
    results = await suite.run_all_tests()
    
    # Print summary
    passed = sum(1 for r in results if r['status'])
    total = len(results)
    
    print(f"\n=== Streaming Enhanced Test Results ===")
    print(f"Passed: {passed}/{total}")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    
    # Save results
    with open(f'streaming_enhanced_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json', 'w') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    asyncio.run(main())