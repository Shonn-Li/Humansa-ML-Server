#!/usr/bin/env python3
"""
Test Code Interpreter Agent specifically
"""

import asyncio
import json
import logging
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_code_interpreter_detection():
    """Test if code interpreter agent is properly detected and triggered"""
    logger.info("🧪 Testing Code Interpreter Agent Detection")
    
    try:
        from chat.endpoints.multi_agent_endpoint_v2 import MultiAgentChatEndpointV2
        
        endpoint = MultiAgentChatEndpointV2()
        
        test_cases = [
            {
                "name": "Python Code Request",
                "query": "Please execute this Python code: print('Hello World')",
                "expected": True
            },
            {
                "name": "Math Calculation",
                "query": "Calculate the square root of 144 using Python",
                "expected": True
            },
            {
                "name": "Data Analysis Request",
                "query": "Analyze this dataset and create a plot",
                "expected": True
            },
            {
                "name": "Code Block Request",
                "query": "Can you help me with this?\n```python\nimport numpy as np\nprint(np.array([1,2,3]))\n```",
                "expected": True
            },
            {
                "name": "Regular Question",
                "query": "What is the weather like today?",
                "expected": False
            }
        ]
        
        results = []
        
        for test_case in test_cases:
            logger.info(f"🔍 Testing: {test_case['name']}")
            
            # Test router detection
            request = {
                "messages": [{"role": "user", "content": test_case["query"]}],
                "model": "gpt-4o-mini",
                "user_id": "test_user_123"
            }
            
            router_result = await endpoint.agents["router"].run(request, {})
            enabled_agents = router_result.get("enabled_agents", [])
            
            code_interpreter_enabled = "code_interpreter" in enabled_agents
            
            result = {
                "name": test_case["name"],
                "query": test_case["query"],
                "expected": test_case["expected"],
                "actual": code_interpreter_enabled,
                "success": code_interpreter_enabled == test_case["expected"],
                "enabled_agents": enabled_agents
            }
            
            results.append(result)
            
            status = "✅" if result["success"] else "❌"
            logger.info(f"{status} {test_case['name']}: Expected={test_case['expected']}, Got={code_interpreter_enabled}")
            logger.info(f"   Enabled agents: {enabled_agents}")
        
        # Summary
        successful = sum(1 for r in results if r["success"])
        total = len(results)
        
        logger.info(f"\n📊 Code Interpreter Detection Results: {successful}/{total} passed")
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Code interpreter detection test failed: {e}")
        import traceback
        traceback.print_exc()
        return []


async def test_code_interpreter_execution():
    """Test actual code interpreter execution"""
    logger.info("⚙️ Testing Code Interpreter Execution")
    
    try:
        from chat.agent.code_interpreter_agent import CodeInterpreterAgent
        
        agent = CodeInterpreterAgent()
        
        test_cases = [
            {
                "name": "Simple Print",
                "message": "print('Hello from code interpreter!')",
                "expected_keywords": ["Hello", "interpreter"]
            },
            {
                "name": "Math Calculation",
                "message": "calculate the factorial of 5",
                "expected_keywords": ["factorial", "120"]
            },
            {
                "name": "Python Code Block",
                "message": "Execute this:\n```python\nimport math\nresult = math.sqrt(16)\nprint(f'Square root of 16 is {result}')\n```",
                "expected_keywords": ["Square root", "4"]
            }
        ]
        
        results = []
        
        for test_case in test_cases:
            logger.info(f"🔬 Testing: {test_case['name']}")
            
            request = {
                "messages": [{"role": "user", "content": test_case["message"]}],
                "model": "gpt-4o-mini",
                "user_id": "test_user_123"
            }
            
            # Test non-streaming execution
            result = await agent.run(request, {})
            
            success = result.get("status") == "success"
            code_blocks = result.get("code_blocks", 0)
            execution_results = result.get("results", [])
            
            test_result = {
                "name": test_case["name"],
                "success": success,
                "code_blocks": code_blocks,
                "execution_results": len(execution_results),
                "details": result
            }
            
            results.append(test_result)
            
            status = "✅" if success else "❌"
            logger.info(f"{status} {test_case['name']}: {code_blocks} code blocks, {len(execution_results)} results")
        
        # Test streaming execution
        logger.info("🌊 Testing streaming execution...")
        
        stream_request = {
            "messages": [{"role": "user", "content": "Create a simple plot using matplotlib"}],
            "model": "gpt-4o-mini",
            "user_id": "test_user_123"
        }
        
        stream_events = []
        async for event in agent.stream(stream_request, {}):
            stream_events.append(event)
            logger.info(f"Stream event: {event.get('type', 'unknown')}")
        
        logger.info(f"📡 Streaming produced {len(stream_events)} events")
        
        return {
            "execution_results": results,
            "streaming_events": len(stream_events),
            "streaming_success": len(stream_events) > 0
        }
        
    except Exception as e:
        logger.error(f"❌ Code interpreter execution test failed: {e}")
        import traceback
        traceback.print_exc()
        return {}


