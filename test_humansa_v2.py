#!/usr/bin/env python3
"""
Test script for Humansa v2 multi-agent system.
"""

import asyncio
import aiohttp
import json
from datetime import datetime
import sys

BASE_URL = "http://localhost:5001"


async def test_v2_health():
    """Test v2 health endpoint."""
    print("\n🔍 Testing v2 health endpoint...")
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}/v2/humansa/health") as response:
            data = await response.json()
            print(f"Status: {response.status}")
            print(f"Response: {json.dumps(data, indent=2)}")
            return response.status == 200


async def test_v2_chat():
    """Test v2 chat endpoint."""
    print("\n🔍 Testing v2 chat endpoint...")
    
    test_queries = [
        {
            "messages": [
                {"role": "user", "content": "I've been having severe headaches for the past week"}
            ],
            "user_id": "test_user_001",
            "stream": False
        },
        {
            "messages": [
                {"role": "user", "content": "I need to book an appointment with a cardiologist"}
            ],
            "user_id": "test_user_001",
            "stream": False
        },
        {
            "messages": [
                {"role": "user", "content": "What are the side effects of aspirin?"}
            ],
            "user_id": "test_user_002",
            "stream": False
        }
    ]
    
    async with aiohttp.ClientSession() as session:
        for i, query in enumerate(test_queries, 1):
            print(f"\n📝 Test Query {i}: {query['messages'][0]['content']}")
            
            try:
                async with session.post(
                    f"{BASE_URL}/v2/humansa/chat",
                    json=query,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"✅ Success: {data.get('response', 'No response')[:200]}...")
                        if 'agents_used' in data:
                            print(f"   Agents used: {data['agents_used']}")
                    else:
                        error_text = await response.text()
                        print(f"❌ Error {response.status}: {error_text}")
            except Exception as e:
                print(f"❌ Exception: {e}")


async def test_v2_appointment_search():
    """Test appointment search."""
    print("\n🔍 Testing appointment search...")
    
    search_request = {
        "user_id": "test_user_001",
        "search_criteria": {
            "specialty": "Cardiology",
            "date_preference": {
                "from": datetime.now().strftime("%Y-%m-%d"),
                "to": (datetime.now().replace(day=datetime.now().day + 7)).strftime("%Y-%m-%d")
            }
        }
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                f"{BASE_URL}/v2/humansa/appointment/search",
                json=search_request,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Found appointments: {json.dumps(data, indent=2)}")
                else:
                    error_text = await response.text()
                    print(f"❌ Error {response.status}: {error_text}")
        except Exception as e:
            print(f"❌ Exception: {e}")


async def test_v2_patient_profile():
    """Test patient profile management."""
    print("\n🔍 Testing patient profile...")
    
    # Test GET
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(
                f"{BASE_URL}/v2/humansa/patient/profile?user_id=test_user_001"
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Retrieved profile: {json.dumps(data, indent=2)}")
                else:
                    error_text = await response.text()
                    print(f"❌ Error {response.status}: {error_text}")
        except Exception as e:
            print(f"❌ Exception: {e}")
    
    # Test PUT
    update_data = {
        "user_id": "test_user_001",
        "profile_data": {
            "name": "Test Patient",
            "age": 45,
            "gender": "Male"
        },
        "medical_history": [
            {"condition": "Hypertension", "diagnosed": "2020-01-01"}
        ],
        "preferences": {
            "preferred_language": "English",
            "appointment_type": "in-person"
        }
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.put(
                f"{BASE_URL}/v2/humansa/patient/profile",
                json=update_data,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Updated profile: {data}")
                else:
                    error_text = await response.text()
                    print(f"❌ Error {response.status}: {error_text}")
        except Exception as e:
            print(f"❌ Exception: {e}")


async def test_streaming_chat():
    """Test streaming chat functionality."""
    print("\n🔍 Testing streaming chat...")
    
    query = {
        "messages": [
            {"role": "user", "content": "I'm experiencing chest pain and shortness of breath"}
        ],
        "user_id": "test_emergency",
        "stream": True
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                f"{BASE_URL}/v2/humansa/chat",
                json=query,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    print("✅ Streaming response:")
                    async for line in response.content:
                        if line:
                            decoded = line.decode('utf-8').strip()
                            if decoded.startswith('data: '):
                                print(f"   {decoded}")
                else:
                    error_text = await response.text()
                    print(f"❌ Error {response.status}: {error_text}")
        except Exception as e:
            print(f"❌ Exception: {e}")


async def main():
    """Run all tests."""
    print("🚀 Starting Humansa v2 System Tests")
    print("=" * 50)
    
    # Check if server is running
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BASE_URL}/health") as response:
                if response.status != 200:
                    print("❌ Server is not running at", BASE_URL)
                    return
    except:
        print("❌ Cannot connect to server at", BASE_URL)
        return
    
    # Run tests
    tests = [
        ("Health Check", test_v2_health),
        ("Chat Endpoint", test_v2_chat),
        ("Appointment Search", test_v2_appointment_search),
        ("Patient Profile", test_v2_patient_profile),
        ("Streaming Chat", test_streaming_chat)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            print(f"\n{'='*50}")
            print(f"Running: {test_name}")
            result = await test_func()
            results.append((test_name, "PASS" if result is not False else "FAIL"))
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results.append((test_name, "ERROR"))
    
    # Summary
    print("\n" + "="*50)
    print("📊 Test Summary:")
    for test_name, status in results:
        emoji = "✅" if status == "PASS" else "❌"
        print(f"   {emoji} {test_name}: {status}")


if __name__ == "__main__":
    asyncio.run(main())