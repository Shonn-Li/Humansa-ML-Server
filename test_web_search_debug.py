#!/usr/bin/env python3
"""
Debug test for web search citations
"""

import asyncio
import sys
import os
import json

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

# Set up TEST ENVIRONMENT
os.environ['DATABASE_URL'] = 'postgresql://postgres:12931@localhost:5454/youwoai_test'
os.environ['PUBLIC_ENV'] = 'test'

# Enable more logging
import logging
logging.basicConfig(level=logging.INFO)


async def test_web_search():
    """Test web search with citations"""
    
    print("\n" + "="*60)
    print("WEB SEARCH CITATION DEBUG TEST")
    print("="*60)
    
    # Import endpoint
    from chat.endpoints.multi_agent_endpoint_v2 import MultiAgentChatEndpointV2
    endpoint = MultiAgentChatEndpointV2()
    
    request = {
        "model": "gpt-4.1-nano",
        "messages": [{"role": "user", "content": "What are the latest AI developments in 2025?"}],
        "stream": True,
        "enable_citations": True,
        "user_id": 10001
    }
    
    print("Request:", request["messages"][0]["content"])
    print("Citations enabled:", request.get("enable_citations", False))
    print("-"*60)
    
    try:
        response = await endpoint.handle_request(request)
        
        tools_used = []
        citations = []
        response_text = ""
        sources = []
        
        async for event in response:
            event_type = event.get("type", "")
            
            if event_type == "response.output_item.added":
                item = event.get("item", {})
                item_type = item.get("type")
                if item_type and item_type != "reasoning" and item_type != "message":
                    tools_used.append(item_type)
                    print(f"✅ Tool: {item_type}")
            
            elif event_type == "response.output_text.delta":
                response_text += event.get("delta", "")
            
            elif event_type == "response.output_text.annotation.added":
                annotation = event.get("annotation", {})
                citations.append(annotation)
                print(f"📍 Citation added: {annotation}")
            
            elif event_type == "annotations":
                # Check if annotations are sent separately
                anns = event.get("annotations", [])
                srcs = event.get("sources", [])
                print(f"📋 Annotations event: {len(anns)} annotations, {len(srcs)} sources")
                citations.extend(anns)
                sources.extend(srcs)
        
        print(f"\n{'='*40}")
        print(f"Tools used: {tools_used}")
        print(f"Citations found: {len(citations)}")
        print(f"Sources found: {len(sources)}")
        print(f"Response length: {len(response_text)} chars")
        
        # Check if response contains citation markers
        import re
        citation_pattern = r'\[\d+\]'
        citation_markers = re.findall(citation_pattern, response_text)
        print(f"Citation markers in text: {citation_markers}")
        
        print(f"\nResponse preview:")
        print("-"*40)
        print(response_text[:500] + ("..." if len(response_text) > 500 else ""))
        
        # Debug: Check context in response agent
        print(f"\n{'='*40}")
        print("DEBUG: Checking if web search returned results...")
        
        # Run a simple web search directly
        from chat.websearch.web_search_processor import WebSearchProcessor
        web_processor = WebSearchProcessor()
        search_result = await web_processor.search_web_content("AI developments 2025")
        print(f"Direct web search returned {len(search_result.results)} results")
        
        if not citations and search_result.results:
            print("\n❌ Web search found results but citations were not generated!")
            print("This suggests the response agent is not creating citations from web sources")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_web_search())