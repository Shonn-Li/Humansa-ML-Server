#!/usr/bin/env python3
"""
Test attachment agent specifically
"""

import asyncio
import httpx
import json

TEST_ATTACHMENTS = {
    "pdfs": [
        "https://arxiv.org/pdf/2505.18499.pdf",  # G1 paper
        "https://arxiv.org/pdf/2311.18703.pdf",  # PARL paper
    ],
    "images": [
        "https://arxiv.org/html/2407.09124v1/x1.png",
        "https://www.scribbr.co.uk/wp-content/uploads/2023/08/the-general-framework-of-reinforcement-learning.webp"
    ]
}

async def test_attachment():
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Test 1: PDF attachment
        print("=== Testing PDF Attachment ===")
        request_data = {
            "messages": [{"role": "user", "content": "Summarize the key findings in this paper"}],
            "user_id": 10001,
            "model": "gpt-4o-mini",
            "stream": True,
            "attachments": [TEST_ATTACHMENTS["pdfs"][0]]
        }
        
        agents_found = []
        response_text = ""
        
        async with client.stream('POST', 'http://localhost:5001/v1/multi-agent/response', json=request_data) as response:
            async for line in response.aiter_lines():
                if line.startswith('data: '):
                    event_data = line[6:]
                    if event_data != '[DONE]':
                        try:
                            event = json.loads(event_data)
                            
                            # Check for attachment events
                            if 'attachment' in event.get('type', ''):
                                if 'attachment' not in agents_found:
                                    agents_found.append('attachment')
                                print(f"Attachment event: {event['type']}")
                            
                            # Check reasoning
                            if event.get('type') == 'response.reasoning_text.done':
                                text = event.get('text', '')
                                print(f"Reasoning: {text}")
                                if 'attachment' in text.lower():
                                    if 'attachment' not in agents_found:
                                        agents_found.append('attachment')
                            
                            # Collect response
                            if event.get('type') == 'response.output_text.delta':
                                response_text += event.get('delta', '')
                                
                        except: pass
        
        print(f"\nAgents detected: {agents_found}")
        print(f"Response length: {len(response_text)} chars")
        print(f"Response preview: {response_text[:200]}...")
        
        # Test 2: Image attachment
        print("\n\n=== Testing Image Attachment ===")
        request_data = {
            "messages": [{"role": "user", "content": "Explain what's shown in this diagram"}],
            "user_id": 10001,
            "model": "gpt-4o-mini",
            "stream": True,
            "attachments": [TEST_ATTACHMENTS["images"][0]]
        }
        
        agents_found = []
        response_text = ""
        
        async with client.stream('POST', 'http://localhost:5001/v1/multi-agent/response', json=request_data) as response:
            async for line in response.aiter_lines():
                if line.startswith('data: '):
                    event_data = line[6:]
                    if event_data != '[DONE]':
                        try:
                            event = json.loads(event_data)
                            
                            if 'attachment' in event.get('type', ''):
                                if 'attachment' not in agents_found:
                                    agents_found.append('attachment')
                                print(f"Attachment event: {event['type']}")
                            
                            if event.get('type') == 'response.output_text.delta':
                                response_text += event.get('delta', '')
                                
                        except: pass
        
        print(f"\nAgents detected: {agents_found}")
        print(f"Response length: {len(response_text)} chars")
        print(f"Response preview: {response_text[:200]}...")

if __name__ == "__main__":
    asyncio.run(test_attachment())