#!/usr/bin/env python3
"""HUMANSA V2 Pattern 2 Test Suite - 70 Test Cases with Enhanced Logging"""

import asyncio
import aiohttp
import json
import os
from datetime import datetime
import time
import sys
from typing import List, Dict, Any, Optional
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'pattern2_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Test configuration
TEST_PORT = os.getenv('ML_SERVER_PORT', '6001')
BASE_URL = f"http://localhost:{TEST_PORT}"

# Colors for output
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
    MAGENTA = '\033[35m'

def print_colored(text, color=Colors.ENDC):
    """Print text with color"""
    print(f"{color}{text}{Colors.ENDC}")

def print_section(title):
    """Print a section header"""
    print_colored(f"\n{'='*80}", Colors.BLUE)
    print_colored(f"  {title}", Colors.BOLD + Colors.BLUE)
    print_colored(f"{'='*80}", Colors.BLUE)

# Import test cases from original file
try:
    from test_HUMANSA_v2_70_cases_multiturn import SINGLE_TURN_TEST_CASES, MULTI_TURN_TEST_CASES
except ImportError:
    print_colored("Error: Could not import test cases. Using minimal set.", Colors.RED)
    # Minimal test cases for Pattern 2 verification
    SINGLE_TURN_TEST_CASES = [
        {
            "id": 1,
            "name": "Basic Identity Query",
            "query": "你是谁？",
            "expected_keywords": ["诺亚新舟", "小诺", "健康医疗助理"],
            "category": "Identity"
        },
        {
            "id": 2,
            "name": "Product Search",
            "query": "我需要维生素C",
            "expected_keywords": ["维生素C", "产品", "推荐"],
            "category": "Product"
        }
    ]
    MULTI_TURN_TEST_CASES = []

