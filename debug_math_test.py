#!/usr/bin/env python3
"""Debug the math calculation test failure"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from chat.agent.code_interpreter_agent import CodeInterpreterAgent, PythonCodeExecutor

async def test_math_calculation():
    agent = CodeInterpreterAgent()
    
    # Test message from test_individual_agents.py
    test_message = "import math\nprint(math.sqrt(144))"
    
    print(f"Test message: {test_message}")
    
    # Extract code
    code_blocks = agent.extract_code_from_message(test_message)
    print(f"Extracted code blocks: {code_blocks}")
    
    # Execute directly
    executor = PythonCodeExecutor()
    result = await executor.execute_code(test_message)
    
    print(f"Execution result: {result}")
    
    # Test via agent.run
    request = {
        "messages": [{"role": "user", "content": test_message}],
        "model": "gpt-4o-mini",
        "user_id": 123
    }
    context = {}
    
    agent_result = await agent.run(request, context)
    print(f"\nAgent result: {agent_result}")

if __name__ == "__main__":
    asyncio.run(test_math_calculation())