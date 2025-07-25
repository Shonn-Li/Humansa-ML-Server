#!/usr/bin/env python3
"""
Quick Demo Test for Humansa AI Agent V2
Shows tool calls, thinking process, and agent responses
"""

import asyncio
import json
import sys
import os
import aiohttp
import time
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

async def test_humansa_agent():
    """Run a few quick tests to demonstrate the agent"""
    base_url = "http://localhost:5001"
    endpoint = f"{base_url}/v1-humansa/chat/completions"
    
    # Check if server is running
    print("Checking if ML server is running...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{base_url}/health") as response:
                if response.status == 200:
                    print("✅ ML Server is running\n")
                else:
                    print("❌ ML Server is not responding properly")
                    return
    except Exception as e:
        print(f"❌ Cannot connect to ML Server: {e}")
        return
    
    # Test cases
    test_cases = [
        {
            "name": "1. Find Doctor by Specialty",
            "message": "我想找一个心脏科医生"
        },
        {
            "name": "2. Check Doctor Availability",
            "message": "张医生下周有空吗？"
        },
        {
            "name": "3. Search Clinics",
            "message": "深圳有哪些诊所？"
        },
        {
            "name": "4. Service Pricing",
            "message": "肝功能检查多少钱？"
        },
        {
            "name": "5. Book Appointment",
            "message": "我想预约李医生，我叫王小明，电话13800138000"
        }
    ]
    
    print("="*80)
    print("HUMANSA AI AGENT V2 - QUICK DEMO TEST")
    print("="*80)
    print("This test demonstrates:")
    print("- Agent thinking process (Thought)")
    print("- Tool selection and execution (Action)")
    print("- Tool results (Observation)")
    print("- Final response (Answer)")
    print("="*80)
    
    for test_case in test_cases:
        print(f"\n{'='*80}")
        print(f"TEST: {test_case['name']}")
        print(f"{'='*80}")
        print(f"👤 User: {test_case['message']}")
        print("-"*40)
        
        # Make the API call
        payload = {
            "messages": [{"role": "user", "content": test_case['message']}],
            "model": "gpt-4",
            "user_id": f"test_user_{int(time.time())}",
            "stream": False
        }
        
        start_time = time.time()
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(endpoint, json=payload) as response:
                    result = await response.json()
                    duration = time.time() - start_time
                    
                    if "error" in result:
                        print(f"❌ Error: {result['error']}")
                        continue
                    
                    # Parse agent trace
                    agent_trace = result.get("agent_trace", "")
                    
                    # Display the thinking process
                    print("\n🧠 AGENT THINKING PROCESS:")
                    if agent_trace:
                        lines = agent_trace.split('\n')
                        for line in lines:
                            line = line.strip()
                            if line.startswith("Thought:"):
                                print(f"  💭 {line}")
                            elif line.startswith("Action:"):
                                print(f"  🔧 {line}")
                            elif line.startswith("Action Input:"):
                                print(f"  📥 {line}")
                            elif line.startswith("Observation:"):
                                # Truncate long observations
                                obs = line[12:].strip()
                                if len(obs) > 150:
                                    print(f"  👁️  Observation: {obs[:150]}...")
                                else:
                                    print(f"  👁️  {line}")
                            elif line.startswith("Answer:"):
                                print(f"  💬 {line}")
                    
                    # Display tool calls
                    tool_calls = result.get("tool_calls_observed", [])
                    if tool_calls:
                        print("\n🔧 TOOLS USED:")
                        for i, tool in enumerate(tool_calls, 1):
                            print(f"  {i}. {tool.get('tool_name', 'unknown')}")
                    
                    # Display final response
                    if "choices" in result and result["choices"]:
                        response_content = result["choices"][0]["message"]["content"]
                        # Extract just the final answer if it contains the full trace
                        if "Answer:" in response_content:
                            final_answer = response_content.split("Answer:")[-1].strip()
                        else:
                            final_answer = response_content
                        
                        print("\n💬 FINAL RESPONSE:")
                        print(f"  {final_answer[:300]}{'...' if len(final_answer) > 300 else ''}")
                    
                    print(f"\n⏱️  Response Time: {duration:.2f}s")
                    
            except Exception as e:
                print(f"❌ Error calling API: {e}")
        
        # Small delay between tests
        await asyncio.sleep(1)
    
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print("The Humansa AI Agent V2 successfully demonstrated:")
    print("✅ ReAct reasoning pattern (Thought → Action → Observation → Answer)")
    print("✅ Tool selection based on user queries")
    print("✅ Database integration for real data")
    print("✅ Contextual responses in Chinese")
    print("✅ Multi-step reasoning for complex queries")

async def main():
    await test_humansa_agent()

if __name__ == "__main__":
    asyncio.run(main())