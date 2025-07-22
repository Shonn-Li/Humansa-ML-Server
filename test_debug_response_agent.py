#!/usr/bin/env python3
"""
Debug what the response agent receives in context
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

# Enable debug logging for response agent
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_debug():
    """Test with debug logging"""
    from chat.endpoints.multi_agent_endpoint_v2 import MultiAgentChatEndpointV2
    from chat.agent.response_agent import ResponseAgent
    
    # Monkey patch the response agent to add debug logging
    original_build_context = ResponseAgent._build_combined_context_with_sources
    
    def debug_build_context(self, context):
        logger.info("="*60)
        logger.info("RESPONSE AGENT - BUILDING CONTEXT")
        logger.info("="*60)
        logger.info(f"Context keys: {list(context.keys())}")
        
        for key in context:
            if key.endswith("_agent"):
                logger.info(f"\n{key}:")
                agent_data = context[key]
                if isinstance(agent_data, dict):
                    logger.info(f"  Status: {agent_data.get('status')}")
                    logger.info(f"  Keys: {list(agent_data.keys())}")
                    if 'sources' in agent_data:
                        logger.info(f"  Sources count: {len(agent_data['sources'])}")
                        for i, source in enumerate(agent_data['sources'][:2]):
                            logger.info(f"    Source {i}: {source.get('title', 'N/A')}")
                    if 'context' in agent_data:
                        context_preview = str(agent_data.get('context', ''))[:200]
                        logger.info(f"  Context preview: {context_preview}...")
        
        # Call original method
        result = original_build_context(self, context)
        combined_context, sources = result
        
        logger.info(f"\nCombined context length: {len(combined_context)}")
        logger.info(f"Total sources: {len(sources)}")
        logger.info("="*60)
        
        return result
    
    ResponseAgent._build_combined_context_with_sources = debug_build_context
    
    endpoint = MultiAgentChatEndpointV2()
    
    print("\n" + "="*60)
    print("DEBUG: MULTI-AGENT CONTEXT")
    print("="*60)
    
    request = {
        "model": "gpt-4.1-nano",
        "messages": [{"role": "user", "content": "Compare this paper with my notes on PARL"}],
        "attachments": ["https://arxiv.org/pdf/2505.18499.pdf"],
        "stream": True,
        "enable_citations": True,
        "user_id": 10001
    }
    
    try:
        response_text = ""
        response = await endpoint.handle_request(request)
        
        async for event in response:
            if event.get("type") == "response.output_text.delta":
                response_text += event.get("delta", "")
        
        print(f"\nResponse preview: {response_text[:300]}...")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_debug())