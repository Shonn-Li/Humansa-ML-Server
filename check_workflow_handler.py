#!/usr/bin/env python3
"""Check how to use WorkflowHandler in new llama-index"""

import asyncio
from llama_index.core.agent import ReActAgent
from llama_index.core.tools import FunctionTool
from llama_index.llms.openai import OpenAI
import os

def simple_tool(query: str) -> str:
    """A simple test tool"""
    return f"Tool response for: {query}"

async def test_workflow():
    """Test the new workflow API"""
    
    # Create a simple LLM
    llm = OpenAI(api_key=os.getenv("OPENAI_API_KEY", "dummy-key"))
    
    # Create tool
    tool = FunctionTool.from_defaults(
        fn=simple_tool,
        name="test_tool",
        description="A test tool"
    )
    
    # Create agent
    agent = ReActAgent(
        name="TestAgent",
        tools=[tool],
        llm=llm,
        verbose=True
    )
    
    # Run the agent
    print("Running agent...")
    handler = agent.run("Use the test_tool with query 'hello'")
    print(f"Handler type: {type(handler)}")
    print(f"Handler methods: {[m for m in dir(handler) if not m.startswith('_')]}")
    
    # Try to get result
    try:
        # Wait for result
        result = await handler
        print(f"Result: {result}")
        
        # Check if result has specific attributes
        if hasattr(result, 'response'):
            print(f"Response: {result.response}")
        if hasattr(result, 'output'):
            print(f"Output: {result.output}")
            
    except Exception as e:
        print(f"Error getting result: {e}")
        
    # Try streaming
    print("\n\nTrying stream_events...")
    handler2 = agent.run("Tell me about tools")
    try:
        async for event in handler2.stream_events():
            print(f"Event: {event}")
    except Exception as e:
        print(f"Error streaming: {e}")

if __name__ == "__main__":
    asyncio.run(test_workflow())