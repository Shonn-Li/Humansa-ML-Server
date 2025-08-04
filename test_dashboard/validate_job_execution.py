#!/usr/bin/env python3
"""
Validate Job Execution
======================

This script validates that the enhanced job execution system is working correctly:
1. Server logs are captured properly
2. Response data is displayed correctly
3. Model is using gpt-4.1
"""

import asyncio
import httpx
import json
import time
from datetime import datetime

# API Configuration
API_BASE_URL = "http://localhost:6002"
ML_SERVER_URL = "http://localhost:6001"

async def check_servers():
    """Check if both servers are running"""
    print("🔍 Checking server status...")
    
    # Check API server
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{API_BASE_URL}/health")
            if resp.status_code == 200:
                print("✅ Test Dashboard API is running on port 6002")
            else:
                print("❌ Test Dashboard API is not responding properly")
                return False
    except Exception as e:
        print(f"❌ Test Dashboard API is not running: {e}")
        return False
    
    # Check ML server
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{ML_SERVER_URL}/health")
            if resp.status_code == 200:
                print("✅ ML Server is running on port 6001")
            else:
                print("⚠️  ML Server is not running (will be started by job)")
    except:
        print("⚠️  ML Server is not running (will be started by job)")
    
    return True

async def create_validation_job():
    """Create a job with specific tests to validate functionality"""
    print("\n📝 Creating validation job...")
    
    job_data = {
        "name": "Validation Job - Server Logs & Response Display",
        "description": "Validates server log capture and response display functionality",
        "tests": [
            {
                "test_id": "IDT_001",  # Identity test - should have simple response
                "suite": "identity"
            },
            {
                "test_id": "DOC_001",  # Doctor search - should use tools
                "suite": "medical"
            },
            {
                "test_id": "MTB_041",  # Multi-turn test - complex interaction
                "suite": "multi_turn"
            }
        ],
        "config": {
            "execution_mode": "sequential",
            "max_parallel_workers": 1,
            "timeout_per_test": 60,
            "retry_failed_tests": False,
            "continue_on_failure": True
        },
        "priority": "high"
    }
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{API_BASE_URL}/api/jobs", json=job_data)
        if resp.status_code == 200:
            job = resp.json()
            print(f"✅ Job created: {job['id']}")
            return job['id']
        else:
            print(f"❌ Failed to create job: {resp.status_code} - {resp.text}")
            return None

async def execute_job(job_id):
    """Execute the job and monitor progress"""
    print(f"\n🚀 Executing job {job_id}...")
    
    execution_data = {
        "environment_id": 1,
        "dry_run": False
    }
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{API_BASE_URL}/api/jobs/{job_id}/execute", json=execution_data)
        if resp.status_code == 200:
            result = resp.json()
            print(f"✅ Job execution started: Run ID {result['run_id']}")
            return result['run_id']
        else:
            print(f"❌ Failed to execute job: {resp.status_code} - {resp.text}")
            return None

async def monitor_job_progress(job_id, run_id):
    """Monitor job execution progress"""
    print(f"\n📊 Monitoring job progress...")
    
    start_time = time.time()
    last_progress = -1
    
    while True:
        async with httpx.AsyncClient() as client:
            # Get job status
            resp = await client.get(f"{API_BASE_URL}/api/jobs/{job_id}")
            if resp.status_code == 200:
                job = resp.json()
                
                # Get progress
                prog_resp = await client.get(f"{API_BASE_URL}/api/jobs/{job_id}/progress")
                if prog_resp.status_code == 200:
                    progress = prog_resp.json()
                    
                    # Display progress
                    completed = progress['completed_tests']
                    total = progress['total_tests']
                    if completed != last_progress:
                        print(f"\r⏳ Progress: {completed}/{total} tests completed", end="", flush=True)
                        last_progress = completed
                    
                    # Check if completed
                    if job['status'] in ['completed', 'failed', 'cancelled']:
                        print(f"\n✅ Job {job['status']} in {time.time() - start_time:.1f}s")
                        return job['status']
            
            await asyncio.sleep(1)
        
        # Timeout after 5 minutes
        if time.time() - start_time > 300:
            print("\n❌ Job execution timeout")
            return 'timeout'

