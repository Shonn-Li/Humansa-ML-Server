#!/usr/bin/env python3
"""Final V2 test to validate all core functionalities"""

import asyncio
import aiohttp
import json
import os

async def test_endpoint(session, query, user_id=123, stream=False):
    """Test a single endpoint"""
    request_data = {
        "user_id": user_id,
        "messages": [{"role": "user", "content": query}],
        "stream": stream
    }
    
    try:
        async with session.post(
            "http://localhost:6001/v2/humansa/chat",
            json=request_data,
            timeout=aiohttp.ClientTimeout(total=30)
        ) as response:
            
            if response.status == 200:
                if stream:
                    # Process streaming response
                    full_response = ""
                    async for line in response.content:
                        if line:
                            decoded = line.decode('utf-8').strip()
                            if decoded.startswith('data: '):
                                data_str = decoded[6:]
                                if data_str == '[DONE]':
                                    break
                                try:
                                    data = json.loads(data_str)
                                    if 'choices' in data:
                                        for choice in data.get('choices', []):
                                            delta = choice.get('delta', {})
                                            if 'content' in delta:
                                                full_response += delta['content']
                                except:
                                    pass
                    return full_response
                else:
                    result = await response.json()
                    return result['choices'][0]['message']['content']
            else:
                return f"Error: HTTP {response.status}"
                
    except Exception as e:
        return f"Error: {e}"

async def test_memory_persistence(session):
    """Test Mem0 memory persistence"""
    print("\n🧠 Testing Memory Persistence...")
    
    # First conversation - store information
    user_id = 99999
    print(f"  User {user_id} - First conversation:")
    
    response = await test_endpoint(session, "我对花生过敏", user_id)
    print(f"    Query: 我对花生过敏")
    print(f"    Response: {response[:100]}...")
    
    # Add delay for memory to persist
    await asyncio.sleep(2)
    
    # Second conversation - recall information
    print(f"\n  User {user_id} - Second conversation:")
    response = await test_endpoint(session, "我有什么过敏史吗？", user_id)
    print(f"    Query: 我有什么过敏史吗？")
    print(f"    Response: {response}")
    
    # Check if memory was recalled
    if "花生" in response:
        print("    ✅ Memory persistence working!")
    else:
        print("    ❌ Memory not recalled")

async def run_tests():
    """Run all tests"""
    print("🧪 Final V2 Test Suite")
    print("="*60)
    
    async with aiohttp.ClientSession() as session:
        # Check health
        async with session.get("http://localhost:6001/v2/humansa/health") as resp:
            if resp.status == 200:
                print("✅ V2 Health check passed\n")
            else:
                print("❌ V2 Health check failed")
                return
        
        # Test core functionalities
        test_cases = [
            ("Identity", "你是谁？", ["诺亚新舟", "小诺"]),
            ("Greeting", "你好", ["你好", "小诺"]),
            ("Emergency", "我现在胸痛很厉害，呼吸困难", ["120", "急救"]),
            ("Booking", "我想预约看医生", ["预约", "诊所"]),
            ("Health Product", "我想买保健品", ["健康商城", "小程序"]),
            ("Company Info", "介绍一下诺亚新舟", ["以爱行舟", "500多位"]),
            ("Sleep Issue", "最近总是失眠怎么办？", ["失眠", "建议"]),
            ("English Identity", "Who are you?", ["Humansa", "health"])
        ]
        
        print("📋 Core Functionality Tests:")
        passed = 0
        
        for name, query, expected in test_cases:
            print(f"\n{name}: {query}")
            response = await test_endpoint(session, query)
            
            # Check expected keywords
            found = all(keyword in response for keyword in expected)
            
            if found:
                print(f"  ✅ PASSED")
                print(f"  Response: {response[:150]}...")
                passed += 1
            else:
                print(f"  ❌ FAILED")
                print(f"  Response: {response[:150]}...")
                print(f"  Missing: {[k for k in expected if k not in response]}")
        
        print(f"\n📊 Results: {passed}/{len(test_cases)} passed")
        
        # Test streaming
        print("\n🌊 Testing Streaming with Thoughts:")
        response = await test_endpoint(session, "我想了解一下你们的服务", stream=True)
        if "💭" in response or "🔧" in response:
            print("  ✅ Streaming shows agent thoughts")
        else:
            print("  ❌ Streaming not showing thoughts properly")
        
        # Test memory
        await test_memory_persistence(session)

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
    
    try:
        # Run tests
        await run_tests()
    finally:
        # Stop server
        print("\n\nStopping server...")
        server.terminate()
        server.wait()

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    asyncio.run(main())