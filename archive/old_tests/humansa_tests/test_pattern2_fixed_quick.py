#!/usr/bin/env python3
"""Quick test for fixed Pattern 2 implementation"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:6001"

async def test_pattern2_fixed():
    """Test the fixed Pattern 2 implementation"""
    
    print("🧪 Testing Fixed Pattern 2 Implementation")
    print("=" * 60)
    
    async with aiohttp.ClientSession() as session:
        # Test 1: Basic query
        print("\n1️⃣ Test 1: Basic Identity Query")
        request_data = {
            "model": "gpt-4-turbo",
            "input": "你是谁？",
            "user_id": "test_user_fixed",
            "metadata": {
                "test": "pattern2_fixed"
            }
        }
        
        start_time = time.time()
        async with session.post(f"{BASE_URL}/v2/humansa/responses/create", json=request_data) as resp:
            if resp.status == 200:
                data = await resp.json()
                elapsed = time.time() - start_time
                
                print(f"✅ Success in {elapsed:.2f}s")
                print(f"Response ID: {data.get('id')}")
                
                # Extract text from output
                output = data.get('output', [])
                for item in output:
                    if item.get('type') == 'text':
                        text = item.get('text', '')
                        print(f"Response: {text[:200]}...")
                        if "诺亚新舟" in text:
                            print("✅ Contains expected brand name")
                        else:
                            print("⚠️  Missing brand name")
                
                usage = data.get('usage', {})
                print(f"Agents used: {usage.get('agents_used', [])}")
            else:
                error_text = await resp.text()
                print(f"❌ Error: {resp.status} - {error_text}")
        
        print("\n" + "-" * 60)
        
        # Test 2: Streaming query
        print("\n2️⃣ Test 2: Product Query (Streaming)")
        request_data = {
            "model": "gpt-4-turbo",
            "input": "我需要维生素C产品推荐",
            "user_id": "test_user_fixed_2",
            "metadata": {
                "test": "pattern2_fixed_streaming"
            }
        }
        
        start_time = time.time()
        async with session.post(f"{BASE_URL}/v2/humansa/responses/stream", json=request_data) as resp:
            if resp.status == 200:
                print("✅ Streaming started")
                
                full_response = ""
                agents_used = []
                reasoning_chain = []
                event_count = 0
                
                async for line in resp.content:
                    line = line.decode('utf-8').strip()
                    if line.startswith('data: '):
                        data_str = line[6:]
                        if data_str == '[DONE]':
                            break
                        
                        try:
                            event = json.loads(data_str)
                            event_count += 1
                            
                            # Process different event types
                            if event.get('type') == 'response.output_item.added':
                                item = event.get('item', {})
                                content = item.get('content', [])
                                for c in content:
                                    if c.get('type') == 'output_text':
                                        text = c.get('text', '')
                                        full_response = text
                            
                            elif event.get('type') == 'response.output_item.delta':
                                delta = event.get('delta', {})
                                if delta.get('type') == 'text_delta':
                                    print(delta.get('text', ''), end='', flush=True)
                            
                            elif event.get('type') == 'response.reasoning':
                                reasoning_chain = event.get('reasoning', [])
                            
                            elif event.get('type') == 'response.usage':
                                usage = event.get('usage', {})
                                agents_used = usage.get('agents_used', [])
                                
                        except json.JSONDecodeError:
                            pass
                
                elapsed = time.time() - start_time
                print(f"\n\n✅ Streaming completed in {elapsed:.2f}s")
                print(f"Events received: {event_count}")
                print(f"Response length: {len(full_response)} chars")
                print(f"Agents used: {agents_used}")
                if reasoning_chain:
                    print(f"Reasoning steps: {len(reasoning_chain)}")
                    for step in reasoning_chain:
                        print(f"  - {step}")
            else:
                error_text = await resp.text()
                print(f"❌ Error: {resp.status} - {error_text}")
        
        print("\n" + "-" * 60)
        
        # Test 3: Medical query
        print("\n3️⃣ Test 3: Medical Symptom Query")
        request_data = {
            "model": "gpt-4-turbo",
            "input": "我最近头痛，需要看医生吗？",
            "user_id": "test_user_fixed_3"
        }
        
        start_time = time.time()
        async with session.post(f"{BASE_URL}/v2/humansa/responses/create", json=request_data) as resp:
            if resp.status == 200:
                data = await resp.json()
                elapsed = time.time() - start_time
                
                print(f"✅ Success in {elapsed:.2f}s")
                
                # Check usage
                usage = data.get('usage', {})
                agents_used = usage.get('agents_used', [])
                print(f"Agents used: {agents_used}")
                
                if 'DiagnosisAgent' in str(agents_used) or 'analyze_symptoms' in str(agents_used):
                    print("✅ DiagnosisAgent was called for medical query")
                else:
                    print("⚠️  DiagnosisAgent was not called for medical query")
                
                # Check for emergency flags
                workflow_state = usage.get('workflow_state', {})
                if emergency_flags := workflow_state.get('emergency_flags', []):
                    print(f"🚨 Emergency flags: {emergency_flags}")
            else:
                error_text = await resp.text()
                print(f"❌ Error: {resp.status} - {error_text}")
    
    print("\n" + "=" * 60)
    print("✅ Fixed Pattern 2 Quick Test Completed")
    
    # Check server logs
    print("\n📋 To see detailed logs, run:")
    print("tail -50 pattern2_fixed_server_*.log | grep 'PATTERN 2 FINAL CONTEXT' -A 10")

if __name__ == "__main__":
    asyncio.run(test_pattern2_fixed())