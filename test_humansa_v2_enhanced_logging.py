#!/usr/bin/env python3
"""
Enhanced HUMANSA V2 Test with Comprehensive Logging
This test script provides detailed logging of the entire V2 process including:
- Thinking process
- Agents called and their order
- Each agent's reasoning
- Tool calls made
- Mem0 integration status
- Full responses (not truncated)
"""

import asyncio
import aiohttp
import json
import os
from datetime import datetime
import time
from typing import Dict, Any, List
import sys

# Test configuration
TEST_PORT = os.getenv('ML_SERVER_PORT', '6001')
BASE_URL = f"http://localhost:{TEST_PORT}"

# Color codes for better visibility
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_colored(text: str, color: str = Colors.ENDC):
    """Print text with color"""
    print(f"{color}{text}{Colors.ENDC}")

def print_section(title: str):
    """Print a section header"""
    print_colored(f"\n{'='*80}", Colors.BLUE)
    print_colored(f"  {title}", Colors.BOLD + Colors.BLUE)
    print_colored(f"{'='*80}", Colors.BLUE)

def print_subsection(title: str):
    """Print a subsection header"""
    print_colored(f"\n{'-'*60}", Colors.CYAN)
    print_colored(f"  {title}", Colors.CYAN)
    print_colored(f"{'-'*60}", Colors.CYAN)

# Test cases focusing on different aspects
TEST_CASES = [
    {
        "id": 1,
        "name": "Identity Query",
        "query": "你是谁？",
        "expected_behavior": "Should identify as 诺亚新舟健康医疗助理/小诺",
        "test_focus": ["identity", "mem0_integration"]
    },
    {
        "id": 2,
        "name": "Medical Consultation with Tool Calls",
        "query": "我最近总是头痛，需要看什么科室？",
        "expected_behavior": "Should analyze symptoms and recommend appropriate department",
        "test_focus": ["agent_routing", "tool_calls", "reasoning"]
    },
    {
        "id": 3,
        "name": "Appointment Booking Flow",
        "query": "我想预约明天下午的心内科医生",
        "expected_behavior": "Should use appointment tools and check availability",
        "test_focus": ["tool_calls", "agent_coordination", "appointment_flow"]
    },
    {
        "id": 4,
        "name": "Emergency Scenario",
        "query": "我现在胸痛很厉害，呼吸困难",
        "expected_behavior": "Should immediately recommend calling 120",
        "test_focus": ["emergency_response", "priority_handling"]
    },
    {
        "id": 5,
        "name": "Multi-Agent Complex Query",
        "query": "我有高血压，正在吃降压药，最近想做个全面体检，你们有什么推荐？",
        "expected_behavior": "Should coordinate multiple agents for comprehensive response",
        "test_focus": ["multi_agent", "reasoning", "tool_coordination"]
    }
]

