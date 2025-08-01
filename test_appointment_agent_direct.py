#!/usr/bin/env python
"""Test the appointment agent directly (bypassing orchestrator)"""

import asyncio
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from llama_index.llms.azure_openai import AzureOpenAI
from humansa.v2.agents.appointment_agent import AppointmentAgent

async def test_appointment_agent_direct():
    """Test appointment agent directly"""
    
    print("🔍 Testing AppointmentAgent directly...")
    
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
    
    # Create appointment agent
    agent = AppointmentAgent(llm=llm, verbose=True)
    
    # Test query
    query = "我想预约心内科医生"
    context = {}
    
    print(f"📝 Query: {query}")
    print("=" * 50)
    
    try:
        # Call agent directly (non-streaming first)
        print("🤖 Calling appointment agent directly (non-streaming)...")
        
        result_chunks = []
        async for chunk in agent.process_query(query, context, stream=False):
            print(f"📦 Chunk: {chunk}")
            if 'response' in chunk:
                result_chunks.append(chunk['response'])
        
        final_response = ''.join(result_chunks) if result_chunks else "No response"
        print(f"\n💬 Final Response: {final_response}")
        
        # Check if it contains real appointment data
        if any(keyword in final_response for keyword in ["孙浩", "广州中山医院", "120元", "09:00"]):
            print("✅ SUCCESS: Response contains real appointment data!")
        elif "search_slots" in final_response or "正在查询" in final_response:
            print("✅ PARTIAL: Agent mentioned searching")
        else:
            print("❌ FAILED: No real appointment data or search mention")
            
    except Exception as e:
        print(f"❌ Error testing appointment agent: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_appointment_agent_direct())