async def test_pattern2_response_api(session, test_case, previous_response_id=None):
    """Test Response API endpoint with Pattern 2 logging"""
    try:
        # Prepare request data
        request_data = {
            "model": "gpt-4-turbo",
            "input": test_case['query'],
            "user_id": test_case.get('user_id', f"test_user_{test_case.get('id', 0)}"),
            "metadata": {
                "test_id": test_case.get('id'),
                "test_name": test_case.get('name', 'Unknown'),
                "orchestrator": "pattern2"
            }
        }
        
        if previous_response_id:
            request_data['previous_response_id'] = previous_response_id
        
        logger.info(f"Testing Pattern 2 - Test #{test_case.get('id')}: {test_case.get('name')}")
        logger.info(f"Query: {test_case['query']}")
        
        # Choose streaming or non-streaming randomly to test both
        test_id = test_case.get('id', 0)
        # Handle string IDs (like "41_turn_1") by extracting first number
        if isinstance(test_id, str):
            test_id = int(test_id.split('_')[0]) if '_' in test_id else 0
        use_streaming = test_id % 2 == 0
        endpoint = "/v2/humansa/responses/stream" if use_streaming else "/v2/humansa/responses/create"
        
        start_time = time.time()
        
        if use_streaming:
            # Test streaming endpoint
            logger.info("Using streaming endpoint")
            full_response = ""
            tools_used = []
            reasoning_chain = []
            emergency_flags = []
            follow_up_actions = []
            new_response_id = None
            
            async with session.post(f"{BASE_URL}{endpoint}", json=request_data) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    logger.error(f"API Error: {resp.status} - {error_text}")
                    return {
                        "success": False,
                        "error": f"API returned {resp.status}: {error_text}",
                        "response_time": 0
                    }
                
                # Process streaming response
                async for line in resp.content:
                    line = line.decode('utf-8').strip()
                    if line.startswith('data: '):
                        data_str = line[6:]
                        if data_str == '[DONE]':
                            break
                        
                        try:
                            event = json.loads(data_str)
                            
                            # Log different event types
                            if event.get('type') == 'response.created':
                                logger.info("Pattern 2 Response Created")
                                response_info = event.get('response', {})
                                logger.debug(f"Response ID: {response_info.get('id')}")
                            
                            elif event.get('type') == 'response.output_item.added':
                                item = event.get('item', {})
                                content = item.get('content', [])
                                for c in content:
                                    if c.get('type') == 'output_text':
                                        text = c.get('text', '')
                                        full_response += text
                                        logger.debug(f"Output text: {text[:100]}...")
                            
                            elif event.get('type') == 'response.reasoning':
                                reasoning = event.get('reasoning', [])
                                reasoning_chain.extend(reasoning)
                                logger.info(f"🧠 Reasoning Chain: {reasoning}")
                            
                            elif event.get('type') == 'response.usage':
                                usage = event.get('usage', {})
                                agents = usage.get('agents_used', [])
                                tools_used.extend(agents)
                                emergency_flags = usage.get('emergency_flags', [])
                                follow_up_actions = usage.get('follow_up_actions', [])
                                
                                logger.info(f"📊 Usage - Agents: {agents}")
                                if emergency_flags:
                                    logger.warning(f"🚨 Emergency Flags: {emergency_flags}")
                                if follow_up_actions:
                                    logger.info(f"📋 Follow-up Actions: {follow_up_actions}")
                            
                            elif event.get('type') == 'response.completed':
                                logger.info("Pattern 2 Response Completed")
                            
                            elif event.get('event') == 'response.metadata':
                                metadata = event.get('data', {})
                                new_response_id = metadata.get('response_id')
                                logger.debug(f"Response ID: {new_response_id}")
                                
                        except json.JSONDecodeError as e:
                            logger.error(f"JSON decode error: {e} - Line: {line}")
            
            elapsed_time = time.time() - start_time
            
            # Log final state
            logger.info(f"✅ Response completed in {elapsed_time:.2f}s")
            logger.info(f"Tools used: {tools_used}")
            logger.info(f"Response length: {len(full_response)} chars")
            
            return {
                "success": True,
                "response": full_response,
                "response_id": new_response_id,
                "response_time": elapsed_time,
                "tools_used": tools_used,
                "reasoning_chain": reasoning_chain,
                "emergency_flags": emergency_flags,
                "follow_up_actions": follow_up_actions
            }
            
        else:
            # Test non-streaming endpoint
            logger.info("Using non-streaming endpoint")
            
            async with session.post(f"{BASE_URL}{endpoint}", json=request_data) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    logger.error(f"API Error: {resp.status} - {error_text}")
                    return {
                        "success": False,
                        "error": f"API returned {resp.status}: {error_text}",
                        "response_time": 0
                    }
                
                data = await resp.json()
                elapsed_time = time.time() - start_time
                
                # Extract response details
                output = data.get('output', [])
                full_response = ""
                tools_used = []
                
                for item in output:
                    if item.get('type') == 'text':
                        full_response += item.get('text', '')
                    elif item.get('type') == 'tool_use':
                        tool_info = item.get('tool_use', {})
                        tool_name = tool_info.get('name', '')
                        if tool_name:
                            tools_used.append(tool_name)
                            logger.info(f"🔧 Tool used: {tool_name}")
                
                # Log usage info
                usage = data.get('usage', {})
                if usage:
                    logger.info(f"📊 Usage: {usage}")
                
                # Log metadata
                metadata = data.get('metadata', {})
                orchestrator = metadata.get('orchestrator', 'unknown')
                logger.info(f"Orchestrator: {orchestrator}")
                
                return {
                    "success": True,
                    "response": full_response,
                    "response_id": data.get('id'),
                    "response_time": elapsed_time,
                    "tools_used": tools_used
                }
            
    except Exception as e:
        logger.error(f"Exception during test: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "response_time": 0
        }

