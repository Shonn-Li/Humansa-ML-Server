#!/usr/bin/env python3
"""
Fixed test script for Humansa doctor tools with string user_ids
Tests doctor search, appointment booking, and other medical tools
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime

# Test configuration with string user_ids
BASE_URL = "http://localhost:6001"
TEST_USER_ID = "test_user_doctor_001"  # String user_id


async def test_doctor_tools():
    """Test doctor-related tools with v2 endpoint"""
    
    test_scenarios = [
        {
            "name": "Find Orthopedic Doctor",
            "description": "Search for orthopedic doctors",
            "query": "我想找个骨科医生",
            "expected_tools": ["find_doctor_info"],
            "expected_keywords": ["骨科", "医生"]
        },
        {
            "name": "Doctor in Specific City",
            "description": "Find doctors in a specific city",
            "query": "帮我找深圳的心脏科医生",
            "expected_tools": ["find_doctor_info"],
            "expected_keywords": ["心", "深圳", "医生"]
        },
        {
            "name": "Book Appointment",
            "description": "Book a doctor appointment",
            "query": "帮我预约张医生明天上午的号",
            "expected_tools": ["find_doctor_info", "find_doctor_availability"],
            "expected_keywords": ["预约", "张"]
        },
        {
            "name": "Check Doctor Availability",
            "description": "Check when a doctor is available",
            "query": "李医生这周还有号吗？",
            "expected_tools": ["find_doctor_info", "find_doctor_availability"],
            "expected_keywords": ["李医生", "号"]
        },
        {
            "name": "Clinic Information",
            "description": "Find clinic information",
            "query": "北京的诊所在哪里？",
            "expected_tools": ["find_clinic_info"],
            "expected_keywords": ["诊所", "北京"]
        }
    ]
    
    async with aiohttp.ClientSession() as session:
        print("="*60)
        print("Fixed Doctor Tools Test - Using String User IDs")
        print(f"Test User ID: {TEST_USER_ID}")
        print(f"Base URL: {BASE_URL}")
        print("="*60)
        
        # First, check v2 health
        print("\nChecking V2 health...")
        try:
            async with session.get(f"{BASE_URL}/v2/humansa/health") as resp:
                if resp.status == 200:
                    health = await resp.json()
                    print(f"✅ V2 Health: {health['status']}")
                else:
                    print(f"❌ V2 Health check failed: {resp.status}")
                    return
        except Exception as e:
            print(f"❌ Cannot connect to V2 endpoint: {e}")
            return
        
        # Run test scenarios
        results = []
        for i, scenario in enumerate(test_scenarios, 1):
            print(f"\n{'='*60}")
            print(f"Test {i}/{len(test_scenarios)}: {scenario['name']}")
            print(f"Description: {scenario['description']}")
            print(f"Query: {scenario['query']}")
            print(f"Expected tools: {scenario['expected_tools']}")
            print("="*60)
            
            # Prepare request
            request_data = {
                "user_id": TEST_USER_ID,  # String user_id
                "messages": [
                    {"role": "user", "content": scenario['query']}
                ],
                "stream": True,
                "debug": True  # Enable debug mode to see tool calls
            }
            
            start_time = time.time()
            tool_calls = []
            full_response = ""
            
            try:
                async with session.post(
                    f"{BASE_URL}/v2/humansa/chat",
                    json=request_data,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    
                    if response.status != 200:
                        error_text = await response.text()
                        print(f"❌ Request failed: {response.status} - {error_text}")
                        results.append({
                            "scenario": scenario['name'],
                            "success": False,
                            "error": f"HTTP {response.status}"
                        })
                        continue
                    
                    # Process streaming response
                    print("\n📡 Streaming response:")
                    async for line in response.content:
                        if line:
                            decoded = line.decode('utf-8').strip()
                            
                            if decoded.startswith('data: '):
                                data_str = decoded[6:]
                                
                                if data_str == '[DONE]':
                                    break
                                
                                try:
                                    data = json.loads(data_str)
                                    
                                    # Track tool calls
                                    if data.get('debug'):
                                        debug_event = data['debug']
                                        if debug_event.get('type') == 'tool_call_start':
                                            tool = debug_event.get('tool', 'unknown')
                                            print(f"  🔧 Tool called: {tool}")
                                            tool_calls.append(tool)
                                    
                                    # Collect response content
                                    if 'choices' in data:
                                        for choice in data.get('choices', []):
                                            delta = choice.get('delta', {})
                                            if 'content' in delta:
                                                full_response += delta['content']
                                                
                                except json.JSONDecodeError:
                                    pass
                    
                    elapsed_time = time.time() - start_time
                    
                    # Analyze results
                    print(f"\n📊 Results:")
                    print(f"  Response time: {elapsed_time:.2f}s")
                    print(f"  Tools called: {tool_calls}")
                    print(f"  Response preview: {full_response[:200]}...")
                    
                    # Check if expected tools were called
                    expected_tools_found = all(
                        any(tool in called for called in tool_calls) 
                        for tool in scenario['expected_tools']
                    )
                    
                    # Check for expected keywords
                    keywords_found = all(
                        keyword.lower() in full_response.lower() 
                        for keyword in scenario['expected_keywords']
                    )
                    
                    success = expected_tools_found and keywords_found
                    
                    if success:
                        print("✅ Test PASSED")
                    else:
                        print("❌ Test FAILED")
                        if not expected_tools_found:
                            print(f"  Missing expected tools: {scenario['expected_tools']}")
                        if not keywords_found:
                            print(f"  Missing keywords: {scenario['expected_keywords']}")
                    
                    results.append({
                        "scenario": scenario['name'],
                        "success": success,
                        "tools_called": tool_calls,
                        "response_time": elapsed_time,
                        "response_length": len(full_response)
                    })
                    
            except asyncio.TimeoutError:
                print("❌ Request timeout")
                results.append({
                    "scenario": scenario['name'],
                    "success": False,
                    "error": "Timeout"
                })
            except Exception as e:
                print(f"❌ Error: {e}")
                results.append({
                    "scenario": scenario['name'],
                    "success": False,
                    "error": str(e)
                })
            
            # Small delay between tests
            await asyncio.sleep(1)
        
        # Summary
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        
        passed = sum(1 for r in results if r.get('success', False))
        total = len(results)
        
        print(f"Total tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success rate: {(passed/total*100):.1f}%")
        
        print("\nDetailed Results:")
        for result in results:
            status = "✅" if result.get('success') else "❌"
            print(f"\n{status} {result['scenario']}")
            if result.get('tools_called'):
                print(f"   Tools: {result['tools_called']}")
            if result.get('response_time'):
                print(f"   Time: {result['response_time']:.2f}s")
            if result.get('error'):
                print(f"   Error: {result['error']}")
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"doctor_tools_test_results_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump({
                "timestamp": timestamp,
                "user_id": TEST_USER_ID,
                "total_tests": total,
                "passed": passed,
                "failed": total - passed,
                "results": results
            }, f, ensure_ascii=False, indent=2)
        
        print(f"\nResults saved to: {filename}")


async def main():
    """Run the doctor tools test"""
    print("Fixed Doctor Tools Test - V2 Endpoint")
    print("=====================================")
    print("This test verifies doctor search and appointment tools")
    print("Using string user IDs for proper Mem0 integration")
    print("")
    
    await test_doctor_tools()


if __name__ == "__main__":
    asyncio.run(main())