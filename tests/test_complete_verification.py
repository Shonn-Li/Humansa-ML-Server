#!/usr/bin/env python3
"""
Complete verification test - checks that citations are ACTUALLY used with real positions
"""

import asyncio
import httpx
import json
import re
from typing import Dict, List, Any
from datetime import datetime

class CitationVerifier:
    def __init__(self):
        self.response_text = ""
        self.annotations = []
        self.citation_sources = []
        
    def verify_citation_in_text(self, text: str, annotation: Dict[str, Any]) -> bool:
        """Verify that the citation actually exists at the claimed position"""
        start = annotation.get("start_index", 0)
        end = annotation.get("end_index", 0)
        citation_text = annotation.get("text", "")
        
        # Extract the actual text at the position
        if 0 <= start < len(text) and start < end <= len(text):
            actual_text = text[start:end]
            return actual_text == citation_text
        return False

async def test_complete_citation_system():
    """Test that citations are actually used in responses with real positions"""
    client = httpx.AsyncClient(timeout=30.0)
    
    print("="*80)
    print("COMPLETE CITATION SYSTEM VERIFICATION")
    print("="*80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    test_cases = [
        {
            "name": "Web Search Citations",
            "request": {
                "messages": [{"role": "user", "content": "What are the key features of GPT-4? List 3 features with sources."}],
                "user_id": 10001,
                "model": "gpt-4o-mini",
                "enable_citations": True,
                "enable_web_search": True,
                "enable_rag": False,
                "stream": True
            }
        },
        {
            "name": "RAG + Web Search Citations",
            "request": {
                "messages": [{"role": "user", "content": "Tell me about machine learning algorithms. Include information from my notes and web sources."}],
                "user_id": 10001,
                "model": "gpt-4o-mini",
                "enable_citations": True,
                "enable_web_search": True,
                "enable_rag": True,
                "stream": True
            }
        },
        {
            "name": "Multiple Citation Verification",
            "request": {
                "messages": [{"role": "user", "content": "Compare Python and JavaScript. Give me 3 differences with citations for each point."}],
                "user_id": 10001,
                "model": "gpt-4o-mini",
                "enable_citations": True,
                "enable_web_search": True,
                "stream": True
            }
        }
    ]
    
    for test in test_cases:
        print(f"\n{'='*60}")
        print(f"TEST: {test['name']}")
        print(f"{'='*60}")
        
        verifier = CitationVerifier()
        events = []
        
        # Collect all streaming events
        async with client.stream("POST", "http://localhost:5002/v1/multi-agent/response", json=test["request"]) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    
                    try:
                        event = json.loads(data_str)
                        events.append(event)
                        
                        # Collect response text
                        if event.get("type") == "response.output_text.delta":
                            verifier.response_text += event.get("delta", "")
                        
                        # Collect annotations
                        elif event.get("type") == "response.output_text.annotation.added":
                            verifier.annotations.append(event.get("annotation", {}))
                        
                        # Collect citation sources
                        elif event.get("type") == "response.citations":
                            verifier.citation_sources = event.get("citations", [])
                            
                    except json.JSONDecodeError:
                        pass
        
        # Verify results
        print(f"\n1. RESPONSE TEXT ANALYSIS:")
        print(f"   Length: {len(verifier.response_text)} chars")
        
        # Find all citations in text
        citation_pattern = re.compile(r'\[(\d+)\]')
        citations_in_text = citation_pattern.findall(verifier.response_text)
        print(f"   Citations found in text: {citations_in_text}")
        print(f"   Unique citations: {sorted(set(citations_in_text))}")
        
        print(f"\n2. ANNOTATION VERIFICATION:")
        print(f"   Total annotations: {len(verifier.annotations)}")
        
        # Verify each annotation
        valid_annotations = 0
        for i, ann in enumerate(verifier.annotations):
            start = ann.get("start_index", 0)
            end = ann.get("end_index", 0)
            text = ann.get("text", "")
            url = ann.get("url", "N/A")
            
            # Verify position
            is_valid = verifier.verify_citation_in_text(verifier.response_text, ann)
            valid_annotations += is_valid
            
            status = "✅" if is_valid else "❌"
            print(f"   {status} Annotation {i+1}: '{text}' at {start}-{end}")
            print(f"      Actual text at position: '{verifier.response_text[start:end] if start < len(verifier.response_text) else 'OUT OF BOUNDS'}'")
            print(f"      URL: {url[:50] if url else 'None'}...")
        
        print(f"\n   Position verification: {valid_annotations}/{len(verifier.annotations)} annotations have correct positions")
        
        print(f"\n3. CITATION SOURCES:")
        print(f"   Total sources provided: {len(verifier.citation_sources)}")
        for i, source in enumerate(verifier.citation_sources[:3]):  # Show first 3
            print(f"   Source {i+1}: {source.get('title', 'N/A')[:50]}...")
            print(f"            URL: {source.get('url', 'N/A')[:50]}...")
        
        print(f"\n4. COMPLETE VERIFICATION:")
        
        # Check 1: All citations in text have annotations
        citations_with_annotations = set()
        for ann in verifier.annotations:
            match = re.search(r'\d+', ann.get("text", ""))
            if match:
                citations_with_annotations.add(match.group())
        
        missing_annotations = set(citations_in_text) - citations_with_annotations
        if missing_annotations:
            print(f"   ❌ Citations without annotations: {missing_annotations}")
        else:
            print(f"   ✅ All citations in text have annotations")
        
        # Check 2: All annotations have valid positions
        if valid_annotations == len(verifier.annotations):
            print(f"   ✅ All annotations have correct positions")
        else:
            print(f"   ❌ {len(verifier.annotations) - valid_annotations} annotations have incorrect positions")
        
        # Check 3: Sources match citations
        max_citation = max([int(c) for c in citations_in_text]) if citations_in_text else 0
        if max_citation <= len(verifier.citation_sources):
            print(f"   ✅ Sufficient sources for all citations")
        else:
            print(f"   ❌ Not enough sources: {len(verifier.citation_sources)} sources for citation [{max_citation}]")
        
        # Show sample with annotations highlighted
        print(f"\n5. SAMPLE TEXT WITH ANNOTATIONS:")
        sample = verifier.response_text[:300]
        print(f"   {sample}...")
        
    await client.aclose()

async def test_non_streaming_citations():
    """Test non-streaming to ensure citations work there too"""
    client = httpx.AsyncClient(timeout=30.0)
    
    print("\n" + "="*80)
    print("NON-STREAMING CITATION TEST")
    print("="*80)
    
    request = {
        "messages": [{"role": "user", "content": "What is artificial intelligence? Give me 2 facts with citations."}],
        "user_id": 10001,
        "model": "gpt-4o-mini",
        "enable_citations": True,
        "stream": False
    }
    
    response = await client.post("http://localhost:5002/v1/multi-agent/response", json=request)
    data = response.json()
    
    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    citations = re.findall(r'\[(\d+)\]', content)
    
    print(f"Response length: {len(content)} chars")
    print(f"Citations found: {citations}")
    print(f"Unique citations: {sorted(set(citations))}")
    
    # Check for sources section
    if "Sources:" in content or "References:" in content:
        print("✅ Sources section included")
        # Extract sources section
        sources_start = content.find("Sources:") if "Sources:" in content else content.find("References:")
        sources_section = content[sources_start:]
        print(f"\nSources section preview:")
        print(sources_section[:300])
    else:
        print("❌ No sources section found")
    
    await client.aclose()

async def test_edge_cases():
    """Test edge cases for citation system"""
    client = httpx.AsyncClient(timeout=30.0)
    
    print("\n" + "="*80)
    print("CITATION EDGE CASES TEST")
    print("="*80)
    
    edge_cases = [
        {
            "name": "Empty query with citations",
            "request": {
                "messages": [{"role": "user", "content": ""}],
                "user_id": 10001,
                "model": "gpt-4o-mini",
                "enable_citations": True,
                "stream": True
            }
        },
        {
            "name": "Query that shouldn't need citations",
            "request": {
                "messages": [{"role": "user", "content": "What is 2 + 2?"}],
                "user_id": 10001,
                "model": "gpt-4o-mini",
                "enable_citations": True,
                "stream": True
            }
        },
        {
            "name": "Very long query requiring many citations",
            "request": {
                "messages": [{"role": "user", "content": "Give me a comprehensive overview of: 1) Machine learning types 2) Deep learning architectures 3) Natural language processing 4) Computer vision 5) Reinforcement learning. Include citations for each topic."}],
                "user_id": 10001,
                "model": "gpt-4o-mini",
                "enable_citations": True,
                "stream": True
            }
        }
    ]
    
    for test in edge_cases:
        print(f"\nEdge case: {test['name']}")
        print("-" * 40)
        
        annotations_count = 0
        response_length = 0
        
        try:
            async with client.stream("POST", "http://localhost:5002/v1/multi-agent/response", json=test["request"]) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            event = json.loads(data_str)
                            if event.get("type") == "response.output_text.delta":
                                response_length += len(event.get("delta", ""))
                            elif event.get("type") == "response.output_text.annotation.added":
                                annotations_count += 1
                        except:
                            pass
            
            print(f"  Response length: {response_length} chars")
            print(f"  Annotations: {annotations_count}")
            
        except Exception as e:
            print(f"  Error: {e}")
    
    await client.aclose()

async def main():
    """Run all verification tests"""
    await test_complete_citation_system()
    await test_non_streaming_citations()
    await test_edge_cases()
    
    print("\n" + "="*80)
    print("VERIFICATION COMPLETE")
    print("="*80)
    print("\nTo run this test:")
    print("cd /Users/shonnli/Non-icloudFile/YouWoAI/Code_V1/YouWoAI-ML-Server")
    print("source youwo-ml-venv/bin/activate")
    print("python tests/test_complete_verification.py")

if __name__ == "__main__":
    asyncio.run(main())