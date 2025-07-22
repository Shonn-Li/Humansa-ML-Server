#!/usr/bin/env python3
"""
Test Server for Multi-Agent System
Runs on port 5002 with test database and fixtures
"""

import sys
import os
import logging

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

# Set up TEST ENVIRONMENT before any imports
os.environ['DATABASE_URL'] = 'postgresql://postgres:12931@localhost:5454/youwoai_test'
os.environ['PUBLIC_ENV'] = 'test'
os.environ['QUART_ENV'] = 'test'
os.environ['PORT'] = '5002'

# Configure logging for test environment
logging.basicConfig(
    level=logging.INFO,
    format='[TEST] %(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Reduce noise from HTTP libraries
for logger_name in ["httpx", "httpcore", "aiohttp", "urllib3"]:
    logging.getLogger(logger_name).setLevel(logging.WARNING)

print("=" * 80)
print("STARTING TEST SERVER")
print("=" * 80)
print(f"Environment: TEST")
print(f"Database: postgresql://localhost:5454/youwoai_test")
print(f"Port: 5002")
print("=" * 80)

# Import and run the main application
from main import app

if __name__ == "__main__":
    print("\n🚀 Test server starting on http://localhost:5002")
    print("📝 Use this server for all testing to ensure isolation from production")
    print("🔍 Test data includes pre-seeded notes and conversations")
    print("\nPress Ctrl+C to stop the server\n")
    
    # Run the app on port 5002
    app.run(host="0.0.0.0", port=5002, debug=False)