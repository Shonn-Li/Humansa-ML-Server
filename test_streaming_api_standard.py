#!/usr/bin/env python3
"""
YouWoAI ML Server Streaming API Standard Test Suite

This comprehensive test validates that streaming endpoints conform to the API standard.
Tests event ordering, required fields, data structures, and error handling.
"""

import asyncio
import json
import time
import logging
from typing import Dict, Any, List, Optional, AsyncGenerator
from dataclasses import dataclass
from enum import Enum

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EventType(Enum):
    """All valid event types from the API standard"""
    # Lifecycle
    RESPONSE_CREATED = "response.created"
    RESPONSE_IN_PROGRESS = "response.in_progress" 
    RESPONSE_COMPLETED = "response.completed"
    RESPONSE_FAILED = "response.failed"
    RESPONSE_INCOMPLETE = "response.incomplete"
    
    # Output Item Envelope
    OUTPUT_ITEM_ADDED = "response.output_item.added"
    OUTPUT_ITEM_DONE = "response.output_item.done"
    
    # Reasoning
    REASONING_PART_ADDED = "response.reasoning_part.added"
    REASONING_TEXT_DELTA = "response.reasoning_text.delta"
    REASONING_TEXT_DONE = "response.reasoning_text.done"
    REASONING_PART_DONE = "response.reasoning_part.done"
    
    # Web Search
    WEB_SEARCH_IN_PROGRESS = "response.web_search_call.in_progress"
    WEB_SEARCH_SEARCHING = "response.web_search_call.searching"
    WEB_SEARCH_COMPLETED = "response.web_search_call.completed"
    
    # File Search
    FILE_SEARCH_IN_PROGRESS = "response.file_search_call.in_progress"
    FILE_SEARCH_SEARCHING = "response.file_search_call.searching"
    FILE_SEARCH_COMPLETED = "response.file_search_call.completed"
    
    # Function Tools
    FUNCTION_TOOL_RESULT_DELTA = "response.function_tool_result.delta"
    FUNCTION_TOOL_RESULT_DONE = "response.function_tool_result.done"
    
    # Assistant Messages
    CONTENT_PART_ADDED = "response.content_part.added"
    OUTPUT_TEXT_DELTA = "response.output_text.delta"
    OUTPUT_TEXT_ANNOTATION_ADDED = "response.output_text.annotation.added"
    OUTPUT_TEXT_DONE = "response.output_text.done"
    CONTENT_PART_DONE = "response.content_part.done"
    
    # Custom Events
    CITATIONS = "response.citations"
    TITLE_GENERATED = "response.title_generated"
    USAGE = "response.usage"


@dataclass
class StreamingEvent:
    """Represents a single streaming event"""
    type: str
    sequence_number: int
    data: Dict[str, Any]
    timestamp: float
    
    @classmethod
    def from_dict(cls, event_dict: Dict[str, Any]) -> 'StreamingEvent':
        return cls(
            type=event_dict.get('type', ''),
            sequence_number=event_dict.get('sequence_number', -1),
            data=event_dict,
            timestamp=time.time()
        )


