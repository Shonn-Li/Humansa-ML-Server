"""Test Humansa v2 directly"""
import asyncio
import aiohttp
import json

BASE_URL = "http://localhost:6001"

async def test_v2():
    """Test v2 endpoints"""
    async with aiohttp.ClientSession() as session:
        # 1. Check v2 health
        print("1. Checking v2 health...")
        try:
            async with session.get(f"{BASE_URL}/v2/humansa/health") as resp:
                if resp.status == 200:
                    health = await resp.json()
                    print(f"   ✓ Health: {json.dumps(health, indent=2)}")
                else:
                    print(f"   ✗ Failed: {resp.status}")
        except Exception as e:
            print(f"   ✗ Error: {e}")
        
        # 2. Test v2 chat
        print("\n2. Testing v2 chat...")
        chat_data = {
            "messages": [{"role": "user", "content": "Hello, I need medical help"}],
            "model": "gpt-4",
            "user_id": "test_v2_user",
            "stream": False
        }
        
        try:
            async with session.post(
                f"{BASE_URL}/v2/humansa/chat",
                json=chat_data
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    print(f"   ✓ Response: {result.get('response', 'No response')[:200]}")
                else:
                    error = await resp.text()
                    print(f"   ✗ Failed {resp.status}: {error}")
        except Exception as e:
            print(f"   ✗ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_v2())