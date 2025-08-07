#!/usr/bin/env python3
"""
Test 70 test cases with fixes applied
"""

import requests
import json
import time
from datetime import datetime

DASHBOARD_API = "http://localhost:6002"

def main():
    print("🚀 Testing 70 Test Cases with Fixes")
    print("=" * 50)
    
    # Step 1: Discover tests
    print("\n1️⃣ Discovering tests...")
    resp = requests.post(f"{DASHBOARD_API}/api/tests/discover")
    if resp.status_code != 200:
        print(f"❌ Failed to discover tests: {resp.status_code}")
        return
    
    data = resp.json()
    print(f"✅ Discovered {data['valid_tests']} valid tests from {data['total_files']} files")
    
    time.sleep(1)
    
    # Step 2: Get all tests
    print("\n2️⃣ Getting available tests...")
    resp = requests.get(f"{DASHBOARD_API}/api/tests?limit=100")
    if resp.status_code != 200:
        print(f"❌ Failed to get tests: {resp.status_code}")
        return
    
    tests = resp.json()
    print(f"📋 Found {len(tests)} tests available")
    
    # Step 3: Select 70 tests
    selected_tests = tests[:70]
    test_ids = [test['id'] for test in selected_tests]
    print(f"Selected {len(test_ids)} tests for execution")
    
    # Step 4: Create job
    print(f"\n3️⃣ Creating job...")
    job_name = f"Fixed Test Run - {datetime.now().strftime('%Y%m%d_%H%M%S')}"
    job_data = {
        "name": job_name,
        "description": "Test run with all fixes applied",
        "tests": [{"test_id": test_id} for test_id in test_ids],
        "priority": "high",
        "config": {
            "parallel_execution": False,
            "continue_on_failure": True,
            "timeout_per_test": 60,
            "retry_on_failure": False,
            "tags": ["fixed", "70-tests"]
        }
    }
    
    resp = requests.post(f"{DASHBOARD_API}/api/jobs", json=job_data)
    if resp.status_code != 200:
        print(f"❌ Failed to create job: {resp.status_code} - {resp.text}")
        return
    
    job = resp.json()
    print(f"✅ Created job: {job['name']} (ID: {job['id']})")
    
    # Step 5: Execute job
    print(f"\n4️⃣ Executing job...")
    execution_data = {
        "environment_id": 1,
        "config_overrides": {},
        "dry_run": False
    }
    
    resp = requests.post(f"{DASHBOARD_API}/api/jobs/{job['id']}/execute", json=execution_data)
    if resp.status_code != 200:
        print(f"❌ Failed to execute job: {resp.status_code} - {resp.text}")
        return
    
    execution = resp.json()
    print(f"✅ Started job execution: Run ID {execution['run_id']}")
    
    # Step 6: Monitor execution
    print(f"\n5️⃣ Monitoring execution...")
    start_time = time.time()
    last_progress = -1
    
    while True:
        resp = requests.get(f"{DASHBOARD_API}/api/jobs/{job['id']}")
        if resp.status_code == 200:
            job_status = resp.json()
            
            if job_status['status'] in ['completed', 'failed', 'cancelled']:
                print(f"\n\n{'✅' if job_status['status'] == 'completed' else '❌'} Job {job_status['status']}!")
                print(f"Duration: {time.time() - start_time:.1f}s")
                print(f"Total tests: {job_status.get('total_tests', 0)}")
                print(f"Passed: {(job_status.get('total_tests', 0) - job_status.get('failed_tests', 0))}")
                print(f"Failed: {job_status.get('failed_tests', 0)}")
                break
            
            # Show progress
            progress = requests.get(f"{DASHBOARD_API}/api/jobs/{job['id']}/progress").json()
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
        
        time.sleep(2)
    
    # Step 7: Get detailed results
    print(f"\n6️⃣ Getting detailed results...")
    resp = requests.get(f"{DASHBOARD_API}/api/jobs/{job['id']}/runs/{execution['run_id']}")
    if resp.status_code == 200:
        data = resp.json()
        results = data.get('results', {})
        
        # Count by status
        passed = len([r for r in results.values() if r.get('success') == True])
        failed = len([r for r in results.values() if r.get('success') == False])
        
        print(f"\n📊 Final Results:")
        print(f"Total tests: {len(results)}")
        print(f"Passed: {passed} ({passed/len(results)*100:.1f}%)")
        print(f"Failed: {failed} ({failed/len(results)*100:.1f}%)")
        
        # Show failed test categories
        if failed > 0:
            print(f"\n❌ Failed Tests Analysis:")
            error_types = {}
            for test_id, result in results.items():
                if not result.get('success'):
                    error = result.get('error', 'Unknown error')
                    error_type = error.split(':')[0] if ':' in error else error[:50]
                    error_types[error_type] = error_types.get(error_type, 0) + 1
            
            for error_type, count in sorted(error_types.items(), key=lambda x: x[1], reverse=True):
                print(f"  - {error_type}: {count} tests")
    
    print("\n" + "=" * 50)
    print("✅ Test execution completed!")

if __name__ == "__main__":
    main()