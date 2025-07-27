#!/usr/bin/env python3
"""Test V2 non-streaming to verify agent functionality"""

import asyncio
import aiohttp
import json
import sys
import os

async def test_non_streaming():
    """Test non-streaming response"""
    BASE_URL = "http://localhost:6001"
    
    # Test queries
    test_cases = [
        {
            "name": "Identity",
            "query": "你是谁？"
        },
        {
            "name": "Emergency",
            "query": "我现在胸痛很厉害，呼吸困难"
        },
        {
            "name": "Company Info",
            "query": "介绍一下诺亚新舟"
        }
    ]
    
    async with aiohttp.ClientSession() as session:
        for test in test_cases:
            print(f"\n{'='*60}")
            print(f"Test: {test['name']}")
            print(f"Query: {test['query']}")
            print(f"{'='*60}")
            
            request_data = {
                "user_id": 123,
                "messages": [{"role": "user", "content": test['query']}],
                "stream": False
            }
            
            try:
                async with session.post(
                    f"{BASE_URL}/v2/humansa/chat",
                    json=request_data,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        content = result['choices'][0]['message']['content']
                        print(f"✅ Response: {content}")
                    else:
                        print(f"❌ Error: HTTP {response.status}")
                        
            except Exception as e:
                print(f"❌ Error: {e}")

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
    await asyncio.sleep(5)
    
    # Check if server is ready
    async with aiohttp.ClientSession() as session:
        for i in range(10):
            try:
                async with session.get("http://localhost:6001/v2/humansa/health") as resp:
                    if resp.status == 200:
                        print("✅ Server is ready!\n")
                        break
            except:
                await asyncio.sleep(1)
    
    try:
        # Run the tests
        await test_non_streaming()
    finally:
        # Stop server
        print("\n\nStopping server...")
        server.terminate()
        server.wait()

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    asyncio.run(main())