#!/usr/bin/env python3
"""
Quick identity test to verify Response Agent improvements
"""

import asyncio
import aiohttp
import json

# Test configuration
BASE_URL = "http://localhost:6001"
TEST_USER_ID = "test_identity_quick"

# Critical identity test cases
IDENTITY_TESTS = [
    "你是谁？",
    "Who are you?",
    "介绍一下诺亚新舟",
    "什么是HUMANSA？",
    "你好"
]


async def test_identity(session, query):
    """Test a single identity query"""
    url = f"{BASE_URL}/v2/humansa/responses/create"
    
    payload = {
        "model": "gpt-4-turbo",
        "input": query,
        "user_id": TEST_USER_ID
    }
    
    try:
        async with session.post(url, json=payload) as response:
            if response.status == 200:
                result = await response.json()
                
                # Extract text
                text = ""
                for item in result.get("output", []):
                    if item.get("type") == "text":
                        text = item.get("text", "")
                        break
                
                # Check for HUMANSA identity
                has_identity = any([
                    "诺亚新舟" in text,
                    "小诺" in text,
                    "HUMANSA" in text.upper(),
                    "Humansa" in text
                ])
                
                return {
                    "query": query,
                    "has_identity": has_identity,
                    "response": text[:200] + "..." if len(text) > 200 else text
                }
            else:
                return {
                    "query": query,
                    "has_identity": False,
                    "error": f"HTTP {response.status}"
                }
    except Exception as e:
        return {
            "query": query,
            "has_identity": False,
            "error": str(e)
        }


async def main():
    print("\n" + "="*60)
    print("  HUMANSA V2 Identity Test - Quick Check")
    print("="*60 + "\n")
    
    async with aiohttp.ClientSession() as session:
        # Check server
        try:
            async with session.get(f"{BASE_URL}/v2/humansa/health") as response:
                if response.status == 200:
                    print("✅ Server is running\n")
                else:
                    print("❌ Server not responding")
                    return
        except:
            print("❌ Cannot connect to server")
            return
        
        # Run tests
        passed = 0
        for query in IDENTITY_TESTS:
            result = await test_identity(session, query)
            
            if result["has_identity"]:
                print(f"✅ {query}")
                print(f"   → {result['response']}")
                passed += 1
            else:
                print(f"❌ {query}")
                if "error" in result:
                    print(f"   → Error: {result['error']}")
                else:
                    print(f"   → No identity found in response")
                    print(f"   → {result['response']}")
            print()
        
        # Summary
        print("\n" + "="*60)
        print(f"RESULTS: {passed}/{len(IDENTITY_TESTS)} passed ({passed/len(IDENTITY_TESTS)*100:.0f}%)")
        print("="*60 + "\n")
        
        if passed == len(IDENTITY_TESTS):
            print("🎉 All identity tests passed!")
        else:
            print("⚠️  Some identity tests failed")


if __name__ == "__main__":
    asyncio.run(main())