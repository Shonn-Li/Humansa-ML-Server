#!/usr/bin/env python3
"""
Test Script for Humansa AI Agent B2
This script tests the virtual environment setup and basic functionality
of the Humansa AI agent.
"""

import sys
import os
import subprocess
import json
from datetime import datetime

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

def check_python_version():
    """Check if Python version is compatible."""
    print("=== Checking Python Version ===")
    version = sys.version_info
    print(f"Python version: {version.major}.{version.minor}.{version.micro}")
    
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python 3.8+ is required")
        return False
    
    print("✅ Python version is compatible")
    return True

def check_virtual_environment():
    """Check if virtual environment is properly set up."""
    print("\n=== Checking Virtual Environment ===")
    
    venv_path = os.path.join(os.path.dirname(__file__), 'youwo-ml-venv')
    
    if not os.path.exists(venv_path):
        print(f"❌ Virtual environment not found at: {venv_path}")
        print("Please run: python3 -m venv youwo-ml-venv")
        return False
    
    # Check if we're in the virtual environment
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("✅ Running inside virtual environment")
    else:
        print("⚠️  Not running inside virtual environment")
        print(f"Please activate: source {venv_path}/bin/activate")
    
    return True

def check_required_modules():
    """Check if required modules are installed."""
    print("\n=== Checking Required Modules ===")
    
    required_modules = [
        'quart',
        'quart_cors',
        'aiofiles',
        'aiohttp',
        'httpx',
        'requests',
        'llama_index',
        'psycopg2',
        'pgvector',
        'sqlalchemy',
        'asyncpg',
        'pandas',
        'numpy',
        'sklearn',
        'bs4',
        'pypdf',
        'PIL',
        'pptx',
        'youtube_transcript_api',
        'dotenv',
        'pydantic',
        'tiktoken',
        'tenacity',
        'yaml',
        'click',
        'uvicorn',
        'fastapi'
    ]
    
    missing_modules = []
    
    for module in required_modules:
        try:
            __import__(module)
            print(f"✅ {module}")
        except ImportError:
            print(f"❌ {module} - Not installed")
            missing_modules.append(module)
    
    if missing_modules:
        print(f"\n❌ Missing modules: {', '.join(missing_modules)}")
        print("Please run: pip install -r requirements.txt")
        return False
    
    return True

def check_humansa_agent_imports():
    """Check if Humansa agent modules can be imported."""
    print("\n=== Checking Humansa Agent Imports ===")
    
    try:
        from humansa.agent.humansa_agent import HumansaAgenticAgent
        print("✅ HumansaAgenticAgent imported successfully")
        
        from humansa.tools.humansa_tools import HumansaAgenticToolManager
        print("✅ HumansaAgenticToolManager imported successfully")
        
        from humansa.prompts.humansa_system_prompt import GENERAL_AGENTIC_POLICY
        print("✅ Humansa prompts imported successfully")
        
        return True
    except ImportError as e:
        print(f"❌ Failed to import Humansa modules: {e}")
        return False

def check_environment_variables():
    """Check if required environment variables are set."""
    print("\n=== Checking Environment Variables ===")
    
    required_vars = [
        'OPENAI_API_KEY',
        'DB_HOST',
        'DB_PORT',
        'DB_USERNAME',
        'DB_ACTIVE_DATABASE'
    ]
    
    optional_vars = [
        'ANTHROPIC_API_KEY',
        'DEEPSEEK_API_KEY',
        'XAI_API_KEY',
        'GOOGLE_API_KEY',
        'SERPER_API_KEY',
        'SERPAPI_API_KEY',
        'BING_SEARCH_API_KEY'
    ]
    
    missing_required = []
    
    for var in required_vars:
        if os.getenv(var):
            print(f"✅ {var} is set")
        else:
            print(f"❌ {var} is NOT set")
            missing_required.append(var)
    
    print("\nOptional variables:")
    for var in optional_vars:
        if os.getenv(var):
            print(f"✅ {var} is set")
        else:
            print(f"⚠️  {var} is not set (optional)")
    
    if missing_required:
        print(f"\n❌ Missing required environment variables: {', '.join(missing_required)}")
        print("Please set these in your .env file or environment")
        return False
    
    return True

def test_humansa_agent_initialization():
    """Test basic Humansa agent initialization."""
    print("\n=== Testing Humansa Agent Initialization ===")
    
    try:
        # Only test if all prerequisites are met
        if not (check_humansa_agent_imports()):
            print("⚠️  Skipping agent initialization test due to missing imports")
            return False
        
        from humansa.agent.humansa_agent import HumansaAgenticAgent
        
        # Test basic initialization (without LLM)
        agent = HumansaAgenticAgent()
        print("✅ HumansaAgenticAgent created successfully")
        
        # Check health
        if agent.is_healthy():
            print("✅ Agent is healthy")
        else:
            print("⚠️  Agent is not healthy (expected without LLM configuration)")
        
        return True
    except Exception as e:
        print(f"❌ Failed to initialize agent: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_basic_server_test():
    """Test if the ML server can start."""
    print("\n=== Testing ML Server Startup ===")
    
    try:
        # Check if main.py exists
        main_path = os.path.join(os.path.dirname(__file__), 'src', 'main.py')
        if not os.path.exists(main_path):
            print(f"❌ main.py not found at: {main_path}")
            return False
        
        print(f"✅ Found main.py at: {main_path}")
        
        # Try to import main (won't actually start the server)
        try:
            import src.main
            print("✅ main.py can be imported successfully")
        except Exception as e:
            print(f"❌ Failed to import main.py: {e}")
            return False
        
        return True
    except Exception as e:
        print(f"❌ Server test failed: {e}")
        return False

def generate_test_report(results):
    """Generate a test report."""
    print("\n" + "="*50)
    print("TEST REPORT FOR HUMANSA AI AGENT B2")
    print("="*50)
    print(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Python Version: {sys.version.split()[0]}")
    print(f"Platform: {sys.platform}")
    print("\nTest Results:")
    
    total_tests = len(results)
    passed_tests = sum(1 for r in results.values() if r)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"  {test_name}: {status}")
    
    print(f"\nSummary: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests < total_tests:
        print("\n⚠️  Some tests failed. Please address the issues above.")
        print("\nRecommended steps:")
        print("1. Activate virtual environment: source youwo-ml-venv/bin/activate")
        print("2. Install dependencies: pip install -r requirements.txt")
        print("3. Set up environment variables in .env file")
        print("4. Re-run this test script")
    else:
        print("\n✅ All tests passed! The Humansa AI Agent B2 environment is properly configured.")

def main():
    """Main test runner."""
    print("HUMANSA AI AGENT B2 - TEST SUITE")
    print("="*50)
    
    results = {}
    
    # Run all tests
    results['Python Version'] = check_python_version()
    results['Virtual Environment'] = check_virtual_environment()
    
    # Only check modules if we're in the right environment
    if results['Virtual Environment']:
        results['Required Modules'] = check_required_modules()
        results['Environment Variables'] = check_environment_variables()
        
        # Only test agent if modules are available
        if results.get('Required Modules', False):
            results['Humansa Agent Init'] = test_humansa_agent_initialization()
            results['ML Server Import'] = run_basic_server_test()
    
    # Generate report
    generate_test_report(results)

if __name__ == "__main__":
    main()