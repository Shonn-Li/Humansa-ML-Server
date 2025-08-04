#!/usr/bin/env python3
"""Test the dashboard API endpoints"""

import requests
import json

API_URL = "http://localhost:6002"

print("Testing Test Dashboard API...")
print("=" * 50)

# Test environment endpoint
print("\n1. Testing /api/environment:")
try:
    res = requests.get(f"{API_URL}/api/environment")
    data = res.json()
    print(f"   ML Digit: {data['ml_digit']}")
    print(f"   Database: {data['database']['name']} (connected: {data['database']['connected']})")
    print(f"   ML Server Port: {data['servers']['ml_server']['port']}")
except Exception as e:
    print(f"   ERROR: {e}")

# Test all tests endpoint
print("\n2. Testing /api/tests/all:")
try:
    res = requests.get(f"{API_URL}/api/tests/all")
    data = res.json()
    print(f"   Total tests: {data['total']}")
    print(f"   Categories: {len(data['by_category'])}")
    
    # Show category breakdown
    print("\n   Category breakdown:")
    for cat, count in data['by_category'].items():
        if isinstance(count, list):
            print(f"     - {cat}: {len(count)} tests")
        else:
            print(f"     - {cat}: {count} tests")
except Exception as e:
    print(f"   ERROR: {e}")

# Test category endpoint
print("\n3. Testing /api/tests/category/appointment:")
try:
    res = requests.get(f"{API_URL}/api/tests/category/appointment")
    data = res.json()
    print(f"   Tests in appointment: {data['total']}")
    if data['tests']:
        print(f"   First test: {data['tests'][0].get('id')} - {data['tests'][0].get('name')}")
except Exception as e:
    print(f"   ERROR: {e}")

print("\n" + "=" * 50)
print("Dashboard API Test Complete")