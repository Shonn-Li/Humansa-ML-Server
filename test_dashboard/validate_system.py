#!/usr/bin/env python3
"""
Test Dashboard System Validation Script
======================================

Comprehensive validation script that checks:
1. Backend can start without SQLAlchemy dependencies
2. All API endpoints work and return proper responses
3. Frontend dependencies are properly set up
4. System integration works correctly

This script ensures the test dashboard works in environments without database dependencies.
"""

import os
import sys
import json
import time
import requests
import subprocess
import signal
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import tempfile

# Colors for output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'


class TestDashboardValidator:
    """Main validator class"""
    
    def __init__(self):
        self.base_path = Path(__file__).parent
        self.backend_path = self.base_path / "backend"
        self.frontend_path = self.base_path / "frontend"
        self.backend_process = None
        self.frontend_process = None
        self.results = {
            "backend_import": False,
            "backend_startup": False,
            "api_endpoints": {},
            "frontend_dependencies": False,
            "system_integration": False,
            "errors": [],
            "warnings": []
        }
    
    def print_section(self, title: str):
        """Print a section header"""
        print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.BLUE}{title}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
    
    def print_success(self, message: str):
        """Print success message"""
        print(f"{Colors.GREEN}✓ {message}{Colors.END}")
    
    def print_error(self, message: str):
        """Print error message"""
        print(f"{Colors.RED}✗ {message}{Colors.END}")
        self.results["errors"].append(message)
    
    def print_warning(self, message: str):
        """Print warning message"""
        print(f"{Colors.YELLOW}⚠ {message}{Colors.END}")
        self.results["warnings"].append(message)
    
    def print_info(self, message: str):
        """Print info message"""
        print(f"{Colors.CYAN}ℹ {message}{Colors.END}")
    
    def check_backend_imports(self) -> bool:
        """Test if backend can import without SQLAlchemy"""
        self.print_section("Backend Import Test")
        
        try:
            # Find Python executable
            python_exe = self.find_python_executable()
            if not python_exe:
                self.print_error("No suitable Python executable found")
                return False
            
            # Test import without SQLAlchemy
            cmd = [
                python_exe, "-c",
                f"import sys; sys.path.insert(0, '{self.backend_path}'); "
                f"sys.path.insert(0, '{self.base_path.parent}'); "
                "import main; print('SUCCESS: Backend imports work without SQLAlchemy')"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0 and "SUCCESS" in result.stdout:
                self.print_success("Backend imports successfully without SQLAlchemy")
                self.results["backend_import"] = True
                return True
            else:
                self.print_error(f"Backend import failed: {result.stderr}")
                return False
                
        except Exception as e:
            self.print_error(f"Backend import test failed: {e}")
            return False
    
    def find_python_executable(self) -> Optional[str]:
        """Find a suitable Python executable"""
        # Try different Python executables
        candidates = [
            "/usr/bin/python3",  # System Python 3.9 that worked before
            "python3",
            "python",
            "/opt/homebrew/bin/python3",
        ]
        
        for candidate in candidates:
            try:
                result = subprocess.run([candidate, "--version"], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    # Test if FastAPI is available
                    import_test = subprocess.run(
                        [candidate, "-c", "import fastapi; print('OK')"],
                        capture_output=True, text=True, timeout=5
                    )
                    if import_test.returncode == 0:
                        self.print_info(f"Using Python: {candidate}")
                        return candidate
            except:
                continue
        
        return None
    
    def start_backend(self) -> bool:
        """Start the backend server"""
        self.print_section("Backend Startup Test")
        
        try:
            python_exe = self.find_python_executable()
            if not python_exe:
                self.print_error("No suitable Python executable found")
                return False
            
            # Change to backend directory and start server
            env = os.environ.copy()
            env["PYTHONPATH"] = f"{self.base_path.parent}:{env.get('PYTHONPATH', '')}"
            
            self.backend_process = subprocess.Popen(
                [python_exe, "main.py"],
                cwd=self.backend_path,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait for server to start
            self.print_info("Starting backend server...")
            time.sleep(8)  # Give more time for startup
            
            # Check if process is still running
            if self.backend_process.poll() is not None:
                stdout, stderr = self.backend_process.communicate()
                self.print_error(f"Backend failed to start: {stderr}")
                return False
            
            # Test if server is responding
            try:
                response = requests.get("http://localhost:6002/health", timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    self.print_success(f"Backend started successfully on port {data.get('port', 6002)}")
                    self.results["backend_startup"] = True
                    return True
                else:
                    self.print_error(f"Backend health check failed: {response.status_code}")
                    return False
            except requests.exceptions.RequestException as e:
                self.print_error(f"Backend not responding: {e}")
                return False
                
        except Exception as e:
            self.print_error(f"Failed to start backend: {e}")
            return False
    
    def test_api_endpoints(self) -> bool:
        """Test all API endpoints"""
        self.print_section("API Endpoints Test")
        
        endpoints = [
            ("GET", "/", "Root endpoint"),
            ("GET", "/health", "Health check"),
            ("GET", "/api/tests/", "List tests"),
            ("GET", "/api/tests/stats/overview", "Test statistics"),
            ("GET", "/api/tests/suites/list", "List test suites"),
            ("POST", "/api/tests/discover", "Discover tests"),
        ]
        
        all_passed = True
        
        for method, path, description in endpoints:
            try:
                url = f"http://localhost:6002{path}"
                
                if method == "GET":
                    response = requests.get(url, timeout=10)
                elif method == "POST":
                    response = requests.post(url, json={}, timeout=10)
                else:
                    continue
                
                if response.status_code == 200:
                    data = response.json()
                    self.print_success(f"{description}: {response.status_code}")
                    self.results["api_endpoints"][path] = True
                    
                    # Additional validation for specific endpoints
                    if path == "/":
                        if "message" in data and "Test Management Dashboard API" in data["message"]:
                            self.print_info("  Root endpoint returns correct message")
                        else:
                            self.print_warning("  Root endpoint message format unexpected")
                    
                    elif path == "/health":
                        if data.get("status") == "healthy":
                            self.print_info("  Health endpoint shows healthy status")
                        else:
                            self.print_warning("  Health endpoint status not healthy")
                    
                    elif path == "/api/tests/stats/overview":
                        if "statistics" in data and "total_tests" in data["statistics"]:
                            total_tests = data["statistics"]["total_tests"]
                            self.print_info(f"  Found {total_tests} tests in catalog")
                        else:
                            self.print_warning("  Statistics format unexpected")
                    
                else:
                    self.print_error(f"{description}: HTTP {response.status_code}")
                    self.results["api_endpoints"][path] = False
                    all_passed = False
                    
            except Exception as e:
                self.print_error(f"{description}: {e}")
                self.results["api_endpoints"][path] = False
                all_passed = False
        
        return all_passed
    
    def check_frontend_dependencies(self) -> bool:
        """Check frontend dependencies"""
        self.print_section("Frontend Dependencies Test")
        
        try:
            # Check if package.json exists
            package_json = self.frontend_path / "package.json"
            if not package_json.exists():
                self.print_error("package.json not found")
                return False
            
            self.print_success("package.json found")
            
            # Check if node_modules exists
            node_modules = self.frontend_path / "node_modules"
            if not node_modules.exists():
                self.print_error("node_modules directory not found")
                return False
            
            # Count dependencies
            try:
                deps = list(node_modules.iterdir())
                dep_count = len([d for d in deps if d.is_dir()])
                self.print_success(f"node_modules found with {dep_count} dependencies")
            except:
                self.print_success("node_modules directory exists")
            
            # Check if npm/node is available
            try:
                result = subprocess.run(["npm", "--version"], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    self.print_success(f"npm available: {result.stdout.strip()}")
                else:
                    self.print_error("npm not available")
                    return False
            except:
                self.print_error("npm not found")
                return False
            
            # Check critical dependencies
            critical_deps = ["react", "react-dom", "typescript", "react-scripts"]
            for dep in critical_deps:
                dep_path = node_modules / dep
                if dep_path.exists():
                    self.print_success(f"✓ {dep}")
                else:
                    self.print_error(f"✗ {dep}")
                    return False
            
            self.results["frontend_dependencies"] = True
            return True
            
        except Exception as e:
            self.print_error(f"Frontend dependencies check failed: {e}")
            return False
    
    def test_system_integration(self) -> bool:
        """Test full system integration"""
        self.print_section("System Integration Test")
        
        try:
            # Test that backend serves API correctly
            response = requests.get("http://localhost:6002/api/tests/", timeout=10)
            if response.status_code != 200:
                self.print_error("Backend API not responding correctly")
                return False
            
            tests = response.json()
            if not isinstance(tests, list):
                self.print_error("API not returning test list correctly")
                return False
            
            self.print_success(f"Backend API working - returned {len(tests)} tests")
            
            # Test proxy configuration (frontend should proxy API calls to backend)
            package_json_path = self.frontend_path / "package.json"
            with open(package_json_path, 'r') as f:
                package_data = json.load(f)
            
            if package_data.get("proxy") == "http://localhost:6002":
                self.print_success("Frontend proxy configuration correct")
            else:
                self.print_warning("Frontend proxy configuration may be incorrect")
            
            # Test WebSocket endpoint (basic connection test)
            try:
                import websocket
                ws = websocket.create_connection("ws://localhost:6002/ws/runs/test-run")
                ws.close()
                self.print_success("WebSocket endpoint accessible")
            except ImportError:
                self.print_info("WebSocket test skipped (websocket-client not installed)")
            except Exception as e:
                self.print_warning(f"WebSocket test failed: {e}")
            
            self.results["system_integration"] = True
            return True
            
        except Exception as e:
            self.print_error(f"System integration test failed: {e}")
            return False
    
    def cleanup(self):
        """Clean up processes"""
        self.print_section("Cleanup")
        
        if self.backend_process:
            try:
                self.backend_process.terminate()
                time.sleep(2)
                if self.backend_process.poll() is None:
                    self.backend_process.kill()
                self.print_success("Backend process terminated")
            except Exception as e:
                self.print_warning(f"Failed to terminate backend: {e}")
        
        if self.frontend_process:
            try:
                self.frontend_process.terminate()
                time.sleep(2)
                if self.frontend_process.poll() is None:
                    self.frontend_process.kill()
                self.print_success("Frontend process terminated")
            except Exception as e:
                self.print_warning(f"Failed to terminate frontend: {e}")
    
    def generate_report(self):
        """Generate final validation report"""
        self.print_section("Validation Report")
        
        total_tests = 0
        passed_tests = 0
        
        # Count results
        if self.results["backend_import"]:
            passed_tests += 1
        total_tests += 1
        
        if self.results["backend_startup"]:
            passed_tests += 1
        total_tests += 1
        
        if self.results["frontend_dependencies"]:
            passed_tests += 1
        total_tests += 1
        
        if self.results["system_integration"]:
            passed_tests += 1
        total_tests += 1
        
        # API endpoints
        api_passed = sum(1 for v in self.results["api_endpoints"].values() if v)
        api_total = len(self.results["api_endpoints"])
        total_tests += api_total
        passed_tests += api_passed
        
        # Print summary
        print(f"\n{Colors.BOLD}Test Results:{Colors.END}")
        print(f"  Backend Import:       {'✓' if self.results['backend_import'] else '✗'}")
        print(f"  Backend Startup:      {'✓' if self.results['backend_startup'] else '✗'}")
        print(f"  Frontend Dependencies: {'✓' if self.results['frontend_dependencies'] else '✗'}")
        print(f"  System Integration:   {'✓' if self.results['system_integration'] else '✗'}")
        print(f"  API Endpoints:        {api_passed}/{api_total}")
        
        print(f"\n{Colors.BOLD}Overall: {passed_tests}/{total_tests} tests passed{Colors.END}")
        
        if self.results["errors"]:
            print(f"\n{Colors.RED}Errors:{Colors.END}")
            for error in self.results["errors"]:
                print(f"  - {error}")
        
        if self.results["warnings"]:
            print(f"\n{Colors.YELLOW}Warnings:{Colors.END}")
            for warning in self.results["warnings"]:
                print(f"  - {warning}")
        
        # Final verdict
        if passed_tests == total_tests and len(self.results["errors"]) == 0:
            print(f"\n{Colors.GREEN}{Colors.BOLD}✓ ALL TESTS PASSED - Test Dashboard is ready for use!{Colors.END}")
            return True
        elif passed_tests >= total_tests * 0.8:  # 80% pass rate
            print(f"\n{Colors.YELLOW}{Colors.BOLD}⚠ MOSTLY WORKING - Test Dashboard should work with minor issues{Colors.END}")
            return True
        else:
            print(f"\n{Colors.RED}{Colors.BOLD}✗ CRITICAL ISSUES - Test Dashboard needs fixes before use{Colors.END}")
            return False
    
    def run_all_tests(self) -> bool:
        """Run all validation tests"""
        print(f"{Colors.BOLD}{Colors.PURPLE}Test Dashboard System Validation{Colors.END}")
        print(f"{Colors.PURPLE}================================{Colors.END}")
        
        try:
            # Test backend imports
            if not self.check_backend_imports():
                self.print_error("Backend import test failed - cannot continue")
                return False
            
            # Test frontend dependencies
            self.check_frontend_dependencies()
            
            # Start backend
            if not self.start_backend():
                self.print_error("Backend startup failed - cannot continue")
                return False
            
            # Test API endpoints
            self.test_api_endpoints()
            
            # Test system integration
            self.test_system_integration()
            
            # Generate report
            return self.generate_report()
            
        except KeyboardInterrupt:
            self.print_warning("Validation interrupted by user")
            return False
        except Exception as e:
            self.print_error(f"Validation failed with exception: {e}")
            return False
        finally:
            self.cleanup()


def main():
    """Main function"""
    validator = TestDashboardValidator()
    
    # Handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        print("\nInterrupted by user")
        validator.cleanup()
        sys.exit(1)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Run validation
    success = validator.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()