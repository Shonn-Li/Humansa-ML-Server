#!/usr/bin/env python
"""Test the orchestrator directly to debug routing"""

import asyncio
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from llama_index.llms.azure_openai import AzureOpenAI
from humansa.v2.orchestrator_agent_subagent import SubAgentOrchestrator

async def test_orchestrator_routing():
    """Test orchestrator routing directly"""
    
    print("🔍 Testing Orchestrator routing...")
    
    # Set up LLM (same as in the main system)
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "https://youwoai-dev-resource.openai.azure.com/")
    azure_api_key = os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("AZURE_INFERENCE_CREDENTIAL")
    
    if not azure_api_key:
        print("❌ No Azure API key found")
        return
    
    llm = AzureOpenAI(
        model="gpt-4.1",
        deployment_name="gpt-4.1",
        api_key=azure_api_key,
        azure_endpoint=azure_endpoint,
        api_version="2024-02-15-preview",
        temperature=0.7,
        max_tokens=4096
    )
    
    # Create database config
    db_config = {
        'host': 'localhost',
        'port': 5454,
        'user': 'postgres',
        'password': '12931',
        'database': 'test4'
    }
    
    # Create orchestrator
    orchestrator = SubAgentOrchestrator(
        llm=llm,
        memory_manager=None,
        debug=True,  # Enable verbose debugging
        db_config=db_config
    )
    
    # Test query
    query = "我想预约心内科医生"
    user_id = "debug_orchestrator"
    
    print(f"📝 Query: {query}")
    print("=" * 60)
    
    try:
        print("🤖 Calling orchestrator (non-streaming)...")
        
        result_chunks = []
        async for chunk in orchestrator.process_query(
            query=query,
            user_id=user_id,
            messages=[],
            stream=False
        ):
            print(f"📦 Chunk type: {chunk.get('type')}")
            print(f"📦 Chunk content: {chunk}")
            if chunk.get('type') == 'content':
                result_chunks.append(chunk.get('chunk', ''))
        
        final_response = ''.join(result_chunks) if result_chunks else "No response"
        print(f"\n💬 Final Response: {final_response}")
        
        # Check if it contains real appointment data or agent routing
        if any(keyword in final_response for keyword in ["孙浩", "广州中山医院", "120元", "09:00"]):
            print("✅ SUCCESS: Response contains real appointment data!")
        elif "appointment_booking_agent" in str(result_chunks) or "search_slots" in final_response:
            print("✅ PARTIAL: Orchestrator mentioned appointment agent or search")
        else:
            print("❌ FAILED: No real appointment data or agent routing")
            
    except Exception as e:
        print(f"❌ Error testing orchestrator: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_orchestrator_routing())