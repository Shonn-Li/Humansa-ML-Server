#!/usr/bin/env python3
"""
Test real execution of the test dashboard with 70 test cases.
This script creates a test suite and executes it via the API.
"""

import requests
import json
import time
from datetime import datetime

# Dashboard API configuration
DASHBOARD_API = "http://localhost:6002"

def discover_tests():
    """Discover all available tests"""
    resp = requests.post(f"{DASHBOARD_API}/api/tests/discover")
    if resp.status_code == 200:
        data = resp.json()
        print(f"✅ Discovered {data['valid_tests']} valid tests from {data['total_files']} files")
        return True
    else:
        print(f"❌ Failed to discover tests: {resp.status_code}")
        return False

def get_all_tests():
    """Get all available tests"""
    resp = requests.get(f"{DASHBOARD_API}/api/tests?limit=100")
    if resp.status_code == 200:
        tests = resp.json()
        print(f"📋 Found {len(tests)} tests available")
        return tests
    else:
        print(f"❌ Failed to get tests: {resp.status_code}")
        return []

def create_test_suite(name: str, test_ids: list):
    """Create a test suite"""
    suite_data = {
        "name": name,
        "description": "Test suite with 70 cases for real execution testing",
        "test_ids": test_ids
    }
    
    resp = requests.post(f"{DASHBOARD_API}/api/tests/suites", json=suite_data)
    if resp.status_code == 200:
        suite = resp.json()
        print(f"✅ Created test suite: {suite['name']} with {len(suite['test_ids'])} tests")
        return suite
    else:
        error = resp.text
        print(f"❌ Failed to create test suite: {resp.status_code} - {error}")
        return None

def create_job(name: str, test_ids: list):
    """Create a job with the selected tests"""
    job_data = {
        "name": name,
        "description": "Real execution test with 70 test cases",
        "tests": [{"test_id": test_id} for test_id in test_ids],
        "priority": "high",
        "config": {
            "parallel_execution": False,
            "continue_on_failure": True,
            "timeout_per_test": 60,
            "retry_on_failure": False,
            "tags": ["real-execution", "70-cases"]
        }
    }
    
    resp = requests.post(f"{DASHBOARD_API}/api/jobs", json=job_data)
    if resp.status_code == 200:
        job = resp.json()
        print(f"✅ Created job: {job['name']} (ID: {job['id']})") 
        return job
    else:
        error = resp.text
        print(f"❌ Failed to create job: {resp.status_code} - {error}")
        return None

def execute_job(job_id: str):
    """Execute a job"""
    execution_data = {
        "environment_id": 1,
        "config_overrides": {},
        "dry_run": False
    }
    
    resp = requests.post(f"{DASHBOARD_API}/api/jobs/{job_id}/execute", json=execution_data)
    if resp.status_code == 200:
        result = resp.json()
        print(f"✅ Started job execution: Run ID {result['run_id']}")
        return result
    else:
        error = resp.text
        print(f"❌ Failed to execute job: {resp.status_code} - {error}")
        return None

def monitor_job(job_id: str, run_id: str):
    """Monitor job execution progress"""
    print(f"\n📊 Monitoring job execution...")
    
    start_time = time.time()
    last_progress = -1
    
    while True:
        # Get job status
        resp = requests.get(f"{DASHBOARD_API}/api/jobs/{job_id}")
        if resp.status_code == 200:
            job = resp.json()
            
            if job['status'] in ['completed', 'failed', 'cancelled']:
                print(f"\n{'✅' if job['status'] == 'completed' else '❌'} Job {job['status']}!")
                print(f"Duration: {time.time() - start_time:.1f}s")
                print(f"Total tests: {job.get('total_tests', 0)}")
                print(f"Passed: {(job.get('total_tests', 0) - job.get('failed_tests', 0))}")
                print(f"Failed: {job.get('failed_tests', 0)}")
                return job
            
            # Show progress
            if job.get('progress'):
                progress = job['progress']
                completed = progress.get('completed_tests', 0)
                total = progress.get('total_tests', 1)
                percent = int((completed / total) * 100)
                
                if percent != last_progress:
                    elapsed = time.time() - start_time
                    if completed > 0:
                        rate = completed / elapsed
                        eta = (total - completed) / rate if rate > 0 else 0
                        print(f"\rProgress: {percent}% ({completed}/{total}) - "
                              f"Elapsed: {elapsed:.1f}s - ETA: {eta:.1f}s - "
                              f"Rate: {rate:.1f} tests/s", end='', flush=True)
                    else:
                        print(f"\rProgress: {percent}% ({completed}/{total}) - "
                              f"Elapsed: {elapsed:.1f}s", end='', flush=True)
                    last_progress = percent
        
        time.sleep(2)  # Poll every 2 seconds

