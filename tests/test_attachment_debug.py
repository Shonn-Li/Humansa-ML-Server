#!/usr/bin/env python3
"""
Debug attachment routing
"""

import asyncio
import httpx
import json

async def test_attachment():
    """Test attachment routing with debug info"""
    client = httpx.AsyncClient(timeout=30.0)
    
    print("ATTACHMENT ROUTING DEBUG TEST")
    print("="*60)
    
    # Test with actual PDF attachment
    request = {
        "messages": [{"role": "user", "content": "What does this PDF say?"}],
        "user_id": 10001,
        "model": "gpt-4o-mini",
        "attachments": [{
            "url": "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf",
            "type": "pdf",
            "name": "dummy.pdf"
        }],
        "stream": False,
        "enable_web_search": False,  # Disable web search to isolate attachment
        "enable_rag": False  # Disable RAG to isolate attachment
    }
    
    print(f"Request: {json.dumps(request, indent=2)}")
    print()
    
    try:
        response = await client.post("http://localhost:5002/v1/multi-agent/response", json=request)
        data = response.json()
        
        print("Response metadata:")
        metadata = data.get("metadata", {})
        print(f"  Agents used: {metadata.get('agents_used', [])}")
        print(f"  Total time: {metadata.get('total_time', 0):.2f}s")
        print()
        
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        print(f"Response length: {len(content)} chars")
        print(f"Response preview: {content[:500]}...")
        print()
        
        # Check for attachment content indicators
        if any(word in content.lower() for word in ["lorem ipsum", "dummy", "pdf", "document"]):
            print("✅ Attachment content found in response")
        else:
            print("❌ No attachment content found in response")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    
    await client.aclose()

if __name__ == "__main__":
    asyncio.run(test_attachment())