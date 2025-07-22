#!/usr/bin/env python3
"""
Test agent detection in streaming responses
"""

import httpx
import asyncio
import json

async def test_streaming():
    async with httpx.AsyncClient() as client:
        request_data = {
            'messages': [{'role': 'user', 'content': 'What notes do I have about reinforcement learning?'}],
            'user_id': 10001,
            'model': 'gpt-4.1-nano',
            'stream': True
        }
        
        events = []
        async with client.stream('POST', 'http://localhost:5001/v1/multi-agent/response', json=request_data) as response:
            async for line in response.aiter_lines():
                if line.startswith('data: '):
                    event_data = line[6:]
                    if event_data != '[DONE]':
                        try:
                            event = json.loads(event_data)
                            events.append(event)
                            if event.get('type') == 'response.reasoning_text.done':
                                print('Reasoning:', event.get('text', ''))
                        except: pass
        
        print('\nAgent detection analysis:')
        agents_triggered = []
        
        # Look for agent information in different event types
        for event in events:
            event_str = json.dumps(event)
            
            # Check reasoning text for agent mentions
            if event.get('type') == 'response.reasoning_text.done':
                text = event.get('text', '')
                if 'routed to agents:' in text:
                    # Extract agents from reasoning text
                    agents_part = text.split('routed to agents:')[1].strip()
                    agents = [a.strip() for a in agents_part.split(',')]
                    agents_triggered.extend(agents)
                    print(f"Agents from reasoning: {agents}")
            
            # Check for specific event types
            if 'web_search' in event.get('type', ''):
                if 'web_search' not in agents_triggered:
                    agents_triggered.append('web_search')
            
            if 'file_search' in event.get('type', ''):
                if 'rag' not in agents_triggered:
                    agents_triggered.append('rag')
        
        print(f"\nTotal agents detected: {agents_triggered}")
        print(f"\nAll event types:")
        event_types = list(set(e.get('type', 'unknown') for e in events))
        for et in sorted(event_types):
            print(f"  - {et}")

asyncio.run(test_streaming())