#!/usr/bin/env python3
"""
Simple non-streaming test to see router decisions
"""

import httpx
import asyncio
import json

async def test_routing():
    async with httpx.AsyncClient() as client:
        test_cases = [
            {
                "name": "Note query",
                "query": "What's in my PARL paper note?",
                "attachments": []
            },
            {
                "name": "Attachment query",
                "query": "Analyze this document",
                "attachments": ["https://arxiv.org/pdf/2505.18499.pdf"]
            },
            {
                "name": "Code query",
                "query": "Write python code to calculate 2+2",
                "attachments": []
            }
        ]
        
        for test in test_cases:
            print(f"\n{'='*60}")
            print(f"TEST: {test['name']}")
            print(f"QUERY: {test['query']}")
            if test['attachments']:
                print(f"ATTACHMENTS: {test['attachments']}")
            
            request_data = {
                "messages": [{"role": "user", "content": test['query']}],
                "user_id": 10001,
                "model": "gpt-4o-mini",
                "stream": False,  # Non-streaming for cleaner output
                "enable_citations": True,
                "attachments": test['attachments']
            }
            
            try:
                response = await client.post(
                    'http://localhost:5001/v1/multi-agent/response',
                    json=request_data
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Check metadata for agent information
                    metadata = data.get('metadata', {})
                    print(f"\nMETADATA: {json.dumps(metadata, indent=2)}")
                    
                    # Check if response was generated
                    if 'choices' in data and data['choices']:
                        content = data['choices'][0].get('message', {}).get('content', '')
                        print(f"\nRESPONSE LENGTH: {len(content)} chars")
                        print(f"RESPONSE PREVIEW: {content[:200]}...")
                    else:
                        print("\nNO RESPONSE GENERATED")
                else:
                    print(f"\nERROR: Status {response.status_code}")
                    print(response.text[:500])
                    
            except Exception as e:
                print(f"\nEXCEPTION: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_routing())