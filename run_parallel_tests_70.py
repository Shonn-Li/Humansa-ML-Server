#!/usr/bin/env python3
"""
Run 70+ HUMANSA Tests in Parallel
=================================

Runs the full 70+ test suite in parallel batches to complete in under 2 minutes.
"""

import asyncio
import aiohttp
import time
import os
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
import uuid

# Setup environment
os.environ['ENVIRONMENT'] = 'test'
os.environ['DB_HOST'] = 'localhost'
os.environ['DB_PORT'] = '5454'
os.environ['DB_USER'] = 'postgres'
os.environ['DB_PASSWORD'] = '12931'
os.environ['DB_NAME'] = 'test4'
os.environ['ML_SERVER_PORT'] = '6001'

# Import test cases
try:
    from test_HUMANSA_v2_70_cases_multiturn import SINGLE_TURN_TEST_CASES, MULTI_TURN_TEST_CASES
    print(f"✅ Imported {len(SINGLE_TURN_TEST_CASES)} single-turn and {len(MULTI_TURN_TEST_CASES)} multi-turn test cases")
except ImportError as e:
    print(f"❌ Failed to import test cases: {e}")
    sys.exit(1)

# Configuration
BASE_URL = "http://localhost:6001"
BATCH_SIZE = 10  # Tests per batch
MAX_WORKERS = 7  # Parallel workers to stay under 2 minutes


class ParallelTestExecutor:
    """Execute tests in parallel with isolated contexts"""
    
    def __init__(self, worker_id: int):
        self.worker_id = worker_id
        self.session = None
        # Unique user prefix per worker to avoid conflicts
        self.user_prefix = f"parallel_worker_{worker_id}_{int(time.time())}"
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def execute_test(self, test_case: Dict[str, Any], test_index: int) -> Dict[str, Any]:
        """Execute a single test case"""
        start_time = time.time()
        
        # Create unique user ID
        user_id = f"{self.user_prefix}_test_{test_index}"
        
        try:
            # Prepare request
            request_data = {
                "model": "gpt-4-turbo",
                "input": test_case['query'],
                "user_id": user_id,
                "metadata": {
                    "test_id": test_case.get('id'),
                    "test_name": test_case.get('name'),
                    "worker_id": self.worker_id
                }
            }
            
            # Use non-streaming for faster execution
            endpoint = "/v2/humansa/responses/create"
            
            async with self.session.post(f"{BASE_URL}{endpoint}", json=request_data) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    return {
                        "test_id": test_case.get('id'),
                        "success": False,
                        "error": f"API error {resp.status}: {error_text}",
                        "response_time": time.time() - start_time
                    }
                
                result = await resp.json()
                
                # Check response
                response_text = result.get('response', '')
                expected_keywords = test_case.get('expected_keywords', [])
                
                # Simple keyword validation
                found_keywords = []
                missing_keywords = []
                for keyword in expected_keywords:
                    if keyword.lower() in response_text.lower():
                        found_keywords.append(keyword)
                    else:
                        missing_keywords.append(keyword)
                
                return {
                    "test_id": test_case.get('id'),
                    "test_name": test_case.get('name'),
                    "success": len(missing_keywords) == 0,
                    "response_length": len(response_text),
                    "found_keywords": found_keywords,
                    "missing_keywords": missing_keywords,
                    "response_time": time.time() - start_time,
                    "worker_id": self.worker_id
                }
                
        except Exception as e:
            return {
                "test_id": test_case.get('id'),
                "success": False,
                "error": str(e),
                "response_time": time.time() - start_time,
                "worker_id": self.worker_id
            }
    
    async def execute_batch(self, test_batch: List[Dict[str, Any]], batch_id: int) -> List[Dict[str, Any]]:
        """Execute a batch of tests"""
        print(f"🔄 Worker {self.worker_id} starting batch {batch_id} with {len(test_batch)} tests")
        
        results = []
        for i, test_case in enumerate(test_batch):
            result = await self.execute_test(test_case, batch_id * BATCH_SIZE + i)
            results.append(result)
            
            # Log progress
            if result['success']:
                print(f"✅ Worker {self.worker_id}: Test {test_case['id']} passed ({result['response_time']:.2f}s)")
            else:
                print(f"❌ Worker {self.worker_id}: Test {test_case['id']} failed ({result.get('error', 'Missing keywords')})")
        
        return results


