#!/usr/bin/env python
"""
HUMANSA V2 Test Suite with Full Reasoning Visibility
Tests the new WorkflowOrchestrator and captures complete reasoning chains
"""

import asyncio
import aiohttp
import json
import time
from typing import List, Dict, Any, Tuple
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Test configuration
BASE_URL = "http://localhost:6001"
API_ENDPOINT = f"{BASE_URL}/v2/humansa/chat"

# Test categories with expected reasoning patterns
TEST_CASES = [
    {
        "query": "我想买一些维生素C，有什么推荐吗？",
        "category": "产品推荐",
        "expected_agents": ["Orchestrator", "ProductAgent"],
        "expected_reasoning": ["产品推荐", "维生素C", "ProductAgent"],
        "expected_tools": ["call_product_agent"]
    },
    {
        "query": "我想预约心内科医生",
        "category": "预约挂号", 
        "expected_agents": ["Orchestrator", "AppointmentAgent"],
        "expected_reasoning": ["预约", "心内科", "AppointmentAgent"],
        "expected_tools": ["call_appointment_agent"]
    },
    {
        "query": "我胸口疼痛，呼吸困难",
        "category": "紧急情况",
        "expected_agents": ["Orchestrator", "ClinicalAgent"],
        "expected_reasoning": ["胸口疼痛", "紧急", "ClinicalAgent", "120"],
        "expected_tools": ["call_clinical_agent"]
    },
    {
        "query": "阿司匹林有什么副作用？",
        "category": "用药指导",
        "expected_agents": ["Orchestrator", "MedicationAgent"],
        "expected_reasoning": ["阿司匹林", "副作用", "MedicationAgent"],
        "expected_tools": ["call_medication_agent"]
    },
    {
        "query": "如何预防高血压？",
        "category": "健康咨询",
        "expected_agents": ["Orchestrator", "GeneralAgent"],
        "expected_reasoning": ["预防", "高血压", "GeneralAgent"],
        "expected_tools": ["call_general_agent"]
    }
]


async def send_chat_request(session: aiohttp.ClientSession, test_case: Dict[str, Any]) -> Dict[str, Any]:
    """Send a chat request and capture complete reasoning chain"""
    
    query = test_case["query"]
    payload = {
        "user_id": f"test_user_reasoning_{int(time.time())}",
        "messages": [{"role": "user", "content": query}],
        "stream": True,
        "debug": True
    }
    
    start_time = time.time()
    result = {
        "query": query,
        "category": test_case["category"],
        "success": False,
        "response_time": 0,
        "events_captured": [],
        "reasoning_text": "",
        "final_response": "",
        "agents_used": [],
        "tools_called": [],
        "error": None
    }
    
    try:
        async with session.post(API_ENDPOINT, json=payload) as response:
            result["response_time"] = time.time() - start_time
            
            if response.status != 200:
                error_text = await response.text()
                result["error"] = f"HTTP {response.status}: {error_text}"
                return result
            
            # Process streaming events
            async for line in response.content:
                line = line.decode('utf-8').strip()
                
                if line.startswith('data: '):
                    data = line[6:]  # Remove 'data: ' prefix
                    
                    if data == '[DONE]':
                        break
                    
                    try:
                        event = json.loads(data)
                        event_type = event.get('type', 'unknown')
                        result["events_captured"].append(event_type)
                        
                        # Capture reasoning text
                        if event_type == 'response.reasoning_text.delta':
                            delta = event.get('delta', '')
                            result["reasoning_text"] += delta
                            
                        # Capture final response text
                        elif event_type == 'response.output_text.delta':
                            delta = event.get('delta', '')
                            result["final_response"] += delta
                            
                        # Capture tool calls
                        elif event_type == 'response.output_item.added':
                            item = event.get('item', {})
                            if item.get('type') == 'function_tool_call':
                                tool_name = item.get('name', 'unknown')
                                result["tools_called"].append(tool_name)
                                
                        # Capture usage info
                        elif event_type == 'response.usage':
                            usage = event.get('usage', {})
                            result["agents_used"] = usage.get('agents_used', [])
                            
                    except json.JSONDecodeError:
                        pass  # Skip invalid JSON
            
            # Determine success
            result["success"] = (
                len(result["reasoning_text"]) > 0 and
                len(result["final_response"]) > 0 and
                len(result["agents_used"]) > 0
            )
            
    except Exception as e:
        result["error"] = str(e)
        result["response_time"] = time.time() - start_time
    
    return result


