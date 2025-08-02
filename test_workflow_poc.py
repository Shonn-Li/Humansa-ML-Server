#!/usr/bin/env python
"""
Proof of Concept: LlamaIndex Workflow Streaming
Demonstrates how FunctionAgent and AgentWorkflow stream reasoning
"""

import asyncio
import os
from llama_index.core.agent.workflow import (
    FunctionAgent,
    AgentWorkflow,
    AgentInput,
    AgentOutput,
    AgentStream,
    ToolCall,
    ToolCallResult
)
from llama_index.core.workflow import Context
from llama_index.core.tools import FunctionTool
from llama_index.llms.openai import OpenAI


# Simple tools for demonstration
def search_products(query: str) -> str:
    """Search for products in the catalog"""
    return f"Found 5 vitamin C products: 1) 诺亚维C片 ¥89, 2) 天然VC胶囊 ¥129..."


def check_inventory(product_id: str) -> str:
    """Check product inventory"""
    return f"Product {product_id} has 50 units in stock"


async def demonstrate_streaming():
    """Demonstrate workflow streaming with reasoning visibility"""
    
    print("🧪 LlamaIndex Workflow Streaming POC")
    print("=" * 60)
    
    # Create LLM
    llm = OpenAI(
        model="gpt-4",
        temperature=0.7,
        api_key=os.getenv("OPENAI_API_KEY", "sk-dummy")
    )
    
    # Create tools
    tools = [
        FunctionTool.from_defaults(search_products),
        FunctionTool.from_defaults(check_inventory)
    ]
    
    # Create a simple product agent
    product_agent = FunctionAgent(
        name="ProductAgent",
        description="Searches and recommends products",
        system_prompt="You are a product recommendation expert. Search for products and check inventory.",
        tools=tools,
        llm=llm
    )
    
    # Create workflow with the agent
    workflow = AgentWorkflow(agents=[product_agent])
    
    # Test query
    query = "I need vitamin C supplements"
    print(f"📝 Query: {query}\n")
    
    # Create context
    ctx = Context(workflow)
    
    # Run and stream events
    handler = workflow.run(user_msg=query, ctx=ctx)
    
    print("🔄 Streaming Events:")
    print("-" * 60)
    
    event_log = []
    
    async for event in handler.stream_events():
        event_type = type(event).__name__
        event_log.append(event_type)
        
        if isinstance(event, AgentInput):
            # AgentInput event structure may vary
            print(f"\n✅ Agent Starting")
            print(f"   Event data: {event.__dict__ if hasattr(event, '__dict__') else event}")
            
        elif isinstance(event, AgentStream):
            # This is the key - agent's thinking process!
            print(f"💭 {event.delta}", end="", flush=True)
            
        elif isinstance(event, ToolCall):
            tool_name = getattr(event, 'tool_name', 'Unknown')
            args = getattr(event, 'arguments', {})
            print(f"\n🔧 Calling Tool: {tool_name}")
            print(f"   Args: {args}")
            
        elif isinstance(event, ToolCallResult):
            result = getattr(event, 'result', 'No result')
            result_preview = str(result)[:100]
            print(f"   ✅ Result: {result_preview}...")
            
        elif isinstance(event, AgentOutput):
            response = getattr(event, 'response', 'No response')
            print(f"\n\n📤 Final Response:")
            print(f"{response}")
    
    # Show event summary
    print("\n\n" + "=" * 60)
    print("📊 Event Summary:")
    event_counts = {}
    for event in event_log:
        event_counts[event] = event_counts.get(event, 0) + 1
    
    for event_type, count in event_counts.items():
        print(f"   - {event_type}: {count}")
    
    print("\n✅ Key Insight: AgentStream events contain the agent's reasoning!")


async def compare_with_react():
    """Compare with current ReActAgent approach"""
    
    print("\n\n🔍 Comparing with ReActAgent")
    print("=" * 60)
    
    from llama_index.core.agent import ReActAgent
    
    # Create ReActAgent (current approach)
    tools = [
        FunctionTool.from_defaults(search_products),
        FunctionTool.from_defaults(check_inventory)
    ]
    
    llm = OpenAI(model="gpt-4", api_key=os.getenv("OPENAI_API_KEY", "sk-dummy"))
    
    react_agent = ReActAgent.from_tools(
        tools=tools,
        llm=llm,
        verbose=True  # This only prints to stdout!
    )
    
    print("❌ ReActAgent.astream_chat only streams final response:")
    
    query = "I need vitamin C supplements"
    response_stream = await react_agent.astream_chat(query)
    
    async for chunk in response_stream.async_response_gen():
        print(f"Chunk: {chunk}", end="", flush=True)
    
    print("\n\n⚠️  No access to reasoning steps in the stream!")


if __name__ == "__main__":
    print("🚀 Starting Workflow Streaming POC\n")
    
    # Run demonstration
    asyncio.run(demonstrate_streaming())
    asyncio.run(compare_with_react())
    
    print("\n\n📌 Conclusion:")
    print("- AgentWorkflow + FunctionAgent = Full reasoning visibility")
    print("- ReActAgent = Only final response in stream")
    print("- We need to migrate to get reasoning events!")