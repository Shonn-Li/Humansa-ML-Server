#!/usr/bin/env python3
"""
Test tool execution in Humansa agent
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.humansa.agent.humansa_agent import HumansaAgenticAgent
from src.humansa.prompts.humansa_system_prompt_v2 import get_humansa_react_prompt_v2

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Disable some noisy loggers
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('openai').setLevel(logging.WARNING)
logging.getLogger('llama_index').setLevel(logging.WARNING)


async def test_tool_execution():
    """Test tool execution with specific queries"""
    print("\n🔧 Tool Execution Test Suite")
    print("=" * 50)
    
    # Initialize agent
    agent = HumansaAgenticAgent()
    await agent.initialize()
    
    # Check if v2 prompt is loaded
    react_prompt = get_humansa_react_prompt_v2()
    print(f"\n📋 V2 React Prompt loaded: {len(react_prompt)} chars")
    print(f"Identity section present: {'【身份信息】' in react_prompt}")
    print(f"Dialogue principles present: {'【对话原则】' in react_prompt}")
    
    # Test queries that should trigger tool calls
    test_queries = [
        {
            "name": "Doctor Search",
            "query": "查找张医生",
            "expected_tool": "search_doctors"
        },
        {
            "name": "Clinic Search", 
            "query": "查看深圳的诊所",
            "expected_tool": "find_clinic_info"
        },
        {
            "name": "Doctor Availability",
            "query": "查看张医生明天的预约时间",
            "expected_tool": "check_doctor_availability"
        },
        {
            "name": "Service Pricing",
            "query": "查询体检套餐的价格",
            "expected_tool": "search_medical_services"
        }
    ]
    
    results = []
    
    for test in test_queries:
        print(f"\n🧪 Test: {test['name']}")
        print(f"   Query: {test['query']}")
        print(f"   Expected Tool: {test['expected_tool']}")
        
        try:
            # Execute query
            response = await agent.execute_with_tools(
                query=test['query'],
                conversation_history=[],
                context_results=[],
                user_id="test_user"
            )
            
            # Extract results
            tool_calls = response.get('tool_calls_observed', [])
            agent_response = response.get('agent_response', '')
            trace = response.get('agent_trace', '')
            
            # Check results
            tool_called = False
            tools_used = []
            for call in tool_calls:
                tools_used.append(call.get('tool_name', 'unknown'))
                if call.get('tool_name') == test['expected_tool']:
                    tool_called = True
            
            # Check if trace contains ReAct pattern
            has_react_pattern = all(pattern in trace for pattern in ["Thought:", "Action:", "Observation:"])
            
            # Check if response contains tool results
            has_results = any(call.get('result') for call in tool_calls)
            
            result = {
                "test": test['name'],
                "query": test['query'],
                "expected_tool": test['expected_tool'],
                "tools_called": tools_used,
                "tool_called_correctly": tool_called,
                "has_react_pattern": has_react_pattern,
                "has_results": has_results,
                "num_tool_calls": len(tool_calls),
                "response_length": len(agent_response)
            }
            
            # Print results
            print(f"   ✅ Tool Called: {tool_called} (Used: {', '.join(tools_used)})")
            print(f"   ✅ ReAct Pattern: {has_react_pattern}")
            print(f"   ✅ Has Results: {has_results}")
            print(f"   ✅ Response Length: {len(agent_response)} chars")
            
            # Show sample of tool results
            if tool_calls and tool_calls[0].get('result'):
                result_preview = str(tool_calls[0]['result'])[:200]
                print(f"   📊 Result Preview: {result_preview}...")
            
            results.append(result)
            
        except Exception as e:
            logger.error(f"❌ Test failed: {e}")
            results.append({
                "test": test['name'],
                "error": str(e)
            })
    
    # Summary
    print("\n📊 Test Summary:")
    print("=" * 50)
    
    successful_tests = [r for r in results if not r.get('error')]
    failed_tests = [r for r in results if r.get('error')]
    correct_tool_calls = [r for r in successful_tests if r.get('tool_called_correctly')]
    
    print(f"Total Tests: {len(results)}")
    print(f"Successful: {len(successful_tests)}")
    print(f"Failed: {len(failed_tests)}")
    print(f"Correct Tool Calls: {len(correct_tool_calls)}/{len(successful_tests)}")
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"tool_execution_test_results_{timestamp}.json"
    
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump({
            "timestamp": timestamp,
            "test_results": results,
            "summary": {
                "total": len(results),
                "successful": len(successful_tests),
                "failed": len(failed_tests),
                "correct_tool_calls": len(correct_tool_calls)
            }
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n📄 Results saved to: {results_file}")


if __name__ == "__main__":
    asyncio.run(test_tool_execution())