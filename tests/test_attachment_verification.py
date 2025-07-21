#!/usr/bin/env python3
"""
Verify attachment processing actually extracts and uses PDF content
"""

import asyncio
import httpx
import json
import base64
from datetime import datetime

async def test_attachment_processing():
    """Test that attachments are actually processed and content is extracted"""
    client = httpx.AsyncClient(timeout=30.0)
    
    print("="*80)
    print("ATTACHMENT PROCESSING VERIFICATION")
    print("="*80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Create a simple PDF content in base64
    # This is a minimal PDF with "Hello World" text
    pdf_base64 = "JVBERi0xLjQKMSAwIG9iago8PAovVHlwZSAvQ2F0YWxvZwovT3V0bGluZXMgMiAwIFIKL1BhZ2VzIDMgMCBSCj4+CmVuZG9iagoyIDAgb2JqCjw8Ci9UeXBlIC9PdXRsaW5lcwovQ291bnQgMAo+PgplbmRvYmoKMyAwIG9iago8PAovVHlwZSAvUGFnZXMKL0NvdW50IDEKL0tpZHMgWzQgMCBSXQo+PgplbmRvYmoKNCAwIG9iago8PAovVHlwZSAvUGFnZQovUGFyZW50IDMgMCBSCi9SZXNvdXJjZXMgPDwKL0ZvbnQgPDwKL0YxIDkgMCBSIAo+PgovUHJvY1NldCA4IDAgUgo+PgovTWVkaWFCb3ggWzAgMCA2MTIgNzkyXQovQ29udGVudHMgNSAwIFIKPj4KZW5kb2JqCjUgMCBvYmoKPDwKL0xlbmd0aCA0NAo+PgpzdHJlYW0KQlQKL0YxIDEyIFRmCjEwMCA3MDAgVGQKKEhlbGxvIFdvcmxkKSBUagpFVAplbmRzdHJlYW0KZW5kb2JqCjYgMCBvYmoKZW5kb2JqCjcgMCBvYmoKZW5kb2JqCjggMCBvYmoKWy9QREYgL1RleHRdCmVuZG9iago5IDAgb2JqCjw8Ci9UeXBlIC9Gb250Ci9TdWJ0eXBlIC9UeXBlMQovTmFtZSAvRjEKL0Jhc2VGb250IC9IZWx2ZXRpY2EKL0VuY29kaW5nIC9XaW5BbnNpRW5jb2RpbmcKPj4KZW5kb2JqCnhyZWYKMCAxMAowMDAwMDAwMDAwIDY1NTM1IGYgCjAwMDAwMDAwMDkgMDAwMDAgbiAKMDAwMDAwMDA3NCAwMDAwMCBuIAowMDAwMDAwMTIwIDAwMDAwIG4gCjAwMDAwMDAxNzkgMDAwMDAgbiAKMDAwMDAwMDM2NCAwMDAwMCBuIAowMDAwMDAwNDYzIDAwMDAwIG4gCjAwMDAwMDA0ODQgMDAwMDAgbiAKMDAwMDAwMDUwNSAwMDAwMCBuIAowMDAwMDAwNTMwIDAwMDAwIG4gCnRyYWlsZXIKPDwKL1NpemUgMTAKL1Jvb3QgMSAwIFIKPj4Kc3RhcnR4cmVmCjYzOAolJUVPRg=="
    
    test_cases = [
        {
            "name": "Local PDF Attachment (Base64)",
            "request": {
                "messages": [{"role": "user", "content": "What text is in this PDF file?"}],
                "user_id": 10001,
                "model": "gpt-4o-mini",
                "attachments": [{
                    "content": pdf_base64,
                    "type": "pdf",
                    "name": "test.pdf"
                }],
                "stream": True,
                "enable_web_search": False,
                "enable_rag": False
            },
            "expected_content": ["hello world", "pdf", "text"]
        },
        {
            "name": "Multiple Attachments",
            "request": {
                "messages": [{"role": "user", "content": "Summarize all the attached files."}],
                "user_id": 10001,
                "model": "gpt-4o-mini",
                "attachments": [
                    {
                        "content": pdf_base64,
                        "type": "pdf",
                        "name": "doc1.pdf"
                    },
                    {
                        "content": "This is a text file with important information about machine learning.",
                        "type": "text",
                        "name": "notes.txt"
                    }
                ],
                "stream": True,
                "enable_web_search": False,
                "enable_rag": False
            },
            "expected_content": ["hello world", "machine learning", "text file", "pdf"]
        },
        {
            "name": "Attachment with Web Search",
            "request": {
                "messages": [{"role": "user", "content": "Compare this PDF content with current information about the topic online."}],
                "user_id": 10001,
                "model": "gpt-4o-mini",
                "attachments": [{
                    "content": "Machine learning is a subset of artificial intelligence.",
                    "type": "text",
                    "name": "ml_basics.txt"
                }],
                "stream": True,
                "enable_web_search": True,
                "enable_citations": True
            },
            "expected_content": ["machine learning", "artificial intelligence", "subset"]
        }
    ]
    
    for test in test_cases:
        print(f"\n{'='*60}")
        print(f"TEST: {test['name']}")
        print(f"{'='*60}")
        
        response_text = ""
        agents_used = []
        attachment_chunks = []
        has_attachment_agent = False
        
        # Track events
        events = {
            "router": False,
            "attachment": False,
            "response": False,
            "web_search": False
        }
        
        async with client.stream("POST", "http://localhost:5002/v1/multi-agent/response", json=test["request"]) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    
                    try:
                        event = json.loads(data_str)
                        event_type = event.get("type", "")
                        
                        # Track response text
                        if event_type == "response.output_text.delta":
                            response_text += event.get("delta", "")
                        
                        # Track which agents are running
                        if "reasoning" in event_type and event.get("item", {}).get("id", "").startswith("router"):
                            events["router"] = True
                        elif "reasoning" in event_type and event.get("item", {}).get("id", "").startswith("attachment"):
                            events["attachment"] = True
                            has_attachment_agent = True
                        elif "message" in event_type and event.get("item", {}).get("id", "").startswith("response"):
                            events["response"] = True
                        elif "reasoning" in event_type and event.get("item", {}).get("id", "").startswith("web_search"):
                            events["web_search"] = True
                            
                    except json.JSONDecodeError:
                        pass
        
        print(f"\n1. AGENT EXECUTION:")
        print(f"   Router: {'✅' if events['router'] else '❌'}")
        print(f"   Attachment: {'✅' if events['attachment'] else '❌'}")
        print(f"   Response: {'✅' if events['response'] else '❌'}")
        if test["request"].get("enable_web_search"):
            print(f"   Web Search: {'✅' if events['web_search'] else '❌'}")
        
        print(f"\n2. RESPONSE ANALYSIS:")
        print(f"   Length: {len(response_text)} chars")
        print(f"   Preview: {response_text[:200]}...")
        
        print(f"\n3. CONTENT VERIFICATION:")
        expected = test.get("expected_content", [])
        found_count = 0
        for content in expected:
            if content.lower() in response_text.lower():
                print(f"   ✅ Found expected content: '{content}'")
                found_count += 1
            else:
                print(f"   ❌ Missing expected content: '{content}'")
        
        print(f"\n   Score: {found_count}/{len(expected)} expected elements found")
        
        # Overall test result
        if has_attachment_agent and found_count > 0:
            print(f"\n   ✅ ATTACHMENT PROCESSING WORKING")
        else:
            print(f"\n   ❌ ATTACHMENT PROCESSING FAILED")
            if not has_attachment_agent:
                print(f"      - Attachment agent was not triggered")
            if found_count == 0:
                print(f"      - No expected content found in response")
    
    await client.aclose()

async def test_attachment_routing_logic():
    """Test the routing logic for attachments"""
    client = httpx.AsyncClient(timeout=30.0)
    
    print("\n" + "="*80)
    print("ATTACHMENT ROUTING LOGIC TEST")
    print("="*80)
    
    routing_tests = [
        {
            "name": "Should route to attachment agent",
            "request": {
                "messages": [{"role": "user", "content": "analyze this file"}],
                "user_id": 10001,
                "model": "gpt-4o-mini",
                "attachments": [{"content": "test", "type": "text", "name": "test.txt"}],
                "stream": False
            },
            "should_use_attachment": True
        },
        {
            "name": "Should NOT route to attachment (empty array)",
            "request": {
                "messages": [{"role": "user", "content": "tell me about files"}],
                "user_id": 10001,
                "model": "gpt-4o-mini",
                "attachments": [],
                "stream": False
            },
            "should_use_attachment": False
        },
        {
            "name": "Should route even with generic query",
            "request": {
                "messages": [{"role": "user", "content": "hello"}],
                "user_id": 10001,
                "model": "gpt-4o-mini",
                "attachments": [{"content": "important data", "type": "text", "name": "data.txt"}],
                "stream": False
            },
            "should_use_attachment": True
        }
    ]
    
    for test in routing_tests:
        print(f"\nTest: {test['name']}")
        print("-" * 40)
        
        response = await client.post("http://localhost:5002/v1/multi-agent/response", json=test["request"])
        data = response.json()
        
        metadata = data.get("metadata", {})
        agents_used = metadata.get("agents_used", [])
        
        used_attachment = "attachment" in agents_used
        expected = test["should_use_attachment"]
        
        if used_attachment == expected:
            print(f"✅ Routing correct: Attachment agent {'used' if used_attachment else 'not used'}")
        else:
            print(f"❌ Routing incorrect: Expected attachment={'expected'}, got={used_attachment}")
            print(f"   Agents used: {agents_used}")
    
    await client.aclose()

async def main():
    """Run all attachment verification tests"""
    await test_attachment_processing()
    await test_attachment_routing_logic()
    
    print("\n" + "="*80)
    print("ATTACHMENT VERIFICATION COMPLETE")
    print("="*80)
    print("\nTo run this test:")
    print("cd /Users/shonnli/Non-icloudFile/YouWoAI/Code_V1/YouWoAI-ML-Server")
    print("source youwo-ml-venv/bin/activate")
    print("python tests/test_attachment_verification.py")

if __name__ == "__main__":
    asyncio.run(main())