#!/usr/bin/env python3
"""Execute a test job to verify the system works"""

import requests
import json
import time

# Wait for backend to be ready
print("Waiting for backend to be ready...")
for i in range(10):
    try:
        resp = requests.get("http://localhost:6002/health")
        if resp.status_code == 200:
            print("✓ Backend is ready")
            break
    except:
        pass
    time.sleep(1)
else:
    print("✗ Backend is not responding")
    exit(1)

# Get list of jobs
print("\nFetching available jobs...")
resp = requests.get("http://localhost:6002/api/jobs")
if resp.status_code != 200:
    print(f"✗ Failed to get jobs: {resp.status_code}")
    exit(1)

jobs = resp.json()
if not jobs:
    print("✗ No jobs available")
    exit(1)

# Take the first job
job = jobs[0]
job_id = job['id']
test_count = job.get('test_count', 0)
print(f"✓ Found job: {job_id} with {test_count} tests")

# Execute the job
print(f"\nExecuting job {job_id}...")
resp = requests.post(
    f"http://localhost:6002/api/jobs/{job_id}/execute",
    json={"environment_id": 1}  # Use numeric ID
)

if resp.status_code != 200:
    print(f"✗ Failed to execute job: {resp.status_code}")
    print(f"Response: {resp.text}")
    exit(1)

result = resp.json()
run_id = result.get('run_id')
print(f"✓ Job execution started with run_id: {run_id}")

# Wait for completion
print("\nWaiting for job to complete...")
for i in range(60):  # Wait up to 60 seconds
    resp = requests.get(f"http://localhost:6002/api/runs/{run_id}")
    if resp.status_code == 200:
        run_data = resp.json()
        status = run_data.get('status')
        if status == 'completed':
            print(f"✓ Job completed successfully!")
            print(f"  Passed: {run_data.get('passed', 0)}")
            print(f"  Failed: {run_data.get('failed', 0)}")
            print(f"  Total: {run_data.get('total', 0)}")
            break
        elif status == 'failed':
            print(f"✗ Job failed")
            break
    time.sleep(1)
    if i % 5 == 0:
        print(f"  Status: {status if 'status' in locals() else 'checking'}...")

print("\n✓ Test complete!")