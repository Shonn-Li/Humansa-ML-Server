#!/usr/bin/env python3
"""
HUMANSA Comprehensive Test Runner
=================================

Run comprehensive tests using the modular test framework.
Supports various test modes and configurations.
"""

import asyncio
import argparse
import logging
import sys
from pathlib import Path
from typing import List, Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from humansa_test_framework import (
    TestCaseManager,
    TestCaseGenerator,
    ParallelTestRunner,
    TestReporter,
    TestCategory,
    TestCase
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def quick_test(count: int = 20):
    """Run a quick test with a small number of test cases"""
    logger.info(f"Running quick test with {count} test cases")
    
    manager = TestCaseManager()
    generator = TestCaseGenerator(manager)
    runner = ParallelTestRunner()
    reporter = TestReporter()
    
    # Generate a small set of diverse test cases
    test_cases = []
    test_cases.extend(generator.generate_medical_consultation_tests(count // 4))
    test_cases.extend(generator.generate_appointment_tests(count // 4))
    test_cases.extend(generator.generate_product_recommendation_tests(count // 4))
    test_cases.extend(generator.generate_edge_cases(count // 4))
    
    # Run tests
    results = await runner.run_tests(test_cases, batch_size=5)
    
    # Generate report
    report_path = reporter.generate_report(test_cases, results, "quick_test")
    logger.info(f"Quick test completed. Report: {report_path}")
    
    # Print summary
    passed = sum(1 for r in results if r.success)
    print(f"\nQuick Test Summary:")
    print(f"  Total: {len(test_cases)}")
    print(f"  Passed: {passed}")
    print(f"  Failed: {len(results) - passed}")
    print(f"  Success Rate: {(passed/len(results)*100):.2f}%")


async def category_test(category: TestCategory, count: int = 50):
    """Run tests for a specific category"""
    logger.info(f"Running {category.value} tests with {count} test cases")
    
    manager = TestCaseManager()
    generator = TestCaseGenerator(manager)
    runner = ParallelTestRunner()
    reporter = TestReporter()
    
    # Generate test cases for specific category
    if category == TestCategory.MEDICAL_CONSULTATION:
        test_cases = generator.generate_medical_consultation_tests(count)
    elif category == TestCategory.APPOINTMENT:
        test_cases = generator.generate_appointment_tests(count)
    elif category == TestCategory.PRODUCT_RECOMMENDATION:
        test_cases = generator.generate_product_recommendation_tests(count)
    elif category == TestCategory.MULTI_TURN:
        test_cases = generator.generate_multi_turn_tests(count)
    elif category == TestCategory.EDGE_CASE:
        test_cases = generator.generate_edge_cases(count)
    elif category == TestCategory.STRESS_TEST:
        test_cases = generator.generate_stress_tests(count)
    else:
        logger.error(f"Unsupported category: {category}")
        return
    
    # Run tests
    results = await runner.run_tests(test_cases, batch_size=10)
    
    # Generate report
    report_path = reporter.generate_report(test_cases, results, f"{category.value}_test")
    logger.info(f"Category test completed. Report: {report_path}")


async def full_test(count: int = 1000):
    """Run full comprehensive test suite"""
    logger.info(f"Running full test suite with {count} test cases")
    
    manager = TestCaseManager()
    generator = TestCaseGenerator(manager)
    runner = ParallelTestRunner()
    reporter = TestReporter()
    
    # Check if we need to generate new tests
    existing_tests = manager.get_test_cases()
    if len(existing_tests) < count:
        logger.info(f"Generating {count - len(existing_tests)} new test cases...")
        generator.generate_all_test_cases(count)
    
    # Get all test cases
    test_cases = manager.get_test_cases()[:count]
    
    # Run tests in larger batches for full test
    results = await runner.run_tests(test_cases, batch_size=50)
    
    # Generate comprehensive report
    report_path = reporter.generate_report(test_cases, results, "full_test")
    logger.info(f"Full test completed. Report: {report_path}")
    
    # Print detailed summary
    print(f"\nFull Test Summary:")
    print(f"  Total Test Cases: {len(test_cases)}")
    print(f"  Executed: {len(results)}")
    
    # Category breakdown
    category_counts = {}
    for tc in test_cases:
        cat = tc.category.value
        if cat not in category_counts:
            category_counts[cat] = {'total': 0, 'executed': 0, 'passed': 0}
        category_counts[cat]['total'] += 1
    
    for result in results:
        tc = next((t for t in test_cases if t.id == result.test_case_id), None)
        if tc:
            cat = tc.category.value
            category_counts[cat]['executed'] += 1
            if result.success:
                category_counts[cat]['passed'] += 1
    
    print("\n  By Category:")
    for cat, counts in category_counts.items():
        if counts['executed'] > 0:
            success_rate = (counts['passed'] / counts['executed']) * 100
            print(f"    {cat}: {counts['passed']}/{counts['executed']} ({success_rate:.1f}%)")


async def parallel_stress_test(concurrent_users: int = 10, requests_per_user: int = 10):
    """Run parallel stress test simulating multiple concurrent users"""
    logger.info(f"Running parallel stress test: {concurrent_users} users, {requests_per_user} requests each")
    
    manager = TestCaseManager()
    generator = TestCaseGenerator(manager)
    
    # Generate test cases
    test_cases = generator.generate_stress_tests(concurrent_users * requests_per_user)
    
    # Split test cases among users
    user_batches = []
    for i in range(concurrent_users):
        start_idx = i * requests_per_user
        end_idx = start_idx + requests_per_user
        user_batches.append(test_cases[start_idx:end_idx])
    
    # Run all user batches concurrently
    async def run_user_batch(user_id: int, batch: List[TestCase]):
        logger.info(f"User {user_id} starting {len(batch)} requests")
        runner = ParallelTestRunner()
        return await runner.run_tests(batch, batch_size=requests_per_user)
    
    # Execute all users concurrently
    all_results = await asyncio.gather(
        *[run_user_batch(i, batch) for i, batch in enumerate(user_batches)]
    )
    
    # Flatten results
    results = []
    for user_results in all_results:
        results.extend(user_results)
    
    # Generate report
    reporter = TestReporter()
    report_path = reporter.generate_report(test_cases, results, "parallel_stress_test")
    logger.info(f"Parallel stress test completed. Report: {report_path}")
    
    # Calculate statistics
    total_requests = len(results)
    successful_requests = sum(1 for r in results if r.success)
    avg_response_time = sum(r.response_time for r in results) / len(results) if results else 0
    
    print(f"\nParallel Stress Test Summary:")
    print(f"  Concurrent Users: {concurrent_users}")
    print(f"  Requests per User: {requests_per_user}")
    print(f"  Total Requests: {total_requests}")
    print(f"  Successful: {successful_requests} ({(successful_requests/total_requests*100):.1f}%)")
    print(f"  Average Response Time: {avg_response_time:.2f}s")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="HUMANSA Comprehensive Test Runner")
    parser.add_argument(
        "--mode",
        choices=["quick", "category", "full", "stress"],
        default="quick",
        help="Test mode to run"
    )
    parser.add_argument(
        "--count",
        type=int,
        default=None,
        help="Number of test cases to run"
    )
    parser.add_argument(
        "--category",
        choices=[c.value for c in TestCategory],
        help="Category for category mode"
    )
    parser.add_argument(
        "--concurrent-users",
        type=int,
        default=10,
        help="Number of concurrent users for stress test"
    )
    parser.add_argument(
        "--requests-per-user",
        type=int,
        default=10,
        help="Requests per user for stress test"
    )
    
    args = parser.parse_args()
    
    # Run appropriate test mode
    if args.mode == "quick":
        count = args.count or 20
        asyncio.run(quick_test(count))
    
    elif args.mode == "category":
        if not args.category:
            print("Error: --category required for category mode")
            sys.exit(1)
        count = args.count or 50
        category = TestCategory(args.category)
        asyncio.run(category_test(category, count))
    
    elif args.mode == "full":
        count = args.count or 1000
        asyncio.run(full_test(count))
    
    elif args.mode == "stress":
        asyncio.run(parallel_stress_test(args.concurrent_users, args.requests_per_user))


if __name__ == "__main__":
    main()