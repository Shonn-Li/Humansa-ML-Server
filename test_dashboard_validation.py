#!/usr/bin/env python3
"""Validate the test dashboard is working correctly"""

import requests
import time
import subprocess
import sys

def test_dashboard():
    print("Testing Test Dashboard...")
    
    # Start the dashboard
    print("Starting dashboard...")
    process = subprocess.Popen(
        ["python3", "test_dashboard_final.py"],
        env={"ML_DIGIT": "5", **subprocess.os.environ},
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for startup
    time.sleep(5)
    
    try:
        # Test endpoints
        endpoints = [
            ("/", "Frontend HTML"),
            ("/api/environment", "Environment API"),
            ("/api/tests/all", "All Tests API"),
            ("/api/tests/category/appointment", "Category API"),
            ("/api/jobs/history", "Jobs History API")
        ]
        
        all_passed = True
        
        for endpoint, name in endpoints:
            try:
                url = f"http://localhost:6002{endpoint}"
                print(f"\nTesting {name}: {url}")
                response = requests.get(url, timeout=5)
                
                if response.status_code == 200:
                    print(f"✓ {name}: OK")
                    if endpoint == "/api/tests/all":
                        data = response.json()
                        print(f"  Total tests: {data.get('total', 0)}")
                        print(f"  Categories: {len(data.get('by_category', {}))}")
                else:
                    print(f"✗ {name}: {response.status_code}")
                    all_passed = False
                    
            except Exception as e:
                print(f"✗ {name}: {str(e)}")
                all_passed = False
        
        # Check if any 404s in stderr
        stderr = process.stderr.read().decode() if process.stderr else ""
        if "404" in stderr:
            print("\nWarning: Found 404 errors in logs")
            all_passed = False
            
        return all_passed
        
    finally:
        # Clean up
        process.terminate()
        time.sleep(1)
        process.kill()

if __name__ == "__main__":
    success = test_dashboard()
    sys.exit(0 if success else 1)