#!/usr/bin/env python3
"""
Health check script for ML Server
Returns exit code 0 if healthy, 1 if unhealthy
"""
import sys
import requests
import os

def check_health():
    port = os.getenv('ML_SERVER_PORT', '5001')
    url = f"http://localhost:{port}/v1/status"
    
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            print(f"✅ ML Server is healthy on port {port}")
            return 0
        else:
            print(f"❌ ML Server returned status code: {response.status_code}")
            return 1
    except requests.exceptions.ConnectionError:
        print(f"❌ ML Server is not running on port {port}")
        return 1
    except requests.exceptions.Timeout:
        print(f"❌ ML Server timeout on port {port}")
        return 1
    except Exception as e:
        print(f"❌ ML Server health check failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(check_health())