#!/usr/bin/env python3
"""
Debug agent routing and triggering
"""

import asyncio
import httpx
import json
from typing import Dict, List

TEST_CASES = [
    {
        "name": "RAG Test - Note Query",
        "query": "What is in my note about PARL paper?",
        "attachments": [],
        "expected": ["router", "rag", "response", "citation"]
    },
    {
        "name": "Web Search Test",
        "query": "What are the latest AI news today in 2024?",
        "attachments": [],
        "expected": ["router", "web_search", "response", "citation"]
    },
    {
        "name": "Code Interpreter Test",
        "query": "Write python code to calculate fibonacci sequence",
        "attachments": [],
        "expected": ["router", "code_interpreter", "response", "citation"]
    },
    {
        "name": "Attachment Test",
        "query": "Analyze this PDF document",
        "attachments": ["https://arxiv.org/pdf/2505.18499.pdf"],
        "expected": ["router", "attachment", "response", "citation"]
    }
]

async def debug_single_query(test_case: Dict):
    """Debug a single query to see how router makes decisions"""
    print(f"\n{'='*80}")
    print(f"TEST: {test_case['name']}")
    print(f"QUERY: {test_case['query']}")
    if test_case['attachments']:
        print(f"ATTACHMENTS: {test_case['attachments']}")
    print(f"EXPECTED AGENTS: {test_case['expected']}")
    print("-" * 80)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        request_data = {
            "messages": [{"role": "user", "content": test_case['query']}],
            "user_id": 10001,
            "model": "gpt-4.1-nano",
            "stream": True,
            "enable_citations": True,
            "attachments": test_case['attachments']
        }
        
        # Collect all events
        events = []
        agents_detected = []
        router_reasoning = ""
        final_response = ""
        
        try:
            async with client.stream('POST', 'http://localhost:5001/v1/multi-agent/response', json=request_data) as response:
                async for line in response.aiter_lines():
                    if line.startswith('data: '):
                        event_data = line[6:]
                        if event_data == '[DONE]':
                            break
                        try:
                            event = json.loads(event_data)
                            events.append(event)
                            
                            # Extract router reasoning
                            if event.get('type') == 'response.reasoning_text.done':
                                router_reasoning = event.get('text', '')
                                
                            # Extract final response
                            if event.get('type') == 'response.output_text.delta':
                                final_response += event.get('delta', '')
                                
                        except json.JSONDecodeError:
                            pass
            
            # Analyze events to detect agents
            for event in events:
                event_type = event.get('type', '')
                
                # Router detection
                if 'reasoning' in event_type:
                    if 'router' not in agents_detected:
                        agents_detected.append('router')
                
                # RAG detection
                if 'file_search' in event_type:
                    if 'rag' not in agents_detected:
                        agents_detected.append('rag')
                
                # Web search detection
                if 'web_search' in event_type:
                    if 'web_search' not in agents_detected:
                        agents_detected.append('web_search')
                
                # Attachment detection
                if 'attachment' in event_type.lower():
                    if 'attachment' not in agents_detected:
                        agents_detected.append('attachment')
                
                # Code interpreter detection
                if 'function_tool' in event_type or 'code' in event_type.lower():
                    if 'code_interpreter' not in agents_detected:
                        agents_detected.append('code_interpreter')
                
                # Response detection
                if 'output_text' in event_type:
                    if 'response' not in agents_detected:
                        agents_detected.append('response')
                
                # Citation detection
                if 'citation' in event_type:
                    if 'citation' not in agents_detected:
                        agents_detected.append('citation')
            
            # Print results
            print(f"\nROUTER REASONING: {router_reasoning}")
            print(f"\nAGENTS DETECTED: {agents_detected}")
            print(f"\nMISSING AGENTS: {set(test_case['expected']) - set(agents_detected)}")
            print(f"\nEVENT TYPES SEEN:")
            event_types = list(set(e.get('type', 'unknown') for e in events))
            for et in sorted(event_types):
                print(f"  - {et}")
            
            print(f"\nRESPONSE LENGTH: {len(final_response)} chars")
            if final_response:
                print(f"RESPONSE PREVIEW: {final_response[:200]}...")
            else:
                print("RESPONSE: No response generated")
                
        except Exception as e:
            print(f"\nERROR: {str(e)}")
            import traceback
            traceback.print_exc()

async def main():
    print("DEBUGGING AGENT ROUTING AND TRIGGERING")
    print("=====================================")
    
    for test_case in TEST_CASES:
        await debug_single_query(test_case)
        await asyncio.sleep(1)  # Avoid rate limiting
    
    print(f"\n{'='*80}")
    print("DEBUGGING COMPLETE")

if __name__ == "__main__":
    asyncio.run(main())