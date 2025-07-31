#!/usr/bin/env python3
"""
Simple test for sub-agent architecture without import complications
"""

import asyncio
import os
import logging
import sys

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_product_agent():
    """Test the Product Agent directly"""
    
    print("\n=== Testing Product Agent ===")
    
    # Import required modules
    from llama_index.llms.azure_openai import AzureOpenAI
    from humansa.v2.agents.product_agent import ProductAgent
    
    # Initialize LLM
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "https://youwoai-dev-resource.openai.azure.com/")
    azure_api_key = os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("AZURE_INFERENCE_CREDENTIAL")
    
    if not azure_api_key:
        print("❌ Azure OpenAI API key not found")
        return False
    
    llm = AzureOpenAI(
        model="gpt-4.1",
        deployment_name="gpt-4.1",
        api_key=azure_api_key,
        azure_endpoint=azure_endpoint,
        api_version="2024-02-15-preview",
        temperature=0.7
    )
    
    # Create Product Agent
    product_agent = ProductAgent(llm=llm)
    
    # Test queries
    test_queries = [
        "我想买一些维生素C，有什么推荐吗？",
        "有什么提高免疫力的保健品？",
        "血压计哪个牌子好？"
    ]
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        print("Response: ", end='', flush=True)
        
        # Process query
        async for chunk in product_agent.process_query(query, {}, stream=False):
            if chunk.get('type') == 'content':
                print(chunk.get('chunk', ''), end='')
        
        print("\n" + "-"*50)
    
    print("\n✅ Product Agent test completed!")
    return True


async def test_agent_wrapper():
    """Test the agent-to-tool wrapper"""
    
    print("\n=== Testing Agent Tool Wrapper ===")
    
    try:
        from llama_index.llms.azure_openai import AzureOpenAI
        from humansa.v2.agent_tool_wrapper import create_agent_tool
        from humansa.v2.agents.product_agent import ProductAgent
        
        # Initialize LLM
        azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "https://youwoai-dev-resource.openai.azure.com/")
        azure_api_key = os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("AZURE_INFERENCE_CREDENTIAL")
        
        llm = AzureOpenAI(
            model="gpt-4.1",
            deployment_name="gpt-4.1",
            api_key=azure_api_key,
            azure_endpoint=azure_endpoint,
            api_version="2024-02-15-preview",
            temperature=0.7
        )
        
        # Create agent and tool
        product_agent = ProductAgent(llm=llm)
        product_tool = create_agent_tool(
            agent=product_agent,
            name="product_recommendation",
            description="产品推荐助手"
        )
        
        print(f"Tool Name: {product_tool.metadata.name}")
        print(f"Tool Description: {product_tool.metadata.description}")
        
        # Test tool invocation
        result = await product_tool.afn(query="推荐一些维生素")
        print(f"\nTool Result:\n{result}")
        
        print("\n✅ Agent wrapper test completed!")
        return True
        
    except Exception as e:
        logger.error(f"Agent wrapper test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_simple_orchestration():
    """Test simple orchestration with ReAct agent"""
    
    print("\n=== Testing Simple Orchestration ===")
    
    try:
        from llama_index.llms.azure_openai import AzureOpenAI
        from llama_index.core.agent import ReActAgent
        from humansa.v2.agent_tool_wrapper import create_agent_tool
        from humansa.v2.agents.product_agent import ProductAgent
        from humansa.v2.agents.appointment_agent import AppointmentAgent
        
        # Initialize LLM
        azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "https://youwoai-dev-resource.openai.azure.com/")
        azure_api_key = os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("AZURE_INFERENCE_CREDENTIAL")
        
        llm = AzureOpenAI(
            model="gpt-4.1",
            deployment_name="gpt-4.1",
            api_key=azure_api_key,
            azure_endpoint=azure_endpoint,
            api_version="2024-02-15-preview",
            temperature=0.7
        )
        
        # Create agents
        product_agent = ProductAgent(llm=llm)
        appointment_agent = AppointmentAgent(llm=llm)
        
        # Create tools
        tools = [
            create_agent_tool(
                agent=product_agent,
                name="product_recommendation_agent",
                description="处理产品推荐和保健品查询"
            ),
            create_agent_tool(
                agent=appointment_agent,
                name="appointment_booking_agent",
                description="处理预约挂号和医生排班查询"
            )
        ]
        
        # Create orchestrator
        orchestrator = ReActAgent.from_tools(
            tools=tools,
            llm=llm,
            verbose=True,
            system_prompt="你是诺亚新舟健康助理的主协调器。根据用户问题选择合适的专业助手来处理。"
        )
        
        # Test queries
        test_cases = [
            "我想买些维生素C",
            "帮我预约一个心内科医生"
        ]
        
        for query in test_cases:
            print(f"\nQuery: {query}")
            response = await orchestrator.achat(query)
            print(f"Response: {response.response}")
            print("-"*50)
        
        print("\n✅ Orchestration test completed!")
        return True
        
    except Exception as e:
        logger.error(f"Orchestration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests"""
    
    print("Starting Sub-Agent Architecture Tests...")
    
    # Test 1: Direct agent test
    await test_product_agent()
    
    # Test 2: Agent wrapper test
    await test_agent_wrapper()
    
    # Test 3: Simple orchestration
    await test_simple_orchestration()
    
    print("\nAll tests completed!")


if __name__ == "__main__":
    asyncio.run(main())