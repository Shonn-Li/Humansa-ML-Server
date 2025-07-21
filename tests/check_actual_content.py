#!/usr/bin/env python3
"""
Check what content is actually being returned for the graph reasoning paper
"""

import asyncio
import httpx
import json

async def check_content():
    """Check actual content returned for graph reasoning paper"""
    
    client = httpx.AsyncClient(timeout=30.0)
    
    # Test the graph reasoning paper that should NOT return PARL content
    request_data = {
        "messages": [{"role": "user", "content": "What is this paper about? Give me the main topic."}],
        "attachments": ["https://arxiv.org/pdf/2505.18499.pdf"],
        "user_id": 10001,
        "model": "gpt-4o-mini",
        "stream": False
    }
    
    print("="*80)
    print("CHECKING ACTUAL CONTENT FOR GRAPH REASONING PAPER")
    print("="*80)
    print("Expected: Content about 'graph reasoning' or 'teaching LLMs to reason on graphs'")
    print("NOT Expected: PARL or 'Predictable Reinforcement Learning'")
    print("-"*80)
    
    try:
        response = await client.post(
            "http://localhost:5002/v1/multi-agent/response",
            json=request_data
        )
        
        result = response.json()
        
        if 'choices' in result:
            content = result['choices'][0]['message']['content']
            
            print("\nRESPONSE CONTENT:")
            print("-"*80)
            print(content[:1000])  # First 1000 chars
            if len(content) > 1000:
                print("\n... [truncated] ...")
                
            print("\n" + "-"*80)
            
            # Check for keywords
            content_lower = content.lower()
            
            print("\nCONTENT ANALYSIS:")
            if 'graph' in content_lower and 'reasoning' in content_lower:
                print("✅ Contains 'graph' and 'reasoning' - CORRECT PAPER!")
            else:
                print("⚠️  Does not contain expected keywords")
                
            if 'parl' in content_lower or 'predictable reinforcement' in content_lower:
                print("❌ Contains PARL content - WRONG PAPER!")
            else:
                print("✅ Does not contain PARL - good sign")
                
            if 'colonel blotto' in content_lower:
                print("❌ Contains 'Colonel Blotto' - This is from knowledge base, not the PDF!")
            
            # Check metadata
            if 'metadata' in result:
                agents = list(result['metadata'].get('agent_results', {}).keys())
                print(f"\nAgents used: {', '.join(agents)}")
                
                # Check if both attachment and RAG were used
                if 'attachment_agent' in agents and 'rag_agent' in agents:
                    print("⚠️  WARNING: Both attachment AND RAG agents were used")
                    print("   This might cause content mixing!")
                    
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        
    await client.aclose()
    
    print("\n" + "="*80)

if __name__ == "__main__":
    asyncio.run(check_content())