async def run_pattern2_tests():
    """Run all 70 test cases with Pattern 2"""
    print_section("HUMANSA V2 Pattern 2 Test Suite - 70 Test Cases")
    logger.info("="*80)
    logger.info("Starting Pattern 2 Test Suite")
    logger.info(f"Test environment: {BASE_URL}")
    logger.info(f"Expected orchestrator: Pattern 2 (FunctionAgent)")
    logger.info("="*80)
    
    # Check if Pattern 2 is enabled
    pattern2_enabled = os.getenv('HUMANSA_USE_PATTERN2', 'false').lower() == 'true'
    if not pattern2_enabled:
        print_colored("\n⚠️  WARNING: HUMANSA_USE_PATTERN2 is not set to true!", Colors.YELLOW)
        print_colored("Pattern 2 orchestrator may not be active.", Colors.YELLOW)
        print_colored("Set: export HUMANSA_USE_PATTERN2=true", Colors.YELLOW)
        logger.warning("Pattern 2 may not be enabled - HUMANSA_USE_PATTERN2 not set")
    
    async with aiohttp.ClientSession() as session:
        # Check health
        try:
            async with session.get(f"{BASE_URL}/v2/humansa/health") as resp:
                if resp.status == 200:
                    print_colored(f"\n✅ V2 Health Check Passed", Colors.GREEN)
                    logger.info("Health check passed")
                else:
                    print_colored(f"❌ V2 Health Check Failed: {resp.status}", Colors.RED)
                    logger.error(f"Health check failed: {resp.status}")
                    return
        except Exception as e:
            print_colored(f"❌ Cannot connect to server: {e}", Colors.RED)
            logger.error(f"Cannot connect to server: {e}")
            return
        
        all_results = []
        
        # Run single-turn tests (1-40)
        print_section("Running Single-Turn Tests (1-40)")
        logger.info("\n" + "="*60)
        logger.info("SINGLE-TURN TESTS")
        logger.info("="*60)
        
        single_turn_passed = 0
        
        for test_case in SINGLE_TURN_TEST_CASES:
            print_colored(f"\n🔹 Test #{test_case['id']}: {test_case['name']}", Colors.CYAN)
            print(f"   Category: {test_case.get('category', 'General')}")
            print(f"   Query: {test_case['query']}")
            
            result = await test_pattern2_response_api(session, test_case)
            
            if result['success']:
                response = result['response']
                print_colored(f"   Response: {response[:150]}...", Colors.GREEN)
                
                # Check keywords
                found_keywords = []
                missing_keywords = []
                for keyword in test_case.get('expected_keywords', []):
                    if keyword.lower() in response.lower():
                        found_keywords.append(keyword)
                    else:
                        missing_keywords.append(keyword)
                
                passed = len(missing_keywords) == 0
                
                if passed:
                    print_colored(f"   ✅ PASSED ({result['response_time']:.2f}s)", Colors.GREEN)
                    single_turn_passed += 1
                else:
                    print_colored(f"   ❌ FAILED - Missing: {missing_keywords}", Colors.RED)
                    logger.warning(f"Test {test_case['id']} failed - missing keywords: {missing_keywords}")
                
                if result.get('tools_used'):
                    print(f"   🔧 Tools: {', '.join(result['tools_used'])}")
                
                if result.get('reasoning_chain'):
                    print(f"   🧠 Reasoning steps: {len(result['reasoning_chain'])}")
                    for step in result['reasoning_chain']:
                        logger.debug(f"      - {step}")
                
                all_results.append({
                    "test_id": test_case['id'],
                    "test_name": test_case['name'],
                    "passed": passed,
                    "response_time": result['response_time'],
                    "tools_used": result.get('tools_used', []),
                    "reasoning_steps": len(result.get('reasoning_chain', []))
                })
            else:
                print_colored(f"   ❌ ERROR: {result['error']}", Colors.RED)
                logger.error(f"Test {test_case['id']} error: {result['error']}")
                all_results.append({
                    "test_id": test_case['id'],
                    "test_name": test_case['name'],
                    "passed": False,
                    "error": result['error']
                })
            
            await asyncio.sleep(0.5)  # Small delay between tests
        
        # Run multi-turn tests if available
        if MULTI_TURN_TEST_CASES:
            print_section("Running Multi-Turn Tests (41-70)")
            logger.info("\n" + "="*60)
            logger.info("MULTI-TURN TESTS")
            logger.info("="*60)
            
            multi_turn_passed = 0
            
            for test_case in MULTI_TURN_TEST_CASES[:30]:  # Limit to 30 to make 70 total
                print_colored(f"\n🔸 Test #{test_case['id']}: {test_case['name']}", Colors.MAGENTA)
                
                response_id = None
                all_turns_passed = True
                
                for i, turn in enumerate(test_case['turns'], 1):
                    print(f"\n   Turn {i}: {turn['query']}")
                    
                    turn_test = {
                        "id": f"{test_case['id']}_turn_{i}",
                        "name": f"{test_case['name']} - Turn {i}",
                        "query": turn['query'],
                        "user_id": f"mt_test_{test_case['id']}"
                    }
                    
                    result = await test_pattern2_response_api(session, turn_test, response_id)
                    
                    if result['success']:
                        response = result['response']
                        response_id = result.get('response_id')
                        print_colored(f"   Response: {response[:150]}...", Colors.GREEN)
                        
                        # Check expected keywords for this turn
                        found = all(kw.lower() in response.lower() for kw in turn.get('expected', []))
                        
                        if found:
                            print_colored(f"   ✓ Turn {i} passed", Colors.GREEN)
                        else:
                            print_colored(f"   ✗ Turn {i} failed", Colors.RED)
                            all_turns_passed = False
                            logger.warning(f"Test {test_case['id']} turn {i} failed")
                        
                        if result.get('tools_used'):
                            print(f"   🔧 Tools: {', '.join(result['tools_used'])}")
                    else:
                        print_colored(f"   ✗ Turn {i} error: {result['error']}", Colors.RED)
                        all_turns_passed = False
                    
                    await asyncio.sleep(0.5)
                
                if all_turns_passed:
                    print_colored(f"\n   ✅ Test #{test_case['id']} PASSED", Colors.GREEN)
                    multi_turn_passed += 1
                else:
                    print_colored(f"\n   ❌ Test #{test_case['id']} FAILED", Colors.RED)
                
                all_results.append({
                    "test_id": test_case['id'],
                    "test_name": test_case['name'],
                    "passed": all_turns_passed,
                    "type": "multi-turn"
                })
        
        # Print summary
        print_section("Test Summary")
        
        total_tests = len(SINGLE_TURN_TEST_CASES) + len(MULTI_TURN_TEST_CASES[:30])
        total_passed = single_turn_passed + (multi_turn_passed if MULTI_TURN_TEST_CASES else 0)
        
        print(f"\nTotal Tests: {total_tests}")
        print(f"Single-turn: {single_turn_passed}/{len(SINGLE_TURN_TEST_CASES)} passed")
        if MULTI_TURN_TEST_CASES:
            print(f"Multi-turn: {multi_turn_passed}/{len(MULTI_TURN_TEST_CASES[:30])} passed")
        
        pass_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
        
        if pass_rate >= 90:
            print_colored(f"\n✅ Overall: {total_passed}/{total_tests} ({pass_rate:.1f}%) - EXCELLENT", Colors.GREEN)
        elif pass_rate >= 70:
            print_colored(f"\n⚠️  Overall: {total_passed}/{total_tests} ({pass_rate:.1f}%) - GOOD", Colors.YELLOW)
        else:
            print_colored(f"\n❌ Overall: {total_passed}/{total_tests} ({pass_rate:.1f}%) - NEEDS IMPROVEMENT", Colors.RED)
        
        # Log final summary
        logger.info("\n" + "="*60)
        logger.info("FINAL SUMMARY")
        logger.info("="*60)
        logger.info(f"Total tests run: {total_tests}")
        logger.info(f"Tests passed: {total_passed}")
        logger.info(f"Pass rate: {pass_rate:.1f}%")
        logger.info(f"Log file: pattern2_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        
        # Analyze tool usage
        tool_usage = {}
        reasoning_counts = []
        
        for result in all_results:
            if 'tools_used' in result:
                for tool in result['tools_used']:
                    tool_usage[tool] = tool_usage.get(tool, 0) + 1
            
            if 'reasoning_steps' in result:
                reasoning_counts.append(result['reasoning_steps'])
        
        if tool_usage:
            print("\n📊 Tool Usage Statistics:")
            for tool, count in sorted(tool_usage.items(), key=lambda x: x[1], reverse=True):
                print(f"   - {tool}: {count} times")
        
        if reasoning_counts:
            avg_reasoning = sum(reasoning_counts) / len(reasoning_counts)
            print(f"\n🧠 Average reasoning steps: {avg_reasoning:.1f}")
        
        print_colored("\n✅ Pattern 2 test suite completed!", Colors.GREEN)
        print_colored(f"Check the log file for detailed execution logs.", Colors.CYAN)

if __name__ == "__main__":
    # Ensure Pattern 2 is enabled
    if os.getenv('HUMANSA_USE_PATTERN2', '').lower() != 'true':
        print_colored("\n⚠️  Setting HUMANSA_USE_PATTERN2=true for this test", Colors.YELLOW)
        os.environ['HUMANSA_USE_PATTERN2'] = 'true'
    
    asyncio.run(run_pattern2_tests())