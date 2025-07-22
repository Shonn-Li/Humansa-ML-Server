#!/usr/bin/env python3
"""
Validate citation annotations follow OpenAI Response API format
"""

import asyncio
import httpx
import json
import re
from typing import Dict, List, Tuple

async def validate_citation_annotations():
    """Validate citation formatting in streaming mode"""
    
    client = httpx.AsyncClient(timeout=30.0)
    
    request = {
        "messages": [{"role": "user", "content": "What is machine learning? Explain with proper citations."}],
        "user_id": 10001,
        "model": "gpt-4.1-nano",
        "stream": True,
        "enable_citations": True
    }
    
    print("="*80)
    print("CITATION ANNOTATION VALIDATION")
    print("="*80)
    print("Testing OpenAI Response API annotation format for citations...")
    print("-"*80)
    
    # Track events
    message_content = ""
    annotations = []
    citation_events = []
    message_id = None
    
    try:
        async with client.stream('POST', 'http://localhost:5002/v1/multi-agent/response', json=request) as response:
            event_num = 0
            
            async for line in response.aiter_lines():
                if line.startswith('data: '):
                    event_data = line[6:]
                    if event_data == '[DONE]':
                        break
                        
                    try:
                        event = json.loads(event_data)
                        event_num += 1
                        event_type = event.get('type', '')
                        
                        # Track message content
                        if event_type == 'response.output_text.delta':
                            message_content += event.get('delta', '')
                            
                        # Track message ID
                        if 'output_item.added' in event_type:
                            item = event.get('item', {})
                            if item.get('type') == 'message':
                                message_id = item.get('id')
                                
                        # Track citation-related events
                        if 'citation' in event_type.lower() or 'annotation' in event_type.lower():
                            citation_events.append({
                                "event_num": event_num,
                                "type": event_type,
                                "event": event
                            })
                            
                        # Track annotations
                        if event_type == 'response.output_text.annotation.added':
                            annotation = event.get('annotation', {})
                            annotations.append(annotation)
                            
                            # Print annotation details
                            print(f"\n📌 Annotation Event #{event_num}:")
                            print(f"  Type: {annotation.get('type', 'unknown')}")
                            print(f"  Start Index: {annotation.get('start_index', 'N/A')}")
                            print(f"  End Index: {annotation.get('end_index', 'N/A')}")
                            print(f"  Title: {annotation.get('title', 'N/A')}")
                            print(f"  URL: {annotation.get('url', 'N/A')}")
                            
                    except json.JSONDecodeError:
                        pass
                        
        print(f"\n\nTotal events processed: {event_num}")
        print(f"Message length: {len(message_content)} characters")
        print(f"Citation events found: {len(citation_events)}")
        print(f"Annotations found: {len(annotations)}")
        
        # Analyze content for citation markers
        citation_markers = re.findall(r'\[(\d+)\]', message_content)
        print(f"\nCitation markers in text: {citation_markers}")
        
        # Validate annotations
        print("\n" + "-"*80)
        print("VALIDATION RESULTS:")
        print("-"*80)
        
        validations = []
        
        # Check if we have annotations
        if annotations:
            validations.append(("✅", f"Found {len(annotations)} annotations"))
            
            # Validate annotation format
            for i, ann in enumerate(annotations, 1):
                print(f"\nAnnotation {i} Validation:")
                
                # Check required fields
                required_fields = ['type', 'start_index', 'end_index']
                for field in required_fields:
                    if field in ann:
                        validations.append(("✅", f"  Has required field: {field}"))
                    else:
                        validations.append(("❌", f"  Missing required field: {field}"))
                        
                # Validate indices
                if 'start_index' in ann and 'end_index' in ann:
                    start = ann['start_index']
                    end = ann['end_index']
                    
                    if isinstance(start, int) and isinstance(end, int):
                        if 0 <= start < len(message_content) and start < end <= len(message_content):
                            # Extract the text at this position
                            cited_text = message_content[start:end]
                            validations.append(("✅", f"  Valid indices: '{cited_text}'"))
                        else:
                            validations.append(("❌", f"  Invalid indices: {start}-{end} (content length: {len(message_content)}"))
                    else:
                        validations.append(("❌", f"  Indices not integers: start={start}, end={end}"))
                        
                # Check annotation type
                if ann.get('type') == 'url_citation':
                    validations.append(("✅", "  Correct annotation type: url_citation"))
                else:
                    validations.append(("⚠️", f"  Unexpected annotation type: {ann.get('type')}"))
                    
        else:
            validations.append(("❌", "No annotations found"))
            
            # Check if we have citation events that might indicate a different format
            if citation_events:
                print("\n⚠️  Found citation events but no annotations. Events:")
                for evt in citation_events[:5]:  # Show first 5
                    print(f"  - {evt['type']}")
                    
        # Print validation summary
        print("\n" + "-"*80)
        print("SUMMARY:")
        print("-"*80)
        
        for status, msg in validations:
            print(f"{status} {msg}")
            
        # Expected annotation format example
        print("\n" + "-"*80)
        print("EXPECTED ANNOTATION FORMAT:")
        print("-"*80)
        print("""
{
  "type": "response.output_text.annotation.added",
  "item_id": "msg_xxxxx",
  "output_index": 0,
  "content_index": 0,
  "annotation": {
    "type": "url_citation",
    "start_index": 245,    // Position where [1] appears
    "end_index": 248,      // End position of [1]
    "title": "Machine Learning - Wikipedia",
    "url": "https://en.wikipedia.org/wiki/Machine_learning"
  }
}
""")
        
        # Show actual content preview with markers
        if citation_markers:
            print("\nContent Preview (first occurrence of citations):")
            print("-"*80)
            
            # Find first citation
            first_match = re.search(r'\[\d+\]', message_content)
            if first_match:
                start = max(0, first_match.start() - 50)
                end = min(len(message_content), first_match.end() + 50)
                preview = message_content[start:end]
                print(f"...{preview}...")
                print(f"Citation at position: {first_match.start()}-{first_match.end()}")
                
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        
    await client.aclose()
    
    print("\n" + "="*80)

if __name__ == "__main__":
    asyncio.run(validate_citation_annotations())