async def validate_results(job_id, run_id):
    """Validate the job results"""
    print(f"\n🔍 Validating results...")
    
    async with httpx.AsyncClient() as client:
        # Get run details
        resp = await client.get(f"{API_BASE_URL}/api/jobs/{job_id}/runs/{run_id}")
        if resp.status_code != 200:
            print(f"❌ Failed to get run details: {resp.status_code}")
            return False
        
        run_data = resp.json()
        results = run_data.get('results', {})
        
        print(f"\n📋 Test Results Summary:")
        print(f"{'Test ID':<15} {'Status':<10} {'Duration':<10} {'Response':<30}")
        print("-" * 70)
        
        validation_passed = True
        
        for test_id, result in results.items():
            status = "✅ PASS" if result.get('success') else "❌ FAIL"
            duration = f"{result.get('duration', 0):.2f}s"
            
            # Check response data
            response = result.get('response', {})
            has_response = False
            response_preview = "No response"
            
            if response:
                if 'output' in response and response['output']:
                    # OpenAI Responses API format
                    has_response = True
                    text_items = [item for item in response['output'] if item.get('type') == 'text']
                    if text_items:
                        response_preview = text_items[0].get('text', '')[:50] + "..."
                elif 'choices' in response and response['choices']:
                    # Standard OpenAI format
                    has_response = True
                    response_preview = response['choices'][0].get('message', {}).get('content', '')[:50] + "..."
                elif 'full_text' in response:
                    # Enhanced format with full text
                    has_response = True
                    response_preview = response['full_text'][:50] + "..."
                elif 'message' in response:
                    has_response = True
                    response_preview = response['message'][:50] + "..."
            
            print(f"{test_id:<15} {status:<10} {duration:<10} {response_preview:<30}")
            
            if not has_response:
                print(f"   ⚠️  WARNING: No response data captured for {test_id}")
                validation_passed = False
        
        # Get detailed logs for first test
        print(f"\n📜 Checking Server Logs and Response Data...")
        
        # Get test case logs from API
        for test_id in ['IDT_001', 'DOC_001']:
            print(f"\n📋 Test: {test_id}")
            log_resp = await client.get(f"{API_BASE_URL}/api/results/test/{run_id}/{test_id}/logs")
            if log_resp.status_code == 200:
                log_data = log_resp.json()
                
                # Parse server logs
                server_logs_str = log_data.get('server_logs', '{}')
                if isinstance(server_logs_str, str):
                    server_logs = json.loads(server_logs_str)
                else:
                    server_logs = server_logs_str
                
                if isinstance(server_logs, dict) and 'logs' in server_logs:
                    logs = server_logs['logs']
                    print(f"   ✅ Server Logs: Captured {len(logs)} lines")
                    
                    # Show sample logs
                    if logs and len(logs) > 5:
                        print("   📝 Sample logs:")
                        for log_line in logs[7:10]:  # Show request details
                            print(f"      {log_line}")
                else:
                    print("   ❌ Server logs not captured properly")
                    validation_passed = False
                
                # Parse response data
                response_str = log_data.get('response', '{}')
                if isinstance(response_str, str):
                    response_data = json.loads(response_str)
                else:
                    response_data = response_str
                
                if response_data and 'output' in response_data:
                    output_text = ""
                    for item in response_data['output']:
                        if item.get('type') in ['text', 'output_text']:
                            output_text += item.get('text', '')
                    
                    if output_text:
                        print(f"   ✅ Response: {output_text[:100]}...")
                    else:
                        print("   ❌ No response text found")
                        validation_passed = False
                    
                    # Check model
                    model = response_data.get('model', 'unknown')
                    if model == 'gpt-4.1':
                        print(f"   ✅ Model: {model}")
                    else:
                        print(f"   ❌ Model: {model} (should be gpt-4.1)")
                        validation_passed = False
                else:
                    print("   ❌ Response data not captured properly")
                    validation_passed = False
                
                break  # Only check first successful test
            else:
                if test_id == 'IDT_001':
                    print(f"   ❌ Failed to get test logs: {log_resp.status_code}")
                    validation_passed = False
        
        # Check model usage
        print(f"\n🤖 Checking Model Usage...")
        model_check_passed = True
        
        for test_id, result in results.items():
            response = result.get('response', {})
            # Check if model info is available
            if 'model' in response:
                if response['model'] != 'gpt-4.1':
                    print(f"❌ {test_id} used wrong model: {response['model']}")
                    model_check_passed = False
                else:
                    print(f"✅ {test_id} used correct model: gpt-4.1")
        
        return validation_passed and model_check_passed

async def main():
    """Main validation flow"""
    print("=" * 70)
    print("TEST DASHBOARD JOB EXECUTION VALIDATION")
    print("=" * 70)
    
    # Check servers
    if not await check_servers():
        print("\n❌ Please ensure the Test Dashboard is running:")
        print("   cd test_dashboard && ./launch_dashboard.sh")
        return
    
    # Create job
    job_id = await create_validation_job()
    if not job_id:
        return
    
    # Execute job
    run_id = await execute_job(job_id)
    if not run_id:
        return
    
    # Monitor progress
    status = await monitor_job_progress(job_id, run_id)
    
    # Validate results
    if await validate_results(job_id, run_id):
        print("\n✅ VALIDATION PASSED! Server logs and response display are working correctly.")
    else:
        print("\n❌ VALIDATION FAILED! Check the implementation.")
    
    print("\n📊 View full results in dashboard: http://localhost:3020")
    print(f"   Job ID: {job_id}")
    print(f"   Run ID: {run_id}")

if __name__ == "__main__":
    asyncio.run(main())