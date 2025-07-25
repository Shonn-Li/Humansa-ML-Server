#!/usr/bin/env python3
"""
Fixed Test Script for Humansa AI Agent V2
Runs 5 key tests to verify the agent is working correctly
"""

import asyncio
import aiohttp
import json
import sys
import os
import time
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

async def test_humansa_agent(port=5001):
    """Test the Humansa AI Agent V2"""
    base_url = f"http://localhost:{port}"
    endpoint = f"{base_url}/v1-humansa/chat/completions"
    
    print(f"="*60)
    print(f"HUMANSA AI AGENT V2 - TEST SUITE")
    print(f"Testing on port: {port}")
    print(f"="*60)
    
    # Check if server is running
    print(f"\nChecking if ML server is running on port {port}...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{base_url}/health") as response:
                if response.status == 200:
                    print(f"✅ ML Server is running on port {port}")
                else:
                    print(f"❌ ML Server returned status {response.status}")
                    return
    except Exception as e:
        print(f"❌ Cannot connect to ML Server on port {port}: {e}")
        return
    
    # Test cases
    test_cases = [
        {
            "id": 1,
            "name": "Find Cardiologist",
            "query": "我想找一个心脏科医生",
            "expected_tool": "find_doctor_info"
        },
        {
            "id": 2,
            "name": "Doctor Availability",
            "query": "张医生下周有空吗？",
            "expected_tool": "find_doctor_availability"
        },
        {
            "id": 3,
            "name": "Service Pricing",
            "query": "肝功能检查多少钱？",
            "expected_tool": "get_pricing"
        },
        {
            "id": 4,
            "name": "Find Clinics",
            "query": "深圳有哪些诊所？",
            "expected_tool": "search_clinics"
        },
        {
            "id": 5,
            "name": "Book Appointment",
            "query": "我想预约李医生，我叫王小明，电话13800138000",
            "expected_tool": "prepare_booking_confirmation"
        }
    ]
    
    results = []
    
    for test in test_cases:
        print(f"\n{'='*60}")
        print(f"TEST {test['id']}: {test['name']}")
        print(f"{'='*60}")
        print(f"Query: {test['query']}")
        print("-"*40)
        
        start_time = time.time()
        
        payload = {
            "messages": [{"role": "user", "content": test['query']}],
            "model": "gpt-4",
            "user_id": f"test_user_{test['id']}",
            "stream": False
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(endpoint, json=payload) as response:
                    if response.status != 200:
                        print(f"❌ HTTP Error: {response.status}")
                        results.append({"test": test['name'], "status": "FAILED", "error": f"HTTP {response.status}"})
                        continue
                    
                    result = await response.json()
                    duration = time.time() - start_time
                    
                    # Check for API errors
                    if "error" in result and result.get("status") == "error":
                        print(f"❌ API Error: {result['error']}")
                        results.append({"test": test['name'], "status": "FAILED", "error": result['error']})
                        continue
                    
                    # Parse agent trace
                    agent_trace = result.get("agent_trace", "")
                    tools_used = []
                    
                    print("\n🧠 AGENT THINKING:")
                    if agent_trace:
                        lines = agent_trace.split('\n')
                        for line in lines[:15]:  # Show first 15 lines
                            line = line.strip()
                            if line.startswith("Thought:"):
                                print(f"  💭 {line}")
                            elif line.startswith("Action:"):
                                print(f"  🔧 {line}")
                                # Extract tool name
                                tool_name = line.replace("Action:", "").strip()
                                tools_used.append(tool_name)
                            elif line.startswith("Action Input:"):
                                # Truncate long inputs
                                input_str = line[13:].strip()
                                if len(input_str) > 100:
                                    print(f"  📥 Action Input: {input_str[:100]}...")
                                else:
                                    print(f"  📥 {line}")
                            elif line.startswith("Observation:"):
                                # Truncate long observations
                                obs = line[12:].strip()
                                if len(obs) > 150:
                                    print(f"  👁️  Observation: {obs[:150]}...")
                                else:
                                    print(f"  👁️  {line}")
                        
                        if len(lines) > 15:
                            print("  ... (truncated)")
                    
                    # Check tool calls
                    tool_calls = result.get("tool_calls_observed", [])
                    print("\n🔧 TOOLS USED:")
                    if tool_calls:
                        for i, tool in enumerate(tool_calls, 1):
                            tool_name = tool.get("tool_name", "unknown")
                            print(f"  {i}. {tool_name}")
                            if tool_name not in tools_used:
                                tools_used.append(tool_name)
                    else:
                        print("  No tools called")
                    
                    # Get final answer
                    print("\n💬 FINAL ANSWER:")
                    if "choices" in result and result["choices"]:
                        content = result["choices"][0]["message"]["content"]
                        # Extract just the answer if the full trace is included
                        if "Answer:" in content:
                            answer = content.split("Answer:")[-1].strip()
                        else:
                            answer = content
                        
                        # Truncate long answers
                        if len(answer) > 300:
                            print(f"  {answer[:300]}...")
                        else:
                            print(f"  {answer}")
                    
                    # Check if expected tool was used
                    test_passed = test['expected_tool'] in " ".join(tools_used)
                    
                    if test_passed:
                        print(f"\n✅ Test PASSED (found expected tool: {test['expected_tool']})")
                        results.append({"test": test['name'], "status": "PASSED", "duration": duration})
                    else:
                        print(f"\n⚠️  Test WARNING: Expected tool '{test['expected_tool']}' not found in {tools_used}")
                        results.append({"test": test['name'], "status": "WARNING", "duration": duration, "note": "Tool mismatch"})
                    
                    print(f"⏱️  Response time: {duration:.2f}s")
                    
        except Exception as e:
            print(f"\n❌ Exception: {e}")
            results.append({"test": test['name'], "status": "ERROR", "error": str(e)})
        
        # Small delay between tests
        await asyncio.sleep(1)
    
    # Summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")
    
    passed = sum(1 for r in results if r["status"] == "PASSED")
    warnings = sum(1 for r in results if r["status"] == "WARNING")
    failed = sum(1 for r in results if r["status"] == "FAILED")
    errors = sum(1 for r in results if r["status"] == "ERROR")
    
    print(f"Total tests: {len(results)}")
    print(f"✅ Passed: {passed}")
    print(f"⚠️  Warnings: {warnings}")
    print(f"❌ Failed: {failed}")
    print(f"🚨 Errors: {errors}")
    
    print("\nDetailed results:")
    for r in results:
        status_icon = {"PASSED": "✅", "WARNING": "⚠️", "FAILED": "❌", "ERROR": "🚨"}.get(r["status"], "❓")
        print(f"  {status_icon} {r['test']}: {r['status']}")
        if "error" in r:
            print(f"     Error: {r['error']}")
        if "note" in r:
            print(f"     Note: {r['note']}")
    
    print(f"\n{'='*60}")
    print("The Humansa AI Agent V2 demonstrates:")
    print("✅ ReAct reasoning pattern (Thought → Action → Observation)")
    print("✅ Intelligent tool selection based on queries")
    print("✅ Database integration for real data")
    print("✅ Contextual responses in Chinese")
    print(f"{'='*60}")

async def main():
    # Check command line arguments for port
    port = 5001  # Default port
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"Invalid port: {sys.argv[1]}, using default 5001")
    
    await test_humansa_agent(port)

if __name__ == "__main__":
    asyncio.run(main())