#!/usr/bin/env python3
"""Quick test to verify attachment priority works"""

import httpx
import asyncio
import json

async def test_attachment():
    async with httpx.AsyncClient() as client:
        # Test with attachment - should trigger attachment agent
        request = {
            "messages": [{"role": "user", "content": "What is this?"}],
            "user_id": 10001,
            "model": "gpt-4.1-nano",
            "stream": False,
            "attachments": ["https://arxiv.org/pdf/2505.18499.pdf"]
        }
        
        print("Testing attachment priority...")
        print(f"Query: {request['messages'][0]['content']}")
        print(f"Attachments: {request['attachments']}")
        
        response = await client.post(
            "http://localhost:5001/v1/multi-agent/response",
            json=request
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Check metadata for agents
            if 'metadata' in data:
                agent_results = data['metadata'].get('agent_results', {})
                agents = [k.replace('_agent', '') for k in agent_results.keys() if k.endswith('_agent')]
                
                print(f"\nAgents triggered: {agents}")
                print(f"Attachment agent: {'✅' if 'attachment' in agents else '❌'}")
                
                # Show response preview
                if 'choices' in data and data['choices']:
                    content = data['choices'][0]['message']['content'][:200]
                    print(f"\nResponse preview: {content}...")
            else:
                print("No metadata in response")
        else:
            print(f"Error: {response.status_code}")

if __name__ == "__main__":
    asyncio.run(test_attachment())