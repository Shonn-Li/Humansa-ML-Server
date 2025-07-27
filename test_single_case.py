#!/usr/bin/env python3
"""Test single case to verify Humansa V2 is working properly."""
import os
import sys
import asyncio
import aiohttp
import json
from datetime import datetime

# Set test environment
os.environ['ENVIRONMENT'] = 'test'
os.environ['DB_HOST'] = 'localhost'
os.environ['DB_PORT'] = '5454'
os.environ['DB_USER'] = 'postgres'
os.environ['DB_PASSWORD'] = '12931'
os.environ['DB_NAME'] = 'youwoai_test'
os.environ['HUMANSA_ENHANCED_LOGGING'] = 'true'

async def test_doctor_search():
    """Test doctor search functionality."""
    base_url = "http://localhost:5001"
    
    # Test case: Search for orthopedic doctor
    test_case = {
        "messages": [
            {
                "role": "user",
                "content": "我想找个骨科医生"
            }
        ],
        "stream": False,
        "user_id": "test_user_single",
        "conversation_id": "test_conv_single"
    }
    
    print("Testing doctor search...")
    print(f"Query: {test_case['messages'][0]['content']}")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                f"{base_url}/v2/humansa/chat",
                json=test_case,
                headers={'Content-Type': 'application/json'}
            ) as response:
                result = await response.json()
                
                print(f"\nStatus: {response.status}")
                print(f"Response: {json.dumps(result, ensure_ascii=False, indent=2)}")
                
                # Check if doctor was found
                if result.get('choices'):
                    content = result['choices'][0]['message']['content']
                    if '赵六' in content:
                        print("\n✅ SUCCESS: Found orthopedic doctor 赵六")
                    else:
                        print("\n❌ FAILED: Doctor not found in response")
                else:
                    print("\n❌ FAILED: Invalid response format")
                    
        except Exception as e:
            print(f"\n❌ ERROR: {e}")

if __name__ == "__main__":
    # Start the test
    asyncio.run(test_doctor_search())