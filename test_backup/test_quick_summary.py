#!/usr/bin/env python3
"""Quick test summary"""
import asyncio
import httpx
import json

async def run_tests():
    client = httpx.AsyncClient(timeout=30.0)
    results = {}
    
    # Test 1: PDF Attachment
    print("Testing PDF attachment processing...")
    response = await client.post("http://localhost:5002/v1/multi-agent/response", json={
        "messages": [{"role": "user", "content": "Summarize this paper"}],
        "attachments": ["https://arxiv.org/pdf/2505.18499.pdf"],
        "user_id": 10001,
        "model": "gpt-4o-mini",
        "stream": False
    })
    content = response.json()['choices'][0]['message']['content']
    results['pdf_attachment'] = 'graph reasoning' in content.lower() and len(content) > 1000
    
    # Test 2: Empty Attachments
    print("Testing empty attachments...")
    response = await client.post("http://localhost:5002/v1/multi-agent/response", json={
        "messages": [{"role": "user", "content": "What is AI?"}],
        "attachments": [],
        "user_id": 10001,
        "model": "gpt-4o-mini",
        "stream": False
    })
    agents = list(response.json()['metadata']['agent_results'].keys())
    results['empty_attachments'] = 'attachment_agent' not in agents
    
    # Test 3: Streaming response.done
    print("Testing streaming response.done...")
    has_done = False
    async with client.stream('POST', 'http://localhost:5002/v1/multi-agent/response', json={
        "messages": [{"role": "user", "content": "Hi"}],
        "user_id": 10001,
        "model": "gpt-4o-mini",
        "stream": True
    }) as stream_response:
        async for line in stream_response.aiter_lines():
            if line.startswith('data: '):
                try:
                    event = json.loads(line[6:])
                    if event.get('type') == 'response.done':
                        has_done = True
                except:
                    pass
    results['streaming_done'] = has_done
    
    await client.aclose()
    
    # Summary
    print("\n" + "="*50)
    print("TEST SUMMARY")
    print("="*50)
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name}: {status}")
    
    passed_count = sum(1 for p in results.values() if p)
    print(f"\nTotal: {passed_count}/{len(results)} passed ({passed_count/len(results)*100:.0f}%)")

if __name__ == "__main__":
    asyncio.run(run_tests())