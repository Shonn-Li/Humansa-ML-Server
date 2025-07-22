#!/usr/bin/env python3
"""Simple test for new features: attachment priority, citations, and iterative agents"""

import httpx
import asyncio
import json
from datetime import datetime

async def test_features():
    """Test all three new features"""
    
    print("=" * 80)
    print("TESTING NEW FEATURES")
    print("=" * 80)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Test 1: Attachment Priority
        print("\n1. TESTING ATTACHMENT PRIORITY")
        print("-" * 40)
        
        attachment_request = {
            "messages": [{"role": "user", "content": "What is this document about?"}],
            "user_id": 10001,
            "model": "gpt-4.1-nano",
            "stream": False,
            "attachments": ["https://arxiv.org/pdf/2505.18499.pdf"]
        }
        
        try:
            response = await client.post(
                "http://localhost:5001/v1/multi-agent/response",
                json=attachment_request
            )
            
            if response.status_code == 200:
                data = response.json()
                agent_results = data.get("metadata", {}).get("agent_results", {})
                agents_used = [k.replace("_agent", "") for k in agent_results.keys()]
                
                print(f"✅ Request successful")
                print(f"Agents triggered: {agents_used}")
                print(f"Attachment agent: {'✅ YES' if 'attachment' in agents_used else '❌ NO'}")
                
                # Show response preview
                if data.get("choices"):
                    content = data["choices"][0]["message"]["content"][:200]
                    print(f"\nResponse preview: {content}...")
            else:
                print(f"❌ Request failed: {response.status_code}")
        except Exception as e:
            print(f"❌ Error: {str(e)}")
        
        # Test 2: Citation Formatting
        print("\n\n2. TESTING CITATION FORMATTING")
        print("-" * 40)
        
        citation_request = {
            "messages": [{"role": "user", "content": "What are transformers in AI? Please cite your sources."}],
            "user_id": 10001,
            "model": "gpt-4.1-nano",
            "stream": False
        }
        
        try:
            response = await client.post(
                "http://localhost:5001/v1/multi-agent/response",
                json=citation_request
            )
            
            if response.status_code == 200:
                data = response.json()
                agent_results = data.get("metadata", {}).get("agent_results", {})
                agents_used = [k.replace("_agent", "") for k in agent_results.keys()]
                
                print(f"✅ Request successful")
                print(f"Agents triggered: {agents_used}")
                print(f"Citation agent: {'✅ YES' if 'citation' in agents_used else '❌ NO'}")
                
                # Check for citation markers
                if data.get("choices"):
                    content = data["choices"][0]["message"]["content"]
                    has_citations = any(f"[{i}]" in content for i in range(1, 10))
                    has_sources = "Sources:" in content or "References:" in content
                    
                    print(f"Citation markers [1], [2], etc: {'✅ YES' if has_citations else '❌ NO'}")
                    print(f"Sources section: {'✅ YES' if has_sources else '❌ NO'}")
                    
                    if has_citations:
                        # Show lines with citations
                        print("\nLines with citations:")
                        for line in content.split('\n'):
                            if '[' in line and ']' in line:
                                print(f"  {line[:100]}...")
                                break
            else:
                print(f"❌ Request failed: {response.status_code}")
        except Exception as e:
            print(f"❌ Error: {str(e)}")
        
        # Test 3: Iterative Agents
        print("\n\n3. TESTING ITERATIVE AGENTS")
        print("-" * 40)
        
        complex_request = {
            "messages": [{"role": "user", "content": "Analyze the latest AI trends and provide a comprehensive overview with examples, research papers, and practical applications. Make sure to be thorough."}],
            "user_id": 10001,
            "model": "gpt-4.1-nano",
            "stream": False
        }
        
        try:
            response = await client.post(
                "http://localhost:5001/v1/multi-agent/response",
                json=complex_request
            )
            
            if response.status_code == 200:
                data = response.json()
                metadata = data.get("metadata", {})
                agent_results = metadata.get("agent_results", {})
                agents_used = [k.replace("_agent", "") for k in agent_results.keys()]
                
                print(f"✅ Request successful")
                print(f"Agents triggered: {agents_used}")
                print(f"Total agents used: {len(agents_used)}")
                
                # Check for iterations
                iterations = metadata.get("iterations", 1)
                print(f"Iterations performed: {iterations}")
                
                # Check response quality indicators
                if data.get("choices"):
                    content = data["choices"][0]["message"]["content"]
                    word_count = len(content.split())
                    print(f"Response word count: {word_count}")
                    print(f"Response quality: {'✅ Comprehensive' if word_count > 200 else '⚠️  Brief'}")
            else:
                print(f"❌ Request failed: {response.status_code}")
        except Exception as e:
            print(f"❌ Error: {str(e)}")
        
        print("\n" + "=" * 80)
        print("TEST COMPLETE")
        print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_features())