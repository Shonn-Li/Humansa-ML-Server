#!/usr/bin/env python3
"""
Test citation format to ensure numbered brackets are used
"""

import asyncio
import httpx
import json
import re

async def test_citation_format():
    """Test that citations use [1] format not markdown"""
    client = httpx.AsyncClient(timeout=30.0)
    
    print("="*80)
    print("CITATION FORMAT TEST")
    print("="*80)
    
    # Test both streaming and non-streaming
    test_cases = [
        {
            "name": "Non-streaming",
            "request": {
                "messages": [{
                    "role": "user", 
                    "content": "What is machine learning? Give a brief answer with sources."
                }],
                "user_id": 10001,
                "model": "gpt-4.1-nano",
                "enable_citations": True,
                "stream": False
            }
        },
        {
            "name": "Streaming",
            "request": {
                "messages": [{
                    "role": "user", 
                    "content": "What is artificial intelligence? Give a brief answer with sources."
                }],
                "user_id": 10001,
                "model": "gpt-4.1-nano",
                "enable_citations": True,
                "stream": True
            }
        }
    ]
    
    for test in test_cases:
        print(f"\n{'='*60}")
        print(f"TEST: {test['name']}")
        print(f"{'='*60}")
        
        if test["request"]["stream"]:
            # Streaming test
            response_text = ""
            async with client.stream("POST", "http://localhost:5002/v1/multi-agent/response", json=test["request"]) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            event = json.loads(data_str)
                            if event.get("type") == "response.output_text.delta":
                                response_text += event.get("delta", "")
                        except:
                            pass
        else:
            # Non-streaming test
            response = await client.post("http://localhost:5002/v1/multi-agent/response", json=test["request"])
            data = response.json()
            response_text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        print(f"\nResponse preview (first 300 chars):")
        print(response_text[:300] + "..." if len(response_text) > 300 else response_text)
        
        # Check citation formats
        numbered_pattern = re.compile(r'\[(\d+)\]')
        markdown_pattern = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
        
        numbered_citations = numbered_pattern.findall(response_text)
        markdown_citations = markdown_pattern.findall(response_text)
        
        print(f"\nCitation Analysis:")
        print(f"  Numbered citations [1], [2], etc: {numbered_citations}")
        print(f"  Markdown citations [text](url): {len(markdown_citations)} found")
        
        if numbered_citations and not markdown_citations:
            print("  ✅ CORRECT: Using numbered citation format")
        elif markdown_citations and not numbered_citations:
            print("  ❌ INCORRECT: Using markdown link format instead of numbered")
        elif numbered_citations and markdown_citations:
            print("  ⚠️  MIXED: Both formats found")
        else:
            print("  ❌ NO CITATIONS found")
        
        # Check for Sources section
        if "Sources:" in response_text or "References:" in response_text:
            print("  ✅ Sources section found")
        else:
            print("  ❌ No Sources section found")
    
    await client.aclose()

if __name__ == "__main__":
    asyncio.run(test_citation_format())