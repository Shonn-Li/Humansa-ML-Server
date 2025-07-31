#!/usr/bin/env python3
"""
Test the new sub-agent architecture implementation
"""

import asyncio
import sys
import os
import logging

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Suppress some verbose logs
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('openai').setLevel(logging.WARNING)


async def test_subagent_orchestrator():
    """Test the sub-agent orchestrator with various queries"""
    
    try:
        # Import required modules
        from llama_index.llms.azure_openai import AzureOpenAI
        
        # Import orchestrator directly to avoid circular imports
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "orchestrator_subagent",
            "src/humansa/v2/orchestrator_agent_subagent.py"
        )
        orchestrator_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(orchestrator_module)
        create_subagent_orchestrator = orchestrator_module.create_subagent_orchestrator
        
        # Initialize LLM
        azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "https://youwoai-dev-resource.openai.azure.com/")
        azure_api_key = os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("AZURE_INFERENCE_CREDENTIAL")
        
        if not azure_api_key:
            raise ValueError("AZURE_OPENAI_API_KEY or AZURE_INFERENCE_CREDENTIAL must be set")
        
        llm = AzureOpenAI(
            model="gpt-4.1",
            deployment_name="gpt-4.1",
            api_key=azure_api_key,
            azure_endpoint=azure_endpoint,
            api_version="2024-02-15-preview",
            temperature=0.7,
            max_tokens=4096
        )
        
        # Create orchestrator with sub-agents
        orchestrator = create_subagent_orchestrator(
            llm=llm,
            memory_manager=None,  # No memory for simple test
            debug=True  # Enable debug to see agent selection
        )
        
        print("\n=== HUMANSA V2 Sub-Agent Architecture Test ===\n")
        
        # Test cases
        test_cases = [
            {
                "name": "Product Recommendation",
                "query": "我想买一些维生素C，有什么推荐吗？",
                "expected_agent": "product_recommendation_agent"
            },
            {
                "name": "Appointment Booking",
                "query": "我想预约心内科医生，最近有什么时间？",
                "expected_agent": "appointment_booking_agent"
            },
            {
                "name": "Symptom Analysis",
                "query": "我最近总是头痛，还有点发烧，该怎么办？",
                "expected_agent": "clinical_analysis_agent"
            },
            {
                "name": "Emergency Detection",
                "query": "我胸口剧烈疼痛，呼吸困难，手臂发麻",
                "expected_agent": "clinical_analysis_agent"
            },
            {
                "name": "General Health Query",
                "query": "诺亚新舟的医疗保险都包括什么？",
                "expected_agent": "general_medical_agent"
            }
        ]
        
        # Run tests
        for i, test in enumerate(test_cases, 1):
            print(f"\n--- Test {i}: {test['name']} ---")
            print(f"Query: {test['query']}")
            print(f"Expected Agent: {test['expected_agent']}")
            print("\nResponse:")
            
            # Process query
            response_chunks = []
            async for chunk in orchestrator.process_query(
                query=test['query'],
                user_id="test_user",
                stream=False
            ):
                if 'choices' in chunk:
                    content = chunk['choices'][0]['message']['content']
                    response_chunks.append(content)
                    print(content)
                elif 'error' in chunk:
                    print(f"Error: {chunk['error']}")
            
            print("\n" + "="*50)
        
        print("\n✅ Sub-agent architecture test completed!")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


async def test_streaming():
    """Test streaming functionality"""
    
    try:
        from llama_index.llms.azure_openai import AzureOpenAI
        
        # Import orchestrator directly to avoid circular imports
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "orchestrator_subagent",
            "src/humansa/v2/orchestrator_agent_subagent.py"
        )
        orchestrator_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(orchestrator_module)
        create_subagent_orchestrator = orchestrator_module.create_subagent_orchestrator
        
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
        
        # Create orchestrator
        orchestrator = create_subagent_orchestrator(llm=llm, debug=False)
        
        print("\n=== Testing Streaming Response ===\n")
        print("Query: 推荐一些提高免疫力的保健品")
        print("\nStreaming response:")
        
        # Test streaming
        async for chunk in orchestrator.process_query(
            query="推荐一些提高免疫力的保健品",
            user_id="test_user",
            stream=True
        ):
            if 'choices' in chunk and chunk['choices'][0]['delta'].get('content'):
                print(chunk['choices'][0]['delta']['content'], end='', flush=True)
        
        print("\n\n✅ Streaming test completed!")
        
    except Exception as e:
        logger.error(f"Streaming test failed: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Run all tests"""
    
    print("Starting HUMANSA V2 Sub-Agent Architecture Tests...")
    
    # Test basic functionality
    success = await test_subagent_orchestrator()
    
    if success:
        # Test streaming
        await test_streaming()
    
    print("\nAll tests completed!")


if __name__ == "__main__":
    asyncio.run(main())