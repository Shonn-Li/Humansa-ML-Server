#!/usr/bin/env python3
"""
Simple streaming flow test - runs one test at a time
"""

import asyncio
import httpx
import json
import sys
from typing import Dict, List, Any

async def test_streaming_flow(name: str, request: Dict[str, Any]):
    """Test a single streaming request and show event flow"""
    print(f"\n{'='*80}")
    print(f"TEST: {name}")
    print(f"{'='*80}")
    print(f"Request: {json.dumps(request, indent=2)}")
    print(f"\nSTREAMING EVENTS:")
    print("-"*60)
    
    client = httpx.AsyncClient(timeout=30.0)
    request["stream"] = True
    
    try:
        event_count = 0
        response_text = ""
        agents_detected = set()
        citations = []
        
        async with client.stream("POST", "http://localhost:5002/v1/multi-agent/response", json=request) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                        
                    try:
                        event = json.loads(data_str)
                        event_type = event.get("type", "")
                        event_count += 1
                        
                        # Print significant events
                        if event_type == "response.output_item.added":
                            item = event.get("item", {})
                            print(f"[{event_count:3d}] ➕ Output item: {item.get('type')} (ID: {item.get('id', 'N/A')[:12]}...)")
                            
                        elif event_type == "response.reasoning_text.delta":
                            text = event.get("delta", "")[:100]
                            if "routed to agents:" in text:
                                print(f"[{event_count:3d}] 🧠 Reasoning: {text}")
                                # Extract agents
                                agent_part = text.split("routed to agents:")[1]
                                for agent in agent_part.split(","):
                                    agent_name = agent.strip()
                                    if agent_name:
                                        agents_detected.add(agent_name)
                                        
                        elif event_type == "response.output_text.delta":
                            delta = event.get("delta", "")
                            response_text += delta
                            if event_count <= 5 or len(delta) > 50:  # Show first few or significant chunks
                                preview = delta[:50] + "..." if len(delta) > 50 else delta
                                print(f"[{event_count:3d}] 📝 Response text: {preview}")
                                
                        elif event_type == "response.output_text.annotation.added":
                            ann = event.get("annotation", {})
                            citations.append(ann)
                            print(f"[{event_count:3d}] 📌 Citation: {ann.get('text', 'N/A')} at {ann.get('start_index', 0)}-{ann.get('end_index', 0)}")
                            print(f"      URL: {ann.get('url', 'N/A')}")
                            print(f"      Title: {ann.get('title', 'N/A')}")
                            
                        elif event_type == "response.web_search_call.created":
                            agents_detected.add("web_search")
                            print(f"[{event_count:3d}] 🔍 Web search initiated")
                            
                        elif event_type == "response.file_search_call.created":
                            agents_detected.add("rag")
                            print(f"[{event_count:3d}] 📁 File search initiated")
                            
                        elif event_type == "response.done":
                            print(f"[{event_count:3d}] ✅ Response completed")
                            
                        elif event_type == "response.usage":
                            metadata = event.get("metadata", {})
                            iterations = metadata.get("iterations", 1)
                            if iterations > 1:
                                print(f"[{event_count:3d}] 🔄 Iterations: {iterations}")
                                
                    except json.JSONDecodeError:
                        pass
        
        print(f"\nSUMMARY:")
        print(f"  Total events: {event_count}")
        print(f"  Agents triggered: {', '.join(sorted(agents_detected)) if agents_detected else 'None'}")
        print(f"  Citations found: {len(citations)}")
        print(f"  Response length: {len(response_text)} chars")
        
        if response_text:
            print(f"\nFINAL RESPONSE (first 500 chars):")
            print("-"*60)
            print(response_text[:500] + "..." if len(response_text) > 500 else response_text)
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
    finally:
        await client.aclose()


async def main():
    """Run individual tests"""
    
    # Test 1: Simple query
    await test_streaming_flow(
        "Simple Query",
        {
            "messages": [{"role": "user", "content": "What is AI?"}],
            "user_id": 10001,
            "model": "gpt-4.1-nano"
        }
    )
    
    # Test 2: Web search with citations
    await test_streaming_flow(
        "Web Search with Citations",
        {
            "messages": [{"role": "user", "content": "What are the latest AI breakthroughs in 2024? Include sources."}],
            "user_id": 10001,
            "model": "gpt-4.1-nano",
            "enable_citations": True
        }
    )
    
    # Test 3: PDF attachment with citations
    await test_streaming_flow(
        "PDF Attachment Analysis",
        {
            "messages": [{"role": "user", "content": "Summarize this paper and cite key findings"}],
            "attachments": ["https://arxiv.org/pdf/2505.18499.pdf"],
            "user_id": 10001,
            "model": "gpt-4.1-nano",
            "enable_citations": True
        }
    )
    
    # Test 4: Iterative reasoning
    await test_streaming_flow(
        "Complex Iterative Query",
        {
            "messages": [{"role": "user", "content": "Compare supervised vs unsupervised learning approaches for anomaly detection. Consider accuracy, data requirements, and implementation complexity. Provide a recommendation."}],
            "user_id": 10001,
            "model": "gpt-4.1-nano",
            "enable_iterations": True,
            "enable_citations": True
        }
    )
    
    # Test 5: Knowledge base query
    await test_streaming_flow(
        "Knowledge Base Query with Citations",
        {
            "messages": [{"role": "user", "content": "What do my notes say about PARL? Include citations and key concepts."}],
            "user_id": 10001,
            "model": "gpt-4.1-nano",
            "enable_citations": True
        }
    )


if __name__ == "__main__":
    # Run specific test if provided as argument
    if len(sys.argv) > 1:
        test_num = int(sys.argv[1])
        tests = [
            ("Simple Query", {"messages": [{"role": "user", "content": "What is AI?"}], "user_id": 10001, "model": "gpt-4.1-nano"}),
            ("Web Search with Citations", {"messages": [{"role": "user", "content": "What are the latest AI breakthroughs in 2024? Include sources."}], "user_id": 10001, "model": "gpt-4.1-nano", "enable_citations": True}),
            ("PDF Attachment Analysis", {"messages": [{"role": "user", "content": "Summarize this paper and cite key findings"}], "attachments": ["https://arxiv.org/pdf/2505.18499.pdf"], "user_id": 10001, "model": "gpt-4.1-nano", "enable_citations": True}),
            ("Complex Iterative Query", {"messages": [{"role": "user", "content": "Compare supervised vs unsupervised learning approaches for anomaly detection. Consider accuracy, data requirements, and implementation complexity. Provide a recommendation."}], "user_id": 10001, "model": "gpt-4.1-nano", "enable_iterations": True, "enable_citations": True}),
            ("Knowledge Base Query with Citations", {"messages": [{"role": "user", "content": "What do my notes say about PARL? Include citations and key concepts."}], "user_id": 10001, "model": "gpt-4.1-nano", "enable_citations": True})
        ]
        if 0 < test_num <= len(tests):
            asyncio.run(test_streaming_flow(*tests[test_num-1]))
        else:
            print(f"Invalid test number. Choose 1-{len(tests)}")
    else:
        asyncio.run(main())