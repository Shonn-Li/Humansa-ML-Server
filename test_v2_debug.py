"""Debug V2 orchestrator recursion issue"""
import asyncio
import aiohttp
import json

BASE_URL = "http://localhost:6001"

async def test_v2_debug():
    """Test V2 chat with minimal payload"""
    async with aiohttp.ClientSession() as session:
        # Check health first
        print("1. Checking V2 health...")
        async with session.get(f"{BASE_URL}/v2/humansa/health") as resp:
            health = await resp.json()
            print(f"   Health: {json.dumps(health, indent=2)}")
        
        # Try simplest possible chat
        print("\n2. Testing simple chat...")
        chat_data = {
            "user_id": "test123",
            "messages": [{"role": "user", "content": "Hi"}],
            "stream": False
        }
        
        try:
            async with session.post(
                f"{BASE_URL}/v2/humansa/chat",
                json=chat_data,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"   Success: {json.dumps(data, indent=2)}")
                else:
                    error = await resp.json()
                    print(f"   Error {resp.status}: {json.dumps(error, indent=2)}")
        except asyncio.TimeoutError:
            print("   Error: Request timed out")
        except Exception as e:
            print(f"   Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_v2_debug())