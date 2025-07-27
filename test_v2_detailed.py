#!/usr/bin/env python3
"""Detailed test for Humansa V2 with agent flow logging"""

import asyncio
import aiohttp
import json
from datetime import datetime

BASE_URL = "http://localhost:6001"

def print_separator(title):
    """Print a formatted separator"""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}")

def validate_openai_format(response):
    """Validate that response follows OpenAI format"""
    required_fields = ['id', 'object', 'created', 'model', 'choices']
    for field in required_fields:
        if field not in response:
            return False, f"Missing field: {field}"
    
    if not isinstance(response['choices'], list) or len(response['choices']) == 0:
        return False, "Choices must be a non-empty list"
    
    choice = response['choices'][0]
    if 'message' not in choice or 'content' not in choice['message']:
        return False, "Choice missing message or content"
    
    if response['object'] != 'chat.completion':
        return False, f"Invalid object type: {response['object']}"
    
    return True, "Valid OpenAI format"

async def test_v2_detailed():
    """Run detailed tests with flow logging"""
    async with aiohttp.ClientSession() as session:
        
        # Test 1: Identity Query
        print_separator("TEST 1: Identity Query")
        print("Query: 你是谁？")
        print("Expected: Should identify as 诺亚新舟健康医疗助理/小诺")
        
        request_data = {
            "user_id": 123,
            "messages": [{"role": "user", "content": "你是谁？"}],
            "stream": False
        }
        
        async with session.post(
            f"{BASE_URL}/v2/humansa/chat",
            json=request_data
        ) as response:
            if response.status == 200:
                result = await response.json()
                
                # Validate OpenAI format
                is_valid, msg = validate_openai_format(result)
                print(f"\nOpenAI Format Validation: {'✅ PASS' if is_valid else '❌ FAIL'} - {msg}")
                
                # Extract and display content
                content = result['choices'][0]['message']['content']
                print(f"\nResponse Content:\n{content}")
                
                # Check for identity keywords
                identity_keywords = ["诺亚新舟", "小诺", "健康医疗助理"]
                found = [k for k in identity_keywords if k in content]
                print(f"\nIdentity Keywords Found: {found}")
                print(f"Identity Test: {'✅ PASS' if found else '❌ FAIL'}")
            else:
                print(f"❌ Request failed: {response.status}")
        
        # Test 2: Emergency with Agent Flow
        print_separator("TEST 2: Emergency Response with Agent Flow")
        print("Query: 我现在胸痛很厉害，呼吸困难")
        print("Expected: Should use emergency_triage_agent and recommend 120")
        
        request_data = {
            "user_id": 456,
            "messages": [{"role": "user", "content": "我现在胸痛很厉害，呼吸困难"}],
            "stream": False
        }
        
        start_time = datetime.now()
        async with session.post(
            f"{BASE_URL}/v2/humansa/chat",
            json=request_data
        ) as response:
            if response.status == 200:
                result = await response.json()
                elapsed = (datetime.now() - start_time).total_seconds()
                
                # Validate format
                is_valid, msg = validate_openai_format(result)
                print(f"\nOpenAI Format: {'✅' if is_valid else '❌'} - {msg}")
                print(f"Response Time: {elapsed:.2f} seconds")
                
                # Extract content
                content = result['choices'][0]['message']['content']
                print(f"\nResponse:\n{content}")
                
                # Check for emergency keywords
                emergency_keywords = ["120", "急救", "紧急", "立即"]
                found = [k for k in emergency_keywords if k in content]
                print(f"\nEmergency Keywords: {found}")
                print(f"Emergency Test: {'✅ PASS' if '120' in content else '❌ FAIL'}")
        
        # Test 3: Memory Persistence
        print_separator("TEST 3: Memory Persistence")
        print("Step 1: Add memory - user is allergic to penicillin")
        
        # First message - establish allergy
        request_data = {
            "user_id": 10001,
            "messages": [
                {"role": "user", "content": "我对青霉素过敏"},
                {"role": "assistant", "content": "了解，我已记录您对青霉素过敏的信息。"}
            ],
            "stream": False
        }
        
        # Add memory via memory endpoint
        async with session.post(
            f"{BASE_URL}/v2/humansa/memory/add",
            json=request_data
        ) as response:
            if response.status == 200:
                print("✅ Memory added successfully")
            else:
                print(f"❌ Failed to add memory: {response.status}")
        
        await asyncio.sleep(1)  # Let memory persist
        
        print("\nStep 2: Query about medications")
        request_data = {
            "user_id": 10001,
            "messages": [{"role": "user", "content": "我可以吃什么抗生素？"}],
            "stream": False
        }
        
        async with session.post(
            f"{BASE_URL}/v2/humansa/chat",
            json=request_data
        ) as response:
            if response.status == 200:
                result = await response.json()
                content = result['choices'][0]['message']['content']
                print(f"\nResponse:\n{content}")
                
                # Check if allergy is mentioned
                allergy_mentioned = "青霉素" in content or "过敏" in content
                print(f"\nMemory Recall Test: {'✅ PASS' if allergy_mentioned else '❌ FAIL'}")
        
        # Test 4: Check memory status
        print_separator("TEST 4: Memory Status Check")
        
        async with session.get(f"{BASE_URL}/v2/humansa/memory/status") as response:
            if response.status == 200:
                status = await response.json()
                print(f"Memory System Status: {json.dumps(status, indent=2)}")
                print(f"Mem0 Initialized: {'✅' if status.get('initialized') else '❌'}")
        
        # Test 5: Agent orchestration flow
        print_separator("TEST 5: Complex Query with Multiple Agents")
        print("Query: 我有糖尿病，想预约内分泌科医生，请推荐合适的检查项目")
        
        request_data = {
            "user_id": 789,
            "messages": [
                {"role": "user", "content": "我有糖尿病，想预约内分泌科医生，请推荐合适的检查项目"}
            ],
            "stream": False
        }
        
        async with session.post(
            f"{BASE_URL}/v2/humansa/chat",
            json=request_data
        ) as response:
            if response.status == 200:
                result = await response.json()
                content = result['choices'][0]['message']['content']
                print(f"\nResponse:\n{content}")
                
                # This should trigger multiple agents
                keywords = ["预约", "诊所", "检查", "糖尿病"]
                found = [k for k in keywords if k in content]
                print(f"\nKeywords found: {found}")
                print(f"Multi-agent Test: {'✅ PASS' if len(found) >= 2 else '❌ FAIL'}")

        # Test 6: Response format details
        print_separator("TEST 6: Detailed Response Format Check")
        
        request_data = {
            "user_id": 999,
            "messages": [{"role": "user", "content": "你好"}],
            "stream": False
        }
        
        async with session.post(
            f"{BASE_URL}/v2/humansa/chat",
            json=request_data
        ) as response:
            if response.status == 200:
                result = await response.json()
                print("Full Response Structure:")
                print(json.dumps(result, indent=2, ensure_ascii=False))
                
                # Detailed format check
                print("\nFormat Analysis:")
                print(f"- ID format: {result.get('id', 'MISSING')}")
                print(f"- Object type: {result.get('object', 'MISSING')}")
                print(f"- Model: {result.get('model', 'MISSING')}")
                print(f"- Created timestamp: {result.get('created', 'MISSING')}")
                print(f"- System fingerprint: {result.get('system_fingerprint', 'MISSING')}")
                print(f"- Usage tokens: {result.get('usage', {})}")

if __name__ == "__main__":
    print("="*80)
    print("  Humansa V2 Detailed Test Suite")
    print("  Testing: Identity, Emergency, Memory, Orchestration, Format")
    print("="*80)
    asyncio.run(test_v2_detailed())