async def run_worker(worker_id: int, test_batches: List[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """Run a worker processing its assigned batches"""
    all_results = []
    
    async with ParallelTestExecutor(worker_id) as executor:
        for batch_id, batch in enumerate(test_batches):
            batch_results = await executor.execute_batch(batch, batch_id)
            all_results.extend(batch_results)
    
    return all_results


async def main():
    """Main execution function"""
    print("="*60)
    print("HUMANSA Parallel Test Execution")
    print("="*60)
    
    # Combine all test cases
    all_tests = SINGLE_TURN_TEST_CASES + MULTI_TURN_TEST_CASES
    total_tests = len(all_tests)
    
    print(f"📊 Total test cases: {total_tests}")
    print(f"⚙️  Batch size: {BATCH_SIZE}")
    print(f"👥 Parallel workers: {MAX_WORKERS}")
    
    # Check server health
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BASE_URL}/v2/humansa/health") as resp:
                if resp.status == 200:
                    print("✅ Server is healthy")
                else:
                    print("❌ Server health check failed")
                    return
    except Exception as e:
        print(f"❌ Cannot connect to server: {e}")
        return
    
    # Split tests into batches
    batches = []
    for i in range(0, total_tests, BATCH_SIZE):
        batch = all_tests[i:i+BATCH_SIZE]
        batches.append(batch)
    
    total_batches = len(batches)
    print(f"📦 Total batches: {total_batches}")
    
    # Distribute batches among workers
    worker_batches = [[] for _ in range(MAX_WORKERS)]
    for i, batch in enumerate(batches):
        worker_id = i % MAX_WORKERS
        worker_batches[worker_id].append(batch)
    
    # Start timing
    start_time = time.time()
    print(f"\n🚀 Starting parallel execution at {datetime.now().strftime('%H:%M:%S')}")
    
    # Run all workers in parallel
    worker_tasks = []
    for worker_id in range(MAX_WORKERS):
        if worker_batches[worker_id]:  # Only create worker if it has batches
            task = run_worker(worker_id, worker_batches[worker_id])
            worker_tasks.append(task)
    
    # Wait for all workers to complete
    all_results = await asyncio.gather(*worker_tasks)
    
    # Flatten results
    final_results = []
    for worker_results in all_results:
        final_results.extend(worker_results)
    
    # Calculate statistics
    end_time = time.time()
    total_time = end_time - start_time
    
    successful_tests = sum(1 for r in final_results if r['success'])
    failed_tests = len(final_results) - successful_tests
    
    # Save results
    results_file = f"parallel_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, 'w') as f:
        json.dump({
            "total_tests": total_tests,
            "successful": successful_tests,
            "failed": failed_tests,
            "success_rate": successful_tests / total_tests,
            "total_time": total_time,
            "average_time_per_test": total_time / total_tests,
            "configuration": {
                "batch_size": BATCH_SIZE,
                "max_workers": MAX_WORKERS
            },
            "results": final_results
        }, f, indent=2)
    
    # Print summary
    print(f"\n{'='*60}")
    print("EXECUTION SUMMARY")
    print(f"{'='*60}")
    print(f"⏱️  Total time: {total_time:.2f} seconds")
    print(f"📈 Tests executed: {len(final_results)}")
    print(f"✅ Successful: {successful_tests}")
    print(f"❌ Failed: {failed_tests}")
    print(f"📊 Success rate: {(successful_tests/total_tests*100):.1f}%")
    print(f"⚡ Average time per test: {total_time/total_tests:.2f}s")
    print(f"💾 Results saved to: {results_file}")
    
    # Performance analysis
    if total_time < 120:
        print(f"\n🎉 Goal achieved! Completed in under 2 minutes!")
    else:
        print(f"\n⚠️  Took longer than 2 minutes. Consider increasing MAX_WORKERS.")
    
    # Show failed test details
    if failed_tests > 0:
        print(f"\n❌ Failed tests:")
        for result in final_results:
            if not result['success']:
                print(f"  - Test {result['test_id']}: {result.get('error', 'Missing keywords: ' + str(result.get('missing_keywords', [])))}")


if __name__ == "__main__":
    asyncio.run(main())