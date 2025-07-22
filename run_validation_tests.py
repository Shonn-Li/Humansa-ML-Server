#!/usr/bin/env python3
"""
Validation Test Runner with Proper Timeouts
Runs critical tests to validate the multi-agent system functionality
"""

import subprocess
import time
import sys
import os
import signal
import requests
import asyncio

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

def run_validation_tests():
    """Run validation tests with proper timeouts"""
    print("\n🧪 Running validation tests...")
    print("=" * 80)
    
    # First run minimal test to verify basic functionality
    print("\n1️⃣ Running minimal functionality test...")
    result = subprocess.run(
        [sys.executable, "test_minimal.py"],
        capture_output=True,
        text=True,
        timeout=120  # 2 minute timeout
    )
    
    if result.returncode != 0:
        print("❌ Minimal test failed!")
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
        return False
    
    print("✅ Minimal test passed!")
    
    # Run quick critical tests
    print("\n2️⃣ Running quick critical tests...")
    result = subprocess.run(
        [sys.executable, "test_multi_agent_quick.py"],
        capture_output=True,
        text=True,
        timeout=300  # 5 minute timeout
    )
    
    if result.returncode != 0:
        print("❌ Quick tests failed!")
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
        return False
    
    print("✅ Quick tests passed!")
    
    # Ask if user wants to run comprehensive tests
    response = input("\n❓ Run comprehensive test suite (30+ tests, ~10 minutes)? (y/n): ")
    if response.lower() == 'y':
        print("\n3️⃣ Running comprehensive test suite...")
        print("This will take approximately 10 minutes...")
        
        # Run comprehensive tests with very long timeout
        result = subprocess.run(
            [sys.executable, "test_multi_agent_comprehensive.py"],
            capture_output=False,  # Show output in real-time
            timeout=900  # 15 minute timeout
        )
        
        if result.returncode != 0:
            print("❌ Some comprehensive tests failed!")
            return False
        
        print("✅ All comprehensive tests passed!")
    
    return True

def main():
    """Main test runner"""
    print("=" * 80)
    print("YOUWOAI ML SERVER VALIDATION TEST RUNNER")
    print("=" * 80)
    print("This will validate the multi-agent system with proper timeouts")
    print("=" * 80)
    
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
        # Run validation tests
        success = run_validation_tests()
        
        # Summary
        print("\n" + "=" * 80)
        if success:
            print("✅ VALIDATION COMPLETE - ALL TESTS PASSED!")
            print("\nKey validations confirmed:")
            print("- Context search uses context_search_call")
            print("- File attachments use file_search_call")
            print("- Web search uses web_search_call")
            print("- Citations work properly")
            print("- Multi-agent coordination successful")
        else:
            print("❌ VALIDATION FAILED - SOME TESTS DID NOT PASS")
            print("\nPlease check the error messages above")
        print("=" * 80)
        
        return 0 if success else 1
        
    finally:
        # Always stop server
        stop_test_server(server_process)

if __name__ == "__main__":
    exit(main())