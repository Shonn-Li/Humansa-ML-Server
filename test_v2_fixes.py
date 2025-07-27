#!/usr/bin/env python3
"""Quick test for V2 fixes"""

import asyncio
import aiohttp
import json
import os

# Test configuration
TEST_PORT = os.getenv('ML_SERVER_PORT', '6001')
BASE_URL = f"http://localhost:{TEST_PORT}"

# Quick test cases
TEST_CASES = [
    {
        "name": "Identity Test",
        "query": "你是谁？",
        "expected": ["诺亚新舟", "小诺", "健康医疗助理"]
    },
    {
        "name": "Emergency Test",
        "query": "我现在胸痛很厉害，呼吸困难",
        "expected": ["120", "急救", "紧急"]
    },
    {
        "name": "Company Info",
        "query": "介绍一下诺亚新舟",
        "expected": ["以爱行舟", "亲近相守", "500多位", "30+家"]
    },
    {
        "name": "Health Mall",
        "query": "我想买保健品",
        "expected": ["健康商城", "小程序"]
    },
    {
        "name": "Article Test",
        "query": "有什么最新的健康文章推荐吗？",
        "expected": ["mp.weixin.qq.com"]
    }
]

async def test_endpoint(session, test_case):
    """Test V2 endpoint"""
    try:
        request_data = {
            "user_id": 123,
            "messages": [{"role": "user", "content": test_case['query']}],
            "stream": False
        }
        
        async with session.post(
            f"{BASE_URL}/v2/humansa/chat",
            json=request_data,
            timeout=aiohttp.ClientTimeout(total=30)
        ) as response:
            
            if response.status == 200:
                result = await response.json()
                content = result['choices'][0]['message']['content']
                
                # Check expected keywords
                found = []
                missing = []
                for keyword in test_case['expected']:
                    if keyword in content:
                        found.append(keyword)
                    else:
                        missing.append(keyword)
                
                return {
                    "passed": len(missing) == 0,
                    "found": found,
                    "missing": missing,
                    "response": content[:200] + "..." if len(content) > 200 else content
                }
            else:
                return {
                    "passed": False,
                    "error": f"HTTP {response.status}"
                }
                
    except Exception as e:
        return {
            "passed": False,
            "error": str(e)
        }

async def run_quick_tests():
    """Run quick tests"""
    print("🧪 Running quick V2 tests...")
    
    async with aiohttp.ClientSession() as session:
        # Check health first
        try:
            async with session.get(f"{BASE_URL}/v2/humansa/health") as resp:
                if resp.status == 200:
                    print("✅ V2 Health check passed")
                else:
                    print("❌ V2 Health check failed")
                    return
        except:
            print("❌ Cannot connect to V2 endpoint")
            return
        
        # Run tests
        for test_case in TEST_CASES:
            print(f"\n📋 {test_case['name']}: {test_case['query']}")
            result = await test_endpoint(session, test_case)
            
            if result['passed']:
                print(f"✅ PASSED - Found: {', '.join(result['found'])}")
            else:
                print(f"❌ FAILED")
                if 'missing' in result:
                    print(f"   Missing: {', '.join(result['missing'])}")
                if 'error' in result:
                    print(f"   Error: {result['error']}")
                if 'response' in result:
                    print(f"   Response: {result['response']}")

if __name__ == "__main__":
    # First start the server
    print("Starting ML server...")
    import subprocess
    server = subprocess.Popen(
        ["python3", "-m", "src.main", "--port", "6001"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for server to start
    import time
    time.sleep(5)
    
    try:
        # Run tests
        asyncio.run(run_quick_tests())
    finally:
        # Stop server
        print("\nStopping server...")
        server.terminate()
        server.wait()