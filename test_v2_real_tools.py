#!/usr/bin/env python3
"""Test V2 with real database tools"""

import asyncio
import aiohttp
import json
import os

async def test_real_tools():
    """Test that V2 is using real database tools"""
    print("🧪 Testing V2 with Real Database Tools")
    print("="*60)
    
    async with aiohttp.ClientSession() as session:
        # Check health
        async with session.get("http://localhost:6001/v2/humansa/health") as resp:
            if resp.status == 200:
                print("✅ V2 Health check passed\n")
            else:
                print("❌ V2 Health check failed")
                return
        
        # Test cases that should return real data
        test_cases = [
            {
                "name": "Find Doctors in Shenzhen",
                "query": "深圳有哪些医生？",
                "expected_real_data": ["张医生", "李医生", "王医生", "诊所"],
                "should_not_contain": ["请告诉我", "为了帮您更好地"]
            },
            {
                "name": "Get Service Pricing",
                "query": "肝功能检查多少钱？",
                "expected_real_data": ["价格", "元", "CNY"],
                "should_not_contain": ["请携带您的"]
            },
            {
                "name": "Find Specific Doctor",
                "query": "张医生的信息",
                "expected_real_data": ["专科", "经验", "诊所"],
                "should_not_contain": ["这可能需要"]
            },
            {
                "name": "List Clinics",
                "query": "广州有哪些诊所？",
                "expected_real_data": ["诊所", "地址", "电话"],
                "should_not_contain": ["通过以下方式"]
            }
        ]
        
        for test in test_cases:
            print(f"\n📝 {test['name']}: {test['query']}")
            
            request_data = {
                "user_id": 12345,
                "messages": [{"role": "user", "content": test["query"]}],
                "stream": False
            }
            
            try:
                async with session.post(
                    "http://localhost:6001/v2/humansa/chat",
                    json=request_data,
                    timeout=aiohttp.ClientTimeout(total=20)
                ) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        content = result['choices'][0]['message']['content']
                        
                        # Check for real data indicators
                        has_real_data = any(keyword in content for keyword in test['expected_real_data'])
                        has_generic = any(phrase in content for phrase in test['should_not_contain'])
                        
                        if has_real_data and not has_generic:
                            print(f"  ✅ REAL DATA DETECTED")
                            print(f"  Found: {[k for k in test['expected_real_data'] if k in content]}")
                        else:
                            print(f"  ⚠️ GENERIC RESPONSE")
                            if has_generic:
                                print(f"  Generic phrases found: {[p for p in test['should_not_contain'] if p in content]}")
                        
                        print(f"  Response preview: {content[:200]}...")
                    else:
                        print(f"  ❌ Error: HTTP {response.status}")
                        
            except Exception as e:
                print(f"  ❌ Exception: {e}")

        print("\n" + "="*60)
        print("🎯 Summary: Check if responses contain real database data")

async def main():
    """Main function"""
    print("Starting ML server...")
    
    # Start the server
    import subprocess
    server = subprocess.Popen(
        ["python3", "-m", "src.main", "--port", "6001"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={**os.environ, "HUMANSA_ENHANCED_LOGGING": "true"}
    )
    
    # Wait for server to start
    print("Waiting for server to start...")
    await asyncio.sleep(10)
    
    try:
        # Run tests
        await test_real_tools()
    finally:
        # Stop server
        print("\n\nStopping server...")
        server.terminate()
        server.wait()

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    asyncio.run(main())