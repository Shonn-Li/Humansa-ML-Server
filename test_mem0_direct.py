"""Direct test of Mem0 memory system"""
import asyncio
import aiohttp
import json

BASE_URL = "http://localhost:6001"

async def test_mem0_direct():
    """Test Mem0 memory endpoints directly"""
    async with aiohttp.ClientSession() as session:
        # 1. Check memory status
        print("1. Checking memory status...")
        async with session.get(f"{BASE_URL}/v2/humansa/memory/status") as resp:
            status = await resp.json()
            print(f"   Status: {json.dumps(status, indent=2)}")
        
        # 2. Add a memory
        print("\n2. Adding memory...")
        memory_data = {
            "user_id": "test_mem0_999",
            "messages": [
                {"role": "user", "content": "I am allergic to penicillin"},
                {"role": "assistant", "content": "I've noted your penicillin allergy"}
            ]
        }
        
        async with session.post(
            f"{BASE_URL}/v2/humansa/memory/add",
            json=memory_data
        ) as resp:
            if resp.status == 200:
                result = await resp.json()
                print(f"   ✓ Memory added: {result}")
            else:
                error = await resp.json()
                print(f"   ✗ Failed {resp.status}: {error}")
        
        # 3. Get user context
        print("\n3. Getting user context...")
        async with session.get(f"{BASE_URL}/v2/humansa/memory/context/test_mem0_999") as resp:
            if resp.status == 200:
                context = await resp.json()
                print(f"   ✓ Context: {json.dumps(context, indent=2)}")
            else:
                error = await resp.text()
                print(f"   ✗ Failed {resp.status}: {error}")
        
        # 4. Search memories
        print("\n4. Searching memories...")
        search_data = {
            "user_id": "test_mem0_999",
            "query": "allergies"
        }
        
        async with session.post(
            f"{BASE_URL}/v2/humansa/memory/search",
            json=search_data
        ) as resp:
            if resp.status == 200:
                results = await resp.json()
                print(f"   ✓ Search results: {json.dumps(results, indent=2)}")
            else:
                error = await resp.json()
                print(f"   ✗ Failed {resp.status}: {error}")

if __name__ == "__main__":
    asyncio.run(test_mem0_direct())