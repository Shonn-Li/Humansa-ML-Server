#!/usr/bin/env python3
"""
Test single test execution to debug issues
"""

import requests
import json
import time
from datetime import datetime

# Dashboard API configuration
DASHBOARD_API = "http://localhost:6002"

def main():
    print("🔍 Testing Single Test Execution")
    print("=" * 50)
    
    # Step 1: Get a single test
    print("\n1️⃣ Getting a single test...")
    resp = requests.get(f"{DASHBOARD_API}/api/tests?limit=1")
    if resp.status_code != 200:
        print(f"❌ Failed to get tests: {resp.status_code}")
        return
    
    tests = resp.json()
    if not tests:
        print("❌ No tests found!")
        return
    
    test = tests[0]
    print(f"✅ Selected test: {test['name']} ({test['id']})")
    
    # Step 2: Create job with single test
    print(f"\n2️⃣ Creating job with single test...")
    job_data = {
        "name": f"Single Test Debug - {datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "description": "Debug single test execution",
        "tests": [{"test_id": test['id']}],
        "priority": "high",
        "config": {
            "parallel_execution": False,
            "continue_on_failure": True,
            "timeout_per_test": 60,
            "retry_on_failure": False,
            "tags": ["debug", "single-test"]
        }
    }
    
    resp = requests.post(f"{DASHBOARD_API}/api/jobs", json=job_data)
    if resp.status_code != 200:
        print(f"❌ Failed to create job: {resp.status_code} - {resp.text}")
        return
    
    job = resp.json()
    print(f"✅ Created job: {job['name']} (ID: {job['id']})")
    
    # Step 3: Execute job
    print(f"\n3️⃣ Executing job...")
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
    
    # Step 4: Monitor execution with more details
    print(f"\n4️⃣ Monitoring execution...")
    for i in range(30):  # Monitor for up to 30 seconds
        resp = requests.get(f"{DASHBOARD_API}/api/jobs/{job['id']}")
        if resp.status_code == 200:
            job_status = resp.json()
            print(f"\rStatus: {job_status['status']} - Completed: {job_status.get('completed_tests', 0)}/{job_status.get('total_tests', 1)}", end='', flush=True)
            
            if job_status['status'] in ['completed', 'failed', 'cancelled']:
                print(f"\n\nFinal status: {job_status['status']}")
                break
        
        time.sleep(1)
    
    # Step 5: Get detailed results
    print(f"\n5️⃣ Getting detailed results...")
    resp = requests.get(f"{DASHBOARD_API}/api/jobs/{job['id']}/runs/{execution['run_id']}")
    if resp.status_code == 200:
        results = resp.json()
        print(f"Run status: {results['status']}")
        print(f"Results: {json.dumps(results['results'], indent=2)}")
    
    # Step 6: Get logs if available
    print(f"\n6️⃣ Getting job logs...")
    resp = requests.get(f"{DASHBOARD_API}/api/jobs/{job['id']}/logs")
    if resp.status_code == 200:
        logs_data = resp.json()
        if logs_data.get('logs'):
            print("Recent logs:")
            for log in logs_data['logs'][-10:]:
                print(f"  [{log.get('timestamp', 'N/A')}] {log.get('level', 'INFO')}: {log.get('message', '')}")
        else:
            print("No logs available")

if __name__ == "__main__":
    main()