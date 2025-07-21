#!/usr/bin/env python3
"""
Summary test showing all implemented features
"""

import asyncio
import httpx
import json
from datetime import datetime

async def test_all_features():
    """Test all implemented features"""
    client = httpx.AsyncClient(timeout=30.0)
    
    print("="*80)
    print("YOUWOAI ML SERVER - ALL FEATURES SUMMARY TEST")
    print("="*80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    features = []
    
    # Test 1: Attachment routing
    print("\n1. TESTING ATTACHMENT ROUTING")
    print("-" * 40)
    
    request = {
        "messages": [{"role": "user", "content": "What does this file say?"}],
        "user_id": 10001,
        "model": "gpt-4o-mini",
        "attachments": [{
            "url": "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf",
            "type": "pdf",
            "name": "dummy.pdf"
        }],
        "stream": False
    }
    
    try:
        response = await client.post("http://localhost:5002/v1/multi-agent/response", json=request)
        data = response.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        if "Lorem ipsum" in content or "Dummy PDF" in content:
            print("✅ Attachment routing works - PDF content extracted")
            features.append("Attachment routing: WORKING")
        else:
            print("❌ Attachment routing failed - no PDF content found")
            features.append("Attachment routing: FAILED")
    except Exception as e:
        print(f"❌ Attachment test error: {e}")
        features.append("Attachment routing: ERROR")
    
    # Test 2: Citation format
    print("\n2. TESTING CITATION FORMAT")
    print("-" * 40)
    
    request = {
        "messages": [{"role": "user", "content": "What is Python programming? Give me a brief answer with sources."}],
        "user_id": 10001,
        "model": "gpt-4o-mini",
        "enable_citations": True,
        "stream": True
    }
    
    try:
        response_text = ""
        async with client.stream("POST", "http://localhost:5002/v1/multi-agent/response", json=request) as response:
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
        
        import re
        numbered_citations = re.findall(r'\[(\d+)\]', response_text)
        if numbered_citations:
            print(f"✅ Citation format correct - found numbered citations: {numbered_citations[:5]}")
            features.append("Citation format: WORKING")
        else:
            print("❌ Citation format incorrect - no numbered citations found")
            features.append("Citation format: FAILED")
    except Exception as e:
        print(f"❌ Citation test error: {e}")
        features.append("Citation format: ERROR")
    
    # Test 3: Citation position tracking
    print("\n3. TESTING CITATION POSITION TRACKING")
    print("-" * 40)
    
    request = {
        "messages": [{"role": "user", "content": "What is machine learning? One sentence with source."}],
        "user_id": 10001,
        "model": "gpt-4o-mini",
        "enable_citations": True,
        "stream": True
    }
    
    try:
        annotation_events = []
        async with client.stream("POST", "http://localhost:5002/v1/multi-agent/response", json=request) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        event = json.loads(data_str)
                        if "annotation" in event.get("type", ""):
                            annotation_events.append(event)
                    except:
                        pass
        
        if annotation_events:
            ann = annotation_events[0].get("annotation", {})
            if ann.get("start_index") is not None and ann.get("end_index") is not None:
                print(f"✅ Citation position tracking works - positions: {ann.get('start_index')}-{ann.get('end_index')}")
                features.append("Citation position tracking: WORKING")
            else:
                print("❌ Citation position tracking failed - no position data")
                features.append("Citation position tracking: FAILED")
        else:
            print("❌ No citation annotation events found")
            features.append("Citation position tracking: FAILED")
    except Exception as e:
        print(f"❌ Position tracking test error: {e}")
        features.append("Citation position tracking: ERROR")
    
    # Test 4: Iterative agent capabilities
    print("\n4. TESTING ITERATIVE AGENT CAPABILITIES")
    print("-" * 40)
    
    request = {
        "messages": [{"role": "user", "content": "Explain quantum computing in detail with its applications, challenges, and future prospects."}],
        "user_id": 10001,
        "model": "gpt-4o-mini",
        "enable_iterations": True,
        "stream": False
    }
    
    try:
        response = await client.post("http://localhost:5002/v1/multi-agent/response", json=request)
        data = response.json()
        metadata = data.get("metadata", {})
        iterations = metadata.get("iterations_performed", 0)
        
        if iterations > 0:
            print(f"✅ Iterative refinement works - performed {iterations} iterations")
            features.append("Iterative refinement: WORKING")
        else:
            print("❌ No iterations performed on complex query")
            features.append("Iterative refinement: NOT TRIGGERED")
    except Exception as e:
        print(f"❌ Iteration test error: {e}")
        features.append("Iterative refinement: ERROR")
    
    # Test 5: Streaming events
    print("\n5. TESTING STREAMING EVENT FLOW")
    print("-" * 40)
    
    request = {
        "messages": [{"role": "user", "content": "Hello, how are you?"}],
        "user_id": 10001,
        "model": "gpt-4o-mini",
        "stream": True
    }
    
    try:
        event_types = set()
        async with client.stream("POST", "http://localhost:5002/v1/multi-agent/response", json=request) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        event = json.loads(data_str)
                        event_types.add(event.get("type"))
                    except:
                        pass
        
        required_events = {"response.created", "response.output_text.delta", "response.completed", "response.done"}
        if required_events.issubset(event_types):
            print(f"✅ Streaming events correct - found all required events")
            features.append("Streaming events: WORKING")
        else:
            missing = required_events - event_types
            print(f"❌ Missing streaming events: {missing}")
            features.append("Streaming events: INCOMPLETE")
    except Exception as e:
        print(f"❌ Streaming test error: {e}")
        features.append("Streaming events: ERROR")
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY OF IMPLEMENTED FEATURES:")
    print("="*80)
    for i, feature in enumerate(features, 1):
        print(f"{i}. {feature}")
    
    working = sum(1 for f in features if "WORKING" in f)
    total = len(features)
    print(f"\n✅ Working features: {working}/{total}")
    
    await client.aclose()

if __name__ == "__main__":
    asyncio.run(test_all_features())