def get_job_results(job_id: str, run_id: str):
    """Get detailed job results"""
    resp = requests.get(f"{DASHBOARD_API}/api/jobs/{job_id}/runs/{run_id}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"\n📊 Detailed Results:")
        
        # Get results dict
        results = data.get('results', {})
        print(f"Total tests: {len(results)}")
        
        # Count by status
        status_counts = {}
        for test_id, test_data in results.items():
            status = test_data.get('status', 'unknown')
            status_counts[status] = status_counts.get(status, 0) + 1
        
        print("\nResults by status:")
        for status, count in sorted(status_counts.items()):
            print(f"  {status}: {count}")
        
        # Show some failed tests
        failed_tests = [(test_id, test_data) for test_id, test_data in results.items() 
                       if test_data.get('status') == 'failed' or not test_data.get('success')]
        if failed_tests:
            print(f"\nFirst 5 failed tests:")
            for test_id, test_data in failed_tests[:5]:
                test_name = test_data.get('test_name', test_id)
                print(f"  - {test_name} ({test_id})")
                if test_data.get('error'):
                    print(f"    Error: {test_data['error']}")
        
        return data
    else:
        print(f"❌ Failed to get results: {resp.status_code}")
        return None

def main():
    """Main test execution flow"""
    print("🚀 Starting Real Test Execution")
    print("=" * 50)
    
    # Step 1: Discover tests
    print("\n1️⃣ Discovering tests...")
    if not discover_tests():
        print("Failed to discover tests. Make sure the dashboard backend is running.")
        return
    
    time.sleep(1)
    
    # Step 2: Get all tests
    print("\n2️⃣ Getting available tests...")
    tests = get_all_tests()
    if not tests:
        print("No tests found!")
        return
    
    # Step 3: Select 70 tests (or all if less than 70)
    selected_tests = tests[:70]
    test_ids = [test['id'] for test in selected_tests]
    print(f"Selected {len(test_ids)} tests for execution")
    
    # Show test distribution
    suite_counts = {}
    for test in selected_tests:
        suite = test.get('suite', 'unknown')
        suite_counts[suite] = suite_counts.get(suite, 0) + 1
    
    print("\nTest distribution by suite:")
    for suite, count in sorted(suite_counts.items()):
        print(f"  {suite}: {count} tests")
    
    # Step 4: Create job (skip suite creation)
    # Step 5: Create job
    print(f"\n4️⃣ Creating job...")
    job_name = f"Real Execution Test - {datetime.now().strftime('%Y%m%d_%H%M%S')}"
    job = create_job(job_name, test_ids)
    if not job:
        print("Failed to create job!")
        return
    
    # Step 6: Execute job
    print(f"\n5️⃣ Executing job...")
    execution = execute_job(job['id'])
    if not execution:
        print("Failed to execute job!")
        return
    
    # Step 7: Monitor execution
    print(f"\n6️⃣ Monitoring execution...")
    final_job = monitor_job(job['id'], execution['run_id'])
    
    # Step 8: Get detailed results
    print(f"\n7️⃣ Getting detailed results...")
    results = get_job_results(job['id'], execution['run_id'])
    
    print("\n" + "=" * 50)
    print("✅ Test execution completed!")
    
    # Final summary
    if final_job:
        success_rate = ((final_job.get('total_tests', 0) - final_job.get('failed_tests', 0)) / 
                       final_job.get('total_tests', 1) * 100)
        print(f"\nFinal Summary:")
        print(f"  Job ID: {job['id']}")
        print(f"  Run ID: {execution['run_id']}")
        print(f"  Success Rate: {success_rate:.1f}%")
        print(f"  Status: {final_job['status']}")

if __name__ == "__main__":
    main()