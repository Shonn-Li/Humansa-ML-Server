#!/usr/bin/env python3
"""Quick test for Pattern 2 appointment functionality"""

import asyncio
import aiohttp
import json
import time

BASE_URL = "http://localhost:6001"

async def test_appointment_queries():
    """Test appointment-related queries with Pattern 2"""
    
    print("🧪 Testing Pattern 2 Appointment Functionality")
    print("=" * 60)
    
    test_queries = [
        ("你是谁？", "Identity test"),
        ("我需要看骨科医生", "Doctor search"),
        ("帮我预约医生", "Appointment booking"),
        ("我需要维生素C", "Product search"),
        ("阿司匹林有什么副作用？", "Medication query")
    ]
    
    async with aiohttp.ClientSession() as session:
        for query, description in test_queries:
            print(f"\n🔹 Test: {description}")
            print(f"   Query: {query}")
            
            request_data = {
                "model": "gpt-4-turbo",
                "input": query,
                "user_id": f"pattern2_test_{int(time.time())}",
                "metadata": {
                    "test": "pattern2_appointment_fix"
                }
            }
            
            start_time = time.time()
            
            try:
                async with session.post(f"{BASE_URL}/v2/humansa/responses/create", json=request_data) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        elapsed = time.time() - start_time
                        
                        print(f"   ✅ Success in {elapsed:.2f}s")
                        
                        # Extract response text
                        output = data.get('output', [])
                        for item in output:
                            if item.get('type') == 'text':
                                text = item.get('text', '')
                                print(f"   Response: {text[:150]}...")
                        
                        # Check usage
                        usage = data.get('usage', {})
                        agents_used = usage.get('agents_used', [])
                        print(f"   Agents used: {agents_used}")
                        
                        # Check metadata
                        metadata = data.get('metadata', {})
                        if metadata.get('orchestrator') == 'pattern2':
                            print("   ✓ Using Pattern 2 orchestrator")
                        
                    else:
                        error_text = await resp.text()
                        print(f"   ❌ Error: {resp.status} - {error_text}")
                        
            except Exception as e:
                print(f"   ❌ Exception: {e}")
            
            print("-" * 60)
    
    print("\n✅ Quick test completed")
    print("\n📋 Summary:")
    print("- If AppointmentAgent was called for doctor/appointment queries ✓")
    print("- If MedicationAgent was called for medication queries ✓")
    print("- If ProductAgent was called for product queries ✓")
    print("Then the fix is working!")

if __name__ == "__main__":
    asyncio.run(test_appointment_queries())