#!/usr/bin/env python3
"""
Validate attachment agent logging specifically
"""

import asyncio
import httpx
import json
from datetime import datetime

async def validate_attachment_logging():
    """Test attachment processing and verify logging"""
    
    print("="*80)
    print("ATTACHMENT AGENT VALIDATION TEST")
    print("="*80)
    
    client = httpx.AsyncClient(timeout=30.0)
    
    # Test 1: Non-streaming with attachment
    print("\nTest 1: Non-streaming with attachment")
    print("-"*80)
    
    request_data = {
        "messages": [{"role": "user", "content": "Analyze this document"}],
        "attachments": ["https://arxiv.org/pdf/2311.10122.pdf"],
        "user_id": 10001,
        "model": "gpt-4o-mini",
        "stream": False,
        "enable_citations": True
    }
    
    try:
        response = await client.post("http://localhost:5002/v1/multi-agent/response", json=request_data)
        result = response.json()
        
        print(f"Status Code: {response.status_code}")
        
        # Check metadata for agents
        if 'metadata' in result:
            metadata = result['metadata']
            print("\nAgent Results from Metadata:")
            
            if 'agent_results' in metadata:
                for agent_key, agent_data in metadata['agent_results'].items():
                    print(f"  - {agent_key}: {agent_data.get('status', 'unknown')}")
                    
                # Specifically check for attachment agent
                if 'attachment_agent' in metadata['agent_results']:
                    print("\n✅ ATTACHMENT AGENT FOUND IN METADATA")
                    attachment_data = metadata['agent_results']['attachment_agent']
                    print(f"   Status: {attachment_data.get('status')}")
                    print(f"   Data: {json.dumps(attachment_data.get('data', {}), indent=4)}")
                else:
                    print("\n❌ ATTACHMENT AGENT NOT FOUND IN METADATA")
                    
            print(f"\nWorkflow Time: {metadata.get('workflow_time', 'N/A')}s")
            print(f"Total Agents Used: {len(metadata.get('agent_results', {}))}")
            
        # Check response content
        if 'choices' in result and result['choices']:
            content = result['choices'][0].get('message', {}).get('content', '')
            print(f"\nResponse Length: {len(content)} chars")
            print(f"Response Preview: {content[:200]}...")
            
    except Exception as e:
        print(f"Error: {str(e)}")
        
    # Test 2: Streaming with attachment
    print("\n\nTest 2: Streaming with attachment")
    print("-"*80)
    
    request_data['stream'] = True
    agents_detected = set()
    output_items = []
    
    try:
        async with client.stream('POST', "http://localhost:5002/v1/multi-agent/response", json=request_data) as response:
            event_count = 0
            async for line in response.aiter_lines():
                if line.startswith('data: '):
                    event_data = line[6:]
                    if event_data == '[DONE]':
                        break
                        
                    try:
                        event = json.loads(event_data)
                        event_count += 1
                        event_type = event.get('type', '')
                        
                        # Track output items
                        if 'output_item.added' in event_type:
                            item = event.get('item', {})
                            item_id = item.get('id', '')
                            item_type = item.get('type', '')
                            
                            output_items.append({
                                "id": item_id,
                                "type": item_type,
                                "event": event_type
                            })
                            
                            # Detect attachment agent
                            if item_id.startswith('attachment_'):
                                agents_detected.add('attachment')
                                print(f"  ✅ ATTACHMENT OUTPUT ITEM DETECTED: {item_id}")
                                
                        # Look for attachment in other event types
                        if 'attachment' in event_type.lower():
                            print(f"  📎 Attachment event: {event_type}")
                            
                        # Check metadata in usage event
                        if event_type == 'response.usage' and 'metadata' in event:
                            metadata = event['metadata']
                            if 'agent_results' in metadata:
                                print("\n  Agents from final metadata:")
                                for agent_key in metadata['agent_results']:
                                    print(f"    - {agent_key}")
                                    if agent_key == 'attachment_agent':
                                        print("      ✅ ATTACHMENT AGENT CONFIRMED IN STREAMING")
                                        
                    except Exception as e:
                        pass
                        
        print(f"\nTotal Events: {event_count}")
        print(f"Agents Detected from Output Items: {list(agents_detected)}")
        print(f"\nOutput Items Summary:")
        for item in output_items:
            print(f"  - {item['type']}: {item['id']}")
            
    except Exception as e:
        print(f"Error: {str(e)}")
        
    # Test 3: Without attachment (for comparison)
    print("\n\nTest 3: Query WITHOUT attachment (for comparison)")
    print("-"*80)
    
    request_data = {
        "messages": [{"role": "user", "content": "What is machine learning?"}],
        "user_id": 10001,
        "model": "gpt-4o-mini",
        "stream": False,
        "enable_citations": True
    }
    
    try:
        response = await client.post("http://localhost:5002/v1/multi-agent/response", json=request_data)
        result = response.json()
        
        if 'metadata' in result:
            metadata = result['metadata']
            print("\nAgents used (no attachment):")
            if 'agent_results' in metadata:
                for agent_key in metadata['agent_results']:
                    print(f"  - {agent_key}")
                    
                if 'attachment_agent' not in metadata['agent_results']:
                    print("\n✅ CORRECT: Attachment agent NOT used when no attachments")
                else:
                    print("\n❌ ERROR: Attachment agent used without attachments!")
                    
    except Exception as e:
        print(f"Error: {str(e)}")
        
    await client.aclose()
    
    print("\n" + "="*80)
    print("VALIDATION COMPLETE")
    print("="*80)

if __name__ == "__main__":
    asyncio.run(validate_attachment_logging())