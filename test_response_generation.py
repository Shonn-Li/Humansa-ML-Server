#!/usr/bin/env python3
"""
Debug why responses aren't using retrieved context
"""

import asyncio
import json
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

# Set up TEST ENVIRONMENT
os.environ['DATABASE_URL'] = 'postgresql://postgres:12931@localhost:5454/youwoai_test'
os.environ['PUBLIC_ENV'] = 'test'

# Enable debug logging
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_response_generation():
    """Test response generation with debug"""
    from chat.endpoints.multi_agent_endpoint_v2 import MultiAgentChatEndpointV2
    from chat.agent.response_agent import ResponseAgent
    
    # Monkey patch to add debug logging
    original_prepare_messages = ResponseAgent._prepare_messages
    
    def debug_prepare_messages(self, request, combined_context, sources, enable_citations):
        logger.info("="*60)
        logger.info("PREPARING MESSAGES FOR RESPONSE")
        logger.info("="*60)
        logger.info(f"Combined context length: {len(combined_context)}")
        logger.info(f"Sources count: {len(sources)}")
        logger.info(f"Enable citations: {enable_citations}")
        logger.info(f"\nContext preview (first 500 chars):")
        logger.info(combined_context[:500] + "..." if len(combined_context) > 500 else combined_context)
        
        # Call original
        messages = original_prepare_messages(self, request, combined_context, sources, enable_citations)
        
        logger.info(f"\nTotal messages: {len(messages)}")
        for i, msg in enumerate(messages):
            logger.info(f"\nMessage {i}:")
            logger.info(f"  Role: {msg.role}")
            logger.info(f"  Content length: {len(msg.content)}")
            if msg.role == "system" and i == 1:  # Context message
                logger.info(f"  Content preview: {msg.content[:300]}...")
        
        return messages
    
    ResponseAgent._prepare_messages = debug_prepare_messages
    
    endpoint = MultiAgentChatEndpointV2()
    
    print("\n" + "="*80)
    print("TESTING RESPONSE GENERATION")
    print("="*80)
    
    request = {
        "model": "gpt-4.1-nano",
        "messages": [{"role": "user", "content": "What do my notes say about PARL?"}],
        "stream": True,
        "enable_citations": True,
        "user_id": 10001
    }
    
    try:
        response_text = ""
        tool_calls = []
        
        response = await endpoint.handle_request(request)
        
        async for event in response:
            event_type = event.get("type", "")
            
            if event_type == "response.output_item.added":
                item = event.get("item", {})
                if item.get("type", "").endswith("_call"):
                    tool_calls.append(item.get("type"))
                    print(f"✓ Tool triggered: {item.get('type')}")
            
            elif event_type == "response.output_text.delta":
                response_text += event.get("delta", "")
        
        print(f"\nTools used: {', '.join(tool_calls)}")
        print(f"\nResponse:")
        print("-" * 60)
        print(response_text[:500] + "..." if len(response_text) > 500 else response_text)
        print("-" * 60)
        
        # Check if response uses context
        if "PARL" in response_text or "Predictability" in response_text:
            print("\n✅ Response uses retrieved context!")
        else:
            print("\n❌ Response doesn't use retrieved context")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*80)


if __name__ == "__main__":
    asyncio.run(test_response_generation())