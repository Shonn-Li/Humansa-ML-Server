#!/usr/bin/env python3
"""
Validate Enhanced Logging in Test Dashboard
==========================================

This script validates that ML server enhanced logging is properly captured.
"""

import asyncio
import httpx
import json
import time

# API Configuration
API_BASE_URL = "http://localhost:6002"

async def create_test_job():
    """Create a simple test job to validate logging"""
    print("📋 Creating test job for enhanced logging validation...")
    
    job_data = {
        "name": "Enhanced Logging Validation",
        "description": "Validate ML server agent thinking logs are captured",
        "tests": [
            {
                "test_id": "DOC_001",  # Doctor search - should trigger agent thinking
                "suite": "medical"
            },
            {
                "test_id": "APT_001",  # Appointment - complex agent interaction
                "suite": "appointment"
            }
        ],
        "config": {
            "execution_mode": "sequential",
            "max_parallel_workers": 1,
            "timeout_per_test": 60
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

async def execute_and_monitor(job_id):
    """Execute job and monitor for enhanced logs"""
    print(f"\n🚀 Executing job {job_id}...")
    
    # Execute job
    execution_data = {"environment_id": 1, "dry_run": False}
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(f"{API_BASE_URL}/api/jobs/{job_id}/execute", json=execution_data)
        if resp.status_code != 200:
            print(f"❌ Failed to execute job: {resp.status_code}")
            return
        
        result = resp.json()
        run_id = result['run_id']
        print(f"✅ Execution started: Run ID {run_id}")
        
        # Wait for completion
        print("\n⏳ Waiting for job to complete...")
        completed = False
        for i in range(60):  # Max 60 seconds
            await asyncio.sleep(1)
            
            # Check job status
            status_resp = await client.get(f"{API_BASE_URL}/api/jobs/{job_id}")
            if status_resp.status_code == 200:
                job = status_resp.json()
                if job['status'] in ['completed', 'failed']:
                    completed = True
                    print(f"\n✅ Job {job['status']}")
                    break
            
            if i % 5 == 0:
                print(".", end="", flush=True)
        
        if not completed:
            print("\n❌ Job did not complete in time")
            return
        
        # Check results and logs
        print("\n🔍 Checking enhanced logs...")
        
        # Get run details
        run_resp = await client.get(f"{API_BASE_URL}/api/jobs/{job_id}/runs/{run_id}")
        if run_resp.status_code != 200:
            print("❌ Failed to get run details")
            return
        
        run_data = run_resp.json()
        results = run_data.get('results', {})
        
        # Check each test result
        enhanced_logs_found = False
        for test_id, result in results.items():
            print(f"\n📊 Test: {test_id}")
            
            # Get test logs
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
                    print(f"  📜 Server logs: {len(logs)} lines captured")
                    
                    # Look for enhanced logging indicators
                    thinking_indicators = ['🤔', '💭', '🔧', '📊', '✅', '🏃']
                    agent_logs = []
                    
                    for log in logs:
                        if any(indicator in log for indicator in thinking_indicators):
                            agent_logs.append(log)
                            enhanced_logs_found = True
                    
                    if agent_logs:
                        print(f"  ✅ Found {len(agent_logs)} enhanced agent thinking logs!")
                        print("  📝 Sample enhanced logs:")
                        for log in agent_logs[:5]:  # Show first 5
                            print(f"     {log}")
                    else:
                        print("  ⚠️  No enhanced agent thinking logs found")
                        print("  📝 Sample logs:")
                        for log in logs[:5]:
                            print(f"     {log}")
                else:
                    print("  ❌ Server logs not in expected format")
        
        # Final verdict
        print("\n" + "="*60)
        if enhanced_logs_found:
            print("✅ SUCCESS: Enhanced ML server logging is working!")
            print("   Agent thinking process logs are being captured properly.")
        else:
            print("❌ FAILED: Enhanced logging not detected")
            print("   Possible issues:")
            print("   - ML server might not have started with HUMANSA_ENHANCED_LOGGING=true")
            print("   - Log capture might not be reading from the correct location")
            print("   - The test might not have triggered complex agent thinking")

async def main():
    """Main validation flow"""
    print("="*60)
    print("ENHANCED LOGGING VALIDATION")
    print("="*60)
    
    # Create and execute test
    job_id = await create_test_job()
    if job_id:
        await execute_and_monitor(job_id)
        print(f"\n📊 View full results at: http://localhost:3020")
        print(f"   Job ID: {job_id}")

if __name__ == "__main__":
    asyncio.run(main())