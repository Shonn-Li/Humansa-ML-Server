#!/usr/bin/env python3
"""
Verify that RAG is disabled when attachments are present
"""

import asyncio
import httpx
import json

async def test_rag_disabled():
    """Test that RAG is not used when attachments are present"""
    
    client = httpx.AsyncClient(timeout=30.0)
    
    request_data = {
        "messages": [{"role": "user", "content": "Tell me about this paper"}],
        "attachments": ["https://arxiv.org/pdf/2505.18499.pdf"],
        "user_id": 10001,
        "model": "gpt-4o-mini",
        "stream": False
    }
    
    print("Testing RAG disabled with attachments...")
    print("-" * 60)
    
    try:
        # Add a debug header to trace execution
        response = await client.post(
            "http://localhost:5002/v1/multi-agent/response",
            json=request_data,
            headers={"X-Debug": "true"}
        )
        
        result = response.json()
        
        if 'metadata' in result:
            agents = result['metadata'].get('agent_results', {})
            print("\nAgents executed:")
            for agent in agents:
                print(f"  - {agent}")
                
            if 'rag_agent' in agents:
                print("\n❌ ERROR: RAG agent was executed when it should be disabled!")
                
                # Check what the router decided
                print("\nDebugging info:")
                print(f"Workflow time: {result['metadata'].get('workflow_time')}")
                
                # Get response content to see if PARL is mentioned
                content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
                if 'parl' in content.lower():
                    print("❌ PARL mentioned in response - knowledge base was used!")
                else:
                    print("✅ No PARL mention - might be using correct attachment content")
                    
            else:
                print("\n✅ SUCCESS: RAG agent was NOT executed")
                
                # Verify attachment agent was used
                if 'attachment_agent' in agents:
                    print("✅ Attachment agent was executed")
                else:
                    print("❌ ERROR: Attachment agent was NOT executed!")
                    
        else:
            print("No metadata in response")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        
    await client.aclose()
    
    print("\n" + "="*60)
    print("IMPORTANT: If RAG is still being used, the ML server might need to be restarted")
    print("to pick up the code changes. Run: supervisorctl restart ml_server")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(test_rag_disabled())