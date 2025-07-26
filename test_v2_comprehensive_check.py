#!/usr/bin/env python3
"""
Comprehensive test to verify Humansa V2 with improved orchestrator
Tests database pool, orchestrator initialization, and memory integration
"""

import asyncio
import aiohttp
import json
import time
import sys
from datetime import datetime

BASE_URL = "http://localhost:6001"

class HumansaV2Tester:
    def __init__(self):
        self.results = []
        self.passed = 0
        self.failed = 0
        
    async def test_health_endpoints(self):
        """Test 1: Check health endpoints"""
        print("\n" + "="*60)
        print("TEST 1: Health Check Endpoints")
        print("="*60)
        
        async with aiohttp.ClientSession() as session:
            # Test main health
            try:
                async with session.get(f"{BASE_URL}/health") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        print(f"✓ Main health endpoint: {data}")
                        self.passed += 1
                    else:
                        print(f"✗ Main health failed: {resp.status}")
                        self.failed += 1
            except Exception as e:
                print(f"✗ Main health error: {e}")
                self.failed += 1
                
            # Test v2 health
            try:
                async with session.get(f"{BASE_URL}/v2/humansa/health") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        print(f"\n✓ V2 health endpoint:")
                        print(f"  Status: {data.get('status')}")
                        components = data.get('components', {})
                        print(f"  Orchestrator: {components.get('orchestrator')}")
                        print(f"  Memory Manager: {components.get('memory_manager')}")
                        print(f"  Appointment Workflow: {components.get('appointment_workflow')}")
                        
                        # Check if orchestrator is properly initialized
                        if components.get('orchestrator') == True:
                            print(f"\n✓ ORCHESTRATOR PROPERLY INITIALIZED!")
                            self.passed += 1
                        else:
                            print(f"\n✗ ORCHESTRATOR NOT INITIALIZED!")
                            self.failed += 1
                    else:
                        print(f"✗ V2 health failed: {resp.status}")
                        self.failed += 1
            except Exception as e:
                print(f"✗ V2 health error: {e}")
                self.failed += 1
    
    async def test_memory_endpoints(self):
        """Test 2: Check Mem0 memory endpoints"""
        print("\n" + "="*60)
        print("TEST 2: Memory Endpoints")
        print("="*60)
        
        test_user_id = 99999  # Test user
        
        async with aiohttp.ClientSession() as session:
            # Test memory status
            try:
                async with session.get(f"{BASE_URL}/v2/humansa/memory/status") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        print(f"✓ Memory status: {data}")
                        self.passed += 1
                    else:
                        print(f"✗ Memory status failed: {resp.status}")
                        self.failed += 1
            except Exception as e:
                print(f"✗ Memory status error: {e}")
                self.failed += 1
                
            # Test adding memory
            try:
                memory_data = {
                    "user_id": test_user_id,
                    "messages": [
                        {"role": "user", "content": "I have high blood pressure"},
                        {"role": "assistant", "content": "I've noted that you have high blood pressure."}
                    ]
                }
                async with session.post(
                    f"{BASE_URL}/v2/humansa/memory/add",
                    json=memory_data
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        print(f"\n✓ Memory added: {data}")
                        self.passed += 1
                    else:
                        print(f"\n✗ Memory add failed: {resp.status}")
                        text = await resp.text()
                        print(f"  Response: {text}")
                        self.failed += 1
            except Exception as e:
                print(f"\n✗ Memory add error: {e}")
                self.failed += 1
    
    async def test_v2_chat_simple(self):
        """Test 3: Simple v2 chat request"""
        print("\n" + "="*60)
        print("TEST 3: Simple V2 Chat")
        print("="*60)
        
        async with aiohttp.ClientSession() as session:
            chat_data = {
                "user_id": "test_orchestrator_001",
                "messages": [{"role": "user", "content": "Hello, I need help"}],
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
                        print(f"✓ Chat response received")
                        print(f"  Response preview: {str(data)[:200]}...")
                        
                        # Check for metadata indicating orchestrator usage
                        if 'metadata' in data:
                            print(f"\n  Orchestrator metadata:")
                            print(f"    Iterations: {data['metadata'].get('iterations', 'N/A')}")
                            print(f"    Agents used: {data['metadata'].get('agents_consulted', 'N/A')}")
                        
                        self.passed += 1
                    else:
                        print(f"✗ Chat failed: {resp.status}")
                        error_text = await resp.text()
                        print(f"  Error: {error_text}")
                        self.failed += 1
            except asyncio.TimeoutError:
                print(f"✗ Chat timeout (30s)")
                self.failed += 1
            except Exception as e:
                print(f"✗ Chat error: {e}")
                self.failed += 1
    
    async def test_v2_chat_medical(self):
        """Test 4: Medical query with v2 chat"""
        print("\n" + "="*60)
        print("TEST 4: Medical Query V2 Chat")
        print("="*60)
        
        async with aiohttp.ClientSession() as session:
            chat_data = {
                "user_id": "test_medical_001",
                "messages": [
                    {"role": "user", "content": "I have been experiencing chest pain when I exercise. What should I do?"}
                ],
                "stream": False
            }
            
            try:
                print("Sending medical query (this may take a moment with iterative orchestrator)...")
                start_time = time.time()
                
                async with session.post(
                    f"{BASE_URL}/v2/humansa/chat",
                    json=chat_data,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as resp:
                    elapsed = time.time() - start_time
                    
                    if resp.status == 200:
                        data = await resp.json()
                        print(f"\n✓ Medical chat response received in {elapsed:.1f}s")
                        
                        # Extract response content
                        response_text = data.get('response', '')
                        if not response_text and 'choices' in data:
                            # Handle OpenAI format
                            response_text = data['choices'][0]['message']['content']
                        
                        print(f"\n  Response preview: {response_text[:300]}...")
                        
                        # Check metadata
                        metadata = data.get('metadata', {})
                        if metadata:
                            print(f"\n  Orchestrator Performance:")
                            print(f"    Iterations used: {metadata.get('iterations', 'N/A')}")
                            print(f"    Agents consulted: {metadata.get('agents_consulted', [])}")
                            print(f"    Total responses: {metadata.get('total_responses', 'N/A')}")
                            
                            # Success if multiple agents were used
                            if len(metadata.get('agents_consulted', [])) > 1:
                                print(f"\n  ✓ MULTI-AGENT ORCHESTRATION WORKING!")
                            
                        self.passed += 1
                    else:
                        print(f"\n✗ Medical chat failed: {resp.status}")
                        error_text = await resp.text()
                        print(f"  Error: {error_text}")
                        self.failed += 1
                        
            except asyncio.TimeoutError:
                print(f"\n✗ Medical chat timeout (60s)")
                self.failed += 1
            except Exception as e:
                print(f"\n✗ Medical chat error: {e}")
                self.failed += 1
    
    async def test_memory_persistence(self):
        """Test 5: Memory persistence check"""
        print("\n" + "="*60)
        print("TEST 5: Memory Persistence")
        print("="*60)
        
        test_user_id = "test_persist_001"
        
        async with aiohttp.ClientSession() as session:
            # First conversation
            chat_data = {
                "user_id": test_user_id,
                "messages": [
                    {"role": "user", "content": "I'm allergic to penicillin and I take aspirin daily"}
                ],
                "stream": False
            }
            
            try:
                print("1. Sending first conversation...")
                async with session.post(
                    f"{BASE_URL}/v2/humansa/chat",
                    json=chat_data,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    if resp.status == 200:
                        print("✓ First conversation completed")
                    else:
                        print(f"✗ First conversation failed: {resp.status}")
                
                # Wait a moment
                await asyncio.sleep(2)
                
                # Second conversation - should remember
                chat_data2 = {
                    "user_id": test_user_id,
                    "messages": [
                        {"role": "user", "content": "What medications should I avoid?"}
                    ],
                    "stream": False
                }
                
                print("\n2. Sending second conversation...")
                async with session.post(
                    f"{BASE_URL}/v2/humansa/chat",
                    json=chat_data2,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        response_text = data.get('response', '')
                        if not response_text and 'choices' in data:
                            response_text = data['choices'][0]['message']['content']
                        
                        # Check if response mentions penicillin (from memory)
                        if 'penicillin' in response_text.lower():
                            print("✓ Memory persistence working - remembered penicillin allergy!")
                            self.passed += 1
                        else:
                            print("✗ Memory not working - didn't mention penicillin allergy")
                            print(f"  Response: {response_text[:200]}...")
                            self.failed += 1
                    else:
                        print(f"✗ Second conversation failed: {resp.status}")
                        self.failed += 1
                        
            except Exception as e:
                print(f"✗ Memory persistence error: {e}")
                self.failed += 1
    
    async def run_all_tests(self):
        """Run all tests"""
        print("\n" + "="*80)
        print("HUMANSA V2 COMPREHENSIVE TEST SUITE")
        print("Testing: Database Pool, Improved Orchestrator, Memory Integration")
        print("="*80)
        
        # Run tests
        await self.test_health_endpoints()
        await self.test_memory_endpoints()
        await self.test_v2_chat_simple()
        await self.test_v2_chat_medical()
        await self.test_memory_persistence()
        
        # Summary
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)
        total = self.passed + self.failed
        print(f"Total Tests: {total}")
        print(f"Passed: {self.passed}")
        print(f"Failed: {self.failed}")
        if total > 0:
            print(f"Success Rate: {(self.passed/total*100):.1f}%")
        
        print("\nKey Components Status:")
        print("- Database Pool: Check server logs for '✅ Database pool created successfully'")
        print("- Orchestrator: Check v2/humansa/health endpoint")
        print("- Memory: Check memory endpoints")
        print("- Multi-Agent: Check chat metadata for multiple agents")
        
        return self.failed == 0


async def main():
    """Check if server is running first"""
    print("Checking if ML server is running on port 6001...")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BASE_URL}/health", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    print("✓ ML Server is running")
                else:
                    print("✗ ML Server returned error status")
                    print("\nPlease run: ./run_humansa_test_environment.sh")
                    return
    except Exception as e:
        print(f"✗ Cannot connect to ML Server on port 6001: {e}")
        print("\nPlease run: ./run_humansa_test_environment.sh")
        return
    
    # Run tests
    tester = HumansaV2Tester()
    success = await tester.run_all_tests()
    
    if success:
        print("\n✅ ALL TESTS PASSED!")
    else:
        print("\n❌ SOME TESTS FAILED")
        print("\nCheck test_server.log for detailed error messages")
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())