class StreamingValidator:
    """Validates streaming events against the API standard"""
    
    def __init__(self):
        self.events: List[StreamingEvent] = []
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.output_items: Dict[str, Dict] = {}  # Track output items by ID
        
    def add_event(self, event_dict: Dict[str, Any]) -> None:
        """Add an event for validation"""
        event = StreamingEvent.from_dict(event_dict)
        self.events.append(event)
        logger.debug(f"Added event: {event.type} (seq: {event.sequence_number})")
    
    def validate_complete_sequence(self) -> bool:
        """Validate the complete event sequence"""
        logger.info("🔍 Validating complete event sequence...")
        
        success = True
        success &= self._validate_lifecycle_events()
        success &= self._validate_sequence_numbers()
        success &= self._validate_event_types()
        success &= self._validate_required_fields()
        success &= self._validate_output_item_envelope()
        success &= self._validate_text_streaming_patterns()
        success &= self._validate_search_patterns()
        
        return success
    
    def _validate_lifecycle_events(self) -> bool:
        """Validate lifecycle events (created, in_progress, completed/failed)"""
        logger.info("🔄 Validating lifecycle events...")
        
        if not self.events:
            self.errors.append("No events found")
            return False
            
        # First event must be response.created
        first_event = self.events[0]
        if first_event.type != EventType.RESPONSE_CREATED.value:
            self.errors.append(f"First event must be 'response.created', got '{first_event.type}'")
            return False
            
        # Last event must be terminal (completed, failed, or incomplete)
        last_event = self.events[-1]
        terminal_events = [
            EventType.RESPONSE_COMPLETED.value,
            EventType.RESPONSE_FAILED.value, 
            EventType.RESPONSE_INCOMPLETE.value
        ]
        if last_event.type not in terminal_events:
            self.errors.append(f"Last event must be terminal, got '{last_event.type}'")
            return False
            
        logger.info("✅ Lifecycle events valid")
        return True
    
    def _validate_sequence_numbers(self) -> bool:
        """Validate sequence numbers are incrementing"""
        logger.info("🔢 Validating sequence numbers...")
        
        for i, event in enumerate(self.events):
            if event.sequence_number != i:
                self.errors.append(f"Sequence number mismatch at index {i}: expected {i}, got {event.sequence_number}")
                return False
                
        logger.info("✅ Sequence numbers valid")
        return True
    
    def _validate_event_types(self) -> bool:
        """Validate all event types are known"""
        logger.info("📝 Validating event types...")
        
        valid_types = {e.value for e in EventType}
        
        for event in self.events:
            if event.type not in valid_types:
                self.errors.append(f"Unknown event type: '{event.type}'")
                return False
                
        logger.info("✅ Event types valid")
        return True
    
    def _validate_required_fields(self) -> bool:
        """Validate required fields for each event type"""
        logger.info("📋 Validating required fields...")
        
        field_requirements = {
            EventType.RESPONSE_CREATED.value: ['response'],
            EventType.OUTPUT_ITEM_ADDED.value: ['output_index', 'item'],
            EventType.OUTPUT_ITEM_DONE.value: ['output_index', 'item'],
            EventType.REASONING_TEXT_DELTA.value: ['item_id', 'output_index', 'content_index', 'delta'],
            EventType.OUTPUT_TEXT_DELTA.value: ['item_id', 'output_index', 'content_index', 'delta'],
            # Add more as needed...
        }
        
        for event in self.events:
            if event.type in field_requirements:
                required_fields = field_requirements[event.type]
                for field in required_fields:
                    if field not in event.data:
                        self.errors.append(f"Event '{event.type}' missing required field: '{field}'")
                        return False
                        
        logger.info("✅ Required fields valid") 
        return True
    
    def _validate_output_item_envelope(self) -> bool:
        """Validate output item envelope pattern (added -> streaming -> done)"""
        logger.info("📦 Validating output item envelope pattern...")
        
        output_item_states = {}  # item_id -> state
        
        for event in self.events:
            if event.type == EventType.OUTPUT_ITEM_ADDED.value:
                item = event.data.get('item', {})
                item_id = item.get('id')
                if not item_id:
                    self.errors.append("output_item.added missing item.id")
                    return False
                    
                if item_id in output_item_states:
                    self.errors.append(f"Duplicate output_item.added for item: {item_id}")
                    return False
                    
                output_item_states[item_id] = 'added'
                self.output_items[item_id] = item
                
            elif event.type == EventType.OUTPUT_ITEM_DONE.value:
                item = event.data.get('item', {})
                item_id = item.get('id')
                if not item_id:
                    self.errors.append("output_item.done missing item.id")
                    return False
                    
                if item_id not in output_item_states:
                    self.errors.append(f"output_item.done without prior added for item: {item_id}")
                    return False
                    
                if output_item_states[item_id] != 'added':
                    self.errors.append(f"Invalid state transition for item {item_id}: {output_item_states[item_id]} -> done")
                    return False
                    
                output_item_states[item_id] = 'done'
                
        # Check all items were completed
        for item_id, state in output_item_states.items():
            if state != 'done':
                self.errors.append(f"Output item {item_id} not completed (state: {state})")
                return False
                
        logger.info("✅ Output item envelope pattern valid")
        return True
    
    def _validate_text_streaming_patterns(self) -> bool:
        """Validate text streaming patterns (part.added -> text.delta -> text.done -> part.done)"""
        logger.info("📝 Validating text streaming patterns...")
        
        text_states = {}  # (item_id, content_index) -> state
        
        for event in self.events:
            if event.type in [EventType.REASONING_PART_ADDED.value, EventType.CONTENT_PART_ADDED.value]:
                item_id = event.data.get('item_id')
                content_index = event.data.get('content_index', 0)
                key = (item_id, content_index)
                
                if key in text_states:
                    self.errors.append(f"Duplicate part.added for {key}")
                    return False
                    
                text_states[key] = 'part_added'
                
            elif event.type in [EventType.REASONING_TEXT_DELTA.value, EventType.OUTPUT_TEXT_DELTA.value]:
                item_id = event.data.get('item_id')
                content_index = event.data.get('content_index', 0)
                key = (item_id, content_index)
                
                if key not in text_states:
                    self.warnings.append(f"text.delta without prior part.added for {key}")
                elif text_states[key] not in ['part_added', 'streaming']:
                    self.errors.append(f"Invalid text.delta state for {key}: {text_states[key]}")
                    return False
                    
                text_states[key] = 'streaming'
                
            elif event.type in [EventType.REASONING_TEXT_DONE.value, EventType.OUTPUT_TEXT_DONE.value]:
                item_id = event.data.get('item_id')
                content_index = event.data.get('content_index', 0)
                key = (item_id, content_index)
                
                if key not in text_states:
                    self.errors.append(f"text.done without prior part.added for {key}")
                    return False
                elif text_states[key] not in ['part_added', 'streaming']:
                    self.errors.append(f"Invalid text.done state for {key}: {text_states[key]}")
                    return False
                    
                text_states[key] = 'text_done'
                
            elif event.type in [EventType.REASONING_PART_DONE.value, EventType.CONTENT_PART_DONE.value]:
                item_id = event.data.get('item_id')
                content_index = event.data.get('content_index', 0)
                key = (item_id, content_index)
                
                if key not in text_states:
                    self.errors.append(f"part.done without prior part.added for {key}")
                    return False
                elif text_states[key] != 'text_done':
                    self.errors.append(f"Invalid part.done state for {key}: {text_states[key]}")
                    return False
                    
                text_states[key] = 'part_done'
                
        logger.info("✅ Text streaming patterns valid")
        return True
    
    def _validate_search_patterns(self) -> bool:
        """Validate search patterns (in_progress -> searching -> completed)"""
        logger.info("🔍 Validating search patterns...")
        
        search_states = {}  # item_id -> state
        
        search_event_patterns = {
            'web_search': [
                EventType.WEB_SEARCH_IN_PROGRESS.value,
                EventType.WEB_SEARCH_SEARCHING.value,
                EventType.WEB_SEARCH_COMPLETED.value
            ],
            'file_search': [
                EventType.FILE_SEARCH_IN_PROGRESS.value,
                EventType.FILE_SEARCH_SEARCHING.value,
                EventType.FILE_SEARCH_COMPLETED.value
            ]
        }
        
        for event in self.events:
            item_id = event.data.get('item_id')
            if not item_id:
                continue
                
            for search_type, pattern in search_event_patterns.items():
                if event.type in pattern:
                    current_index = pattern.index(event.type)
                    
                    if item_id not in search_states:
                        if current_index != 0:
                            self.errors.append(f"Search pattern violation for {item_id}: started with {event.type}")
                            return False
                        search_states[item_id] = current_index
                    else:
                        expected_index = search_states[item_id] + 1
                        if current_index != expected_index:
                            self.errors.append(f"Search pattern violation for {item_id}: expected index {expected_index}, got {current_index}")
                            return False
                        search_states[item_id] = current_index
                        
        logger.info("✅ Search patterns valid")
        return True
    
    def get_report(self) -> Dict[str, Any]:
        """Get validation report"""
        return {
            'total_events': len(self.events),
            'errors': self.errors,
            'warnings': self.warnings,
            'output_items': list(self.output_items.keys()),
            'success': len(self.errors) == 0
        }


