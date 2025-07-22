#!/usr/bin/env python3

"""
Final validation test with proper queries to trigger RAG
"""

import asyncio
import json
import sys
import os
import re
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

# Set up environment
os.environ['DATABASE_URL'] = os.environ.get('DATABASE_URL', 'postgresql://postgres:12931@localhost:5454/youwoai_test')

async def test_comprehensive_citations():
    """Test comprehensive citations with multi-agent system"""
    
    print("🚀 FINAL VALIDATION TEST")
    print("="*60)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # Import the endpoint
    try:
        from chat.endpoints.multi_agent_endpoint_v2 import MultiAgentChatEndpointV2
        endpoint = MultiAgentChatEndpointV2()
        print("✅ Successfully imported MultiAgentChatEndpointV2")
    except Exception as e:
        print(f"❌ Failed to import: {e}")
        return
    
    # Test cases designed to trigger different agents
    test_cases = [
        {
            "name": "RAG Test - Explicit Note Search",
            "request": {
                "model": "gpt-4.1-nano",
                "messages": [
                    {"role": "user", "content": "Search my notes for information about PARL and predictable AI"}
                ],
                "stream": True,
                "temperature": 0.7,
                "enable_citations": True,
                "user_id": 10001
            }
        },
        {
            "name": "RAG Test - My Notes Query",
            "request": {
                "model": "gpt-4.1-nano",
                "messages": [
                    {"role": "user", "content": "What do my notes say about machine learning and AI frameworks?"}
                ],
                "stream": True,
                "temperature": 0.7,
                "enable_citations": True,
                "user_id": 10001
            }
        },
        {
            "name": "Web Search Test",
            "request": {
                "model": "gpt-4.1-nano",
                "messages": [
                    {"role": "user", "content": "What are the latest OpenAI announcements in 2025?"}
                ],
                "stream": True,
                "temperature": 0.7,
                "enable_citations": True,
                "user_id": 10001
            }
        },
        {
            "name": "Cross-Source Test",
            "request": {
                "model": "gpt-4.1-nano",
                "messages": [
                    {"role": "user", "content": "Based on my notes about startups and current web trends, what are good AI business opportunities?"}
                ],
                "stream": True,
                "temperature": 0.7,
                "enable_citations": True,
                "user_id": 10001
            }
        },
        {
            "name": "Code Interpreter Test",
            "request": {
                "model": "gpt-4.1-nano",
                "messages": [
                    {"role": "user", "content": "Calculate and plot the first 20 Fibonacci numbers"}
                ],
                "stream": True,
                "temperature": 0.7,
                "user_id": 10001
            }
        }
    ]
    
    # Run tests
    total_tests = len(test_cases)
    passed_tests = 0
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n[{i}/{total_tests}] {test_case['name']}")
        print("-" * 60)
        
        try:
            # Handle streaming response
            response = await endpoint.handle_request(test_case['request'])
            
            if hasattr(response, '__aiter__'):
                # Process streaming response
                event_count = 0
                response_text = ""
                citations_found = []
                agents_used = set()
                
                async for event in response:
                    event_count += 1
                    
                    # Collect response text
                    if event.get("type") == "response.output_text.delta":
                        response_text += event.get("delta", "")
                    
                    # Collect citations
                    elif event.get("type") == "response.output_text.annotation.added":
                        annotation = event.get("annotation", {})
                        citations_found.append(annotation)
                    
                    # Track agents
                    elif event.get("type") == "response.output_item.added":
                        item = event.get("item", {})
                        if item.get("type") == "reasoning":
                            item_id = item.get("id", "")
                            for agent in ["router", "rag", "web_search", "attachment", "code"]:
                                if agent in item_id:
                                    agents_used.add(agent)
                        elif item.get("type") == "function_call":
                            func_name = item.get("function", {}).get("name", "")
                            if "web_search" in func_name:
                                agents_used.add("web_search")
                            elif "execute_python" in func_name:
                                agents_used.add("code_interpreter")
                
                # Results summary
                print(f"✅ Response generated")
                print(f"📊 Metrics:")
                print(f"   - Response length: {len(response_text)} chars")
                print(f"   - Events: {event_count}")
                print(f"   - Agents used: {', '.join(sorted(agents_used))}")
                print(f"   - Citations: {len(citations_found)}")
                
                # Check for citation markers
                citation_pattern = re.compile(r'\[(\d+)\]')
                markers = citation_pattern.findall(response_text)
                print(f"   - Citation markers: {markers}")
                
                # Show first few citations
                if citations_found:
                    print(f"\n📍 Citation Examples:")
                    for j, cit in enumerate(citations_found[:3], 1):
                        print(f"   {j}. [{cit.get('text')}] - {cit.get('title', 'N/A')}")
                        if cit.get('metadata'):
                            print(f"      Metadata: {cit['metadata']}")
                
                # Validation
                test_passed = True
                if "RAG" in test_case['name'] and "rag" not in agents_used:
                    print("   ⚠️  Warning: Expected RAG agent but it wasn't activated")
                    test_passed = False
                elif "Web Search" in test_case['name'] and "web_search" not in agents_used:
                    print("   ⚠️  Warning: Expected web search but it wasn't activated")
                    test_passed = False
                elif test_case['request'].get('enable_citations') and len(citations_found) == 0 and ("rag" in agents_used or "web_search" in agents_used):
                    print("   ⚠️  Warning: Expected citations but found none")
                    test_passed = False
                
                if test_passed:
                    passed_tests += 1
                
            else:
                print(f"❌ Non-streaming response received")
        
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    # Final summary
    print("\n" + "="*60)
    print("📊 FINAL SUMMARY")
    print("="*60)
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")
    print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
    
    if passed_tests == total_tests:
        print("\n✅ All tests passed! The multi-agent system with citations is working correctly.")
    else:
        print("\n⚠️  Some tests failed. Review the warnings above.")
    
    print("="*60)


async def main():
    """Main entry point"""
    await test_comprehensive_citations()


if __name__ == "__main__":
    asyncio.run(main())