async def test_v2_streaming_endpoint(session: aiohttp.ClientSession, test_case: Dict[str, Any]):
    """Test V2 endpoint with streaming to capture all process details"""
    
    print_subsection(f"Test {test_case['id']}: {test_case['name']}")
    print(f"Query: {test_case['query']}")
    print(f"Expected: {test_case['expected_behavior']}")
    print(f"Focus areas: {', '.join(test_case['test_focus'])}")
    
    request_data = {
        "user_id": f"test_user_{test_case['id']}",
        "messages": [{"role": "user", "content": test_case['query']}],
        "stream": True,  # Enable streaming for detailed output
        "debug": True    # Request debug information if supported
    }
    
    # Track the entire process
    process_log = {
        "test_id": test_case['id'],
        "test_name": test_case['name'],
        "query": test_case['query'],
        "timestamp": datetime.now().isoformat(),
        "thinking_steps": [],
        "agents_called": [],
        "tool_calls": [],
        "mem0_data": {},
        "full_response": "",
        "streaming_events": []
    }
    
    try:
        print_colored("\n🚀 Sending request...", Colors.YELLOW)
        start_time = time.time()
        
        async with session.post(
            f"{BASE_URL}/v2/humansa/chat",
            json=request_data,
            timeout=aiohttp.ClientTimeout(total=60)
        ) as response:
            
            if response.status != 200:
                error_text = await response.text()
                print_colored(f"❌ Error {response.status}: {error_text}", Colors.RED)
                process_log["error"] = f"HTTP {response.status}: {error_text}"
                return process_log
            
            print_colored("✅ Connected, receiving stream...\n", Colors.GREEN)
            
            # Process streaming response
            async for line in response.content:
                if line:
                    decoded = line.decode('utf-8').strip()
                    
                    # Parse SSE format
                    if decoded.startswith('data: '):
                        data_str = decoded[6:]  # Remove 'data: ' prefix
                        
                        if data_str == '[DONE]':
                            print_colored("\n✅ Stream completed", Colors.GREEN)
                            break
                        
                        try:
                            data = json.loads(data_str)
                            process_log["streaming_events"].append(data)
                            
                            # Extract and display different types of events
                            event_type = data.get('type', 'unknown')
                            
                            # Agent thinking/reasoning
                            if event_type == 'thinking' or 'thought' in data:
                                thought = data.get('thought') or data.get('content', '')
                                print_colored(f"💭 Thinking: {thought}", Colors.CYAN)
                                process_log["thinking_steps"].append({
                                    "timestamp": time.time() - start_time,
                                    "thought": thought
                                })
                            
                            # Agent invocation
                            elif event_type == 'agent_call' or 'agent' in data:
                                agent_name = data.get('agent', 'unknown')
                                agent_input = data.get('input', '')
                                print_colored(f"🤖 Agent Called: {agent_name}", Colors.YELLOW)
                                print_colored(f"   Input: {agent_input}", Colors.YELLOW)
                                process_log["agents_called"].append({
                                    "timestamp": time.time() - start_time,
                                    "agent": agent_name,
                                    "input": agent_input
                                })
                            
                            # Tool calls
                            elif event_type == 'tool_call' or 'tool' in data:
                                tool_name = data.get('tool', 'unknown')
                                tool_input = data.get('input', {})
                                print_colored(f"🔧 Tool Called: {tool_name}", Colors.BLUE)
                                print_colored(f"   Parameters: {json.dumps(tool_input, ensure_ascii=False)}", Colors.BLUE)
                                process_log["tool_calls"].append({
                                    "timestamp": time.time() - start_time,
                                    "tool": tool_name,
                                    "input": tool_input
                                })
                            
                            # Tool results
                            elif event_type == 'tool_result' or 'observation' in data:
                                result = data.get('observation') or data.get('result', '')
                                print_colored(f"📊 Tool Result: {result[:200]}{'...' if len(str(result)) > 200 else ''}", Colors.GREEN)
                            
                            # Mem0 data
                            elif event_type == 'memory' or 'mem0' in data:
                                memory_data = data.get('memory', {})
                                print_colored(f"🧠 Mem0 Data: {json.dumps(memory_data, ensure_ascii=False)[:200]}...", Colors.MAGENTA)
                                process_log["mem0_data"] = memory_data
                            
                            # Regular content
                            elif 'choices' in data:
                                for choice in data.get('choices', []):
                                    delta = choice.get('delta', {})
                                    if 'content' in delta:
                                        content = delta['content']
                                        process_log["full_response"] += content
                                        print(content, end='', flush=True)
                            
                            # Debug information
                            elif event_type == 'debug' or 'debug' in data:
                                debug_info = data.get('debug', data)
                                print_colored(f"🐛 Debug: {json.dumps(debug_info, ensure_ascii=False, indent=2)}", Colors.CYAN)
                            
                        except json.JSONDecodeError:
                            print_colored(f"⚠️  Raw data: {data_str}", Colors.YELLOW)
            
            elapsed_time = time.time() - start_time
            process_log["elapsed_time"] = elapsed_time
            
            print_colored(f"\n\n⏱️  Total time: {elapsed_time:.2f}s", Colors.GREEN)
            
    except asyncio.TimeoutError:
        print_colored("❌ Request timeout", Colors.RED)
        process_log["error"] = "Timeout"
    except Exception as e:
        print_colored(f"❌ Exception: {e}", Colors.RED)
        process_log["error"] = str(e)
    
    return process_log

async def analyze_process_log(log: Dict[str, Any]):
    """Analyze and display process insights"""
    print_subsection("Process Analysis")
    
    # Agent flow
    if log["agents_called"]:
        print_colored("\n🤖 Agent Execution Flow:", Colors.BOLD)
        for i, agent in enumerate(log["agents_called"], 1):
            print(f"   {i}. {agent['agent']} (at {agent['timestamp']:.2f}s)")
    else:
        print_colored("   No explicit agent calls logged", Colors.YELLOW)
    
    # Tool usage
    if log["tool_calls"]:
        print_colored("\n🔧 Tools Used:", Colors.BOLD)
        tool_counts = {}
        for tool in log["tool_calls"]:
            tool_name = tool['tool']
            tool_counts[tool_name] = tool_counts.get(tool_name, 0) + 1
        for tool_name, count in tool_counts.items():
            print(f"   - {tool_name}: {count} call(s)")
    else:
        print_colored("   No tool calls logged", Colors.YELLOW)
    
    # Thinking process
    if log["thinking_steps"]:
        print_colored("\n💭 Thinking Process Summary:", Colors.BOLD)
        print(f"   Total thinking steps: {len(log['thinking_steps'])}")
        print(f"   First thought: {log['thinking_steps'][0]['thought'][:100]}...")
        if len(log["thinking_steps"]) > 1:
            print(f"   Last thought: {log['thinking_steps'][-1]['thought'][:100]}...")
    
    # Mem0 integration
    if log["mem0_data"]:
        print_colored("\n🧠 Mem0 Integration:", Colors.BOLD)
        print(f"   Memory data available: Yes")
        print(f"   Data preview: {json.dumps(log['mem0_data'], ensure_ascii=False)[:200]}...")
    else:
        print_colored("\n🧠 Mem0 Integration: No memory data detected", Colors.YELLOW)
    
    # Response analysis
    if log["full_response"]:
        print_colored("\n📝 Response Analysis:", Colors.BOLD)
        print(f"   Response length: {len(log['full_response'])} characters")
        print(f"   Response preview: {log['full_response'][:200]}...")

