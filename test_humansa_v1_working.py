#!/usr/bin/env python3
"""Test Humansa V1 endpoint which is already working."""

import asyncio
import aiohttp
import json
from datetime import datetime
import os

BASE_URL = "http://localhost:5001"

async def test_v1_chat():
    """Test the V1 Humansa chat endpoint."""
    
    test_cases = [
        {
            "name": "Basic Health Query",
            "user_id": "test_user_001",
            "message": "What are the symptoms of high blood pressure?"
        },
        {
            "name": "Doctor Search",
            "user_id": "test_user_002", 
            "message": "I need to find a cardiologist in Singapore"
        },
        {
            "name": "Appointment Booking",
            "user_id": "test_user_003",
            "message": "Can you help me book an appointment with Dr. Sarah Chen?"
        },
        {
            "name": "Emergency Symptoms",
            "user_id": "test_user_004",
            "message": "I'm having severe chest pain and difficulty breathing"
        },
        {
            "name": "Medication Query",
            "user_id": "test_user_005",
            "message": "Can I take aspirin with metformin?"
        }
    ]
    
    print("🏥 Testing Humansa V1 Endpoint")
    print("=" * 50)
    print()
    
    async with aiohttp.ClientSession() as session:
        for i, test in enumerate(test_cases, 1):
            print(f"Test {i}/{len(test_cases)}: {test['name']}")
            print(f"User: {test['message']}")
            
            payload = {
                "model": "gpt-4",
                "messages": [
                    {"role": "user", "content": test['message']}
                ],
                "stream": False,
                "user_id": test['user_id']
            }
            
            try:
                async with session.post(
                    f"{BASE_URL}/v1-humansa/chat/completions",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Extract response content
                        if "choices" in data and data["choices"]:
                            content = data["choices"][0]["message"]["content"]
                            print(f"✅ Response: {content[:150]}...")
                        else:
                            print(f"✅ Response: {json.dumps(data)[:150]}...")
                            
                        # Check if tools were used
                        if "tool_calls" in data:
                            print(f"   Tools used: {len(data.get('tool_calls', []))}")
                            
                    else:
                        error_data = await response.text()
                        print(f"❌ Error ({response.status}): {error_data[:100]}")
                        
            except Exception as e:
                print(f"❌ Request failed: {e}")
                
            print("-" * 50)
            await asyncio.sleep(1)  # Small delay between requests
            
    print("\n✅ Test completed!")

if __name__ == "__main__":
    # Set database port for Humansa test environment
    os.environ["DB_PORT"] = "5456"
    asyncio.run(test_v1_chat())