async def test_multi_agent_endpoint():
    """Test the multi-agent endpoint streaming"""
    logger.info("🚀 Testing Multi-Agent Endpoint Streaming")
    
    # Import the endpoint
    try:
        from chat.endpoints.multi_agent_endpoint_v2 import multi_agent_endpoint_v2
    except ImportError as e:
        logger.error(f"Failed to import multi-agent endpoint: {e}")
        return False
    
    # Create test request
    test_request = {
        "messages": [
            {"role": "user", "content": "Search for information about AI and then explain the latest developments"}
        ],
        "model": "gpt-4o-mini",
        "user_id": "test_user",
        "stream": True,
        "enable_web_search": True,
        "enable_citations": True
    }
    
    # Validate streaming response
    validator = StreamingValidator()
    
    try:
        result = await multi_agent_endpoint_v2.handle_request(test_request)
        
        if hasattr(result, '__aiter__'):
            # Streaming response
            logger.info("📡 Processing streaming response...")
            
            event_count = 0
            async for event in result:
                event_count += 1
                logger.debug(f"Event {event_count}: {event.get('type', 'unknown')}")
                validator.add_event(event)
                
                # Limit events for testing
                if event_count >= 100:
                    logger.warning("Limiting to 100 events for testing")
                    break
                    
            logger.info(f"📊 Processed {event_count} events")
            
        else:
            logger.error("Expected streaming response, got non-streaming")
            return False
            
    except Exception as e:
        logger.error(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Validate the sequence
    success = validator.validate_complete_sequence()
    report = validator.get_report()
    
    # Print report
    logger.info("📋 Validation Report:")
    logger.info(f"  Total Events: {report['total_events']}")
    logger.info(f"  Output Items: {len(report['output_items'])}")
    logger.info(f"  Errors: {len(report['errors'])}")
    logger.info(f"  Warnings: {len(report['warnings'])}")
    
    if report['errors']:
        logger.error("❌ Validation Errors:")
        for error in report['errors']:
            logger.error(f"  - {error}")
            
    if report['warnings']:
        logger.warning("⚠️ Validation Warnings:")
        for warning in report['warnings']:
            logger.warning(f"  - {warning}")
            
    if success:
        logger.info("✅ Multi-Agent Endpoint streaming validation PASSED")
    else:
        logger.error("❌ Multi-Agent Endpoint streaming validation FAILED")
        
    return success


async def test_o3_demo_endpoint():
    """Test the O3 demo endpoint streaming"""
    logger.info("🚀 Testing O3 Demo Endpoint Streaming")
    
    try:
        from humansa.endpoints.o3_demo_endpoint import handle_o3_demo_request
    except ImportError as e:
        logger.error(f"Failed to import O3 demo endpoint: {e}")
        return False
    
    test_request = {
        "messages": [
            {"role": "user", "content": "Explain quantum computing"}
        ],
        "stream": True,
        "user_id": "test_user",
        "enable_reasoning": True
    }
    
    validator = StreamingValidator()
    
    try:
        result = await handle_o3_demo_request(test_request)
        
        if hasattr(result, '__aiter__'):
            logger.info("📡 Processing O3 streaming response...")
            
            event_count = 0
            async for raw_event in result:
                event_count += 1
                
                # Parse SSE format
                if isinstance(raw_event, str) and raw_event.startswith('data: '):
                    data_str = raw_event[6:]  # Remove "data: "
                    if data_str != '[DONE]':
                        try:
                            event = json.loads(data_str)
                            validator.add_event(event)
                            logger.debug(f"Event {event_count}: {event.get('type', 'unknown')}")
                        except json.JSONDecodeError:
                            logger.warning(f"Failed to parse event: {data_str}")
                
                if event_count >= 100:
                    break
                    
            logger.info(f"📊 Processed {event_count} events")
            
        else:
            logger.error("Expected streaming response, got non-streaming")
            return False
            
    except Exception as e:
        logger.error(f"❌ O3 test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    success = validator.validate_complete_sequence()
    report = validator.get_report()
    
    logger.info("📋 O3 Validation Report:")
    logger.info(f"  Total Events: {report['total_events']}")
    logger.info(f"  Output Items: {len(report['output_items'])}")
    logger.info(f"  Errors: {len(report['errors'])}")
    logger.info(f"  Warnings: {len(report['warnings'])}")
    
    if report['errors']:
        logger.error("❌ O3 Validation Errors:")
        for error in report['errors']:
            logger.error(f"  - {error}")
            
    if success:
        logger.info("✅ O3 Demo Endpoint streaming validation PASSED")
    else:
        logger.error("❌ O3 Demo Endpoint streaming validation FAILED")
        
    return success


async def main():
    """Run all streaming tests"""
    logger.info("🧪 YouWoAI ML Server Streaming API Standard Test Suite")
    logger.info("=" * 60)
    
    results = []
    
    # Test Multi-Agent Endpoint
    logger.info("\n" + "=" * 60)
    multi_agent_success = await test_multi_agent_endpoint()
    results.append(("Multi-Agent Endpoint", multi_agent_success))
    
    # Test O3 Demo Endpoint
    logger.info("\n" + "=" * 60)
    o3_success = await test_o3_demo_endpoint()
    results.append(("O3 Demo Endpoint", o3_success))
    
    # Final Report
    logger.info("\n" + "=" * 60)
    logger.info("🏁 Final Test Results:")
    logger.info("=" * 60)
    
    all_passed = True
    for name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        logger.info(f"  {name}: {status}")
        all_passed &= success
    
    if all_passed:
        logger.info("\n🎉 ALL TESTS PASSED - Streaming API Standard Compliant!")
    else:
        logger.error("\n💥 SOME TESTS FAILED - Review implementation!")
        
    return all_passed


if __name__ == "__main__":
    asyncio.run(main())