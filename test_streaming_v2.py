#!/usr/bin/env python3
"""Test V2 streaming with thoughts visibility"""

import asyncio
import aiohttp
import json
import sys

async def test_streaming():
    """Test streaming response"""
    BASE_URL = "http://localhost:6001"
    
    # Test query that should trigger agent reasoning
    request_data = {
        "user_id": 123,
        "messages": [{"role": "user", "content": "我现在胸痛很厉害，呼吸困难"}],
        "stream": True
    }
    
    print("🚀 Testing V2 streaming with thoughts...")
    print(f"Query: {request_data['messages'][0]['content']}")
    print("-" * 60)
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                f"{BASE_URL}/v2/humansa/chat",
                json=request_data,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                
                if response.status != 200:
                    print(f"❌ Error: HTTP {response.status}")
                    return
                
                # Process streaming response
                async for line in response.content:
                    if line:
                        decoded = line.decode('utf-8').strip()
                        
                        if decoded.startswith('data: '):
                            data_str = decoded[6:]
                            
                            if data_str == '[DONE]':
                                print("\n✅ Streaming completed")
                                break
                            
                            try:
                                data = json.loads(data_str)
                                
                                # Extract content from the streaming chunk
                                if 'choices' in data:
                                    for choice in data.get('choices', []):
                                        delta = choice.get('delta', {})
                                        if 'content' in delta:
                                            content = delta['content']
                                            # Print without newline for continuous streaming
                                            print(content, end='', flush=True)
                                            
                            except json.JSONDecodeError:
                                pass
                            
        except Exception as e:
            print(f"\n❌ Error: {e}")

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
        # Run the streaming test
        await test_streaming()
    finally:
        # Stop server
        print("\n\nStopping server...")
        server.terminate()
        server.wait()

if __name__ == "__main__":
    import os
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    asyncio.run(main())