async def test_multi_agent_with_code_interpreter():
    """Test full multi-agent workflow with code interpreter"""
    logger.info("🔄 Testing Multi-Agent Workflow with Code Interpreter")
    
    try:
        from chat.endpoints.multi_agent_endpoint_v2 import MultiAgentChatEndpointV2
        
        endpoint = MultiAgentChatEndpointV2()
        
        # Test streaming with code interpreter trigger
        request = {
            "messages": [
                {"role": "user", "content": "Please calculate the fibonacci sequence up to 10 terms using Python code and explain the results"}
            ],
            "model": "gpt-4o-mini",
            "user_id": "test_user_123",
            "stream": True
        }
        
        result = await endpoint.handle_request(request)
        
        events = []
        code_interpreter_events = []
        
        async for event in result:
            events.append(event)
            
            # Track code interpreter related events
            if 'code' in event.get('type', '').lower() or 'function_tool' in event.get('type', ''):
                code_interpreter_events.append(event)
            
            logger.info(f"Event: {event.get('type')} - {event.get('item', {}).get('type', '')}")
            
            # Limit for testing
            if len(events) >= 50:
                break
        
        logger.info(f"📊 Multi-Agent with Code Interpreter Results:")
        logger.info(f"   Total Events: {len(events)}")
        logger.info(f"   Code Interpreter Events: {len(code_interpreter_events)}")
        
        # Check if code interpreter was triggered
        code_interpreter_triggered = any(
            event.get('item', {}).get('name') == 'python_interpreter' or
            'code' in event.get('type', '').lower()
            for event in events
        )
        
        return {
            "success": len(events) > 0,
            "total_events": len(events),
            "code_interpreter_events": len(code_interpreter_events),
            "code_interpreter_triggered": code_interpreter_triggered
        }
        
    except Exception as e:
        logger.error(f"❌ Multi-agent with code interpreter test failed: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


async def main():
    """Run all code interpreter tests"""
    logger.info("🧪 Code Interpreter Agent Test Suite")
    logger.info("=" * 60)
    
    # Test 1: Detection
    logger.info("\n" + "=" * 60)
    detection_results = await test_code_interpreter_detection()
    
    # Test 2: Execution
    logger.info("\n" + "=" * 60)
    execution_results = await test_code_interpreter_execution()
    
    # Test 3: Multi-Agent Integration
    logger.info("\n" + "=" * 60)
    integration_results = await test_multi_agent_with_code_interpreter()
    
    # Final Report
    logger.info("\n" + "=" * 60)
    logger.info("🏁 Code Interpreter Test Results")
    logger.info("=" * 60)
    
    detection_success = sum(1 for r in detection_results if r.get("success", False)) if detection_results else 0
    detection_total = len(detection_results) if detection_results else 0
    
    execution_success = bool(execution_results.get("execution_results")) and execution_results.get("streaming_success", False)
    integration_success = integration_results.get("success", False)
    
    logger.info(f"📊 Test Results:")
    logger.info(f"   Detection: {detection_success}/{detection_total} ({'✅ PASS' if detection_success == detection_total else '❌ FAIL'})")
    logger.info(f"   Execution: {'✅ PASS' if execution_success else '❌ FAIL'}")
    logger.info(f"   Integration: {'✅ PASS' if integration_success else '❌ FAIL'}")
    
    if integration_results.get("code_interpreter_triggered"):
        logger.info("✅ Code interpreter was successfully triggered in multi-agent workflow")
    else:
        logger.warning("⚠️ Code interpreter was not triggered in multi-agent workflow")
    
    overall_success = (detection_success == detection_total) and execution_success and integration_success
    
    if overall_success:
        logger.info("\n🎉 ALL CODE INTERPRETER TESTS PASSED!")
    else:
        logger.error("\n💥 SOME CODE INTERPRETER TESTS FAILED!")
    
    # Save results
    results = {
        "detection": detection_results,
        "execution": execution_results,
        "integration": integration_results,
        "summary": {
            "detection_success": detection_success,
            "detection_total": detection_total,
            "execution_success": execution_success,
            "integration_success": integration_success,
            "overall_success": overall_success
        }
    }
    
    with open("code_interpreter_test_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    logger.info(f"\n📄 Detailed results saved to: code_interpreter_test_results.json")
    
    return overall_success


if __name__ == "__main__":
    asyncio.run(main())