async def test_health_and_status():
    """Check V2 health and component status"""
    print_section("Health Check")
    
    async with aiohttp.ClientSession() as session:
        try:
            # V2 Health check
            async with session.get(f"{BASE_URL}/v2/humansa/health") as resp:
                if resp.status == 200:
                    health = await resp.json()
                    print_colored("✅ V2 Health Check Passed", Colors.GREEN)
                    print(f"   Status: {health.get('status', 'unknown')}")
                    print(f"   Version: {health.get('version', 'unknown')}")
                    
                    # Check components
                    components = health.get('components', {})
                    print_colored("\n📦 Components:", Colors.BOLD)
                    for component, status in components.items():
                        status_color = Colors.GREEN if status == 'healthy' else Colors.RED
                        print_colored(f"   - {component}: {status}", status_color)
                    
                    # Check Mem0 status specifically
                    if 'mem0' in components:
                        print_colored(f"\n🧠 Mem0 Status: {components['mem0']}", Colors.CYAN)
                    else:
                        print_colored("\n⚠️  Mem0 status not reported", Colors.YELLOW)
                    
                    return True
                else:
                    print_colored(f"❌ V2 Health Check Failed: {resp.status}", Colors.RED)
                    return False
                    
        except Exception as e:
            print_colored(f"❌ Cannot connect to V2 endpoint: {e}", Colors.RED)
            return False

async def run_enhanced_tests():
    """Run all tests with enhanced logging"""
    print_colored("""
╔═══════════════════════════════════════════════════════════════╗
║     HUMANSA V2 Enhanced Test Suite with Full Logging         ║
║                                                               ║
║  This test will show:                                         ║
║  • Complete thinking process                                  ║
║  • All agents called and their order                          ║
║  • Each agent's reasoning                                     ║
║  • All tool calls with parameters                             ║
║  • Mem0 integration status and data                           ║
║  • Full untruncated responses                                 ║
╚═══════════════════════════════════════════════════════════════╝
    """, Colors.CYAN + Colors.BOLD)
    
    # Check health first
    if not await test_health_and_status():
        return
    
    # Run tests
    all_logs = []
    async with aiohttp.ClientSession() as session:
        for test_case in TEST_CASES:
            print_section(f"Running Test {test_case['id']}/{len(TEST_CASES)}")
            
            log = await test_v2_streaming_endpoint(session, test_case)
            all_logs.append(log)
            
            # Analyze the process
            await analyze_process_log(log)
            
            # Wait between tests
            await asyncio.sleep(2)
    
    # Save detailed results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"HUMANSA_v2_enhanced_test_logs_{timestamp}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump({
            "test_run": timestamp,
            "total_tests": len(TEST_CASES),
            "detailed_logs": all_logs
        }, f, ensure_ascii=False, indent=2)
    
    print_section("Test Summary")
    print(f"✅ Completed {len(TEST_CASES)} tests")
    print(f"📄 Detailed logs saved to: {filename}")
    
    # Summary statistics
    total_agents = sum(len(log.get("agents_called", [])) for log in all_logs)
    total_tools = sum(len(log.get("tool_calls", [])) for log in all_logs)
    mem0_tests = sum(1 for log in all_logs if log.get("mem0_data"))
    
    print_colored("\n📊 Statistics:", Colors.BOLD)
    print(f"   Total agent calls: {total_agents}")
    print(f"   Total tool calls: {total_tools}")
    print(f"   Tests with Mem0 data: {mem0_tests}/{len(TEST_CASES)}")

if __name__ == "__main__":
    # Enable colored output on Windows
    if sys.platform == "win32":
        os.system("color")
    
    asyncio.run(run_enhanced_tests())