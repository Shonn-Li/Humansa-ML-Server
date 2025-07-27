#\!/usr/bin/env python3
"""Test memory persistence with correct user ID"""

import asyncio
import aiohttp
import json

BASE_URL = "http://localhost:6001"

async def test_memory():
    async with aiohttp.ClientSession() as session:
        print("=== Memory Persistence Test ===\n")
        
        # Step 1: Add allergy info
        print("Step 1: Tell system about penicillin allergy")
        request_data = {
            "user_id": 5555,
            "messages": [{"role": "user", "content": "我对青霉素过敏，请记住这个信息"}],
            "stream": False
        }
        
        async with session.post(f"{BASE_URL}/v2/humansa/chat", json=request_data) as response:
            if response.status == 200:
                result = await response.json()
                print(f"Response: {result['choices'][0]['message']['content']}\n")
        
        await asyncio.sleep(2)  # Let memory persist
        
        # Step 2: Ask about antibiotics
        print("Step 2: Ask about antibiotics (should recall allergy)")
        request_data = {
            "user_id": 5555,
            "messages": [{"role": "user", "content": "我感冒了，可以吃什么抗生素？"}],
            "stream": False
        }
        
        async with session.post(f"{BASE_URL}/v2/humansa/chat", json=request_data) as response:
            if response.status == 200:
                result = await response.json()
                content = result['choices'][0]['message']['content']
                print(f"Response: {content}\n")
                
                # Check if allergy is mentioned
                if "青霉素" in content or "过敏" in content:
                    print("✅ Memory recall SUCCESS - allergy was mentioned\!")
                else:
                    print("❌ Memory recall FAILED - allergy not mentioned")
        
        # Step 3: Check memory status
        print("\nStep 3: Check memory context")
        async with session.get(f"{BASE_URL}/v2/humansa/memory/context/5555") as response:
            if response.status == 200:
                context = await response.json()
                print(f"Memory context: {json.dumps(context, indent=2, ensure_ascii=False)}")

if __name__ == "__main__":
    asyncio.run(test_memory())
