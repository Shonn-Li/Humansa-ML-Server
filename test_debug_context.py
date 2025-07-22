#!/usr/bin/env python3
"""
Debug test to see what's in the context for multi-agent queries
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
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class DebugResponseAgent:
    """Debug version of response agent that shows what's in context"""
    
    async def run(self, request, context):
        logger.info("=== DEBUG RESPONSE AGENT ===")
        logger.info(f"Context keys: {list(context.keys())}")
        
        # Check each agent's result
        for key in context:
            if key.endswith("_agent"):
                logger.info(f"\n{key}:")
                agent_data = context[key]
                if isinstance(agent_data, dict):
                    logger.info(f"  Status: {agent_data.get('status')}")
                    logger.info(f"  Keys: {list(agent_data.keys())}")
                    if 'sources' in agent_data:
                        logger.info(f"  Sources count: {len(agent_data['sources'])}")
                    if 'context' in agent_data:
                        logger.info(f"  Context length: {len(agent_data.get('context', ''))}")
                    if 'results' in agent_data:
                        logger.info(f"  Results count: {len(agent_data['results'])}")
        
        # Call original response agent
        from chat.agent.response_agent import ResponseAgent
        response_agent = ResponseAgent(
            self.llm_provider_manager,
            self.system_prompt_manager,
            self.citation_engine
        )
        return await response_agent.run(request, context)


async def test_debug():
    """Test with debug logging"""
    
    print("\n" + "="*60)
    print("DEBUG CONTEXT TEST")
    print("="*60)
    
    # Monkey patch the response agent to debug
    from chat.endpoints.multi_agent_endpoint_v2 import MultiAgentChatEndpointV2
    endpoint = MultiAgentChatEndpointV2()
    
    # Store original response agent
    original_response_agent = endpoint.agents["response"]
    
    # Create debug response agent
    debug_agent = DebugResponseAgent()
    debug_agent.llm_provider_manager = original_response_agent.llm_provider_manager
    debug_agent.system_prompt_manager = original_response_agent.system_prompt_manager
    debug_agent.citation_engine = original_response_agent.citation_engine
    
    # Replace with debug version
    endpoint.agents["response"] = debug_agent
    
    # Test multi-agent query
    request = {
        "model": "gpt-4.1-nano",
        "messages": [{"role": "user", "content": "Compare this paper with my notes on PARL"}],
        "attachments": ["https://arxiv.org/pdf/2505.18499.pdf"],
        "stream": True,
        "enable_citations": True,
        "user_id": 10001
    }
    
    print("Running multi-agent query...")
    print("-" * 60)
    
    try:
        response = await endpoint.handle_request(request)
        
        response_text = ""
        async for event in response:
            if event.get("type") == "response.output_text.delta":
                response_text += event.get("delta", "")
        
        print(f"\nResponse: {response_text[:200]}...")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_debug())