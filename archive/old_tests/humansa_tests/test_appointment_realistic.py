#!/usr/bin/env python
"""Test appointment agent with realistic data"""

import asyncio
import aiohttp
import json
from datetime import datetime, timedelta

async def test_appointment_query(query, description):
    """Test a single appointment query"""
    
    url = "http://localhost:6001/v2/humansa/chat"
    
    data = {
        "user_id": "test_user_appointment",
        "messages": [
            {
                "role": "user", 
                "content": query
            }
        ],
        "stream": False
    }
    
    print(f"\n{'='*60}")
    print(f"🧪 Testing: {description}")
    print(f"📝 Query: {query}")
    print("="*60)
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    
                    if "choices" in result:
                        content = result["choices"][0]["message"]["content"]
                        
                        # Handle response agent format
                        if isinstance(content, dict) and "output" in content:
                            actual_content = content["output"][0].get("content", "")
                        else:
                            actual_content = str(content)
                        
                        print(f"✅ SUCCESS!")
                        print(f"📄 Response Preview:\n{actual_content[:800]}{'...' if len(actual_content) > 800 else ''}")
                        
                        return True, actual_content
                    else:
                        print(f"❌ Error: Invalid response format")
                        return False, ""
                else:
                    error_text = await response.text()
                    print(f"❌ Error {response.status}: {error_text}")
                    return False, ""
                    
        except Exception as e:
            print(f"❌ Exception: {e}")
            return False, ""

async def main():
    """Run appointment testing scenarios"""
    
    print("🏥 Testing HUMANSA V2 Appointment Agent with Realistic Data")
    print(f"⏰ Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    # Test scenarios
    test_cases = [
        # Basic appointment queries
        ("我想预约心内科医生", "Basic cardiology appointment request"),
        ("明天有哪些儿科医生可以预约？", "Pediatrics availability tomorrow"),
        ("帮我查一下后天上午的骨科专家", "Orthopedics morning slots day after tomorrow"), 
        
        # Specific doctor queries
        ("孙浩医生明天有号吗？", "Specific doctor availability - Dr. Sun Hao"),
        ("我想预约张伟医生", "Specific doctor booking - Dr. Zhang Wei"),
        
        # Specialty-based queries
        ("皮肤科最早什么时候可以预约？", "Earliest dermatology appointment"),
        ("中医科下周有空的时间吗？", "TCM availability next week"),
        
        # Time-specific queries  
        ("今天下午还有医生可以看吗？", "Today afternoon availability"),
        ("这周五上午有内科医生吗？", "Friday morning internal medicine"),
        
        # Online consultation queries
        ("可以在线咨询吗？有什么医生？", "Online consultation availability"),
    ]
    
    results = []
    
    for query, description in test_cases:
        success, response = await test_appointment_query(query, description)
        results.append({
            "query": query,
            "description": description, 
            "success": success,
            "response_length": len(response)
        })
        
        await asyncio.sleep(1)  # Brief pause between requests
    
    # Summary
    print(f"\n{'='*80}")
    print("📊 TEST SUMMARY")
    print("="*80)
    
    successful = sum(1 for r in results if r["success"])
    total = len(results)
    
    print(f"✅ Successful Tests: {successful}/{total} ({successful/total*100:.1f}%)")
    print(f"❌ Failed Tests: {total-successful}/{total}")
    
    print(f"\n📋 Individual Results:")
    for i, result in enumerate(results, 1):
        status = "✅" if result["success"] else "❌"
        print(f"  {i:2d}. {status} {result['description']}")
    
    if successful == total:
        print(f"\n🎉 ALL TESTS PASSED! Appointment agent working perfectly with realistic data.")
    else:
        print(f"\n⚠️  Some tests failed. Check server logs for details.")

if __name__ == "__main__":
    asyncio.run(main())