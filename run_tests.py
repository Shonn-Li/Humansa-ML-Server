#!/usr/bin/env python3
"""
Test Runner for Multi-Agent System
Properly sets up and runs tests against the test server
"""

import subprocess
import time
import sys
import os
import signal
import requests

def start_test_server():
    """Start the test server on port 5002"""
    print("🚀 Starting test server on port 5002...")
    
    # Start server in subprocess
    server_process = subprocess.Popen(
        [sys.executable, "test_server.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        preexec_fn=os.setsid if os.name != 'nt' else None
    )
    
    # Wait for server to start
    max_attempts = 30
    for i in range(max_attempts):
        try:
            response = requests.get("http://localhost:5002/health")
            if response.status_code == 200:
                print("✅ Test server is running!")
                return server_process
        except:
            pass
        
        # Check if process has died
        if server_process.poll() is not None:
            stdout, stderr = server_process.communicate()
            print("❌ Test server failed to start!")
            print(f"STDOUT: {stdout.decode()}")
            print(f"STDERR: {stderr.decode()}")
            return None
        
        time.sleep(1)
        if i % 5 == 0:
            print(f"⏳ Waiting for server to start... ({i+1}/{max_attempts})")
    
    print("❌ Test server failed to start after 30 seconds")
    return None

def stop_test_server(server_process):
    """Stop the test server gracefully"""
    if server_process:
        print("\n🛑 Stopping test server...")
        try:
            if os.name == 'nt':
                server_process.terminate()
            else:
                os.killpg(os.getpgid(server_process.pid), signal.SIGTERM)
            server_process.wait(timeout=5)
            print("✅ Test server stopped")
        except:
            server_process.kill()
            print("✅ Test server killed")

def run_tests(test_file="test_multi_agent_quick.py"):
    """Run the test suite"""
    print(f"\n🧪 Running {test_file}...")
    
    # Run tests
    result = subprocess.run(
        [sys.executable, test_file],
        capture_output=False
    )
    
    return result.returncode == 0

def main():
    """Main test runner"""
    print("=" * 80)
    print("YOUWOAI ML SERVER TEST RUNNER")
    print("=" * 80)
    
    # Parse arguments
    test_file = "test_multi_agent_quick.py"
    if len(sys.argv) > 1:
        if sys.argv[1] == "full":
            test_file = "test_multi_agent_comprehensive.py"
        elif sys.argv[1].endswith(".py"):
            test_file = sys.argv[1]
    
    # Check virtual environment
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("⚠️  WARNING: Virtual environment not activated!")
        print("Run: source youwo-ml-venv/bin/activate")
        return 1
    
    # Start test server
    server_process = start_test_server()
    if not server_process:
        return 1
    
    try:
        # Run tests
        success = run_tests(test_file)
        
        # Summary
        print("\n" + "=" * 80)
        if success:
            print("✅ ALL TESTS PASSED!")
        else:
            print("❌ SOME TESTS FAILED!")
        print("=" * 80)
        
        return 0 if success else 1
        
    finally:
        # Always stop server
        stop_test_server(server_process)

if __name__ == "__main__":
    exit(main())