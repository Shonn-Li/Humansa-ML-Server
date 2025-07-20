#!/usr/bin/env python3
"""
Debug why attachment agent isn't triggering
"""

import asyncio
import httpx
import json

async def debug_attachment_routing():
    """Test attachment routing with detailed logging"""
    
    test_cases = [
        {
            "name": "PDF with explicit attachment query",
            "query": "Analyze this attached PDF document",
            "attachments": ["https://arxiv.org/pdf/2505.18499.pdf"]
        },
        {
            "name": "Image with explicit query",
            "query": "What's in this attached image?",
            "attachments": ["https://arxiv.org/html/2407.09124v1/x1.png"]
        },
        {
            "name": "Attachment without keyword",
            "query": "Summarize this",
            "attachments": ["https://arxiv.org/pdf/2505.18499.pdf"]
        }
    ]
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for test in test_cases:
            print(f"\n{'='*60}")
            print(f"TEST: {test['name']}")
            print(f"QUERY: {test['query']}")
            print(f"ATTACHMENTS: {test['attachments']}")
            print("-"*60)
            
            request_data = {
                "messages": [{"role": "user", "content": test['query']}],
                "user_id": 10001,
                "model": "gpt-4o-mini",
                "stream": True,
                "enable_citations": True,
                "attachments": test['attachments']
            }
            
            # Track what happens
            router_reasoning = ""
            enabled_agents = []
            agent_events = []
            
            async with client.stream('POST', 'http://localhost:5001/v1/multi-agent/response', json=request_data) as response:
                async for line in response.aiter_lines():
                    if line.startswith('data: '):
                        event_data = line[6:]
                        if event_data == '[DONE]':
                            break
                        try:
                            event = json.loads(event_data)
                            
                            # Capture router reasoning
                            if event.get('type') == 'response.reasoning_text.done':
                                text = event.get('text', '')
                                if 'routed to agents:' in text:
                                    router_reasoning = text
                                    # Extract agents from reasoning
                                    agents_part = text.split('routed to agents:')[1].strip()
                                    enabled_agents = [a.strip() for a in agents_part.split(',')]
                            
                            # Track agent-related events
                            event_type = event.get('type', '')
                            if any(agent in event_type for agent in ['attachment', 'file_search', 'web_search', 'function_tool']):
                                agent_events.append(event_type)
                                
                        except: pass
            
            print(f"\nROUTER REASONING: {router_reasoning}")
            print(f"ENABLED AGENTS (from reasoning): {enabled_agents}")
            print(f"AGENT EVENTS SEEN: {list(set(agent_events))}")
            
            # Check if attachment agent should have been enabled
            if test['attachments']:
                if 'attachment' not in enabled_agents:
                    print("\n⚠️ ISSUE: Attachments present but attachment agent not enabled!")
                    print("   Router should detect attachments from request, not just query text")
                else:
                    print("\n✅ Attachment agent correctly enabled")

if __name__ == "__main__":
    asyncio.run(debug_attachment_routing())