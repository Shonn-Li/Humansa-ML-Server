#!/usr/bin/env python3
"""
Test Azure OpenAI with ReActAgent to debug the blocks issue
"""

import os
import asyncio
from llama_index.llms.azure_openai import AzureOpenAI
from llama_index.core.agent import ReActAgent
from llama_index.core.tools import FunctionTool

# Set up logging
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def simple_tool(query: str) -> str:
    """A simple test tool"""
    return f"Tool response for: {query}"


async def test_azure_react():
    """Test Azure OpenAI with ReActAgent"""
    
    # Initialize Azure OpenAI
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "https://youwoai-dev-resource.openai.azure.com/")
    azure_api_key = os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("AZURE_INFERENCE_CREDENTIAL")
    
    if not azure_api_key:
        raise ValueError("AZURE_OPENAI_API_KEY or AZURE_INFERENCE_CREDENTIAL must be set")
    
    print(f"Using Azure endpoint: {azure_endpoint}")
    
    # Create LLM
    llm = AzureOpenAI(
        model="gpt-4.1",
        deployment_name="gpt-4.1",
        api_key=azure_api_key,
        azure_endpoint=azure_endpoint,
        api_version="2024-02-01",
        temperature=0.7
    )
    
    # Create a simple tool
    tool = FunctionTool.from_defaults(
        fn=simple_tool,
        name="test_tool",
        description="A test tool"
    )
    
    # Create ReActAgent
    try:
        print("\nCreating ReActAgent...")
        agent = ReActAgent.from_tools(
            tools=[tool],
            llm=llm,
            verbose=True
        )
        print("✅ ReActAgent created successfully")
    except Exception as e:
        print(f"❌ Error creating ReActAgent: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Test chat
    try:
        print("\nTesting chat...")
        response = agent.chat("Hello, please use the test_tool to process 'test query'")
        print(f"Response: {response}")
    except Exception as e:
        print(f"❌ Error in chat: {e}")
        import traceback
        traceback.print_exc()
        
        # Check if it's the blocks error
        if "'dict' object has no attribute 'blocks'" in str(e):
            print("\n⚠️  This is the 'blocks' error we're trying to fix!")
            print("The issue is likely in the Azure OpenAI message formatting")


if __name__ == "__main__":
    asyncio.run(test_azure_react())