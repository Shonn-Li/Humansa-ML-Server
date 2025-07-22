#!/usr/bin/env python3
"""
Debug citation agent functionality
"""

import asyncio
import httpx
import json
import logging

# Set up logging to see what's happening
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def test_citation_flow():
    """Test citation agent with detailed tracking"""
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Test cases specifically designed to trigger citations
        test_cases = [
            {
                "name": "Simple RAG with Citation",
                "query": "What does my PARL paper say about reinforcement learning? Please cite sources.",
                "stream": False  # Non-streaming first to see full response
            },
            {
                "name": "Web Search with Citation",
                "query": "What are the latest AI developments in 2024? Include citations.",
                "stream": False
            },
            {
                "name": "Mixed Sources Citation",
                "query": "Compare information from my notes with current research. Provide citations for all claims.",
                "stream": True
            }
        ]
        
        for test in test_cases:
            print(f"\n{'='*80}")
            print(f"TEST: {test['name']}")
            print(f"Query: {test['query']}")
            print(f"Stream: {test['stream']}")
            print("-"*80)
            
            request_data = {
                "messages": [{"role": "user", "content": test['query']}],
                "user_id": 10001,
                "model": "gpt-4.1-nano",
                "stream": test['stream'],
                "enable_citations": True
            }
            
            if test['stream']:
                # Streaming request
                citation_events = []
                response_text = ""
                all_events = []
                
                async with client.stream('POST', 'http://localhost:5001/v1/multi-agent/response', json=request_data) as response:
                    async for line in response.aiter_lines():
                        if line.startswith('data: '):
                            event_data = line[6:]
                            if event_data == '[DONE]':
                                break
                            try:
                                event = json.loads(event_data)
                                event_type = event.get('type', '')
                                all_events.append(event_type)
                                
                                # Track citation-related events
                                if 'citation' in event_type.lower():
                                    citation_events.append(event)
                                    print(f"Citation event: {event_type}")
                                    if 'citations' in event:
                                        print(f"Citations data: {json.dumps(event['citations'], indent=2)}")
                                
                                # Collect response
                                if event_type == 'response.output_text.delta':
                                    response_text += event.get('delta', '')
                                    
                            except Exception as e:
                                print(f"Error parsing event: {e}")
                
                print(f"\nAll event types seen: {sorted(set(all_events))}")
                print(f"Citation events count: {len(citation_events)}")
                print(f"Response length: {len(response_text)} chars")
                
                # Check if citations are in the response text
                if '[' in response_text and ']' in response_text:
                    print("✅ Response contains citation markers")
                else:
                    print("❌ No citation markers found in response")
                    
            else:
                # Non-streaming request
                response = await client.post(
                    'http://localhost:5001/v1/multi-agent/response',
                    json=request_data
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Check for citations in metadata
                    metadata = data.get('metadata', {})
                    agent_results = metadata.get('agent_results', {})
                    
                    print(f"\nAgent results keys: {list(agent_results.keys())}")
                    
                    # Check citation agent specifically
                    if 'citation_agent' in agent_results:
                        citation_agent = agent_results['citation_agent']
                        print(f"\nCitation agent status: {citation_agent.get('status')}")
                        citation_data = citation_agent.get('data', {})
                        citations = citation_data.get('citations', {})
                        print(f"Citation sources: {citations.get('sources', [])}")
                        
                        # Check if response was modified with citations
                        original_response = agent_results.get('response_agent', {}).get('data', {}).get('response', '')
                        cited_response = citations.get('response', '')
                        
                        if cited_response and cited_response != original_response:
                            print("✅ Citation agent modified the response")
                        else:
                            print("❌ Citation agent did not modify the response")
                    else:
                        print("❌ Citation agent not found in results")
                    
                    # Check final response
                    if 'choices' in data and data['choices']:
                        content = data['choices'][0].get('message', {}).get('content', '')
                        if '[' in content and ']' in content:
                            print("✅ Final response contains citation markers")
                        else:
                            print("❌ No citation markers in final response")
                            
                else:
                    print(f"Error: Status {response.status_code}")

async def check_citation_initialization():
    """Check if citation engine is properly initialized"""
    print("\n\nChecking Citation Engine Initialization...")
    
    # This would need to be done on the server side, but we can check via API
    async with httpx.AsyncClient() as client:
        # Make a simple health check request
        response = await client.get("http://localhost:5001/health")
        if response.status_code == 200:
            print("✅ ML Server is running")
        else:
            print("❌ ML Server not responding")

if __name__ == "__main__":
    asyncio.run(test_citation_flow())
    asyncio.run(check_citation_initialization())