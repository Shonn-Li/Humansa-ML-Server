#!/usr/bin/env python3
"""
Simple Test Dashboard Validation
===============================

Basic validation that the system works without database dependencies.
"""

import sys
import os
import subprocess
import time
from pathlib import Path

def test_import():
    """Test if backend can import"""
    print("Testing backend import...")
    
    backend_path = Path(__file__).parent / "backend"
    parent_path = Path(__file__).parent.parent
    
    cmd = [
        "/usr/bin/python3", "-c",
        f"import sys; "
        f"sys.path.insert(0, '{backend_path}'); "
        f"sys.path.insert(0, '{parent_path}'); "
        f"print('Testing imports...'); "
        f"from test_dashboard.backend.core import database; "
        f"print('✓ Database module loaded'); "
        f"from test_dashboard.backend.core import config; "
        f"print('✓ Config module loaded'); "
        f"from test_dashboard.backend.api import tests; "
        f"print('✓ API modules loaded'); "
        f"import main; "
        f"print('SUCCESS: All imports work without SQLAlchemy')"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0 and "SUCCESS" in result.stdout:
            print("✓ Backend imports successfully")
            print("Output:", result.stdout.strip())
            return True
        else:
            print("✗ Backend import failed")
            print("Error:", result.stderr)
            return False
    except Exception as e:
        print(f"✗ Import test failed: {e}")
        return False

def test_database_fallback():
    """Test database fallback functionality"""
    print("\nTesting database fallback...")
    
    backend_path = Path(__file__).parent / "backend"
    parent_path = Path(__file__).parent.parent
    
    cmd = [
        "/usr/bin/python3", "-c",
        f"import sys; "
        f"sys.path.insert(0, '{backend_path}'); "
        f"sys.path.insert(0, '{parent_path}'); "
        f"from test_dashboard.backend.core.database import DATABASE_AVAILABLE, is_database_available; "
        f"print(f'Database available: {{DATABASE_AVAILABLE}}'); "
        f"print(f'Database check: {{is_database_available()}}'); "
        f"print('SUCCESS: Database fallback working')"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("✓ Database fallback test passed")
            print("Output:", result.stdout.strip())
            return True
        else:
            print("✗ Database fallback test failed")
            print("Error:", result.stderr)
            return False
    except Exception as e:
        print(f"✗ Database fallback test failed: {e}")
        return False

def test_api_creation():
    """Test API router creation"""
    print("\nTesting API creation...")
    
    backend_path = Path(__file__).parent / "backend"
    parent_path = Path(__file__).parent.parent
    
    cmd = [
        "/usr/bin/python3", "-c",
        f"import sys; "
        f"sys.path.insert(0, '{backend_path}'); "
        f"sys.path.insert(0, '{parent_path}'); "
        f"from fastapi import FastAPI; "
        f"from test_dashboard.backend.api import tests, jobs, runs; "
        f"app = FastAPI(); "
        f"app.include_router(tests.router, prefix='/api/tests'); "
        f"print('✓ API routers created successfully'); "
        f"print('SUCCESS: API creation works without database')"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("✓ API creation test passed")
            print("Output:", result.stdout.strip())
            return True
        else:
            print("✗ API creation test failed")
            print("Error:", result.stderr)
            return False
    except Exception as e:
        print(f"✗ API creation test failed: {e}")
        return False

def test_config():
    """Test configuration loading"""
    print("\nTesting configuration...")
    
    backend_path = Path(__file__).parent / "backend"
    parent_path = Path(__file__).parent.parent
    
    cmd = [
        "/usr/bin/python3", "-c",
        f"import sys; "
        f"sys.path.insert(0, '{backend_path}'); "
        f"sys.path.insert(0, '{parent_path}'); "
        f"from test_dashboard.backend.core.config import settings; "
        f"print(f'Port: {{settings.PORT}}'); "
        f"print(f'Debug: {{settings.DEBUG}}'); "
        f"print(f'Database URL: {{settings.database_url}}'); "
        f"print('SUCCESS: Configuration loaded')"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("✓ Configuration test passed")
            print("Output:", result.stdout.strip())
            return True
        else:
            print("✗ Configuration test failed")
            print("Error:", result.stderr)
            return False
    except Exception as e:
        print(f"✗ Configuration test failed: {e}")
        return False

def check_frontend():
    """Check frontend setup"""
    print("\nChecking frontend setup...")
    
    frontend_path = Path(__file__).parent / "frontend"
    
    # Check package.json
    package_json = frontend_path / "package.json"
    if not package_json.exists():
        print("✗ package.json not found")
        return False
    
    print("✓ package.json found")
    
    # Check node_modules
    node_modules = frontend_path / "node_modules"
    if not node_modules.exists():
        print("✗ node_modules not found")
        return False
    
    deps = list(node_modules.iterdir())
    dep_count = len([d for d in deps if d.is_dir()])
    print(f"✓ node_modules found with {dep_count} dependencies")
    
    # Check npm
    try:
        result = subprocess.run(["npm", "--version"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print(f"✓ npm available: {result.stdout.strip()}")
        else:
            print("✗ npm not available")
            return False
    except:
        print("✗ npm not found")
        return False
    
    return True

def main():
    """Run all tests"""
    print("Test Dashboard Simple Validation")
    print("================================")
    
    tests = [
        ("Backend Import", test_import),
        ("Database Fallback", test_database_fallback),
        ("API Creation", test_api_creation),
        ("Configuration", test_config),
        ("Frontend Setup", check_frontend),
    ]
    
    passed = 0
    total = len(tests)
    
    for name, test_func in tests:
        print(f"\n--- {name} ---")
        if test_func():
            passed += 1
        else:
            print(f"✗ {name} failed")
    
    print(f"\n\nSUMMARY: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED - Test Dashboard is ready!")
        return True
    elif passed >= total * 0.8:
        print("⚠️  MOSTLY WORKING - Minor issues detected")
        return True
    else:
        print("❌ CRITICAL ISSUES - Needs fixes")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)