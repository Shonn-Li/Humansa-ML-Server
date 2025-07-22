#!/usr/bin/env python3
"""
Simple test for multi-agent streaming endpoint
"""

import asyncio
import json
import logging
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_multi_agent_streaming():
    """Test the multi-agent endpoint streaming implementation"""
    logger.info("🚀 Testing Multi-Agent Streaming Implementation")
    
    try:
        # Import the endpoint
        from chat.endpoints.multi_agent_endpoint_v2 import MultiAgentChatEndpointV2
        
        # Create endpoint instance
        endpoint = MultiAgentChatEndpointV2()
        
        # Create test request
        test_request = {
            "messages": [
                {"role": "user", "content": "Search for AI developments and explain them"}
            ],
            "model": "gpt-4.1-nano",
            "user_id": "test_user_123",
            "stream": True,
            "enable_web_search": True,
            "enable_citations": True,
            "attachments": [
                {"type": "image", "url": "test.jpg", "filename": "test.jpg"}
            ]
        }
        
        logger.info("📝 Test request created")
        
        # Test streaming
        result = await endpoint.handle_request(test_request)
        
        if not hasattr(result, '__aiter__'):
            logger.error("❌ Expected streaming response, got non-streaming")
            return False
        
        # Collect and validate events
        events = []
        event_types = set()
        
        logger.info("📡 Processing streaming events...")
        
        async for event in result:
            events.append(event)
            event_type = event.get('type', 'unknown')
            event_types.add(event_type)
            
            logger.info(f"Event {len(events)}: {event_type}")
            
            # Log details for important events
            if event_type in ['response.output_item.added', 'response.output_item.done']:
                item = event.get('item', {})
                logger.info(f"  Item: {item.get('type', 'unknown')} ({item.get('id', 'no-id')})")
            elif 'delta' in event:
                delta = event.get('delta', '')
                logger.info(f"  Delta: {delta[:50]}...")
            
            # Limit events for testing
            if len(events) >= 50:
                logger.warning("⚠️ Limiting to 50 events for testing")
                break
        
        logger.info(f"📊 Collected {len(events)} events")
        logger.info(f"📋 Event types: {sorted(event_types)}")
        
        # Basic validation
        success = True
        
        # Check lifecycle events
        if not events:
            logger.error("❌ No events received")
            success = False
        elif events[0].get('type') != 'response.created':
            logger.error(f"❌ First event should be 'response.created', got '{events[0].get('type')}'")
            success = False
        elif events[-1].get('type') not in ['response.completed', 'response.failed']:
            logger.error(f"❌ Last event should be terminal, got '{events[-1].get('type')}'")
            success = False
        
        # Check for required event types
        required_events = [
            'response.created',
            'response.in_progress', 
            'response.output_item.added',
            'response.output_item.done',
            'response.completed'
        ]
        
        missing_events = []
        for required_event in required_events:
            if required_event not in event_types:
                missing_events.append(required_event)
        
        if missing_events:
            logger.error(f"❌ Missing required events: {missing_events}")
            success = False
        
        # Check for expected multi-agent events
        expected_events = [
            'response.reasoning_text.delta',
            'response.web_search_call.in_progress',
            'response.file_search_call.searching',
            'response.function_tool_result.delta',
            'response.output_text.delta'
        ]
        
        found_expected = []
        for expected_event in expected_events:
            if expected_event in event_types:
                found_expected.append(expected_event)
        
        logger.info(f"✅ Found expected multi-agent events: {found_expected}")
        
        # Check sequence numbers
        for i, event in enumerate(events):
            expected_seq = i
            actual_seq = event.get('sequence_number', -1)
            if actual_seq != expected_seq:
                logger.error(f"❌ Sequence number mismatch at index {i}: expected {expected_seq}, got {actual_seq}")
                success = False
                break
        
        if success:
            logger.info("✅ Multi-Agent Streaming Test PASSED")
            logger.info(f"   Total Events: {len(events)}")
            logger.info(f"   Event Types: {len(event_types)}")
            logger.info(f"   Expected Events Found: {len(found_expected)}/{len(expected_events)}")
        else:
            logger.error("❌ Multi-Agent Streaming Test FAILED")
        
        return success
        
    except Exception as e:
        logger.error(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run the test"""
    logger.info("🧪 Multi-Agent Streaming API Test")
    logger.info("=" * 50)
    
    success = await test_multi_agent_streaming()
    
    logger.info("=" * 50)
    if success:
        logger.info("🎉 TEST PASSED!")
    else:
        logger.error("💥 TEST FAILED!")
    
    return success


if __name__ == "__main__":
    asyncio.run(main())