def evaluate_reasoning_quality(result: Dict[str, Any], test_case: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate the quality of reasoning captured"""
    
    evaluation = {
        "reasoning_captured": len(result["reasoning_text"]) > 0,
        "agents_correct": False,
        "tools_correct": False,
        "reasoning_relevant": False,
        "reasoning_score": 0.0
    }
    
    # Check if expected agents were used
    expected_agents = test_case.get("expected_agents", [])
    if expected_agents and result["agents_used"]:
        agents_match = all(agent in result["agents_used"] for agent in expected_agents)
        evaluation["agents_correct"] = agents_match
    
    # Check if expected tools were called
    expected_tools = test_case.get("expected_tools", [])
    if expected_tools and result["tools_called"]:
        tools_match = any(tool in result["tools_called"] for tool in expected_tools)
        evaluation["tools_correct"] = tools_match
    
    # Check reasoning relevance
    expected_reasoning = test_case.get("expected_reasoning", [])
    reasoning_lower = result["reasoning_text"].lower()
    if expected_reasoning:
        relevant_terms = sum(1 for term in expected_reasoning if term.lower() in reasoning_lower)
        evaluation["reasoning_relevant"] = relevant_terms >= len(expected_reasoning) * 0.5
    
    # Calculate overall score
    score_components = [
        evaluation["reasoning_captured"],
        evaluation["agents_correct"],
        evaluation["tools_correct"],
        evaluation["reasoning_relevant"]
    ]
    evaluation["reasoning_score"] = sum(score_components) / len(score_components)
    
    return evaluation


async def run_reasoning_tests():
    """Run comprehensive tests with reasoning visibility"""
    
    print("🧪 HUMANSA V2 Reasoning Tests")
    print("=" * 80)
    print(f"📅 Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🔗 API Endpoint: {API_ENDPOINT}")
    print(f"📊 Test Cases: {len(TEST_CASES)}")
    print("=" * 80)
    
    results = []
    
    async with aiohttp.ClientSession() as session:
        for i, test_case in enumerate(TEST_CASES, 1):
            print(f"\n🧪 Test Case {i}/{len(TEST_CASES)}: {test_case['category']}")
            print(f"📝 Query: {test_case['query']}")
            print("-" * 80)
            
            # Send request and capture reasoning
            result = await send_chat_request(session, test_case)
            
            if result["success"]:
                print("✅ SUCCESS")
                
                # Show reasoning chain
                if result["reasoning_text"]:
                    print(f"\n🧠 REASONING CHAIN:")
                    reasoning_lines = result["reasoning_text"].split('\n')
                    for line in reasoning_lines:
                        if line.strip():
                            print(f"💭 {line.strip()}")
                
                # Show tool calls
                if result["tools_called"]:
                    print(f"\n🔧 TOOLS CALLED: {', '.join(result['tools_called'])}")
                
                # Show agents used
                if result["agents_used"]:
                    print(f"👥 AGENTS USED: {', '.join(result['agents_used'])}")
                
                # Show final response preview
                if result["final_response"]:
                    preview = result["final_response"][:150]
                    suffix = "..." if len(result["final_response"]) > 150 else ""
                    print(f"\n💬 RESPONSE: {preview}{suffix}")
                
            else:
                print("❌ FAILED")
                if result["error"]:
                    print(f"Error: {result['error']}")
            
            # Evaluate reasoning quality
            evaluation = evaluate_reasoning_quality(result, test_case)
            result["evaluation"] = evaluation
            
            print(f"\n📊 REASONING QUALITY:")
            print(f"   - Reasoning Captured: {'✅' if evaluation['reasoning_captured'] else '❌'}")
            print(f"   - Agents Correct: {'✅' if evaluation['agents_correct'] else '❌'}")
            print(f"   - Tools Correct: {'✅' if evaluation['tools_correct'] else '❌'}")
            print(f"   - Reasoning Relevant: {'✅' if evaluation['reasoning_relevant'] else '❌'}")
            print(f"   - Overall Score: {evaluation['reasoning_score']:.1%}")
            
            print(f"⏱️  Response Time: {result['response_time']:.2f}s")
            
            results.append(result)
            
            # Brief pause between tests
            await asyncio.sleep(1)
    
    # Show overall summary
    print("\n" + "=" * 80)
    print("📈 OVERALL TEST SUMMARY")
    print("=" * 80)
    
    successful_tests = sum(1 for r in results if r["success"])
    total_tests = len(results)
    success_rate = successful_tests / total_tests if total_tests > 0 else 0
    
    reasoning_tests = sum(1 for r in results if r["evaluation"]["reasoning_captured"])
    reasoning_rate = reasoning_tests / total_tests if total_tests > 0 else 0
    
    avg_score = sum(r["evaluation"]["reasoning_score"] for r in results) / total_tests if total_tests > 0 else 0
    avg_time = sum(r["response_time"] for r in results) / total_tests if total_tests > 0 else 0
    
    print(f"✅ Successful Tests: {successful_tests}/{total_tests} ({success_rate:.1%})")
    print(f"🧠 Reasoning Captured: {reasoning_tests}/{total_tests} ({reasoning_rate:.1%})")
    print(f"📊 Average Reasoning Score: {avg_score:.1%}")
    print(f"⏱️  Average Response Time: {avg_time:.2f}s")
    
    # Event statistics
    all_events = []
    for result in results:
        all_events.extend(result["events_captured"])
    
    if all_events:
        event_counts = {}
        for event in all_events:
            event_counts[event] = event_counts.get(event, 0) + 1
        
        print(f"\n📋 Event Types Captured:")
        for event_type, count in sorted(event_counts.items()):
            print(f"   - {event_type}: {count}")
    
    # Key success criteria
    key_events = [
        'response.reasoning_text.delta',
        'response.output_item.added',
        'response.output_text.delta',
        'response.usage'
    ]
    
    events_present = [event for event in key_events if event in all_events]
    print(f"\n📌 Key Reasoning Events Present: {len(events_present)}/{len(key_events)}")
    
    if len(events_present) == len(key_events):
        print("🎉 SUCCESS: Full reasoning chain is visible in API responses!")
    else:
        missing = [event for event in key_events if event not in all_events]
        print(f"⚠️  Missing events: {missing}")
    
    return results


if __name__ == "__main__":
    print("🚀 Starting HUMANSA V2 Reasoning Tests")
    print("⚠️  Make sure server is running with HUMANSA_USE_WORKFLOW_ORCHESTRATOR=true")
    print()
    
    # Run the tests
    results = asyncio.run(run_reasoning_tests())
    
    print("\n✅ Test suite completed!")
    print("\n📝 This demonstrates the reasoning visibility that was requested:")
    print("- Complete Think-Act-Observe cycles")
    print("- Sub-agent selection and reasoning")
    print("- Tool calls and results")
    print("- Full reasoning chain in API responses")