#!/usr/bin/env python3
"""
Test a subset of agent tests
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from tests.test_agents_real_environment import MultiAgentTester

async def test_subset():
    tester = MultiAgentTester()
    
    print("Testing subset of agent tests...\n")
    
    # Test 1: RAG Agent
    result1 = await tester.run_test_case(
        "RAG_Test",
        "What notes do I have about reinforcement learning?",
        ["router", "rag", "response"],
        stream=True
    )
    
    # Test 2: Web Search
    result2 = await tester.run_test_case(
        "WebSearch_Test", 
        "What are the latest AI news today?",
        ["router", "web_search", "response"],
        stream=True
    )
    
    # Test 3: Code Interpreter
    result3 = await tester.run_test_case(
        "Code_Test",
        "Write Python code to calculate 2+2",
        ["router", "response"],  # Code interpreter might not trigger for simple request
        stream=True
    )
    
    await tester.client.aclose()
    
    # Summary
    print("\n\n=== TEST SUMMARY ===")
    for result in [result1, result2, result3]:
        print(f"{result.test_name}: {result.status}")
        print(f"  Agents: {result.actual_agents}")
        if result.error:
            print(f"  Error: {result.error}")

if __name__ == "__main__":
    asyncio.run(test_subset())